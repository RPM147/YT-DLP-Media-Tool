from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_spec_includes_transcript_runtime_modules():
    spec = (ROOT / "YT-DLP Media Tool.spec").read_text(encoding="utf-8")

    required_hiddenimports = [
        "transcript_worker",
        "core.transcripts",
        "core.transcripts.io",
        "core.transcripts.models",
        "core.transcripts.service",
        "core.transcripts.subtitle_parser",
        "core.transcripts.ytdlp_adapter",
    ]
    for module_name in required_hiddenimports:
        assert f"'{module_name}'" in spec


def test_transcript_feature_docs_cover_distribution_and_legal_notes():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    required_phrases = [
        "Transcript Archiving",
        "`both`",
        "`txt`",
        "`md`",
        "`metadata-only`",
        "`videos.json`",
        "`videos.csv`",
        "legal/copyright",
        "TRANSCRIPT_MANUAL_VERIFICATION.md",
    ]
    for phrase in required_phrases:
        assert phrase in readme


def test_manual_verification_covers_phase14_required_scenarios():
    manual = (ROOT / "TRANSCRIPT_MANUAL_VERIFICATION.md").read_text(encoding="utf-8")

    required_scenarios = [
        "Single video",
        "Playlist max 3",
        "Channel dry-run",
        "Format `txt`",
        "Format `md`",
        "Timestamps",
        "Metadata-only",
        "Manual-only",
        "Turkish language",
        "Cookie-required video",
        "Packaged build smoke",
    ]
    for scenario in required_scenarios:
        assert scenario in manual


def test_phase14_does_not_add_transcript_runtime_dependencies():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()

    normalized = {
        line.strip().lower()
        for line in requirements
        if line.strip() and not line.strip().startswith("#")
    }
    assert normalized == {"yt-dlp>=2025.1.1", "pyqt6>=6.6"}
