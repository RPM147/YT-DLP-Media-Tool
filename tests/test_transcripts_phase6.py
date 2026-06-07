from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.transcripts import TranscriptRequest, TranscriptService
from core.transcripts import io as transcript_io
from core.transcripts.io import build_md_content, build_txt_content


CHANNEL_NAME = "Phase 6 Channel"
CHANNEL_SLUG = "phase-6-channel"
VIDEO_URL = "https://www.youtube.com/watch?v=vid1"


def write_existing_transcript(
    base_dir: Path,
    *,
    basename: str = "001_original-title",
    video_id: str = "vid1",
    title: str = "Original Title",
    include_txt: bool = True,
    include_md: bool = True,
) -> None:
    txt_dir = base_dir / "txt"
    md_dir = base_dir / "md"
    txt_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    if include_txt:
        (txt_dir / f"{basename}.txt").write_text(
            build_txt_content("Existing transcript"),
            encoding="utf-8",
        )
    if include_md:
        (md_dir / f"{basename}.md").write_text(
            build_md_content(
                title=title,
                url=VIDEO_URL,
                upload_date="2026-06-06",
                channel=CHANNEL_NAME,
                video_id=video_id,
                transcript="Existing transcript",
            ),
            encoding="utf-8",
        )


def list_single_video(title: str = "Original Title") -> tuple[str, list[dict[str, Any]]]:
    return (
        CHANNEL_NAME,
        [
            {
                "id": "vid1",
                "title": title,
                "url": VIDEO_URL,
                "upload_date": "20260606",
            }
        ],
    )


def fetch_metadata(title: str = "Original Title") -> dict[str, Any]:
    return {
        "id": "vid1",
        "title": title,
        "channel": CHANNEL_NAME,
        "upload_date": "20260606",
        "subtitles": {"en": [{"ext": "vtt"}]},
        "automatic_captions": {},
    }


def download_subtitle(
    _video_url: str,
    video_id: str,
    lang: str,
    _sub_type: str,
    out_dir: Path,
) -> Path:
    sub_path = out_dir / f"{video_id}.{lang}.vtt"
    sub_path.write_text(
        """WEBVTT

00:00:01.000 --> 00:00:02.000
Fresh transcript
""",
        encoding="utf-8",
    )
    return sub_path


def make_service(
    *,
    listed_title: str = "Original Title",
    metadata_title: str = "Original Title",
) -> TranscriptService:
    return TranscriptService(
        list_videos=lambda _url: list_single_video(listed_title),
        fetch_metadata=lambda _url: fetch_metadata(metadata_title),
        download_subtitle=download_subtitle,
        sleeper=lambda _delay: None,
    )


def test_existing_pair_skips_by_video_id_even_when_title_changes(tmp_path: Path):
    base_dir = tmp_path / CHANNEL_SLUG
    write_existing_transcript(base_dir)

    def fail_fetch_metadata(_url: str) -> dict[str, Any]:
        raise AssertionError("metadata should not be fetched for an existing transcript pair")

    service = TranscriptService(
        list_videos=lambda _url: list_single_video("Changed Title"),
        fetch_metadata=fail_fetch_metadata,
        download_subtitle=download_subtitle,
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            delay=0,
        )
    )

    assert report["processed_count"] == 0
    assert report["existing_count"] == 1
    assert report["skipped"][0]["reason"] == "already_exists"
    assert report["skipped"][0]["basename"] == "001_original-title"
    assert (base_dir / "md" / "001_original-title.md").exists()
    assert not (base_dir / "md" / "001_changed-title.md").exists()


def test_partial_md_only_is_repaired_by_video_id_and_keeps_existing_basename(tmp_path: Path):
    base_dir = tmp_path / CHANNEL_SLUG
    write_existing_transcript(base_dir, include_txt=False, include_md=True)

    service = make_service(
        listed_title="Changed Title",
        metadata_title="Changed Title",
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            delay=0,
        )
    )

    assert report["processed_count"] == 1
    assert report["partial_repaired_count"] == 1
    assert report["processed"][0]["partial_repaired"] is True
    assert report["processed"][0]["basename"] == "001_original-title"
    assert (base_dir / "txt" / "001_original-title.txt").read_text(encoding="utf-8") == (
        "Fresh transcript\n"
    )
    assert (base_dir / "md" / "001_original-title.md").exists()
    assert not (base_dir / "md" / "001_changed-title.md").exists()


def test_partial_txt_only_is_repaired_when_proposed_pair_is_missing(tmp_path: Path):
    base_dir = tmp_path / CHANNEL_SLUG
    write_existing_transcript(
        base_dir,
        basename="001_original-title",
        include_txt=True,
        include_md=False,
    )

    service = make_service()

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            delay=0,
        )
    )

    assert report["processed_count"] == 1
    assert report["partial_repaired_count"] == 1
    assert report["processed"][0]["partial_repaired"] is True
    assert report["processed"][0]["basename"] == "001_original-title"
    assert (base_dir / "txt" / "001_original-title.txt").exists()
    assert (base_dir / "md" / "001_original-title.md").exists()


def test_output_layout_reports_and_tmp_files_after_success(tmp_path: Path):
    service = make_service()

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            delay=0,
        )
    )

    base_dir = tmp_path / CHANNEL_SLUG
    assert report["processed_count"] == 1
    assert (base_dir / "txt").is_dir()
    assert (base_dir / "md").is_dir()
    assert (base_dir / "reports").is_dir()
    assert (base_dir / "report.json").exists()
    assert (base_dir / "last_run_report.json").exists()
    assert (base_dir / "cumulative_report.json").exists()
    assert (base_dir / "index.md").exists()
    assert (base_dir / "reports" / "report_001_001.json").exists()
    assert list(base_dir.rglob("*.tmp")) == []

    cumulative = json.loads((base_dir / "cumulative_report.json").read_text(encoding="utf-8"))
    assert cumulative["completed_count"] == 1
    assert cumulative["completed"][0]["basename"] == "001_original-title"


def test_dry_run_reports_existing_and_partial_work_without_writing_reports(tmp_path: Path):
    base_dir = tmp_path / CHANNEL_SLUG
    write_existing_transcript(base_dir, include_txt=False, include_md=True)
    service = make_service()

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            dry_run=True,
            delay=0,
        )
    )

    assert report["dry_run"] is True
    assert report["would_repair_partial_count"] == 1
    assert report["would_write_files"] is False
    assert not (base_dir / "report.json").exists()
    assert not (base_dir / "reports").exists()


def test_atomic_write_failure_leaves_existing_file_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    base_dir = tmp_path / CHANNEL_SLUG
    write_existing_transcript(base_dir)
    txt_path = base_dir / "txt" / "001_original-title.txt"
    before = txt_path.read_text(encoding="utf-8")

    service = make_service()
    original_replace = transcript_io.os.replace

    def fail_txt_replace(source: Path | str, target: Path | str) -> None:
        if target == txt_path:
            raise OSError("simulated replace failure")
        original_replace(source, target)

    monkeypatch.setattr(transcript_io.os, "replace", fail_txt_replace)

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@phase6",
            output_dir=tmp_path,
            languages=("en",),
            force=True,
            delay=0,
        )
    )

    assert report["processed_count"] == 0
    assert report["error_count"] == 1
    assert txt_path.read_text(encoding="utf-8") == before
