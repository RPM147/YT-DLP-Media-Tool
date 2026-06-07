from __future__ import annotations

from pathlib import Path

from core.transcripts import TranscriptRequest, TranscriptService


def sample_videos() -> list[dict]:
    return [
        {
            "id": "vid1",
            "title": "New Video",
            "url": "https://www.youtube.com/watch?v=vid1",
            "upload_date": "20240101",
        }
    ]


def fake_list_videos(_url: str) -> tuple[str, list[dict]]:
    return "Test Channel", sample_videos()


def fake_metadata(_url: str) -> dict:
    return {
        "title": "New Video",
        "upload_date": "20240101",
        "channel": "Test Channel",
        "subtitles": {"en": [{}]},
        "automatic_captions": {},
    }


def fake_download_subtitle(
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
Hello &amp; welcome [Music]
""",
        encoding="utf-8",
    )
    return path


def test_transcript_service_dry_run_writes_no_files(tmp_path: Path):
    def fail_metadata(_url: str) -> dict:
        raise AssertionError("dry-run must not fetch metadata")

    service = TranscriptService(list_videos=fake_list_videos, fetch_metadata=fail_metadata)

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            delay=0,
            dry_run=True,
        )
    )

    assert report["dry_run"] is True
    assert report["would_process_count"] == 1
    assert report["would_write_files"] is False
    assert not any(tmp_path.rglob("*"))


def test_transcript_service_process_writes_transcript_pair(tmp_path: Path):
    service = TranscriptService(
        list_videos=fake_list_videos,
        fetch_metadata=fake_metadata,
        download_subtitle=fake_download_subtitle,
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test/videos",
            output_dir=tmp_path,
            delay=0,
        )
    )

    base = tmp_path / "test-channel"
    txt_path = base / "txt" / "001_new-video.txt"
    md_path = base / "md" / "001_new-video.md"

    assert report["processed_count"] == 1
    assert txt_path.exists()
    assert md_path.exists()
    assert "Hello & welcome" in txt_path.read_text(encoding="utf-8")
    assert "[Music]" not in txt_path.read_text(encoding="utf-8")
    assert '"vid1"' in md_path.read_text(encoding="utf-8")
    assert (base / "report.json").exists()
    assert (base / "index.md").exists()


def test_transcript_backend_has_no_qt_imports():
    package_dir = Path(__file__).resolve().parents[1] / "core" / "transcripts"

    for path in package_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert "PyQt" not in content
        assert "QtCore" not in content
