import pytest
import os
from unittest.mock import patch, MagicMock
from downloader import Downloader

@pytest.fixture
def downloader(qtbot):
    dl = Downloader()
    return dl

def test_downloader_initialization(downloader):
    assert downloader._cancel_flag is False
    assert downloader._ydl is None
    assert downloader.cookie_browser is None

def test_set_cookie_browser(downloader):
    downloader.set_cookie_browser("chrome", "Default")
    assert downloader.cookie_browser == "chrome"
    assert downloader.cookie_browser_profile == "Default"
    assert downloader.cookie_file is None

def test_set_cookie_file(downloader):
    downloader.set_cookie_file("/path/to/cookies.txt")
    assert downloader.cookie_file == "/path/to/cookies.txt"
    assert downloader.cookie_browser is None
    assert downloader.cookie_browser_profile is None

@patch("downloader.yt_dlp.YoutubeDL")
def test_get_info(mock_ydl, downloader):
    # Setup mock
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {"id": "test_id", "title": "Test Video"}
    
    # Call method
    info = downloader.get_info("https://example.com/video")
    
    # Assert
    assert info is not None
    assert info["title"] == "Test Video"
    mock_instance.extract_info.assert_called_once_with("https://example.com/video", download=False)

def test_downloader_cancel(downloader):
    downloader._ydl = MagicMock()
    downloader._ydl.params = {}
    downloader.cancel()
    assert downloader._cancel_flag is True
    assert downloader._ydl.params.get('abort_on_error') is True
