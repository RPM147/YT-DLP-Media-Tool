"""Filesystem and report helpers for transcript archiving."""

from __future__ import annotations

import json
import csv
import os
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import urlsplit, urlunsplit

from core.transcripts.models import OutputFormat, RetryError, UserError, VideoAction

CHANNEL_TAB_SUFFIXES = ("/videos", "/shorts", "/streams", "/playlists", "/featured", "/about")
MD_INDEX_RE = re.compile(r"^(\d+)_.+\.md$")
TXT_INDEX_RE = re.compile(r"^(\d+)_.+\.txt$")
T = TypeVar("T")


def normalize_channel_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url

    if "watch?v=" in url or "playlist?list=" in url:
        return url.rstrip("/")

    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    has_tab_suffix = any(path.endswith(suffix) for suffix in CHANNEL_TAB_SUFFIXES)

    if "/@" in path and not has_tab_suffix:
        path = f"{path}/videos"
    elif "/channel/" in path and not has_tab_suffix:
        path = f"{path}/videos"

    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def resolve_video_url(entry: dict[str, Any], video_id: str) -> str:
    raw_url = entry.get("webpage_url") or entry.get("url")
    if raw_url and str(raw_url).startswith("http"):
        return str(raw_url)
    return f"https://www.youtube.com/watch?v={video_id}"


def slugify(text: str, max_length: int = 80) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_length].rstrip("-") or "untitled"


def format_upload_date(raw: str | None) -> str:
    if not raw or len(raw) != 8:
        return ""
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def yaml_str(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def md_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def md_heading_text(value: str) -> str:
    text = re.sub(r"[\r\n\t]+", " ", value or "")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Untitled"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd: int | None = None
    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            fd = None
            handle.write(content)
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


NON_RETRYABLE_EXCEPTIONS = (TypeError, ValueError, KeyError, AssertionError)


def is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, NON_RETRYABLE_EXCEPTIONS):
        return False
    if isinstance(exc, UserError):
        return False
    return True


def retry_call(
    fn: Callable[[], T],
    attempts: int,
    delay: float,
    action: str,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable_error(exc):
                raise
            last_exc = exc
            if attempt < attempts - 1:
                sleeper(delay)
    assert last_exc is not None
    raise RetryError(f"{action} failed after {attempts} attempt(s): {last_exc}") from last_exc


def select_videos(
    all_videos: list[dict[str, Any]],
    max_videos: int | None,
    start_index: int | None,
    end_index: int | None,
) -> list[tuple[int, dict[str, Any]]]:
    total = len(all_videos)
    if start_index is not None or end_index is not None:
        start = start_index if start_index is not None else 1
        end = end_index if end_index is not None else total
        if start > total:
            return []
        end = min(end, total)
        return [(index, all_videos[index - 1]) for index in range(start, end + 1)]

    if max_videos is not None:
        count = min(max_videos, total)
        return [(index, all_videos[index - 1]) for index in range(1, count + 1)]

    return [(index, all_videos[index - 1]) for index in range(1, total + 1)]


def build_txt_content(transcript: str) -> str:
    return transcript.strip() + "\n"


def build_md_content(
    title: str,
    url: str,
    upload_date: str,
    channel: str,
    video_id: str,
    transcript: str,
    *,
    timestamps: bool = False,
) -> str:
    front_matter = [
        "---",
        f"title: {yaml_str(title)}",
        f"url: {yaml_str(url)}",
        f"upload_date: {yaml_str(upload_date)}",
        f"channel: {yaml_str(channel)}",
        f"video_id: {yaml_str(video_id)}",
    ]
    if timestamps:
        front_matter.append("timestamps: true")
    lines = [
        *front_matter,
        "---",
        "",
        f"# {md_heading_text(title)}",
        "",
        transcript.strip(),
        "",
    ]
    return "\n".join(lines)


def transcript_file_fields(
    output_format: OutputFormat,
    txt_path: Path,
    md_path: Path,
    base_dir: Path,
) -> dict[str, str]:
    """Report file fields for the selected output format, relative to base_dir."""
    fields: dict[str, str] = {}
    if output_format in ("both", "txt"):
        fields["txt_file"] = str(txt_path.relative_to(base_dir))
    if output_format in ("both", "md"):
        fields["md_file"] = str(md_path.relative_to(base_dir))
    return fields


def frontmatter_value_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return ""
    return str(value)


def parse_md_frontmatter(md_path: Path) -> dict[str, str]:
    content = md_path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        try:
            fields[key] = frontmatter_value_to_str(json.loads(value))
        except json.JSONDecodeError:
            fields[key] = value.strip('"')
    return fields


def build_metadata_videos_list(selected_videos: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "index": video.index,
            "id": video.video_id,
            "title": video.title,
            "url": video.url,
            "upload_date": format_upload_date(video.upload_date),
        }
        for video in selected_videos
    ]


def build_metadata_payload(
    *,
    channel_url: str,
    channel_name: str,
    total_channel_videos: int,
    selected_count: int,
    start_index: int | None,
    end_index: int | None,
    max_videos: int | None,
    videos: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "channel_url": channel_url,
        "channel_name": channel_name,
        "total_channel_videos": total_channel_videos,
        "total_videos": total_channel_videos,
        "selected_count": selected_count,
        "start_index": start_index,
        "end_index": end_index,
        "max_videos": max_videos,
        "generated_at": generated_at or utc_now(),
        "videos": videos,
    }


def write_videos_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def safe_csv_cell(value: Any) -> str:
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return f"'{text}"
    return text


def write_videos_csv(path: Path, videos: list[dict[str, Any]]) -> None:
    fieldnames = ["index", "id", "title", "url", "upload_date"]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for video in videos:
        writer.writerow({field: safe_csv_cell(video[field]) for field in fieldnames})
    atomic_write_text(path, buffer.getvalue())


def build_existing_files_index(md_dir: Path, txt_dir: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for md_path in md_dir.glob("*.md"):
        meta = parse_md_frontmatter(md_path)
        video_id = meta.get("video_id")
        if not video_id:
            continue

        basename = md_path.stem
        txt_path = txt_dir / f"{basename}.txt"
        match = MD_INDEX_RE.match(md_path.name)
        index[video_id] = {
            "video_id": video_id,
            "basename": basename,
            "txt_path": txt_path,
            "md_path": md_path,
            "index": int(match.group(1)) if match else 0,
            "title": meta.get("title") or basename,
        }
    return index


def build_existing_txt_index(md_dir: Path, txt_dir: Path) -> dict[int, dict[str, Any]]:
    """Index existing TXT files by numeric prefix for format-aware resume.

    TXT files have no frontmatter, so ``txt`` runs cannot always match by
    ``video_id``. They fall back to matching the global index prefix.
    """
    index: dict[int, dict[str, Any]] = {}
    for txt_path in sorted(txt_dir.glob("*.txt")):
        match = TXT_INDEX_RE.match(txt_path.name)
        if not match:
            continue
        file_index = int(match.group(1))
        if file_index in index:
            continue
        basename = txt_path.stem
        index[file_index] = {
            "video_id": "",
            "basename": basename,
            "txt_path": txt_path,
            "md_path": md_dir / f"{basename}.md",
            "index": file_index,
            "title": basename,
        }
    return index


def resolve_video_action(
    video_id: str,
    proposed_basename: str,
    proposed_txt_path: Path,
    proposed_md_path: Path,
    existing_by_id: dict[str, dict[str, Any]],
    force: bool,
    *,
    output_format: OutputFormat = "both",
    global_index: int | None = None,
    existing_by_index: dict[int, dict[str, Any]] | None = None,
) -> tuple[VideoAction, Path, Path, str, bool]:
    entry = existing_by_id.get(video_id)
    if (
        entry is None
        and output_format == "txt"
        and existing_by_index
        and global_index is not None
    ):
        entry = existing_by_index.get(global_index)

    if entry:
        txt_path = entry["txt_path"]
        md_path = entry["md_path"]
        basename = entry["basename"]
    else:
        txt_path = proposed_txt_path
        md_path = proposed_md_path
        basename = proposed_basename

    txt_exists = txt_path.exists()
    md_exists = md_path.exists()

    if output_format == "txt":
        if not force and txt_exists:
            return "skip", txt_path, md_path, basename, False
        return "process", txt_path, md_path, basename, False

    if output_format == "md":
        if not force and md_exists:
            return "skip", txt_path, md_path, basename, False
        return "process", txt_path, md_path, basename, False

    if not force and txt_exists and md_exists:
        return "skip", txt_path, md_path, basename, False
    if not force and (txt_exists or md_exists):
        return "repair", txt_path, md_path, basename, True
    return "process", txt_path, md_path, basename, False


def enrich_report_fields(report: dict[str, Any], total_channel_videos: int) -> dict[str, Any]:
    report["total_channel_videos"] = total_channel_videos
    report["total_videos"] = total_channel_videos
    return report


def run_report_filename(
    start_index: int | None,
    end_index: int | None,
    max_videos: int | None,
    total_channel_videos: int,
) -> str:
    if start_index is not None or end_index is not None:
        start = start_index if start_index is not None else 1
        end = end_index if end_index is not None else total_channel_videos
        return f"report_{start:03d}_{end:03d}.json"
    if max_videos is not None:
        return f"report_001_{max_videos:03d}.json"
    return f"report_001_{total_channel_videos:03d}.json"


def collect_completed_from_disk(
    md_dir: Path,
    txt_dir: Path,
    output_format: OutputFormat = "both",
) -> list[dict[str, Any]]:
    base_dir = md_dir.parent

    if output_format == "txt":
        items: list[dict[str, Any]] = []
        for txt_path in txt_dir.glob("*.txt"):
            match = TXT_INDEX_RE.match(txt_path.name)
            if not match:
                continue
            basename = txt_path.stem
            items.append(
                {
                    "index": int(match.group(1)),
                    "id": "",
                    "title": basename,
                    "url": "",
                    "upload_date": "",
                    "basename": basename,
                    "txt_file": str(txt_path.relative_to(base_dir)),
                }
            )
        return sorted(items, key=lambda row: row["index"])

    items = []
    for md_path in md_dir.glob("*.md"):
        match = MD_INDEX_RE.match(md_path.name)
        if not match:
            continue

        basename = md_path.stem
        txt_path = txt_dir / f"{basename}.txt"
        if output_format == "both" and not txt_path.exists():
            continue

        file_index = int(match.group(1))
        meta = parse_md_frontmatter(md_path)
        row: dict[str, Any] = {
            "index": file_index,
            "id": meta.get("video_id") or "",
            "title": meta.get("title") or basename,
            "url": meta.get("url") or "",
            "upload_date": meta.get("upload_date") or "",
            "basename": basename,
            "md_file": str(md_path.relative_to(base_dir)),
        }
        if output_format == "both":
            row["txt_file"] = str(txt_path.relative_to(base_dir))
        items.append(row)

    return sorted(items, key=lambda row: row["index"])


def build_cumulative_report(
    *,
    base_dir: Path,
    channel_url: str,
    channel_name: str,
    total_channel_videos: int,
    md_dir: Path,
    txt_dir: Path,
    reports_dir: Path,
    output_format: OutputFormat = "both",
    timestamps: bool = False,
) -> dict[str, Any]:
    completed = collect_completed_from_disk(md_dir, txt_dir, output_format)
    completed_ids = {item["id"] for item in completed if item.get("id")}

    skipped_by_id: dict[str, dict[str, Any]] = {}
    partial_repaired_count = 0
    run_report_files: list[str] = []

    for report_path in sorted(reports_dir.glob("report_*.json")):
        run_report_files.append(str(report_path.relative_to(base_dir)))
        try:
            run_report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        partial_repaired_count += sum(
            1 for item in run_report.get("processed", []) if item.get("partial_repaired")
        )

        for item in run_report.get("skipped", []):
            vid = item.get("id")
            if not vid or vid in completed_ids:
                continue
            if item.get("reason") == "already_exists":
                continue
            skipped_by_id[vid] = item

    cumulative_skipped = sorted(skipped_by_id.values(), key=lambda row: row.get("index", 0))

    return {
        "channel_url": channel_url,
        "channel_name": channel_name,
        "total_channel_videos": total_channel_videos,
        "total_videos": total_channel_videos,
        "output_format": output_format,
        "timestamps": timestamps,
        "completed_count": len(completed),
        "skipped_count": len(cumulative_skipped),
        "partial_repaired_count": partial_repaired_count,
        "run_reports": run_report_files,
        "completed": completed,
        "skipped": cumulative_skipped,
        "last_updated_at": utc_now(),
        "output_path": str(base_dir),
        "cumulative_report_path": str(base_dir / "cumulative_report.json"),
    }


def collect_index_items_from_disk(
    md_dir: Path,
    txt_dir: Path,
    output_format: OutputFormat = "both",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if output_format == "txt":
        for txt_path in txt_dir.glob("*.txt"):
            match = TXT_INDEX_RE.match(txt_path.name)
            if not match:
                continue
            basename = txt_path.stem
            items.append(
                {
                    "index": int(match.group(1)),
                    "title": basename,
                    "upload_date": "",
                    "basename": basename,
                }
            )
        return sorted(items, key=lambda row: row["index"])

    for md_path in md_dir.glob("*.md"):
        match = MD_INDEX_RE.match(md_path.name)
        if not match:
            continue

        file_index = int(match.group(1))
        basename = md_path.stem
        meta = parse_md_frontmatter(md_path)
        items.append(
            {
                "index": file_index,
                "title": meta.get("title") or basename,
                "upload_date": meta.get("upload_date") or "",
                "basename": basename,
            }
        )

    return sorted(items, key=lambda row: row["index"])


def write_index_md(
    path: Path,
    channel: str,
    index_items: list[dict[str, Any]],
    output_format: OutputFormat = "both",
) -> None:
    subdir = "txt" if output_format == "txt" else "md"
    ext = "txt" if output_format == "txt" else "md"
    lines = [
        f"# {channel} - Transcript Index",
        "",
        f"Total transcripts: {len(index_items)}",
        "",
        "| # | Title | Date | File |",
        "|---|-------|------|------|",
    ]
    for item in index_items:
        date = md_table_cell(item.get("upload_date") or "-")
        title = md_table_cell(item["title"])
        file_label = md_table_cell(f"{item['basename']}.{ext}")
        lines.append(
            f"| {item['index']:03d} | {title} | {date} | "
            f"[{file_label}]({subdir}/{item['basename']}.{ext}) |"
        )
    lines.append("")
    atomic_write_text(path, "\n".join(lines))


def sanitize_video_id_for_filename(video_id: str) -> str:
    sanitized = re.sub(r"[^\w-]", "-", video_id or "")
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return sanitized or "unknown"


def sanitize_video_id(video_id: str) -> str:
    """Backward-compatible alias for filename-safe video ids."""
    return sanitize_video_id_for_filename(video_id)


def make_basename(index: int, title: str, video_id: str, used_basenames: set[str]) -> str:
    basename = f"{index:03d}_{slugify(title)}"
    if basename in used_basenames:
        basename = f"{basename}_{sanitize_video_id_for_filename(video_id)}"
    used_basenames.add(basename)
    return basename


def count_skip_reasons(skipped: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "existing_count": 0,
        "error_count": 0,
        "other_skipped_count": 0,
    }
    for item in skipped:
        reason = item.get("reason")
        if reason == "already_exists":
            counts["existing_count"] += 1
        elif reason == "error":
            counts["error_count"] += 1
        else:
            counts["other_skipped_count"] += 1
    return counts


def count_partial_repaired(processed: list[dict[str, Any]]) -> int:
    return sum(1 for item in processed if item.get("partial_repaired"))


def should_write_progress(
    position: int,
    progress_interval: int,
    *,
    is_last: bool = False,
    on_error: bool = False,
) -> bool:
    if on_error or is_last:
        return True
    if position == 1:
        return True
    return position % progress_interval == 0


def save_progress(
    progress_path: Path,
    *,
    channel_url: str,
    channel_name: str,
    total_channel_videos: int,
    run_videos: int,
    start_index: int | None,
    end_index: int | None,
    max_videos: int | None,
    force: bool,
    manual_only: bool,
    retries: int,
    processed: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    last_global_index: int | None,
    run_started_at: str,
    auto_fallback: bool | None = None,
    languages: list[str] | None = None,
    keep_cues: bool | None = None,
    output_format: OutputFormat | None = None,
    timestamps: bool | None = None,
    metadata_only: bool | None = None,
    progress_interval: int | None = None,
) -> None:
    skip_counts = count_skip_reasons(skipped)
    progress = {
        "channel_url": channel_url,
        "channel_name": channel_name,
        "total_channel_videos": total_channel_videos,
        "total_videos": total_channel_videos,
        "run_videos": run_videos,
        "start_index": start_index,
        "end_index": end_index,
        "max_videos": max_videos,
        "forced": force,
        "manual_only": manual_only,
        "retries": retries,
        "run_started_at": run_started_at,
        "last_updated_at": utc_now(),
        "last_global_index": last_global_index,
        "processed_count": len(processed),
        "skipped_count": len(skipped),
        "existing_count": skip_counts["existing_count"],
        "partial_repaired_count": count_partial_repaired(processed),
        "error_count": skip_counts["error_count"],
        "other_skipped_count": skip_counts["other_skipped_count"],
        "processed": processed,
        "skipped": skipped,
    }
    if auto_fallback is not None:
        progress["auto_fallback"] = auto_fallback
    if languages is not None:
        progress["languages"] = languages
    if keep_cues is not None:
        progress["keep_cues"] = keep_cues
    if output_format is not None:
        progress["output_format"] = output_format
    if timestamps is not None:
        progress["timestamps"] = timestamps
    if metadata_only is not None:
        progress["metadata_only"] = metadata_only
    if progress_interval is not None:
        progress["progress_interval"] = progress_interval
    atomic_write_json(progress_path, progress)
