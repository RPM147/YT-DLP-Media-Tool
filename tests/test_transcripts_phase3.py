from __future__ import annotations

from pathlib import Path

import pytest

from core.transcripts import (
    DEFAULT_TRANSCRIPT_LANGUAGES,
    TranscriptProcessedItem,
    TranscriptRequest,
    TranscriptResult,
    TranscriptService,
    TranscriptSkippedItem,
    TranscriptVideo,
)


def test_transcript_request_normalizes_path_and_languages(tmp_path: Path):
    request = TranscriptRequest(
        url="https://www.youtube.com/watch?v=abc",
        output_dir=str(tmp_path),
        languages=[" tr ", "", "en"],
    )

    assert request.output_dir == tmp_path
    assert request.languages == ("tr", "en")
    assert request.report_fields()["languages"] == ["tr", "en"]


def test_transcript_request_defaults_are_product_safe(tmp_path: Path):
    request = TranscriptRequest(
        url="https://www.youtube.com/watch?v=abc",
        output_dir=tmp_path,
    )

    assert request.languages == DEFAULT_TRANSCRIPT_LANGUAGES
    assert request.auto_fallback is True
    assert request.manual_only is False


def test_transcript_request_rejects_ambiguous_positional_options(tmp_path: Path):
    with pytest.raises(TypeError):
        TranscriptRequest("https://www.youtube.com/watch?v=abc", tmp_path, ["en"])


def test_transcript_video_from_entry_fills_missing_url():
    video = TranscriptVideo.from_entry(7, {"id": "abc123", "title": "A Video"})

    assert video.index == 7
    assert video.video_id == "abc123"
    assert video.url == "https://www.youtube.com/watch?v=abc123"
    assert video.to_dict()["id"] == "abc123"


def test_processed_and_skipped_items_keep_legacy_report_keys():
    processed = TranscriptProcessedItem(
        index=1,
        video_id="vid1",
        title="Done",
        url="https://example.com",
        upload_date="2024-01-01",
        basename="001_done",
        subtitle_lang="en",
        subtitle_type="manual",
        txt_file="txt/001_done.txt",
        md_file="md/001_done.md",
        partial_repaired=True,
    )
    skipped = TranscriptSkippedItem(
        index=2,
        video_id="vid2",
        title="Skipped",
        url="https://example.com/2",
        reason="no_english_subtitles",
    )

    assert processed.to_dict()["id"] == "vid1"
    assert processed.to_dict()["partial_repaired"] is True
    assert skipped.to_dict() == {
        "index": 2,
        "id": "vid2",
        "title": "Skipped",
        "url": "https://example.com/2",
        "reason": "no_english_subtitles",
    }


def test_transcript_result_wraps_report_without_mutating_input():
    report = {"processed_count": 1}
    result = TranscriptResult.from_report(report)
    copied = result.to_dict()
    copied["processed_count"] = 2

    assert report["processed_count"] == 1


def test_service_report_includes_phase3_request_fields(tmp_path: Path):
    service = TranscriptService(
        list_videos=lambda _url: (
            "Test Channel",
            [{"id": "vid1", "title": "Video", "url": "https://example.com/vid1"}],
        )
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            languages=["tr", "en"],
            auto_fallback=False,
            delay=0,
            dry_run=True,
        )
    )

    assert report["languages"] == ["tr", "en"]
    assert report["auto_fallback"] is False
    assert report["dry_run"] is True
    assert report["planned"][0]["action"] == "process"
