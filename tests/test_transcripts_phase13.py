from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.transcripts import (
    TranscriptCallbacks,
    TranscriptCancelledError,
    TranscriptRequest,
    TranscriptService,
)
from core.transcripts import io as transcript_io
from core.transcripts.subtitle_parser import pick_subtitle, subtitle_skip_message
from core.transcripts.ytdlp_adapter import YtDlpTranscriptAdapter


def make_request(tmp_path: Path, **kwargs: Any) -> TranscriptRequest:
    params: dict[str, Any] = {
        "url": "https://www.youtube.com/@phase13",
        "output_dir": tmp_path,
        "languages": ("en",),
        "delay": 0,
        "progress_interval": 1,
    }
    params.update(kwargs)
    return TranscriptRequest(**params)


def write_vtt(
    _video_url: str,
    video_id: str,
    lang: str,
    _sub_type: str,
    out_dir: Path,
) -> Path:
    sub_path = out_dir / f"{video_id}.{lang}.vtt"
    sub_path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello world\n",
        encoding="utf-8",
    )
    return sub_path


def test_language_variant_matching_covers_upstream_language_candidates():
    lang, sub_type = pick_subtitle(
        {"pt-BR": [{}], "tr-TR": [{}]},
        {},
        languages=("tr", "pt"),
    )
    assert (lang, sub_type) == ("tr-TR", "manual")

    lang, sub_type = pick_subtitle(
        {},
        {"zh-Hant": [{}]},
        languages=("zh",),
    )
    assert (lang, sub_type) == ("zh-Hant", "auto")

    assert pick_subtitle({}, {"en-US": [{}]}, languages=("en",), auto_fallback=False) == (
        None,
        None,
    )
    assert subtitle_skip_message(True, ("tr",)) == "no manual subtitles for selected language"


def test_service_writes_reports_index_progress_and_cumulative_report(tmp_path: Path):
    videos = [
        {
            "id": "vid1",
            "title": "Video | One",
            "url": "https://www.youtube.com/watch?v=vid1",
            "upload_date": "20260601",
        },
        {
            "id": "vid2",
            "title": "No Subs",
            "url": "https://www.youtube.com/watch?v=vid2",
            "upload_date": "20260602",
        },
    ]

    def fetch_metadata(video_url: str) -> dict[str, Any]:
        if video_url.endswith("vid1"):
            return {
                "id": "vid1",
                "title": "Video | One",
                "channel": "Phase 13 Channel",
                "upload_date": "20260601",
                "subtitles": {"en": [{"ext": "vtt"}]},
                "automatic_captions": {},
            }
        return {
            "id": "vid2",
            "title": "No Subs",
            "channel": "Phase 13 Channel",
            "upload_date": "20260602",
            "subtitles": {},
            "automatic_captions": {},
        }

    service = TranscriptService(
        list_videos=lambda _url: ("Phase 13 Channel", videos),
        fetch_metadata=fetch_metadata,
        download_subtitle=write_vtt,
        sleeper=lambda _delay: None,
    )

    report = service.process(make_request(tmp_path, timestamps=True))
    base = tmp_path / "phase-13-channel"

    assert report["processed_count"] == 1
    assert report["skipped_count"] == 1
    assert report["other_skipped_count"] == 1
    assert report["timestamps"] is True
    assert Path(report["report_path"]).is_file()
    assert Path(report["last_run_report_path"]).is_file()
    assert Path(report["cumulative_report_path"]).is_file()
    assert Path(report["progress_path"]).is_file()
    assert Path(report["index_path"]).is_file()
    assert (base / report["chunk_report_path"]).is_file()

    progress = json.loads(Path(report["progress_path"]).read_text(encoding="utf-8"))
    assert progress["last_global_index"] == 2
    assert progress["processed_count"] == 1
    assert progress["skipped_count"] == 1
    assert progress["timestamps"] is True

    cumulative = json.loads(Path(report["cumulative_report_path"]).read_text(encoding="utf-8"))
    assert cumulative["completed_count"] == 1
    assert cumulative["skipped_count"] == 1
    assert [path.replace("\\", "/") for path in cumulative["run_reports"]] == [
        "reports/report_001_002.json"
    ]

    index_text = Path(report["index_path"]).read_text(encoding="utf-8")
    assert "Video \\| One" in index_text
    assert "(md/001_video-one.md)" in index_text


def test_ytdlp_adapter_lists_playlist_with_mocked_ytdlp_and_cookie_profile():
    class FakeYoutubeDL:
        calls: list[dict[str, Any]] = []

        def __init__(self, opts: dict[str, Any]) -> None:
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def extract_info(self, url: str, *, download: bool) -> dict[str, Any]:
            self.calls.append({"url": url, "download": download, "opts": self.opts})
            return {
                "channel": "Mock Channel",
                "entries": [
                    {"id": "vid1", "title": "One", "url": "vid1"},
                    {},
                    {"title": "Missing ID"},
                    {
                        "id": "vid2",
                        "title": "Two",
                        "webpage_url": "https://www.youtube.com/watch?v=vid2",
                    },
                ],
            }

    fake_module = SimpleNamespace(YoutubeDL=FakeYoutubeDL)
    adapter = YtDlpTranscriptAdapter(
        cookie_browser="firefox",
        cookie_browser_profile="default-release",
        ytdlp_module=fake_module,
    )

    channel, videos = adapter.list_videos("https://www.youtube.com/@mock")

    call = FakeYoutubeDL.calls[0]
    assert channel == "Mock Channel"
    assert call["url"] == "https://www.youtube.com/@mock/videos"
    assert call["download"] is False
    assert call["opts"]["extract_flat"] == "in_playlist"
    assert call["opts"]["cookiesfrombrowser"] == (
        "firefox",
        "default-release",
        None,
        None,
    )
    assert videos == [
        {
            "id": "vid1",
            "title": "One",
            "url": "https://www.youtube.com/watch?v=vid1",
            "upload_date": None,
        },
        {
            "id": "vid2",
            "title": "Two",
            "url": "https://www.youtube.com/watch?v=vid2",
            "upload_date": None,
        },
    ]


def test_videos_csv_uses_windows_safe_lf_newlines_and_formula_sanitization(tmp_path: Path):
    path = tmp_path / "videos.csv"

    transcript_io.write_videos_csv(
        path,
        [
            {
                "index": 1,
                "id": "=cmd",
                "title": "+title",
                "url": "https://example.com",
                "upload_date": "2026-06-07",
            }
        ],
    )

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    assert b"\r\n" not in raw
    assert raw.count(b"\n") == 2
    assert "'=cmd" in text
    assert "'+title" in text
    assert not text.endswith("\n\n")


def test_service_cancellation_before_first_video_avoids_network_operations(tmp_path: Path):
    fetch_called = False
    download_called = False
    videos = [
        {
            "id": "vid1",
            "title": "Video",
            "url": "https://www.youtube.com/watch?v=vid1",
            "upload_date": "20260601",
        }
    ]

    def fetch_metadata(_video_url: str) -> dict[str, Any]:
        nonlocal fetch_called
        fetch_called = True
        raise AssertionError("metadata fetch should not run after cancellation")

    def download_subtitle(*_args) -> Path:
        nonlocal download_called
        download_called = True
        raise AssertionError("subtitle download should not run after cancellation")

    service = TranscriptService(
        list_videos=lambda _url: ("Phase 13 Channel", videos),
        fetch_metadata=fetch_metadata,
        download_subtitle=download_subtitle,
        sleeper=lambda _delay: None,
    )

    with pytest.raises(TranscriptCancelledError):
        service.process(
            make_request(tmp_path),
            TranscriptCallbacks(should_cancel=lambda: True),
        )

    base = tmp_path / "phase-13-channel"
    assert fetch_called is False
    assert download_called is False
    assert not (base / "report.json").exists()
    assert not (base / "progress.json").exists()
