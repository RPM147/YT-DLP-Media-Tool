from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from PyQt6.QtCore import QDateTime

from downloader import Downloader
from ui.main_window import MainWindow
from ui.pages.pages import SearchPage


def test_schedule_time_today_when_future():
    now = QDateTime.fromString("2026-06-06 10:30", "yyyy-MM-dd HH:mm")

    target = MainWindow._parse_schedule_target("11:00", now)

    assert target.toString("yyyy-MM-dd HH:mm") == "2026-06-06 11:00"


def test_schedule_time_rolls_to_tomorrow_when_past_today():
    now = QDateTime.fromString("2026-06-06 10:30", "yyyy-MM-dd HH:mm")

    target = MainWindow._parse_schedule_target("10:00", now)

    assert target.toString("yyyy-MM-dd HH:mm") == "2026-06-07 10:00"


def test_schedule_accepts_explicit_future_datetime():
    now = QDateTime.fromString("2026-06-06 10:30", "yyyy-MM-dd HH:mm")

    target = MainWindow._parse_schedule_target("2026-06-07 03:15", now)

    assert target.toString("yyyy-MM-dd HH:mm") == "2026-06-07 03:15"


def test_schedule_rejects_invalid_or_past_explicit_datetime():
    now = QDateTime.fromString("2026-06-06 10:30", "yyyy-MM-dd HH:mm")

    assert MainWindow._parse_schedule_target("not a time", now) is None
    assert MainWindow._parse_schedule_target("2026-06-05 03:15", now) is None


def test_search_duration_formatting():
    assert SearchPage._format_duration(215) == "3:35"
    assert SearchPage._format_duration(3661) == "1:01:01"
    assert SearchPage._format_duration(None) == "Bilinmiyor"
    assert SearchPage._format_duration("bad") == "Bilinmiyor"


@patch("downloader.yt_dlp.YoutubeDL")
def test_get_info_applies_ffmpeg_location(mock_ydl, monkeypatch):
    monkeypatch.setattr("downloader._FFMPEG_LOCATION", r"C:\tools\ffmpeg")
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {"id": "test_id"}

    Downloader().get_info("https://example.com/video")

    opts = mock_ydl.call_args.args[0]
    assert opts["ffmpeg_location"] == r"C:\tools\ffmpeg"


@patch("ui.main_window.QTimer.singleShot")
def test_download_complete_clears_pending_for_single_download(mock_single_shot):
    window = SimpleNamespace(
        _pending=SimpleNamespace(output_dir="downloads"),
        _queue_running=False,
        settings={"max_history": 50},
        dl_page=MagicMock(),
        hist_page=MagicMock(),
        logs_page=MagicMock(),
        _toast=MagicMock(),
    )

    MainWindow._on_complete(window, {"title": "Done", "ext": "mp4", "webpage_url": "https://example.com"})

    assert window._pending is None
    window.hist_page.add_entry.assert_called_once()
    mock_single_shot.assert_called_once()


def test_download_complete_clears_pending_before_queue_continues():
    item = SimpleNamespace(status="downloading")
    window = SimpleNamespace(
        _pending=SimpleNamespace(output_dir="downloads"),
        _queue_running=True,
        _queue=[item],
        settings={"max_history": 50},
        dl_page=MagicMock(),
        hist_page=MagicMock(),
        logs_page=MagicMock(),
        q_page=MagicMock(),
        _run_next_in_queue=MagicMock(),
    )

    MainWindow._on_complete(window, {"title": "Done", "ext": "mp4", "webpage_url": "https://example.com"})

    assert window._pending is None
    assert item.status == "done"
    window._run_next_in_queue.assert_called_once()
