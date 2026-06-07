"""yt-dlp-backed transcript operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.transcripts import io
from core.transcripts.models import CookieLockedError, DependencyError, SubtitleType
from core.transcripts.subtitle_parser import find_subtitle_file

try:
    import yt_dlp
except ImportError as exc:
    yt_dlp = None  # type: ignore[assignment]
    _YT_DLP_IMPORT_ERROR = exc
else:
    _YT_DLP_IMPORT_ERROR = None


class YtDlpTranscriptAdapter:
    """Centralized yt-dlp operations for transcript archiving."""

    def __init__(
        self,
        *,
        cookie_browser: str | None = None,
        cookie_browser_profile: str | None = None,
        cookie_file: str | os.PathLike[str] | None = None,
        ytdlp_module: Any | None = None,
    ):
        self.cookie_browser = cookie_browser
        self.cookie_browser_profile = cookie_browser_profile
        self.cookie_file = Path(cookie_file) if cookie_file else None
        self._yt_dlp = ytdlp_module

    def list_videos(self, url: str) -> tuple[str, list[dict[str, Any]]]:
        normalized_url = io.normalize_channel_url(url)
        opts = self._opts(
            {
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
        )
        info = self._extract_info(normalized_url, opts, download=False)

        channel_name = info.get("channel") or info.get("uploader") or info.get("title") or "channel"
        entries = info.get("entries")

        videos: list[dict[str, Any]] = []
        if entries:
            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get("id")
                if not video_id:
                    continue
                videos.append(
                    {
                        "id": video_id,
                        "title": entry.get("title") or video_id,
                        "url": io.resolve_video_url(entry, video_id),
                        "upload_date": entry.get("upload_date"),
                    }
                )
        elif info.get("id"):
            video_id = info["id"]
            videos.append(
                {
                    "id": video_id,
                    "title": info.get("title") or video_id,
                    "url": io.resolve_video_url(info, video_id),
                    "upload_date": info.get("upload_date"),
                }
            )
            channel_name = info.get("channel") or info.get("uploader") or channel_name

        return channel_name, videos

    def fetch_metadata(self, video_url: str) -> dict[str, Any]:
        opts = self._opts({"skip_download": True})
        return self._extract_info(video_url, opts, download=False)

    def download_subtitle(
        self,
        video_url: str,
        video_id: str,
        lang: str,
        sub_type: SubtitleType,
        out_dir: Path,
    ) -> Path | None:
        if sub_type == "manual":
            sub_opts = {
                "writesubtitles": True,
                "writeautomaticsub": False,
                "subtitleslangs": [lang],
            }
        else:
            sub_opts = {
                "writesubtitles": False,
                "writeautomaticsub": True,
                "subtitleslangs": [lang],
            }

        opts = self._opts(
            {
                "noprogress": True,
                "skip_download": True,
                "subtitlesformat": "vtt/best",
                "outtmpl": str(out_dir / "%(id)s"),
                **sub_opts,
            }
        )
        self._download([video_url], opts)
        return find_subtitle_file(out_dir, video_id, lang)

    def _opts(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        if extra:
            opts.update(extra)
        self._apply_cookie_opts(opts)
        return opts

    def _apply_cookie_opts(self, opts: dict[str, Any]) -> None:
        if self.cookie_browser:
            if self.cookie_browser_profile:
                opts["cookiesfrombrowser"] = (
                    self.cookie_browser,
                    self.cookie_browser_profile,
                    None,
                    None,
                )
            else:
                opts["cookiesfrombrowser"] = (self.cookie_browser,)
        elif self.cookie_file and self.cookie_file.is_file():
            opts["cookiefile"] = str(self.cookie_file)

    def _extract_info(self, url: str, opts: dict[str, Any], *, download: bool) -> dict[str, Any]:
        ytdlp = self._require_ytdlp()
        try:
            with ytdlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as exc:
            self._raise_mapped_error(exc)

    def _download(self, urls: list[str], opts: dict[str, Any]) -> None:
        ytdlp = self._require_ytdlp()
        try:
            with ytdlp.YoutubeDL(opts) as ydl:
                ydl.download(urls)
        except Exception as exc:
            self._raise_mapped_error(exc)

    def _require_ytdlp(self) -> Any:
        module = self._yt_dlp if self._yt_dlp is not None else yt_dlp
        if module is None:
            raise DependencyError(
                "yt-dlp is not installed or could not be imported. Install it with: pip install yt-dlp"
            ) from _YT_DLP_IMPORT_ERROR
        return module

    @staticmethod
    def _raise_mapped_error(exc: Exception) -> None:
        text = str(exc)
        if "Could not copy" in text and "cookie" in text.lower():
            raise CookieLockedError() from exc
        raise exc
