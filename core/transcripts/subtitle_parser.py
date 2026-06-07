"""Subtitle selection and text parsing helpers."""

from __future__ import annotations

import html
import re
from pathlib import Path

EN_SUB_LANGS = ["en", "en-US", "en-GB", "en-orig"]
SUBTITLE_CUE_PATTERNS = [
    re.compile(r"\[Music\]", re.IGNORECASE),
    re.compile(r"\[Applause\]", re.IGNORECASE),
    re.compile(r"\[Laughter\]", re.IGNORECASE),
    re.compile(r"\[applause and cheering\]", re.IGNORECASE),
    re.compile(r"\[Submit subtitle corrections at[^\]]*\]", re.IGNORECASE),
]


def _language_base(language: str) -> str:
    return language.lower().split("-", 1)[0]


def _is_default_english(languages: list[str] | tuple[str, ...] | None) -> bool:
    return not languages or tuple(languages) == tuple(EN_SUB_LANGS)


def _find_language(available: dict, languages: list[str] | tuple[str, ...]) -> str | None:
    if not available:
        return None

    for language in languages:
        if language in available:
            return language

    for language in languages:
        prefix = f"{language.lower()}-"
        for candidate in available:
            if candidate.lower().startswith(prefix):
                return candidate

    requested_bases = [_language_base(language) for language in languages]
    for requested_base in requested_bases:
        for candidate in available:
            if _language_base(candidate) == requested_base:
                return candidate

    return None


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def clean_transcript_text(text: str, *, keep_cues: bool = False) -> str:
    text = strip_html(text)
    text = re.sub(r"\{[^}]+\}", "", text)
    if not keep_cues:
        for pattern in SUBTITLE_CUE_PATTERNS:
            text = pattern.sub("", text)
        text = text.replace("♪", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


CUE_TIMING_RE = re.compile(r"^(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->")


def format_timestamp(raw: str) -> str:
    """Normalize a VTT/SRT cue start time to a ``HH:MM:SS`` string."""
    cleaned = raw.strip().replace(",", ".").split(".", 1)[0]
    try:
        numbers = [int(part) for part in cleaned.split(":")]
    except ValueError:
        return "00:00:00"

    if len(numbers) == 3:
        hours, minutes, seconds = numbers
    elif len(numbers) == 2:
        hours, minutes, seconds = 0, numbers[0], numbers[1]
    elif len(numbers) == 1:
        hours, minutes, seconds = 0, 0, numbers[0]
    else:
        return "00:00:00"

    minutes += seconds // 60
    seconds %= 60
    hours += minutes // 60
    minutes %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _parse_cue_timestamp(line: str) -> str | None:
    """Return the normalized start time for a cue timing line, else ``None``."""
    match = CUE_TIMING_RE.match(line.strip())
    if not match:
        return None
    return format_timestamp(match.group("start"))


def _is_metadata_line(line: str) -> bool:
    if line.startswith("WEBVTT") or line.startswith("NOTE"):
        return True
    if re.match(r"^\d+$", line):
        return True
    if line.startswith("Kind:") or line.startswith("Language:"):
        return True
    return False


def _parse_plain(content: str, *, keep_cues: bool) -> str:
    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_metadata_line(line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s+-->", line):
            continue
        if re.match(r"^\d{2}:\d{2}[.,]\d{3}\s+-->", line):
            continue

        cleaned = clean_transcript_text(line, keep_cues=keep_cues)
        if cleaned:
            lines.append(cleaned)

    merged: list[str] = []
    for line in lines:
        if merged and merged[-1] == line:
            continue
        merged.append(line)

    return re.sub(r"\s+", " ", " ".join(merged)).strip()


def _parse_timestamped(content: str, *, keep_cues: bool) -> str:
    entries: list[tuple[str, str]] = []
    current_ts: str | None = None
    pending: list[str] = []

    def flush() -> None:
        nonlocal current_ts, pending
        if current_ts is not None and pending:
            text = clean_transcript_text(" ".join(pending), keep_cues=keep_cues)
            if text:
                entries.append((current_ts, text))
        pending = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cue_ts = _parse_cue_timestamp(line)
        if cue_ts is not None:
            flush()
            current_ts = cue_ts
            continue
        if _is_metadata_line(line):
            continue
        pending.append(line)
    flush()

    merged: list[tuple[str, str]] = []
    for timestamp, text in entries:
        if merged and merged[-1][1] == text:
            continue
        merged.append((timestamp, text))

    return "\n".join(f"[{timestamp}] {text}" for timestamp, text in merged)


def parse_subtitle_file(
    path: Path,
    *,
    keep_cues: bool = False,
    timestamps: bool = False,
) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    if timestamps:
        return _parse_timestamped(content, keep_cues=keep_cues)
    return _parse_plain(content, keep_cues=keep_cues)


def pick_subtitle(
    subtitles: dict,
    automatic_captions: dict,
    *,
    languages: list[str] | tuple[str, ...] = tuple(EN_SUB_LANGS),
    manual_only: bool = False,
    auto_fallback: bool = True,
) -> tuple[str | None, str | None]:
    lang = _find_language(subtitles, tuple(languages))
    if lang:
        return lang, "manual"

    if manual_only or not auto_fallback:
        return None, None

    lang = _find_language(automatic_captions, tuple(languages))
    if lang:
        return lang, "auto"

    return None, None


def pick_english_subtitle(
    subtitles: dict,
    automatic_captions: dict,
    *,
    manual_only: bool = False,
) -> tuple[str | None, str | None]:
    return pick_subtitle(
        subtitles,
        automatic_captions,
        languages=tuple(EN_SUB_LANGS),
        manual_only=manual_only,
        auto_fallback=True,
    )


def subtitle_skip_reason(
    manual_only: bool,
    languages: list[str] | tuple[str, ...] | None = None,
) -> str:
    if manual_only:
        if _is_default_english(languages):
            return "no_manual_english_subtitles"
        return "no_manual_selected_language_subtitles"
    if _is_default_english(languages):
        return "no_english_subtitles"
    return "no_selected_language_subtitles"


def subtitle_skip_message(
    manual_only: bool,
    languages: list[str] | tuple[str, ...] | None = None,
) -> str:
    if manual_only:
        if _is_default_english(languages):
            return "no manual English subtitles"
        return "no manual subtitles for selected language"
    if _is_default_english(languages):
        return "no English subtitles"
    return "no subtitles for selected language"


def find_subtitle_file(out_dir: Path, video_id: str, lang: str) -> Path | None:
    patterns = [
        f"*.{lang}.vtt",
        f"*.{lang}.srt",
        f"*.{lang}.*.vtt",
        f"*.{lang}.*.srt",
        f"{video_id}.{lang}.vtt",
        f"{video_id}.{lang}.srt",
        f"{video_id}.{lang}.*.vtt",
        f"{video_id}.{lang}.*.srt",
    ]

    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(out_dir.glob(pattern))

    if candidates:
        return sorted(set(candidates))[0]

    fallback = sorted(out_dir.glob("*.vtt")) + sorted(out_dir.glob("*.srt"))
    return fallback[0] if fallback else None
