from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from core.transcripts import (
    DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL,
    TranscriptRequest,
    TranscriptService,
    UserError,
)
from core.transcripts import io as transcript_io


CHANNEL_NAME = "Phase 9 Channel"
CHANNEL_SLUG = "phase-9-channel"


def sample_videos(count: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": f"vid{i}",
            "title": f"Video {i}",
            "url": f"https://www.youtube.com/watch?v=vid{i}",
            "upload_date": f"20260{min(i, 3)}0{i}",
        }
        for i in range(1, count + 1)
    ]


def make_request(tmp_path: Path, **kwargs: Any) -> TranscriptRequest:
    params: dict[str, Any] = {
        "url": "https://www.youtube.com/@phase9",
        "output_dir": tmp_path,
        "languages": ("en",),
        "delay": 0,
    }
    params.update(kwargs)
    return TranscriptRequest(**params)


def metadata_for(video_url: str) -> dict[str, Any]:
    video_id = video_url.rsplit("=", 1)[-1]
    index = int(video_id.replace("vid", ""))
    return {
        "id": video_id,
        "title": f"Video {index}",
        "channel": CHANNEL_NAME,
        "upload_date": f"20260{min(index, 3)}0{index}",
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
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n",
        encoding="utf-8",
    )
    return sub_path


def make_service(
    *,
    videos: list[dict[str, Any]] | None = None,
    fetch_metadata: Any = metadata_for,
    download: Any = download_subtitle,
) -> TranscriptService:
    rows = videos if videos is not None else sample_videos()
    return TranscriptService(
        list_videos=lambda _url: (CHANNEL_NAME, rows),
        fetch_metadata=fetch_metadata,
        download_subtitle=download,
        sleeper=lambda _delay: None,
    )


def test_request_defaults_metadata_only_and_progress_interval(tmp_path: Path):
    request = make_request(tmp_path)

    assert request.metadata_only is False
    assert request.progress_interval == DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL
    assert request.report_fields()["metadata_only"] is False
    assert request.report_fields()["progress_interval"] == DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL


def test_metadata_only_writes_videos_json_and_csv_without_fetching_subtitles(tmp_path: Path):
    def fail_fetch(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("metadata_only must not fetch per-video subtitle metadata")

    service = make_service(fetch_metadata=fail_fetch, download=fail_fetch)

    report = service.process(make_request(tmp_path, metadata_only=True, max_videos=3))

    base = tmp_path / CHANNEL_SLUG
    videos_json = base / "videos.json"
    videos_csv = base / "videos.csv"
    assert report["metadata_only"] is True
    assert report["selected_count"] == 3
    assert report["total_videos"] == 5
    assert len(report["videos"]) == 3
    assert videos_json.exists()
    assert videos_csv.exists()
    assert not (base / "txt").exists()
    assert not (base / "md").exists()
    assert not (base / "progress.json").exists()
    assert not (base / "report.json").exists()


def test_metadata_only_videos_json_structure_and_index_range(tmp_path: Path):
    report = make_service().process(
        make_request(tmp_path, metadata_only=True, start_index=2, end_index=4)
    )

    payload = json.loads(
        (tmp_path / CHANNEL_SLUG / "videos.json").read_text(encoding="utf-8")
    )
    assert report["selected_count"] == 3
    assert [video["index"] for video in report["videos"]] == [2, 3, 4]
    assert payload["channel_name"] == CHANNEL_NAME
    assert payload["total_videos"] == 5
    assert payload["selected_count"] == 3
    assert payload["videos"][0]["index"] == 2
    assert payload["videos"][0]["id"] == "vid2"
    assert payload["videos"][0]["upload_date"] == "2026-02-02"


def test_metadata_only_csv_has_no_blank_rows_and_sanitizes_formulas(tmp_path: Path):
    videos = [
        {
            "id": "vid1",
            "title": '=HYPERLINK("http://evil.example","click")',
            "url": "https://www.youtube.com/watch?v=vid1",
            "upload_date": "20260101",
        }
    ]
    service = make_service(videos=videos)

    service.process(make_request(tmp_path, metadata_only=True))

    csv_path = tmp_path / CHANNEL_SLUG / "videos.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    assert rows == [
        ["index", "id", "title", "url", "upload_date"],
        [
            "1",
            "vid1",
            '\'=HYPERLINK("http://evil.example","click")',
            "https://www.youtube.com/watch?v=vid1",
            "2026-01-01",
        ],
    ]


def test_metadata_only_dry_run_writes_no_files(tmp_path: Path):
    report = make_service().process(
        make_request(tmp_path, metadata_only=True, dry_run=True, max_videos=2)
    )

    base = tmp_path / CHANNEL_SLUG
    assert report["metadata_only"] is True
    assert report["dry_run"] is True
    assert report["selected_count"] == 2
    assert report["would_write_metadata_files"] is False
    assert not base.exists()


def test_transcript_behavior_unchanged_without_metadata_only(tmp_path: Path):
    service = make_service(videos=sample_videos(1))

    report = service.process(make_request(tmp_path))

    base = tmp_path / CHANNEL_SLUG
    assert report["metadata_only"] is False
    assert report["processed_count"] == 1
    assert len(list((base / "txt").glob("*.txt"))) == 1
    assert len(list((base / "md").glob("*.md"))) == 1
    assert not (base / "videos.json").exists()
    assert not (base / "videos.csv").exists()


def test_progress_interval_is_written_on_first_interval_last_and_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[dict[str, Any]] = []

    def record_progress(_progress_path: Path, **kwargs: Any) -> None:
        calls.append(
            {
                "processed_count": len(kwargs["processed"]),
                "skipped_count": len(kwargs["skipped"]),
                "progress_interval": kwargs["progress_interval"],
            }
        )

    monkeypatch.setattr(transcript_io, "save_progress", record_progress)
    service = make_service(videos=sample_videos(4))

    service.process(make_request(tmp_path, progress_interval=2))

    assert calls == [
        {"processed_count": 1, "skipped_count": 0, "progress_interval": 2},
        {"processed_count": 2, "skipped_count": 0, "progress_interval": 2},
        {"processed_count": 4, "skipped_count": 0, "progress_interval": 2},
    ]


def test_validation_rejects_progress_interval_zero(tmp_path: Path):
    service = make_service()

    with pytest.raises(UserError, match="progress_interval"):
        service.process(make_request(tmp_path, progress_interval=0))


def test_validation_rejects_max_videos_with_index_range(tmp_path: Path):
    service = make_service()

    with pytest.raises(UserError, match="max_videos"):
        service.process(make_request(tmp_path, max_videos=2, start_index=1))


def test_retry_call_does_not_retry_programming_errors():
    calls = 0

    def broken() -> None:
        nonlocal calls
        calls += 1
        raise TypeError("programming bug")

    with pytest.raises(TypeError):
        transcript_io.retry_call(broken, attempts=3, delay=0, action="Test")

    assert calls == 1


def test_retry_call_retries_retryable_errors():
    calls = 0

    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("temporary")
        return "ok"

    assert (
        transcript_io.retry_call(flaky, attempts=3, delay=0, action="Test", sleeper=lambda _: None)
        == "ok"
    )
    assert calls == 2


def test_frontmatter_values_are_parsed_as_strings(tmp_path: Path):
    md_path = tmp_path / "001_test.md"
    md_path.write_text(
        "---\n"
        "video_id: abc123\n"
        "timestamps: true\n"
        "year: 2024\n"
        "---\n\n"
        "# Example\n",
        encoding="utf-8",
    )

    meta = transcript_io.parse_md_frontmatter(md_path)

    assert meta["timestamps"] == "true"
    assert meta["year"] == "2024"
    assert all(isinstance(value, str) for value in meta.values())


def test_normalize_channel_url_preserves_query():
    assert transcript_io.normalize_channel_url("https://www.youtube.com/@foo?x=1") == (
        "https://www.youtube.com/@foo/videos?x=1"
    )


def test_video_id_sanitization_and_duplicate_basename():
    assert transcript_io.sanitize_video_id_for_filename("abc/def") == "abc-def"
    used = {"001_same-title"}

    basename = transcript_io.make_basename(1, "Same Title", "abc/def", used)

    assert basename == "001_same-title_abc-def"


def test_build_md_content_uses_safe_heading():
    content = transcript_io.build_md_content(
        title="Bad\nTitle <b>bold</b>",
        url="https://example.com",
        upload_date="2026-06-07",
        channel="Channel",
        video_id="vid1",
        transcript="Hello",
    )

    heading_lines = [line for line in content.splitlines() if line.startswith("# ")]
    assert heading_lines == ["# Bad Title &lt;b&gt;bold&lt;/b&gt;"]


def test_atomic_write_text_cleans_temp_file_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    path = tmp_path / "out.txt"
    before = {item.name for item in tmp_path.iterdir()}

    def fail_replace(_source: Path | str, _target: Path | str) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(transcript_io.os, "replace", fail_replace)

    with pytest.raises(OSError):
        transcript_io.atomic_write_text(path, "data\n")

    assert {item.name for item in tmp_path.iterdir()} == before
    assert not path.exists()


def test_should_write_progress_interval_logic():
    assert transcript_io.should_write_progress(1, 10) is True
    assert transcript_io.should_write_progress(10, 10) is True
    assert transcript_io.should_write_progress(5, 10) is False
    assert transcript_io.should_write_progress(25, 10, is_last=True) is True
    assert transcript_io.should_write_progress(5, 10, on_error=True) is True
