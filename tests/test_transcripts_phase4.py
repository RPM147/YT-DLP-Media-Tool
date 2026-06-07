from __future__ import annotations

from pathlib import Path

from core.transcripts import TranscriptRequest, TranscriptService
from core.transcripts.subtitle_parser import (
    pick_english_subtitle,
    pick_subtitle,
    subtitle_skip_reason,
)


def fake_video_rows() -> tuple[str, list[dict]]:
    return (
        "Test Channel",
        [{"id": "vid1", "title": "Video", "url": "https://example.com/vid1"}],
    )


def subtitle_file(
    _url: str,
    video_id: str,
    lang: str,
    _sub_type: str,
    out_dir: Path,
) -> Path:
    path = out_dir / f"{video_id}.{lang}.vtt"
    path.write_text(
        """WEBVTT

00:00:01.000 --> 00:00:02.000
Merhaba
""",
        encoding="utf-8",
    )
    return path


def test_pick_subtitle_prefers_requested_language_manual():
    lang, sub_type = pick_subtitle(
        subtitles={"en": [{}], "tr": [{}]},
        automatic_captions={"tr": [{}]},
        languages=("tr", "en"),
    )

    assert (lang, sub_type) == ("tr", "manual")


def test_pick_subtitle_uses_language_variant():
    lang, sub_type = pick_subtitle(
        subtitles={"tr-TR": [{}]},
        automatic_captions={},
        languages=("tr",),
    )

    assert (lang, sub_type) == ("tr-TR", "manual")


def test_pick_subtitle_respects_auto_fallback_false():
    lang, sub_type = pick_subtitle(
        subtitles={},
        automatic_captions={"tr": [{}]},
        languages=("tr",),
        auto_fallback=False,
    )

    assert (lang, sub_type) == (None, None)


def test_pick_subtitle_manual_only_ignores_auto():
    lang, sub_type = pick_subtitle(
        subtitles={},
        automatic_captions={"tr": [{}]},
        languages=("tr",),
        manual_only=True,
    )

    assert (lang, sub_type) == (None, None)


def test_pick_english_subtitle_keeps_legacy_default():
    lang, sub_type = pick_english_subtitle(
        subtitles={},
        automatic_captions={"en-US": [{}]},
    )

    assert (lang, sub_type) == ("en-US", "auto")


def test_subtitle_skip_reason_is_language_aware():
    assert subtitle_skip_reason(False, ("tr",)) == "no_selected_language_subtitles"
    assert (
        subtitle_skip_reason(True, ("tr",))
        == "no_manual_selected_language_subtitles"
    )
    assert subtitle_skip_reason(False) == "no_english_subtitles"


def test_service_uses_requested_language_for_output(tmp_path: Path):
    service = TranscriptService(
        list_videos=lambda _url: fake_video_rows(),
        fetch_metadata=lambda _url: {
            "title": "Video",
            "channel": "Test Channel",
            "subtitles": {"en": [{}], "tr": [{}]},
            "automatic_captions": {},
        },
        download_subtitle=subtitle_file,
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            languages=("tr", "en"),
            delay=0,
        )
    )

    assert report["processed"][0]["subtitle_lang"] == "tr"
    assert report["processed"][0]["subtitle_type"] == "manual"


def test_service_auto_fallback_false_skips_auto_only(tmp_path: Path):
    service = TranscriptService(
        list_videos=lambda _url: fake_video_rows(),
        fetch_metadata=lambda _url: {
            "title": "Video",
            "channel": "Test Channel",
            "subtitles": {},
            "automatic_captions": {"tr": [{}]},
        },
        download_subtitle=subtitle_file,
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            languages=("tr",),
            auto_fallback=False,
            delay=0,
        )
    )

    assert report["processed_count"] == 0
    assert report["skipped"][0]["reason"] == "no_selected_language_subtitles"


def test_service_manual_only_skips_auto_only_selected_language(tmp_path: Path):
    service = TranscriptService(
        list_videos=lambda _url: fake_video_rows(),
        fetch_metadata=lambda _url: {
            "title": "Video",
            "channel": "Test Channel",
            "subtitles": {},
            "automatic_captions": {"tr": [{}]},
        },
        download_subtitle=subtitle_file,
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            languages=("tr",),
            manual_only=True,
            delay=0,
        )
    )

    assert report["processed_count"] == 0
    assert report["skipped"][0]["reason"] == "no_manual_selected_language_subtitles"
