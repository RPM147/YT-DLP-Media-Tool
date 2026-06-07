from __future__ import annotations

import json

from core import config
from ui.components.widgets import SettingsDialog
from ui.pages.pages import TranscriptPage


def transcript_settings(**overrides):
    settings = config.DEFAULT_SETTINGS.copy()
    settings.update(overrides)
    return settings


def test_default_settings_include_transcript_defaults():
    assert config.DEFAULT_SETTINGS["transcript_output_path"].endswith("Transcripts")
    assert config.DEFAULT_SETTINGS["transcript_languages"] == "en,en-US,en-GB,en-orig"
    assert config.DEFAULT_SETTINGS["transcript_output_format"] == "both"
    assert config.DEFAULT_SETTINGS["transcript_timestamps"] is False
    assert config.DEFAULT_SETTINGS["transcript_metadata_only"] is False
    assert config.DEFAULT_SETTINGS["transcript_auto_fallback"] is True
    assert config.DEFAULT_SETTINGS["transcript_manual_only"] is False
    assert config.DEFAULT_SETTINGS["transcript_keep_cues"] is False
    assert config.DEFAULT_SETTINGS["transcript_retries"] == 3
    assert config.DEFAULT_SETTINGS["transcript_retry_delay"] == 2.0
    assert config.DEFAULT_SETTINGS["transcript_progress_interval"] == 10
    assert config.DEFAULT_SETTINGS["transcript_delay"] == 0.5


def test_load_settings_merges_transcript_defaults_for_older_files(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "download_path": str(tmp_path / "downloads"),
                "default_quality": "720p",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "SETTINGS_FILE", str(settings_file))

    loaded = config.load_settings()

    assert loaded["download_path"] == str(tmp_path / "downloads")
    assert loaded["default_quality"] == "720p"
    assert loaded["transcript_output_path"] == config.DEFAULT_SETTINGS["transcript_output_path"]
    assert loaded["transcript_languages"] == config.DEFAULT_SETTINGS["transcript_languages"]
    assert loaded["transcript_auto_fallback"] is True


def test_transcript_page_uses_saved_defaults(tmp_path, qtbot):
    settings = transcript_settings(
        transcript_output_path=str(tmp_path / "transcripts"),
        transcript_languages="tr,en",
        transcript_output_format="md",
        transcript_timestamps=True,
        transcript_metadata_only=True,
        transcript_auto_fallback=False,
        transcript_manual_only=True,
        transcript_keep_cues=True,
        transcript_retries=5,
        transcript_retry_delay=1.25,
        transcript_progress_interval=8,
        transcript_delay=0.25,
    )

    page = TranscriptPage(settings)
    qtbot.addWidget(page)

    assert page.output_entry.text() == str(tmp_path / "transcripts")
    assert page.lang_entry.text() == "tr,en"
    assert page.format_combo.currentText() == "md"
    assert page.timestamps_check.isChecked() is True
    assert page.metadata_only_check.isChecked() is True
    assert page.auto_fallback_check.isChecked() is False
    assert page.manual_only_check.isChecked() is True
    assert page.keep_cues_check.isChecked() is True
    assert page.retries_spin.value() == 5
    assert page.retry_delay_spin.value() == 1.25
    assert page.progress_interval_spin.value() == 8
    assert page.delay_spin.value() == 0.25


def test_transcript_page_update_settings_refreshes_idle_controls(tmp_path, qtbot):
    page = TranscriptPage(transcript_settings(transcript_output_path=str(tmp_path / "old")))
    qtbot.addWidget(page)

    page.update_settings(
        transcript_settings(
            transcript_output_path=str(tmp_path / "new"),
            transcript_languages="de,en",
            transcript_output_format="txt",
            transcript_auto_fallback=False,
            transcript_retries=6,
        )
    )

    assert page.output_entry.text() == str(tmp_path / "new")
    assert page.lang_entry.text() == "de,en"
    assert page.format_combo.currentText() == "txt"
    assert page.auto_fallback_check.isChecked() is False
    assert page.retries_spin.value() == 6


def test_transcript_page_update_settings_does_not_overwrite_running_job(tmp_path, qtbot):
    page = TranscriptPage(transcript_settings(transcript_output_path=str(tmp_path / "old")))
    qtbot.addWidget(page)
    page.set_running(True)

    page.update_settings(transcript_settings(transcript_output_path=str(tmp_path / "new")))

    assert page.output_entry.text() == str(tmp_path / "old")
    assert page._settings["transcript_output_path"] == str(tmp_path / "new")


def test_settings_dialog_saves_transcript_section(tmp_path, qtbot):
    dialog = SettingsDialog(transcript_settings())
    qtbot.addWidget(dialog)

    dialog.transcript_output_entry.setText(str(tmp_path / "out"))
    dialog.transcript_languages_entry.setText("tr,en")
    dialog.transcript_format_combo.setCurrentText("txt")
    dialog.transcript_timestamps_check.setChecked(True)
    dialog.transcript_metadata_only_check.setChecked(True)
    dialog.transcript_auto_fallback_check.setChecked(False)
    dialog.transcript_manual_only_check.setChecked(True)
    dialog.transcript_keep_cues_check.setChecked(True)
    dialog.transcript_retries_spin.setValue(7)
    dialog.transcript_retry_delay_spin.setValue(1.5)
    dialog.transcript_progress_interval_spin.setValue(9)
    dialog.transcript_delay_spin.setValue(0.75)

    dialog._save()
    saved = dialog.result_settings()

    assert saved["transcript_output_path"] == str(tmp_path / "out")
    assert saved["transcript_languages"] == "tr,en"
    assert saved["transcript_output_format"] == "txt"
    assert saved["transcript_timestamps"] is True
    assert saved["transcript_metadata_only"] is True
    assert saved["transcript_auto_fallback"] is False
    assert saved["transcript_manual_only"] is True
    assert saved["transcript_keep_cues"] is True
    assert saved["transcript_retries"] == 7
    assert saved["transcript_retry_delay"] == 1.5
    assert saved["transcript_progress_interval"] == 9
    assert saved["transcript_delay"] == 0.75
