import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError
import threading
import os
import sys
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

if getattr(sys, 'frozen', False):
    _base_exe = os.path.dirname(sys.executable)
    if os.path.exists(os.path.join(_base_exe, "ffmpeg.exe")):
        _base = _base_exe
    else:
        _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

_ffmpeg = os.path.join(_base, "ffmpeg.exe")
_FFMPEG_LOCATION = _base if os.path.isfile(_ffmpeg) else None
if _FFMPEG_LOCATION:
    os.environ["PATH"] = _base + os.pathsep + os.environ.get("PATH", "")


def _apply_ffmpeg_opts(opts):
    if _FFMPEG_LOCATION:
        opts['ffmpeg_location'] = _FFMPEG_LOCATION

BROWSER_PROFILE_PATHS = {
    "chrome": [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        os.path.expanduser("~/.config/google-chrome"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome"),
    ],
    "brave": [
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
        os.path.expanduser("~/.config/BraveSoftware/Brave-Browser"),
        os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser"),
    ],
    "firefox": [
        os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
        os.path.expanduser("~/.mozilla/firefox"),
        os.path.expanduser("~/Library/Application Support/Firefox/Profiles"),
    ],
    "edge": [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
        os.path.expanduser("~/.config/microsoft-edge"),
        os.path.expanduser("~/Library/Application Support/Microsoft Edge"),
    ],
    "opera": [
        os.path.expandvars(r"%APPDATA%\Opera Software\Opera Stable"),
        os.path.expanduser("~/.config/opera"),
    ],
    "chromium": [
        os.path.expandvars(r"%LOCALAPPDATA%\Chromium\User Data"),
        os.path.expanduser("~/.config/chromium"),
    ],
    "vivaldi": [
        os.path.expandvars(r"%LOCALAPPDATA%\Vivaldi\User Data"),
        os.path.expanduser("~/.config/vivaldi"),
    ],
}

AUDIO_FORMATS   = ["mp3", "aac", "flac", "wav", "opus", "m4a"]
VIDEO_FORMATS   = ["mp4", "webm", "mkv"]
AUDIO_QUALITIES = ["best", "320", "256", "192", "128", "96"]
VIDEO_QUALITIES = ["Best Quality", "2160p", "1440p", "1080p", "720p", "480p", "360p", "Audio Only"]

SUPPORTED_BROWSERS = ["brave", "chrome", "firefox", "edge", "opera", "chromium", "vivaldi", "safari"]

# Küçük resim gömmeyi destekleyen video formatları
THUMBNAIL_EMBED_SUPPORTED = {"mp4", "mkv", "m4a", "mp3", "ogg", "opus", "flac"}


class DownloadWorker(QRunnable):
    def __init__(self, downloader, url, quality, fmt, output_dir, subtitles, audio_quality, playlist_items, embed_thumbnail, write_description, concurrent_fragments, start_time, end_time, embed_metadata):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.quality = quality
        self.fmt = fmt
        self.output_dir = output_dir
        self.subtitles = subtitles
        self.audio_quality = audio_quality
        self.playlist_items = playlist_items
        self.embed_thumbnail = embed_thumbnail
        self.write_description = write_description
        self.concurrent_fragments = concurrent_fragments
        self.start_time = start_time
        self.end_time = end_time
        self.embed_metadata = embed_metadata

    def run(self):
        self.downloader._download(
            self.url, self.quality, self.fmt, self.output_dir,
            self.subtitles, self.audio_quality, self.playlist_items,
            self.embed_thumbnail, self.write_description, self.concurrent_fragments,
            self.start_time, self.end_time, self.embed_metadata
        )

class SearchWorker(QRunnable):
    def __init__(self, downloader, query, limit):
        super().__init__()
        self.downloader = downloader
        self.query = query
        self.limit = limit

    def run(self):
        self.downloader._search(self.query, self.limit)


class Downloader(QObject):
    progress = pyqtSignal(float, str, str, int, int, object, object)
    complete = pyqtSignal(dict)
    error = pyqtSignal(str)
    postprocess = pyqtSignal()
    search_complete = pyqtSignal(list)
    search_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancel_flag           = False
        self._ydl                   = None
        self._ydl_lock              = threading.Lock()
        self.cookie_browser         = None
        self.cookie_browser_profile = None
        self.cookie_file            = None

    # ── Public API ──────────────────────────────────────────

    def set_cookie_browser(self, browser, profile=None):
        self.cookie_browser         = browser
        self.cookie_browser_profile = profile
        self.cookie_file            = None

    def set_cookie_file(self, path):
        self.cookie_file            = path
        self.cookie_browser         = None
        self.cookie_browser_profile = None

    def start(self, url, quality, fmt, output_dir,
              subtitles=False, audio_quality="192",
              playlist_items=None, embed_thumbnail=False,
              write_description=False, concurrent_fragments=4,
              start_time="", end_time="", embed_metadata=True):
        self._cancel_flag = False
        worker = DownloadWorker(
            self, url, quality, fmt, output_dir,
            subtitles, audio_quality, playlist_items,
            embed_thumbnail, write_description, concurrent_fragments,
            start_time, end_time, embed_metadata
        )
        QThreadPool.globalInstance().start(worker)

    def search(self, query, limit=10):
        worker = SearchWorker(self, query, limit)
        QThreadPool.globalInstance().start(worker)

    def cancel(self):
        self._cancel_flag = True

    def get_info(self, url, flat_playlist=False):
        opts = {'quiet': True, 'no_warnings': True}
        if flat_playlist:
            opts['extract_flat'] = 'in_playlist'
        _apply_ffmpeg_opts(opts)
        self._apply_cookie_opts(opts)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except DownloadError as e:
            err = str(e)
            if "Could not copy" in err and "cookie" in err.lower():
                raise RuntimeError("COOKIE_DB_LOCKED")
            return None
        except Exception:
            return None

    def get_browser_profile_path(self, browser):
        paths = BROWSER_PROFILE_PATHS.get(browser.lower(), [])
        for p in paths:
            if os.path.isdir(p):
                return p
        return None

    # ── Internal ─────────────────────────────────────────────

    def _apply_cookie_opts(self, opts):
        if self.cookie_browser:
            if self.cookie_browser_profile:
                opts['cookiesfrombrowser'] = (
                    self.cookie_browser,
                    self.cookie_browser_profile,
                    None, None,
                )
            else:
                opts['cookiesfrombrowser'] = (self.cookie_browser,)
        elif self.cookie_file and os.path.isfile(self.cookie_file):
            opts['cookiefile'] = self.cookie_file

    def _progress_hook(self, d):
        if self._cancel_flag:
            raise Exception("Download cancelled")

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes') or 0
            total      = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if total > 0:
                percent = min(100.0, (downloaded / total) * 100.0)
            else:
                pstr = d.get('_percent_str', '0%').strip()
                try:
                    clean   = ''.join(c for c in pstr if c.isdigit() or c == '.')
                    percent = min(100.0, float(clean)) if clean else 0.0
                except Exception:
                    percent = 0.0

            speed_str  = d.get('_speed_str', '0 KB/s').strip()
            eta_str    = d.get('_eta_str',   '00:00').strip()
            frag_index = d.get('fragment_index')
            frag_count = d.get('fragment_count')
            self.progress.emit(percent, speed_str, eta_str, downloaded, total, frag_index, frag_count)

        elif d['status'] == 'finished':
            self.progress.emit(100.0, 'Done', '00:00', 0, 0, None, None)

    def _postprocess_hook(self, d):
        # yt-dlp post-processor durumları: 'started' / 'processing' / 'finished'.
        # Birleştirme/dönüştürme başladığında "İşleniyor…" göstergesini tetikle.
        if d.get('status') == 'started':
            self.postprocess.emit()

    def _download(self, url, quality, fmt, output_dir,
                  subtitles, audio_quality, playlist_items,
                  embed_thumbnail, write_description, concurrent_fragments,
                  start_time, end_time, embed_metadata):
        is_audio = (quality == "Audio Only")

        # Küçük resim gömme sadece desteklenen formatlarda aktif
        can_embed_thumbnail = embed_thumbnail and (fmt in THUMBNAIL_EMBED_SUPPORTED)

        # Video/ses kaynak formatlarını çıktı formatına göre belirle
        if not is_audio and fmt == "webm":
            _vext, _aext = "webm", "webm"
        elif not is_audio and fmt == "mkv":
            _vext, _aext = None, None
        else:
            _vext, _aext = "mp4", "m4a"

        def _fmt(vext, aext, height=None):
            h = f"[height<={height}]" if height else ""
            if vext and aext:
                return (f"bestvideo{h}[ext={vext}]+bestaudio[ext={aext}]"
                        f"/bestvideo{h}+bestaudio"
                        + (f"/best[height<={height}]" if height else "/best"))
            else:
                return f"bestvideo{h}+bestaudio/best{h}" if height else "bestvideo+bestaudio/best"

        format_map = {
            "Best Quality": _fmt(_vext, _aext),
            "2160p":        _fmt(_vext, _aext, 2160),
            "1440p":        _fmt(_vext, _aext, 1440),
            "1080p":        _fmt(_vext, _aext, 1080),
            "720p":         _fmt(_vext, _aext, 720),
            "480p":         _fmt(_vext, _aext, 480),
            "360p":         _fmt(_vext, _aext, 360),
            "Audio Only":   "bestaudio/best",
        }
        fmt_str = format_map.get(quality, "best")

        ydl_opts = {
            'format':                        fmt_str,
            'outtmpl':                       os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks':                [self._progress_hook],
            'postprocessor_hooks':           [self._postprocess_hook],
            'quiet':                         True,
            'no_warnings':                   True,
            'concurrent_fragment_downloads': concurrent_fragments,
        }
        _apply_ffmpeg_opts(ydl_opts)

        if playlist_items:
            ydl_opts['playlist_items'] = playlist_items

        if is_audio:
            pq = "0" if audio_quality == "best" else audio_quality
            _VALID_AUDIO_CODECS = {"mp3", "aac", "flac", "wav", "opus", "m4a", "vorbis", "alac"}
            codec = fmt if fmt in _VALID_AUDIO_CODECS else "mp3"
            pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': pq}]
            if can_embed_thumbnail:
                pp.append({'key': 'EmbedThumbnail'})
            ydl_opts['postprocessors'] = pp
            if can_embed_thumbnail:
                ydl_opts['writethumbnail']     = True
                ydl_opts['postprocessor_args'] = {'EmbedThumbnail': []}
        else:
            ydl_opts['merge_output_format'] = fmt
            if can_embed_thumbnail:
                ydl_opts['postprocessors'] = [
                    {'key': 'FFmpegMetadata'},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
                ]
                ydl_opts['writethumbnail'] = True

        if subtitles:
            ydl_opts.update({
                'writesubtitles':    True,
                'subtitleslangs':    ['en', 'tr'],
                'allsubtitles':      False,
                'writeautomaticsub': True,
            })

        if write_description:
            ydl_opts['writedescription'] = True

        if start_time or end_time:
            from yt_dlp.utils import parse_duration, download_range_func
            try:
                st = parse_duration(start_time) if start_time else 0
                et = parse_duration(end_time) if end_time else float('inf')
                if st > 0 or et != float('inf'):
                    ydl_opts['download_ranges'] = download_range_func(None, [(st, et)])
                    ydl_opts['force_keyframes_at_cuts'] = True
            except Exception:
                pass

        if embed_metadata:
            pp = ydl_opts.setdefault('postprocessors', [])
            if not any(p.get('key') == 'FFmpegMetadata' for p in pp):
                pp.insert(0, {'key': 'FFmpegMetadata', 'add_metadata': True})

        self._apply_cookie_opts(ydl_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                with self._ydl_lock:
                    self._ydl = ydl
                info = ydl.extract_info(url, download=True)
                if self._cancel_flag:
                    self.error.emit("Cancelled")
                    return
                self.complete.emit(info)
        except DownloadError as e:
            err = str(e)
            if self._cancel_flag or "Download cancelled" in err:
                self.error.emit("Cancelled")
            elif "Could not copy" in err and "cookie" in err.lower():
                self.error.emit("COOKIE_DB_LOCKED")
            else:
                self.error.emit(err)
        except (ExtractorError, PostProcessingError) as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Hata: {str(e)}")
        finally:
            with self._ydl_lock:
                self._ydl = None

    def _search(self, query, limit):
        opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
        }
        _apply_ffmpeg_opts(opts)
        self._apply_cookie_opts(opts)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                search_query = f"ytsearch{limit}:{query}"
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])
                results = []
                for e in entries:
                    results.append({
                        'title': e.get('title'),
                        'url': e.get('url'),
                        'duration': e.get('duration'),
                        'uploader': e.get('uploader') or 'Bilinmiyor',
                        'thumbnails': e.get('thumbnails', [])
                    })
                self.search_complete.emit(results)
        except Exception as e:
            self.search_error.emit(str(e))
