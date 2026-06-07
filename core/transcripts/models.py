"""Data contracts for transcript processing."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

SubtitleType = Literal["manual", "auto"]
VideoAction = Literal["skip", "repair", "process"]
OutputFormat = Literal["both", "txt", "md"]
DEFAULT_TRANSCRIPT_LANGUAGES = ("en", "en-US", "en-GB", "en-orig")
DEFAULT_TRANSCRIPT_OUTPUT_FORMAT: OutputFormat = "both"
DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL = 10


class UserError(Exception):
    """User-facing error with a clear message."""


class DependencyError(UserError):
    """Missing or unwired runtime dependency."""


class RetryError(UserError):
    """Operation failed after all retry attempts."""


class CookieLockedError(UserError):
    """Browser cookie database is locked by the browser."""

    def __init__(self) -> None:
        super().__init__("COOKIE_DB_LOCKED")


class TranscriptCancelledError(UserError):
    """Transcript job was cancelled by the caller."""

    def __init__(self) -> None:
        super().__init__("Transcript processing cancelled.")


@dataclass(frozen=True)
class TranscriptRequest:
    """Inputs for one transcript archiving job."""

    url: str
    output_dir: Path
    _: KW_ONLY
    languages: Sequence[str] = DEFAULT_TRANSCRIPT_LANGUAGES
    manual_only: bool = False
    auto_fallback: bool = True
    keep_cues: bool = False
    dry_run: bool = False
    force: bool = False
    delay: float = 0.5
    max_videos: int | None = None
    start_index: int | None = None
    end_index: int | None = None
    retries: int = 3
    retry_delay: float = 2.0
    output_format: OutputFormat = DEFAULT_TRANSCRIPT_OUTPUT_FORMAT
    timestamps: bool = False
    metadata_only: bool = False
    progress_interval: int = DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        languages = tuple(lang.strip() for lang in self.languages if lang.strip())
        object.__setattr__(self, "languages", languages)

    def report_fields(self) -> dict[str, Any]:
        return {
            "languages": list(self.languages),
            "manual_only": self.manual_only,
            "auto_fallback": self.auto_fallback,
            "keep_cues": self.keep_cues,
            "dry_run": self.dry_run,
            "forced": self.force,
            "retries": self.retries,
            "output_format": self.output_format,
            "timestamps": self.timestamps,
            "metadata_only": self.metadata_only,
            "progress_interval": self.progress_interval,
        }


@dataclass(frozen=True)
class TranscriptVideo:
    """A selected video row normalized for transcript processing."""

    index: int
    video_id: str
    title: str
    url: str
    upload_date: str | None = None

    @classmethod
    def from_entry(cls, index: int, entry: dict[str, Any]) -> "TranscriptVideo":
        video_id = entry.get("id") or ""
        return cls(
            index=index,
            video_id=video_id,
            title=entry.get("title") or video_id or "untitled",
            url=entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
            upload_date=entry.get("upload_date"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "id": self.video_id,
            "title": self.title,
            "url": self.url,
            "upload_date": self.upload_date,
        }


@dataclass(frozen=True)
class TranscriptProcessedItem:
    """One successfully written transcript entry."""

    index: int
    video_id: str
    title: str
    url: str
    upload_date: str
    basename: str
    subtitle_lang: str
    subtitle_type: str
    txt_file: str | None = None
    md_file: str | None = None
    partial_repaired: bool = False

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "index": self.index,
            "id": self.video_id,
            "title": self.title,
            "url": self.url,
            "upload_date": self.upload_date,
            "basename": self.basename,
            "subtitle_lang": self.subtitle_lang,
            "subtitle_type": self.subtitle_type,
        }
        if self.txt_file is not None:
            item["txt_file"] = self.txt_file
        if self.md_file is not None:
            item["md_file"] = self.md_file
        if self.partial_repaired:
            item["partial_repaired"] = True
        return item


@dataclass(frozen=True)
class TranscriptSkippedItem:
    """One skipped transcript entry."""

    index: int
    video_id: str
    title: str
    url: str
    reason: str
    error: str | None = None
    basename: str | None = None
    txt_file: str | None = None
    md_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "index": self.index,
            "id": self.video_id,
            "title": self.title,
            "url": self.url,
            "reason": self.reason,
        }
        for key, value in {
            "error": self.error,
            "basename": self.basename,
            "txt_file": self.txt_file,
            "md_file": self.md_file,
        }.items():
            if value is not None:
                item[key] = value
        return item


@dataclass(frozen=True)
class TranscriptResult:
    """Typed wrapper around the JSON-compatible transcript report."""

    report: dict[str, Any]

    @classmethod
    def from_report(cls, report: dict[str, Any]) -> "TranscriptResult":
        return cls(report=report)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.report)


@dataclass(frozen=True)
class TranscriptProgress:
    """Progress event emitted by the service without any Qt dependency."""

    index: int
    total: int
    global_index: int
    video_id: str
    title: str
    action: str
    message: str


@dataclass(frozen=True)
class TranscriptCallbacks:
    """Optional callbacks used by UI workers or tests."""

    on_progress: Callable[[TranscriptProgress], None] | None = None
    on_log: Callable[[str], None] | None = None
    should_cancel: Callable[[], bool] | None = None


ListVideosFn = Callable[[str], tuple[str, list[dict[str, Any]]]]
FetchMetadataFn = Callable[[str], dict[str, Any]]
DownloadSubtitleFn = Callable[[str, str, str, SubtitleType, Path], Path | None]
