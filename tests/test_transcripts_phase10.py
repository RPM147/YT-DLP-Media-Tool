from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.transcripts import TranscriptProgress
from ui.main_window import MainWindow
from ui.pages.pages import TranscriptPage


def make_options(output_dir: str) -> dict:
    return {
        "url": "https://www.youtube.com/@phase10",
        "output_dir": output_dir,
        "languages": ("tr", "en"),
        "output_format": "md",
        "manual_only": True,
        "auto_fallback": False,
        "keep_cues": True,
        "timestamps": True,
        "metadata_only": True,
        "dry_run": False,
        "force": True,
        "max_videos": None,
        "start_index": 3,
        "end_index": 5,
        "retries": 4,
        "retry_delay": 1.25,
        "delay": 0.25,
        "progress_interval": 7,
    }


def test_transcript_page_collects_phase10_options(tmp_path, qtbot):
    page = TranscriptPage({"download_path": str(tmp_path)})
    qtbot.addWidget(page)

    page.url_entry.setText("https://www.youtube.com/@phase10")
    page.output_entry.setText(str(tmp_path / "out"))
    page.lang_entry.setText("tr, en, ")
    page.format_combo.setCurrentText("md")
    page.manual_only_check.setChecked(True)
    page.auto_fallback_check.setChecked(False)
    page.keep_cues_check.setChecked(True)
    page.timestamps_check.setChecked(True)
    page.metadata_only_check.setChecked(True)
    page.force_check.setChecked(True)
    page.start_index_spin.setValue(3)
    page.end_index_spin.setValue(5)
    page.retries_spin.setValue(4)
    page.retry_delay_spin.setValue(1.25)
    page.delay_spin.setValue(0.25)
    page.progress_interval_spin.setValue(7)

    values = page.values()

    assert values == make_options(str(tmp_path / "out"))


def test_transcript_page_emits_valid_start_and_rejects_missing_url(tmp_path, qtbot):
    page = TranscriptPage({"download_path": str(tmp_path)})
    qtbot.addWidget(page)
    seen = []
    page.request_start.connect(seen.append)

    page.url_entry.setText("")
    page._emit_start()

    assert seen == []
    assert page.status_lbl.text() == "URL gerekli"

    page.url_entry.setText("https://www.youtube.com/@phase10")
    page.output_entry.setText(str(tmp_path))
    page._emit_start()

    assert seen[0]["url"] == "https://www.youtube.com/@phase10"
    assert seen[0]["output_dir"] == str(tmp_path)


def test_main_window_builds_transcript_request_from_ui_options(tmp_path):
    request = MainWindow._build_transcript_request(make_options(str(tmp_path)))

    assert request.url == "https://www.youtube.com/@phase10"
    assert request.output_dir == tmp_path
    assert request.languages == ("tr", "en")
    assert request.output_format == "md"
    assert request.manual_only is True
    assert request.auto_fallback is False
    assert request.keep_cues is True
    assert request.timestamps is True
    assert request.metadata_only is True
    assert request.force is True
    assert request.start_index == 3
    assert request.end_index == 5
    assert request.retries == 4
    assert request.retry_delay == 1.25
    assert request.delay == 0.25
    assert request.progress_interval == 7


def test_transcript_start_wires_worker_with_cookies_and_page_state(tmp_path):
    class FakeSignal:
        def __init__(self) -> None:
            self.slots = []

        def connect(self, slot):
            self.slots.append(slot)

    class FakeSignals:
        def __init__(self) -> None:
            self.progress = FakeSignal()
            self.log = FakeSignal()
            self.result = FakeSignal()
            self.error = FakeSignal()
            self.error_detail = FakeSignal()
            self.cancelled = FakeSignal()
            self.finished = FakeSignal()

    class FakeWorker:
        instances = []

        def __init__(self, request, **kwargs) -> None:
            self.request = request
            self.kwargs = kwargs
            self.signals = FakeSignals()
            FakeWorker.instances.append(self)

    pool = MagicMock()
    window = SimpleNamespace(
        _is_transcribing=False,
        _transcript_worker=None,
        _last_transcript_options=None,
        transcript_page=MagicMock(),
        logs_page=MagicMock(),
        downloader=SimpleNamespace(
            cookie_browser="firefox",
            cookie_browser_profile="default-release",
            cookie_file=None,
        ),
        _toast=MagicMock(),
        _on_transcript_progress=MagicMock(),
        _on_transcript_result=MagicMock(),
        _on_transcript_error=MagicMock(),
        _on_transcript_cancelled=MagicMock(),
        _on_transcript_finished=MagicMock(),
        _build_transcript_request=MainWindow._build_transcript_request,
    )

    with (
        patch("ui.main_window.TranscriptWorker", FakeWorker),
        patch("ui.main_window.QThreadPool.globalInstance", return_value=pool),
    ):
        MainWindow._start_transcript(window, make_options(str(tmp_path)))

    worker = FakeWorker.instances[0]
    assert window._is_transcribing is True
    assert window._transcript_worker is worker
    assert worker.request.output_dir == tmp_path
    assert worker.kwargs["cookie_browser"] == "firefox"
    assert worker.kwargs["cookie_browser_profile"] == "default-release"
    assert worker.kwargs["cookie_file"] is None
    assert worker.signals.progress.slots == [window._on_transcript_progress]
    pool.start.assert_called_once_with(worker)
    window.transcript_page.set_running.assert_called_once_with(True)
    window.transcript_page.reset_progress.assert_called_once()


def test_transcript_progress_is_mirrored_to_page_and_logs():
    window = SimpleNamespace(transcript_page=MagicMock(), logs_page=MagicMock())
    progress = TranscriptProgress(
        index=2,
        total=5,
        global_index=12,
        video_id="vid2",
        title="Video 2",
        action="saved",
        message="manual, en",
    )

    MainWindow._on_transcript_progress(window, progress)

    window.transcript_page.add_progress.assert_called_once_with(progress)
    window.logs_page.append.assert_called_once()
    assert "Transcript saved: Video 2 manual, en" in window.logs_page.append.call_args.args[0]


def test_transcript_result_updates_page_and_logs_summary():
    window = SimpleNamespace(
        transcript_page=MagicMock(),
        logs_page=MagicMock(),
        _toast=MagicMock(),
    )

    MainWindow._on_transcript_result(
        window,
        {
            "processed_count": 2,
            "skipped_count": 1,
            "partial_repaired_count": 1,
        },
    )

    window.transcript_page.set_result.assert_called_once()
    window.transcript_page.set_status.assert_called_once()
    window.logs_page.append.assert_called_once()
    assert "2 kayit, 1 skip, 1 repair" in window.logs_page.append.call_args.args[0]
    window._toast.assert_called_once()


def test_transcript_finished_starts_pending_retry_after_old_worker_finishes():
    retry_options = {"url": "https://www.youtube.com/@phase10"}
    window = SimpleNamespace(
        _transcript_retry_options=retry_options,
        _is_transcribing=True,
        _transcript_worker=MagicMock(),
        transcript_page=MagicMock(),
        _start_transcript=MagicMock(),
    )

    with patch("ui.main_window.QTimer.singleShot") as single_shot:
        MainWindow._on_transcript_finished(window)

    assert window._is_transcribing is False
    assert window._transcript_worker is None
    assert window._transcript_retry_options is None
    window.transcript_page.set_running.assert_called_once_with(False)

    delay, callback = single_shot.call_args.args
    assert delay == 0
    callback()
    window._start_transcript.assert_called_once_with(retry_options)
