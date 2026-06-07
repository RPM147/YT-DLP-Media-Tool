from __future__ import annotations

from pathlib import Path
from typing import Any

from core.transcripts import TranscriptRequest, TranscriptService
from core.transcripts.io import build_md_content
from core.transcripts.subtitle_parser import format_timestamp, parse_subtitle_file

CHANNEL_NAME = "Phase 8 Channel"
CHANNEL_SLUG = "phase-8-channel"
VIDEO_URL = "https://www.youtube.com/watch?v=vid1"
BASENAME = "001_original-title"

VTT_CONTENT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
Second cue
"""

SRT_CONTENT = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
Second cue
"""


# ── Fakes / helpers ──────────────────────────────────────────


def list_single_video(title: str = "Original Title") -> tuple[str, list[dict[str, Any]]]:
    return (
        CHANNEL_NAME,
        [{"id": "vid1", "title": title, "url": VIDEO_URL, "upload_date": "20260606"}],
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


def make_download_subtitle(content: str = VTT_CONTENT, ext: str = "vtt"):
    def download_subtitle(
        _video_url: str,
        video_id: str,
        lang: str,
        _sub_type: str,
        out_dir: Path,
    ) -> Path:
        sub_path = out_dir / f"{video_id}.{lang}.{ext}"
        sub_path.write_text(content, encoding="utf-8")
        return sub_path

    return download_subtitle


def make_service(
    *,
    download: Any | None = None,
    listed_title: str = "Original Title",
    metadata_title: str = "Original Title",
) -> TranscriptService:
    return TranscriptService(
        list_videos=lambda _url: list_single_video(listed_title),
        fetch_metadata=lambda _url: fetch_metadata(metadata_title),
        download_subtitle=download or make_download_subtitle(),
        sleeper=lambda _delay: None,
    )


def make_request(tmp_path: Path, **kwargs: Any) -> TranscriptRequest:
    params: dict[str, Any] = {
        "url": "https://www.youtube.com/@phase8",
        "output_dir": tmp_path,
        "languages": ("en",),
        "delay": 0,
    }
    params.update(kwargs)
    return TranscriptRequest(**params)


def write_existing_md(base_dir: Path, *, video_id: str = "vid1", title: str = "Original Title") -> None:
    md_dir = base_dir / "md"
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / f"{BASENAME}.md").write_text(
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


def write_existing_txt(base_dir: Path) -> None:
    txt_dir = base_dir / "txt"
    txt_dir.mkdir(parents=True, exist_ok=True)
    (txt_dir / f"{BASENAME}.txt").write_text("Existing transcript\n", encoding="utf-8")


def write_sub(tmp_path: Path, content: str, name: str) -> Path:
    sub_path = tmp_path / name
    sub_path.write_text(content, encoding="utf-8")
    return sub_path


# ── 1. Request defaults ──────────────────────────────────────


def test_request_defaults_output_format_and_timestamps(tmp_path: Path):
    request = TranscriptRequest(url=VIDEO_URL, output_dir=tmp_path)
    assert request.output_format == "both"
    assert request.timestamps is False
    fields = request.report_fields()
    assert fields["output_format"] == "both"
    assert fields["timestamps"] is False


# ── 2. Output format writing ─────────────────────────────────


def test_both_writes_txt_and_md(tmp_path: Path):
    report = make_service().process(make_request(tmp_path, output_format="both"))
    base = tmp_path / CHANNEL_SLUG
    assert report["processed_count"] == 1
    assert (base / "txt" / f"{BASENAME}.txt").exists()
    assert (base / "md" / f"{BASENAME}.md").exists()


def test_txt_writes_only_txt(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="txt"))
    base = tmp_path / CHANNEL_SLUG
    assert (base / "txt" / f"{BASENAME}.txt").exists()
    assert list((base / "md").glob("*.md")) == []


def test_md_writes_only_md(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="md"))
    base = tmp_path / CHANNEL_SLUG
    assert (base / "md" / f"{BASENAME}.md").exists()
    assert list((base / "txt").glob("*.txt")) == []


# ── 3. Processed report fields ───────────────────────────────


def test_processed_fields_both(tmp_path: Path):
    report = make_service().process(make_request(tmp_path, output_format="both"))
    item = report["processed"][0]
    assert "txt_file" in item
    assert "md_file" in item


def test_processed_fields_txt_only(tmp_path: Path):
    report = make_service().process(make_request(tmp_path, output_format="txt"))
    item = report["processed"][0]
    assert "txt_file" in item
    assert "md_file" not in item


def test_processed_fields_md_only(tmp_path: Path):
    report = make_service().process(make_request(tmp_path, output_format="md"))
    item = report["processed"][0]
    assert "md_file" in item
    assert "txt_file" not in item


# ── 4. Resume behavior ───────────────────────────────────────


def test_txt_skips_when_matching_txt_exists(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_txt(base)

    def fail_fetch(_url: str) -> dict[str, Any]:
        raise AssertionError("metadata should not be fetched when txt already exists")

    service = TranscriptService(
        list_videos=lambda _url: list_single_video(),
        fetch_metadata=fail_fetch,
        download_subtitle=make_download_subtitle(),
        sleeper=lambda _delay: None,
    )

    report = service.process(make_request(tmp_path, output_format="txt"))
    assert report["processed_count"] == 0
    assert report["existing_count"] == 1
    assert report["skipped"][0]["reason"] == "already_exists"


def test_md_skips_when_matching_md_exists(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_md(base)

    def fail_fetch(_url: str) -> dict[str, Any]:
        raise AssertionError("metadata should not be fetched when md already exists")

    service = TranscriptService(
        list_videos=lambda _url: list_single_video(),
        fetch_metadata=fail_fetch,
        download_subtitle=make_download_subtitle(),
        sleeper=lambda _delay: None,
    )

    report = service.process(make_request(tmp_path, output_format="md"))
    assert report["processed_count"] == 0
    assert report["existing_count"] == 1


def test_both_still_requires_pair_and_repairs_partial(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_md(base)  # md only, txt missing

    report = make_service().process(make_request(tmp_path, output_format="both"))
    assert report["processed_count"] == 1
    assert report["partial_repaired_count"] == 1
    assert report["processed"][0]["partial_repaired"] is True
    assert (base / "txt" / f"{BASENAME}.txt").exists()


def test_txt_title_change_does_not_duplicate_when_index_matches(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_txt(base)

    service = make_service(listed_title="Changed Title", metadata_title="Changed Title")
    report = service.process(make_request(tmp_path, output_format="txt"))

    assert report["processed_count"] == 0
    assert report["existing_count"] == 1
    assert not (base / "txt" / "001_changed-title.txt").exists()


def test_md_title_change_does_not_duplicate_when_video_id_matches(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_md(base)

    service = make_service(listed_title="Changed Title", metadata_title="Changed Title")
    report = service.process(make_request(tmp_path, output_format="md"))

    assert report["processed_count"] == 0
    assert not (base / "md" / "001_changed-title.md").exists()


# ── 5. Dry-run ───────────────────────────────────────────────


def test_dry_run_respects_output_format_and_writes_nothing(tmp_path: Path):
    report = make_service().process(
        make_request(tmp_path, output_format="txt", dry_run=True)
    )
    base = tmp_path / CHANNEL_SLUG
    assert report["dry_run"] is True
    assert report["output_format"] == "txt"
    assert report["would_process_count"] == 1
    assert report["would_write_files"] is False
    assert report["planned"][0]["action"] == "process"
    assert not base.exists()


def test_dry_run_txt_reports_skip_when_txt_exists(tmp_path: Path):
    base = tmp_path / CHANNEL_SLUG
    write_existing_txt(base)

    report = make_service().process(
        make_request(tmp_path, output_format="txt", dry_run=True)
    )
    assert report["would_skip_existing_count"] == 1
    assert report["planned"][0]["action"] == "skip"
    assert not (base / "report.json").exists()


# ── 6. Timestamp parsing ─────────────────────────────────────


def test_format_timestamp_variants():
    assert format_timestamp("00:00:01.000") == "00:00:01"
    assert format_timestamp("01:02.500") == "00:01:02"
    assert format_timestamp("1:02:03,456") == "01:02:03"


def test_vtt_timestamps_produce_prefixed_lines(tmp_path: Path):
    sub_path = write_sub(tmp_path, VTT_CONTENT, "a.vtt")
    out = parse_subtitle_file(sub_path, timestamps=True)
    assert out == "[00:00:01] Hello world\n[00:00:05] Second cue"


def test_srt_timestamps_produce_prefixed_lines(tmp_path: Path):
    sub_path = write_sub(tmp_path, SRT_CONTENT, "a.srt")
    out = parse_subtitle_file(sub_path, timestamps=True)
    assert out == "[00:00:01] Hello world\n[00:00:05] Second cue"


def test_non_timestamp_parsing_remains_unchanged(tmp_path: Path):
    sub_path = write_sub(tmp_path, VTT_CONTENT, "a.vtt")
    assert parse_subtitle_file(sub_path) == "Hello world Second cue"


def test_keep_cues_preserved_in_timestamped_output(tmp_path: Path):
    content = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:02.000\n[Music]\n\n"
        "00:00:03.000 --> 00:00:04.000\nReal text\n"
    )
    sub_path = write_sub(tmp_path, content, "a.vtt")

    kept = parse_subtitle_file(sub_path, timestamps=True, keep_cues=True)
    assert "[00:00:01] [Music]" in kept

    dropped = parse_subtitle_file(sub_path, timestamps=True, keep_cues=False)
    assert "[Music]" not in dropped
    assert dropped == "[00:00:03] Real text"


def test_duplicate_cue_text_is_deduplicated_in_timestamped_output(tmp_path: Path):
    content = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:02.000\nHello world\n\n"
        "00:00:02.000 --> 00:00:03.000\nHello world\n\n"
        "00:00:03.000 --> 00:00:04.000\nBye\n"
    )
    sub_path = write_sub(tmp_path, content, "a.vtt")
    out = parse_subtitle_file(sub_path, timestamps=True)
    assert out == "[00:00:01] Hello world\n[00:00:03] Bye"


# ── 7. Markdown timestamp metadata ───────────────────────────


def test_md_includes_timestamp_metadata_only_when_enabled(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="md", timestamps=True))
    md_text = (tmp_path / CHANNEL_SLUG / "md" / f"{BASENAME}.md").read_text(encoding="utf-8")
    assert "timestamps: true" in md_text
    assert "[00:00:01] Hello world" in md_text


def test_md_excludes_timestamp_metadata_when_disabled(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="md"))
    md_text = (tmp_path / CHANNEL_SLUG / "md" / f"{BASENAME}.md").read_text(encoding="utf-8")
    assert "timestamps:" not in md_text


# ── 8. Index output ──────────────────────────────────────────


def test_index_links_to_txt_for_txt_format(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="txt"))
    index_text = (tmp_path / CHANNEL_SLUG / "index.md").read_text(encoding="utf-8")
    assert f"(txt/{BASENAME}.txt)" in index_text
    assert f"(md/{BASENAME}.md)" not in index_text


def test_index_links_to_md_for_both_format(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="both"))
    index_text = (tmp_path / CHANNEL_SLUG / "index.md").read_text(encoding="utf-8")
    assert f"(md/{BASENAME}.md)" in index_text


def test_index_links_to_md_for_md_format(tmp_path: Path):
    make_service().process(make_request(tmp_path, output_format="md"))
    index_text = (tmp_path / CHANNEL_SLUG / "index.md").read_text(encoding="utf-8")
    assert f"(md/{BASENAME}.md)" in index_text
