"""Qt-independent transcript processing service."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from core.transcripts import io
from core.transcripts.models import (
    DependencyError,
    DownloadSubtitleFn,
    FetchMetadataFn,
    ListVideosFn,
    CookieLockedError,
    SubtitleType,
    TranscriptCancelledError,
    TranscriptCallbacks,
    TranscriptProcessedItem,
    TranscriptProgress,
    TranscriptRequest,
    TranscriptSkippedItem,
    TranscriptVideo,
    UserError,
)
from core.transcripts.subtitle_parser import (
    parse_subtitle_file,
    pick_subtitle,
    subtitle_skip_reason,
)
from core.transcripts.ytdlp_adapter import YtDlpTranscriptAdapter


class TranscriptService:
    """Single public entry point for transcript archiving.

    Phase 2 keeps real yt-dlp network operations injectable. Phase 5 will wire
    the default yt-dlp-backed implementations into this service.
    """

    def __init__(
        self,
        *,
        list_videos: ListVideosFn | None = None,
        fetch_metadata: FetchMetadataFn | None = None,
        download_subtitle: DownloadSubtitleFn | None = None,
        cookie_browser: str | None = None,
        cookie_browser_profile: str | None = None,
        cookie_file: str | Path | None = None,
        ytdlp_module: Any | None = None,
        sleeper: Any = time.sleep,
    ):
        self._list_videos = list_videos or self._default_list_videos
        self._fetch_metadata = fetch_metadata or self._default_fetch_metadata
        self._download_subtitle = download_subtitle or self._default_download_subtitle
        self._cookie_browser = cookie_browser
        self._cookie_browser_profile = cookie_browser_profile
        self._cookie_file = cookie_file
        self._ytdlp_module = ytdlp_module
        self._adapter: YtDlpTranscriptAdapter | None = None
        self._sleep = sleeper

    def process(
        self,
        request: TranscriptRequest,
        callbacks: TranscriptCallbacks | None = None,
    ) -> dict[str, Any]:
        """Process a transcript request and return the same report shape the UI will use."""

        callbacks = callbacks or TranscriptCallbacks()
        self._validate_request(request)
        self._ensure_list_videos()

        channel_name, all_videos = self._list_videos(request.url)  # type: ignore[misc]
        total_channel_videos = len(all_videos)
        if total_channel_videos == 0:
            raise UserError("No videos found for the provided URL.")

        selected_video_rows = io.select_videos(
            all_videos,
            request.max_videos,
            request.start_index,
            request.end_index,
        )
        selected_videos = [
            TranscriptVideo.from_entry(index, video)
            for index, video in selected_video_rows
        ]
        run_videos = len(selected_videos)
        if run_videos == 0:
            raise UserError("The selected range contains no videos.")

        channel_slug = io.slugify(channel_name)
        base_dir = request.output_dir / channel_slug

        if request.metadata_only:
            return self._process_metadata_only(
                request=request,
                channel_name=channel_name,
                total_channel_videos=total_channel_videos,
                selected_videos=selected_videos,
                base_dir=base_dir,
            )

        txt_dir = base_dir / "txt"
        md_dir = base_dir / "md"
        progress_path = base_dir / "progress.json"
        report_path = base_dir / "report.json"
        last_run_report_path = base_dir / "last_run_report.json"
        cumulative_report_path = base_dir / "cumulative_report.json"
        reports_dir = base_dir / "reports"
        index_path = base_dir / "index.md"

        if not request.dry_run:
            txt_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            reports_dir.mkdir(parents=True, exist_ok=True)

        processed: list[TranscriptProcessedItem] = []
        skipped: list[TranscriptSkippedItem] = []
        planned: list[dict[str, Any]] = []
        used_basenames: set[str] = set()
        existing_by_id = io.build_existing_files_index(md_dir, txt_dir)
        existing_by_index = (
            io.build_existing_txt_index(md_dir, txt_dir)
            if request.output_format == "txt"
            else {}
        )
        run_started_at = io.utc_now()
        last_global_index: int | None = None
        would_process_count = 0
        would_skip_existing_count = 0
        would_repair_partial_count = 0

        for position, video in enumerate(selected_videos, start=1):
            self._raise_if_cancelled(callbacks)

            global_index = video.index
            last_global_index = global_index
            video_id = video.video_id
            title = video.title
            video_url = video.url

            proposed_basename = io.make_basename(global_index, title, video_id, used_basenames)
            proposed_txt_path = txt_dir / f"{proposed_basename}.txt"
            proposed_md_path = md_dir / f"{proposed_basename}.md"

            action, txt_path, md_path, basename, partial_repair = io.resolve_video_action(
                video_id,
                proposed_basename,
                proposed_txt_path,
                proposed_md_path,
                existing_by_id,
                request.force,
                output_format=request.output_format,
                global_index=global_index,
                existing_by_index=existing_by_index,
            )

            if request.dry_run:
                plan = self._record_dry_run_plan(
                    action=action,
                    global_index=global_index,
                    video_id=video_id,
                    title=title,
                    video_url=video_url,
                    basename=basename,
                    force=request.force,
                    planned=planned,
                )
                if plan == "skip":
                    would_skip_existing_count += 1
                elif plan == "repair":
                    would_repair_partial_count += 1
                else:
                    would_process_count += 1
                self._emit(callbacks, position, run_videos, global_index, video_id, title, plan, plan)
                continue

            if action == "skip":
                skip_fields = io.transcript_file_fields(
                    request.output_format, txt_path, md_path, base_dir
                )
                skipped.append(
                    TranscriptSkippedItem(
                        index=global_index,
                        video_id=video_id,
                        title=title,
                        url=video_url,
                        reason="already_exists",
                        basename=basename,
                        txt_file=skip_fields.get("txt_file"),
                        md_file=skip_fields.get("md_file"),
                    )
                )
                self._emit(
                    callbacks,
                    position,
                    run_videos,
                    global_index,
                    video_id,
                    title,
                    "skip",
                    "already exists",
                )
                self._maybe_save_progress(
                    progress_path,
                    request,
                    channel_name,
                    total_channel_videos,
                    run_videos,
                    position,
                    processed,
                    skipped,
                    last_global_index,
                    run_started_at,
                )
                self._sleep_if_needed(request.delay, callbacks)
                continue

            self._ensure_video_operations()
            on_error = False
            try:
                metadata = io.retry_call(
                    lambda: self._fetch_metadata(video_url),  # type: ignore[misc]
                    attempts=request.retries,
                    delay=request.retry_delay,
                    action="Fetching video metadata",
                    sleeper=lambda delay: self._sleep_if_needed(delay, callbacks),
                )
                upload_date = io.format_upload_date(
                    metadata.get("upload_date") or video.upload_date
                )
                resolved_title = metadata.get("title") or title
                resolved_channel = metadata.get("channel") or metadata.get("uploader") or channel_name

                lang, sub_type = pick_subtitle(
                    metadata.get("subtitles") or {},
                    metadata.get("automatic_captions") or {},
                    languages=tuple(request.languages),
                    manual_only=request.manual_only,
                    auto_fallback=request.auto_fallback,
                )
                if not lang or not sub_type:
                    skipped.append(
                        TranscriptSkippedItem(
                            index=global_index,
                            video_id=video_id,
                            title=resolved_title,
                            url=video_url,
                            reason=subtitle_skip_reason(
                                request.manual_only,
                                tuple(request.languages),
                            ),
                        )
                    )
                    self._emit(
                        callbacks,
                        position,
                        run_videos,
                        global_index,
                        video_id,
                        resolved_title,
                        "skip",
                        "no subtitles",
                    )
                    self._maybe_save_progress(
                        progress_path,
                        request,
                        channel_name,
                        total_channel_videos,
                        run_videos,
                        position,
                        processed,
                        skipped,
                        last_global_index,
                        run_started_at,
                    )
                    self._sleep_if_needed(request.delay, callbacks)
                    continue

                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    sub_path = io.retry_call(
                        lambda: self._download_subtitle(  # type: ignore[misc]
                            video_url,
                            video_id,
                            lang,
                            sub_type,
                            tmp_path,
                        ),
                        attempts=request.retries,
                        delay=request.retry_delay,
                        action="Downloading subtitles",
                        sleeper=lambda delay: self._sleep_if_needed(delay, callbacks),
                    )
                    transcript = (
                        parse_subtitle_file(
                            sub_path,
                            keep_cues=request.keep_cues,
                            timestamps=request.timestamps,
                        )
                        if sub_path
                        else ""
                    )

                if not sub_path or not transcript.strip():
                    skipped.append(
                        TranscriptSkippedItem(
                            index=global_index,
                            video_id=video_id,
                            title=resolved_title,
                            url=video_url,
                            reason="empty_transcript"
                            if sub_path
                            else "subtitle_download_failed",
                        )
                    )
                    self._emit(
                        callbacks,
                        position,
                        run_videos,
                        global_index,
                        video_id,
                        resolved_title,
                        "skip",
                        "empty transcript",
                    )
                    self._maybe_save_progress(
                        progress_path,
                        request,
                        channel_name,
                        total_channel_videos,
                        run_videos,
                        position,
                        processed,
                        skipped,
                        last_global_index,
                        run_started_at,
                    )
                    self._sleep_if_needed(request.delay, callbacks)
                    continue

                if request.output_format in ("both", "txt"):
                    io.atomic_write_text(txt_path, io.build_txt_content(transcript))
                if request.output_format in ("both", "md"):
                    io.atomic_write_text(
                        md_path,
                        io.build_md_content(
                            title=resolved_title,
                            url=video_url,
                            upload_date=upload_date,
                            channel=resolved_channel,
                            video_id=video_id,
                            transcript=transcript,
                            timestamps=request.timestamps,
                        ),
                    )

                file_fields = io.transcript_file_fields(
                    request.output_format, txt_path, md_path, base_dir
                )
                processed_entry = TranscriptProcessedItem(
                    index=global_index,
                    video_id=video_id,
                    title=resolved_title,
                    url=video_url,
                    upload_date=upload_date,
                    basename=basename,
                    subtitle_lang=lang,
                    subtitle_type=sub_type,
                    txt_file=file_fields.get("txt_file"),
                    md_file=file_fields.get("md_file"),
                    partial_repaired=partial_repair,
                )
                processed.append(processed_entry)
                existing_by_id[video_id] = {
                    "video_id": video_id,
                    "basename": basename,
                    "txt_path": txt_path,
                    "md_path": md_path,
                    "index": global_index,
                    "title": resolved_title,
                }
                self._emit(
                    callbacks,
                    position,
                    run_videos,
                    global_index,
                    video_id,
                    resolved_title,
                    "saved",
                    f"{sub_type}, {lang}",
                )
            except (CookieLockedError, TranscriptCancelledError):
                raise
            except Exception as exc:
                on_error = True
                skipped.append(
                    TranscriptSkippedItem(
                        index=global_index,
                        video_id=video_id,
                        title=title,
                        url=video_url,
                        reason="error",
                        error=str(exc),
                    )
                )
                self._emit(
                    callbacks,
                    position,
                    run_videos,
                    global_index,
                    video_id,
                    title,
                    "error",
                    str(exc),
                )

            self._maybe_save_progress(
                progress_path,
                request,
                channel_name,
                total_channel_videos,
                run_videos,
                position,
                processed,
                skipped,
                last_global_index,
                run_started_at,
                on_error=on_error,
            )
            self._sleep_if_needed(request.delay, callbacks)

        if request.dry_run:
            report = {
                "dry_run": True,
                "channel_url": request.url,
                "channel_name": channel_name,
                "run_videos": run_videos,
                "start_index": request.start_index,
                "end_index": request.end_index,
                "max_videos": request.max_videos,
                "forced": request.force,
                "keep_cues": request.keep_cues,
                "manual_only": request.manual_only,
                "would_process_count": would_process_count,
                "would_skip_existing_count": would_skip_existing_count,
                "would_repair_partial_count": would_repair_partial_count,
                "would_write_files": False,
                "run_started_at": run_started_at,
                "run_finished_at": io.utc_now(),
                "output_path": str(base_dir),
                "planned": planned,
            }
            report.update(request.report_fields())
            return io.enrich_report_fields(report, total_channel_videos)

        report = self._build_final_report(
            request,
            channel_name,
            total_channel_videos,
            run_videos,
            base_dir,
            report_path,
            last_run_report_path,
            cumulative_report_path,
            progress_path,
            index_path,
            reports_dir,
            processed,
            skipped,
            run_started_at,
        )
        return report

    @staticmethod
    def _validate_request(request: TranscriptRequest) -> None:
        if not request.url.strip():
            raise UserError("URL is required.")
        if request.output_format not in ("both", "txt", "md"):
            raise UserError("output_format must be one of: both, txt, md.")
        if request.progress_interval < 1:
            raise UserError("progress_interval must be at least 1.")
        if not request.languages:
            raise UserError("At least one transcript language is required.")
        if request.max_videos is not None and request.max_videos <= 0:
            raise UserError("max_videos must be a positive integer.")
        if request.max_videos is not None and (
            request.start_index is not None or request.end_index is not None
        ):
            raise UserError("max_videos cannot be combined with start_index/end_index.")
        if request.start_index is not None and request.start_index <= 0:
            raise UserError("start_index must be a positive integer.")
        if request.end_index is not None and request.end_index <= 0:
            raise UserError("end_index must be a positive integer.")
        if (
            request.start_index is not None
            and request.end_index is not None
            and request.end_index < request.start_index
        ):
            raise UserError("end_index must be greater than or equal to start_index.")
        if request.delay < 0:
            raise UserError("delay must not be negative.")
        if request.retries < 1:
            raise UserError("retries must be at least 1.")
        if request.retry_delay < 0:
            raise UserError("retry_delay must not be negative.")

    def _ensure_list_videos(self) -> None:
        if self._list_videos is None:
            raise DependencyError("TranscriptService requires a list_videos implementation.")

    def _ensure_video_operations(self) -> None:
        if self._fetch_metadata is None:
            raise DependencyError("TranscriptService requires a fetch_metadata implementation.")
        if self._download_subtitle is None:
            raise DependencyError("TranscriptService requires a download_subtitle implementation.")

    def _get_adapter(self) -> YtDlpTranscriptAdapter:
        if self._adapter is None:
            self._adapter = YtDlpTranscriptAdapter(
                cookie_browser=self._cookie_browser,
                cookie_browser_profile=self._cookie_browser_profile,
                cookie_file=self._cookie_file,
                ytdlp_module=self._ytdlp_module,
            )
        return self._adapter

    def _default_list_videos(self, url: str) -> tuple[str, list[dict[str, Any]]]:
        return self._get_adapter().list_videos(url)

    def _default_fetch_metadata(self, video_url: str) -> dict[str, Any]:
        return self._get_adapter().fetch_metadata(video_url)

    def _default_download_subtitle(
        self,
        video_url: str,
        video_id: str,
        lang: str,
        sub_type: SubtitleType,
        out_dir: Path,
    ) -> Path | None:
        return self._get_adapter().download_subtitle(video_url, video_id, lang, sub_type, out_dir)

    @staticmethod
    def _record_dry_run_plan(
        *,
        action: str,
        global_index: int,
        video_id: str,
        title: str,
        video_url: str,
        basename: str,
        force: bool,
        planned: list[dict[str, Any]],
    ) -> str:
        if action == "skip":
            planned.append(
                {
                    "index": global_index,
                    "id": video_id,
                    "title": title,
                    "url": video_url,
                    "action": "skip",
                    "reason": "already_exists",
                    "basename": basename,
                }
            )
            return "skip"
        if action == "repair":
            planned.append(
                {
                    "index": global_index,
                    "id": video_id,
                    "title": title,
                    "url": video_url,
                    "action": "repair",
                    "basename": basename,
                }
            )
            return "repair"

        planned.append(
            {
                "index": global_index,
                "id": video_id,
                "title": title,
                "url": video_url,
                "action": "process",
                "basename": basename,
                "forced": force,
            }
        )
        return "process"

    @staticmethod
    def _process_metadata_only(
        *,
        request: TranscriptRequest,
        channel_name: str,
        total_channel_videos: int,
        selected_videos: list[TranscriptVideo],
        base_dir: Path,
    ) -> dict[str, Any]:
        selected_count = len(selected_videos)
        metadata_videos = io.build_metadata_videos_list(selected_videos)
        generated_at = io.utc_now()
        videos_json_path = base_dir / "videos.json"
        videos_csv_path = base_dir / "videos.csv"

        payload = io.build_metadata_payload(
            channel_url=request.url,
            channel_name=channel_name,
            total_channel_videos=total_channel_videos,
            selected_count=selected_count,
            start_index=request.start_index,
            end_index=request.end_index,
            max_videos=request.max_videos,
            videos=metadata_videos,
            generated_at=generated_at,
        )

        report: dict[str, Any] = {
            "metadata_only": True,
            "dry_run": request.dry_run,
            "channel_url": request.url,
            "channel_name": channel_name,
            "total_channel_videos": total_channel_videos,
            "total_videos": total_channel_videos,
            "selected_count": selected_count,
            "start_index": request.start_index,
            "end_index": request.end_index,
            "max_videos": request.max_videos,
            "generated_at": generated_at,
            "output_path": str(base_dir),
            "videos_json_path": str(videos_json_path),
            "videos_csv_path": str(videos_csv_path),
            "videos": metadata_videos,
            "would_write_metadata_files": not request.dry_run,
        }
        report.update(request.report_fields())

        if not request.dry_run:
            base_dir.mkdir(parents=True, exist_ok=True)
            io.write_videos_json(videos_json_path, payload)
            io.write_videos_csv(videos_csv_path, metadata_videos)

        return report

    @staticmethod
    def _emit(
        callbacks: TranscriptCallbacks,
        index: int,
        total: int,
        global_index: int,
        video_id: str,
        title: str,
        action: str,
        message: str,
    ) -> None:
        if callbacks.on_progress:
            callbacks.on_progress(
                TranscriptProgress(
                    index=index,
                    total=total,
                    global_index=global_index,
                    video_id=video_id,
                    title=title,
                    action=action,
                    message=message,
                )
            )
        if callbacks.on_log:
            callbacks.on_log(f"[{index}/{total}] #{global_index} {title}: {message}")

    @staticmethod
    def _raise_if_cancelled(callbacks: TranscriptCallbacks) -> None:
        if callbacks.should_cancel and callbacks.should_cancel():
            raise TranscriptCancelledError()

    def _sleep_if_needed(
        self,
        delay: float,
        callbacks: TranscriptCallbacks | None = None,
    ) -> None:
        if callbacks:
            self._raise_if_cancelled(callbacks)
        if delay <= 0:
            return

        remaining = delay
        while remaining > 0:
            step = min(remaining, 0.1)
            self._sleep(step)
            remaining -= step
            if callbacks:
                self._raise_if_cancelled(callbacks)

    @staticmethod
    def _maybe_save_progress(
        progress_path: Path,
        request: TranscriptRequest,
        channel_name: str,
        total_channel_videos: int,
        run_videos: int,
        position: int,
        processed: list[TranscriptProcessedItem],
        skipped: list[TranscriptSkippedItem],
        last_global_index: int | None,
        run_started_at: str,
        *,
        on_error: bool = False,
    ) -> None:
        if not io.should_write_progress(
            position,
            request.progress_interval,
            is_last=position == run_videos,
            on_error=on_error,
        ):
            return

        processed_rows = [item.to_dict() for item in processed]
        skipped_rows = [item.to_dict() for item in skipped]
        io.save_progress(
            progress_path,
            channel_url=request.url,
            channel_name=channel_name,
            total_channel_videos=total_channel_videos,
            run_videos=run_videos,
            start_index=request.start_index,
            end_index=request.end_index,
            max_videos=request.max_videos,
            force=request.force,
            manual_only=request.manual_only,
            retries=request.retries,
            processed=processed_rows,
            skipped=skipped_rows,
            last_global_index=last_global_index,
            run_started_at=run_started_at,
            auto_fallback=request.auto_fallback,
            languages=list(request.languages),
            keep_cues=request.keep_cues,
            output_format=request.output_format,
            timestamps=request.timestamps,
            metadata_only=request.metadata_only,
            progress_interval=request.progress_interval,
        )

    @staticmethod
    def _build_final_report(
        request: TranscriptRequest,
        channel_name: str,
        total_channel_videos: int,
        run_videos: int,
        base_dir: Path,
        report_path: Path,
        last_run_report_path: Path,
        cumulative_report_path: Path,
        progress_path: Path,
        index_path: Path,
        reports_dir: Path,
        processed: list[TranscriptProcessedItem],
        skipped: list[TranscriptSkippedItem],
        run_started_at: str,
    ) -> dict[str, Any]:
        processed_rows = [item.to_dict() for item in processed]
        skipped_rows = [item.to_dict() for item in skipped]
        skip_counts = io.count_skip_reasons(skipped_rows)
        partial_repaired_count = io.count_partial_repaired(processed_rows)
        chunk_report_path = reports_dir / io.run_report_filename(
            request.start_index,
            request.end_index,
            request.max_videos,
            total_channel_videos,
        )

        report = {
            "channel_url": request.url,
            "channel_name": channel_name,
            "run_videos": run_videos,
            "start_index": request.start_index,
            "end_index": request.end_index,
            "max_videos": request.max_videos,
            "processed_count": len(processed),
            "skipped_count": len(skipped),
            "existing_count": skip_counts["existing_count"],
            "partial_repaired_count": partial_repaired_count,
            "error_count": skip_counts["error_count"],
            "other_skipped_count": skip_counts["other_skipped_count"],
            "forced": request.force,
            "keep_cues": request.keep_cues,
            "manual_only": request.manual_only,
            "retries": request.retries,
            "progress_interval": request.progress_interval,
            "run_started_at": run_started_at,
            "run_finished_at": io.utc_now(),
            "output_path": str(base_dir),
            "report_path": str(report_path),
            "last_run_report_path": str(last_run_report_path),
            "cumulative_report_path": str(cumulative_report_path),
            "progress_path": str(progress_path),
            "index_path": str(index_path),
            "chunk_report_path": str(chunk_report_path.relative_to(base_dir)),
            "processed": processed_rows,
            "skipped": skipped_rows,
        }
        report.update(request.report_fields())
        io.enrich_report_fields(report, total_channel_videos)

        io.atomic_write_json(chunk_report_path, report)
        io.atomic_write_json(last_run_report_path, report)
        io.atomic_write_json(report_path, report)

        cumulative_report = io.build_cumulative_report(
            base_dir=base_dir,
            channel_url=request.url,
            channel_name=channel_name,
            total_channel_videos=total_channel_videos,
            md_dir=base_dir / "md",
            txt_dir=base_dir / "txt",
            reports_dir=reports_dir,
            output_format=request.output_format,
            timestamps=request.timestamps,
        )
        io.atomic_write_json(cumulative_report_path, cumulative_report)
        io.write_index_md(
            index_path,
            channel_name,
            io.collect_index_items_from_disk(
                base_dir / "md", base_dir / "txt", request.output_format
            ),
            request.output_format,
        )
        return report
