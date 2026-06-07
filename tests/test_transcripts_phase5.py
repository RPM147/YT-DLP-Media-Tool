from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.transcripts import CookieLockedError, TranscriptRequest, TranscriptService
from core.transcripts.ytdlp_adapter import YtDlpTranscriptAdapter


class FakeYoutubeDL:
    calls: list[dict] = []
    raise_extract: Exception | None = None
    raise_download: Exception | None = None

    def __init__(self, opts):
        self.opts = opts
        self.calls.append({"method": "init", "opts": opts})

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def extract_info(self, url, download=False):
        self.calls.append(
            {
                "method": "extract_info",
                "url": url,
                "download": download,
                "opts": self.opts,
            }
        )
        if self.raise_extract:
            raise self.raise_extract
        if self.opts.get("extract_flat") == "in_playlist":
            return {
                "channel": "Test Channel",
                "entries": [
                    {
                        "id": "vid1",
                        "title": "Video",
                        "url": "https://www.youtube.com/watch?v=vid1",
                    }
                ],
            }
        return {
            "title": "Video",
            "channel": "Test Channel",
            "subtitles": {"tr": [{}]},
            "automatic_captions": {},
        }

    def download(self, urls):
        self.calls.append({"method": "download", "urls": urls, "opts": self.opts})
        if self.raise_download:
            raise self.raise_download
        out_dir = Path(self.opts["outtmpl"]).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "vid1.tr.vtt").write_text(
            """WEBVTT

00:00:01.000 --> 00:00:02.000
Merhaba
""",
            encoding="utf-8",
        )


@pytest.fixture(autouse=True)
def reset_fake_ytdlp():
    FakeYoutubeDL.calls = []
    FakeYoutubeDL.raise_extract = None
    FakeYoutubeDL.raise_download = None


def fake_ytdlp_module():
    return SimpleNamespace(YoutubeDL=FakeYoutubeDL)


def test_adapter_list_videos_normalizes_url_and_applies_browser_cookie():
    adapter = YtDlpTranscriptAdapter(
        cookie_browser="chrome",
        cookie_browser_profile="Default",
        ytdlp_module=fake_ytdlp_module(),
    )

    channel, videos = adapter.list_videos("https://www.youtube.com/@test")

    extract_call = [call for call in FakeYoutubeDL.calls if call["method"] == "extract_info"][0]
    opts = extract_call["opts"]
    assert channel == "Test Channel"
    assert videos[0]["id"] == "vid1"
    assert extract_call["url"] == "https://www.youtube.com/@test/videos"
    assert opts["extract_flat"] == "in_playlist"
    assert opts["skip_download"] is True
    assert opts["cookiesfrombrowser"] == ("chrome", "Default", None, None)


def test_adapter_fetch_metadata_applies_cookie_file(tmp_path: Path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# cookies", encoding="utf-8")
    adapter = YtDlpTranscriptAdapter(
        cookie_file=cookie_file,
        ytdlp_module=fake_ytdlp_module(),
    )

    metadata = adapter.fetch_metadata("https://example.com/vid1")

    extract_call = [call for call in FakeYoutubeDL.calls if call["method"] == "extract_info"][0]
    assert metadata["title"] == "Video"
    assert extract_call["opts"]["cookiefile"] == str(cookie_file)


def test_adapter_download_subtitle_uses_auto_caption_options(tmp_path: Path):
    adapter = YtDlpTranscriptAdapter(ytdlp_module=fake_ytdlp_module())

    path = adapter.download_subtitle(
        "https://example.com/vid1",
        "vid1",
        "tr",
        "auto",
        tmp_path,
    )

    download_call = [call for call in FakeYoutubeDL.calls if call["method"] == "download"][0]
    opts = download_call["opts"]
    assert path is not None
    assert path.name == "vid1.tr.vtt"
    assert opts["writesubtitles"] is False
    assert opts["writeautomaticsub"] is True
    assert opts["subtitleslangs"] == ["tr"]
    assert opts["subtitlesformat"] == "vtt/best"


def test_adapter_maps_cookie_lock_error_to_shared_code():
    FakeYoutubeDL.raise_extract = RuntimeError("Could not copy browser cookie database")
    adapter = YtDlpTranscriptAdapter(ytdlp_module=fake_ytdlp_module())

    with pytest.raises(CookieLockedError) as exc:
        adapter.fetch_metadata("https://example.com/vid1")

    assert str(exc.value) == "COOKIE_DB_LOCKED"


def test_service_defaults_to_ytdlp_adapter_with_cookie_options(tmp_path: Path):
    service = TranscriptService(
        cookie_browser="chrome",
        cookie_browser_profile="Default",
        ytdlp_module=fake_ytdlp_module(),
        sleeper=lambda _delay: None,
    )

    report = service.process(
        TranscriptRequest(
            url="https://www.youtube.com/@test",
            output_dir=tmp_path,
            languages=("tr",),
            delay=0,
        )
    )

    init_calls = [call for call in FakeYoutubeDL.calls if call["method"] == "init"]
    assert report["processed_count"] == 1
    assert report["processed"][0]["subtitle_lang"] == "tr"
    assert all(
        call["opts"]["cookiesfrombrowser"] == ("chrome", "Default", None, None)
        for call in init_calls
    )


def test_service_surfaces_cookie_lock_instead_of_skipping(tmp_path: Path):
    FakeYoutubeDL.raise_extract = RuntimeError("Could not copy browser cookie database")
    service = TranscriptService(
        ytdlp_module=fake_ytdlp_module(),
        sleeper=lambda _delay: None,
    )

    with pytest.raises(CookieLockedError):
        service.process(
            TranscriptRequest(
                url="https://www.youtube.com/@test",
                output_dir=tmp_path,
                languages=("tr",),
                delay=0,
            )
        )
