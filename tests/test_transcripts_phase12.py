from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ui.main_window import MainWindow
from ui.pages.pages import TranscriptPage


def make_options(output_dir: str) -> dict:
    return {
        "url": "https://www.youtube.com/@phase12",
        "output_dir": output_dir,
        "languages": ("en",),
        "output_format": "both",
        "manual_only": False,
        "auto_fallback": True,
        "keep_cues": False,
        "timestamps": False,
        "metadata_only": False,
        "dry_run": False,
        "force": False,
        "max_videos": None,
        "start_index": None,
        "end_index": None,
        "retries": 3,
        "retry_delay": 2.0,
        "delay": 0.5,
        "progress_interval": 10,
    }


def test_transcript_page_enables_normal_result_actions(tmp_path, qtbot):
    page = TranscriptPage({"download_path": str(tmp_path)})
    qtbot.addWidget(page)
    seen = []
    page.request_open_path.connect(seen.append)

    report_path = tmp_path / "report.json"
    index_path = tmp_path / "index.md"
    page.set_result(
        {
            "output_path": str(tmp_path),
            "report_path": str(report_path),
            "index_path": str(index_path),
            "processed_count": 2,
            "skipped_count": 1,
        }
    )

    assert page.open_output_btn.isEnabled() is True
    assert page.open_primary_btn.text() == "Open Report"
    assert page.open_secondary_btn.text() == "Open Index"

    page.open_output_btn.click()
    page.open_primary_btn.click()
    page.open_secondary_btn.click()

    assert seen == [str(tmp_path), str(report_path), str(index_path)]


def test_transcript_page_uses_metadata_result_actions(tmp_path, qtbot):
    page = TranscriptPage({"download_path": str(tmp_path)})
    qtbot.addWidget(page)
    videos_json = tmp_path / "videos.json"
    videos_csv = tmp_path / "videos.csv"

    page.set_result(
        {
            "metadata_only": True,
            "selected_count": 3,
            "videos_json_path": str(videos_json),
            "videos_csv_path": str(videos_csv),
        }
    )

    assert page.open_output_btn.property("path") == str(tmp_path)
    assert page.open_primary_btn.text() == "Open JSON"
    assert page.open_primary_btn.property("path") == str(videos_json)
    assert page.open_secondary_btn.text() == "Open CSV"
    assert page.open_secondary_btn.property("path") == str(videos_csv)


def test_transcript_page_disables_result_actions_for_dry_run(tmp_path, qtbot):
    page = TranscriptPage({"download_path": str(tmp_path)})
    qtbot.addWidget(page)

    page.set_result(
        {
            "dry_run": True,
            "planned": [{"index": 1}],
            "output_path": str(tmp_path),
            "report_path": str(tmp_path / "report.json"),
        }
    )

    assert page.open_output_btn.isEnabled() is False
    assert page.open_primary_btn.isEnabled() is False
    assert page.open_secondary_btn.isEnabled() is False


def test_start_transcript_warns_but_does_not_mutate_media_queue(tmp_path):
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
    queued_item = SimpleNamespace(status="downloading")
    queue = [queued_item]
    window = SimpleNamespace(
        _is_transcribing=False,
        _is_downloading=True,
        _queue_running=True,
        _queue=queue,
        _transcript_worker=None,
        _last_transcript_options=None,
        transcript_page=MagicMock(),
        logs_page=MagicMock(),
        downloader=SimpleNamespace(
            cookie_browser=None,
            cookie_browser_profile=None,
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

    assert window._is_transcribing is True
    assert window._transcript_worker is FakeWorker.instances[0]
    assert queue == [queued_item]
    assert queued_item.status == "downloading"
    pool.start.assert_called_once_with(FakeWorker.instances[0])
    assert "paralel calisiyor" in window.logs_page.append.call_args_list[0].args[0]
    assert any(
        call.args[0] == "Media download active; transcript runs independently"
        for call in window._toast.call_args_list
    )


def test_open_transcript_path_uses_qdesktopservices_for_existing_path(tmp_path):
    target = tmp_path / "report.json"
    target.write_text("{}", encoding="utf-8")
    window = SimpleNamespace(logs_page=MagicMock(), _toast=MagicMock())

    with patch("ui.main_window.QDesktopServices.openUrl", return_value=True) as open_url:
        MainWindow._open_transcript_path(window, str(target))

    open_url.assert_called_once()
    assert "Transcript path acildi" in window.logs_page.append.call_args.args[0]
    window._toast.assert_not_called()


def test_open_transcript_path_reports_missing_path(tmp_path):
    target = tmp_path / "missing.json"
    window = SimpleNamespace(logs_page=MagicMock(), _toast=MagicMock())

    with patch("ui.main_window.QDesktopServices.openUrl") as open_url:
        MainWindow._open_transcript_path(window, str(target))

    open_url.assert_not_called()
    assert "bulunamadi" in window.logs_page.append.call_args.args[0]
    window._toast.assert_called_once()
