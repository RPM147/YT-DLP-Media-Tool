import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError
import threading
import os
import sys

# FFmpeg yolu
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

_ffmpeg = os.path.join(_base, "ffmpeg.exe")
if os.path.isfile(_ffmpeg):
    os.environ["PATH"] = _base + os.pathsep + os.environ.get("PATH", "")

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


class Downloader:
    def __init__(self, on_progress, on_complete, on_error, on_postprocess=None):
        self.on_progress            = on_progress
        self.on_complete            = on_complete
        self.on_error               = on_error
        self.on_postprocess         = on_postprocess or (lambda: None)
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
              write_description=False, concurrent_fragments=4):
        self._cancel_flag = False
        threading.Thread(
            target=self._download,
            args=(url, quality, fmt, output_dir,
                  subtitles, audio_quality, playlist_items,
                  embed_thumbnail, write_description, concurrent_fragments),
            daemon=True
        ).start()

    def cancel(self):
        self._cancel_flag = True
        with self._ydl_lock:
            ydl = self._ydl
        if ydl:
            try:
                ydl.params['abort_on_error'] = True
            except Exception:
                pass

    def get_info(self, url, flat_playlist=False):
        opts = {'quiet': True, 'no_warnings': True}
        if flat_playlist:
            opts['extract_flat'] = 'in_playlist'
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
            self.on_progress(percent, speed_str, eta_str, downloaded, total, frag_index, frag_count)

        elif d['status'] == 'finished':
            self.on_progress(100.0, 'Done', '00:00', 0, 0, None, None)

        elif d['status'] == 'processing':
            self.on_postprocess()

    def _download(self, url, quality, fmt, output_dir,
                  subtitles, audio_quality, playlist_items,
                  embed_thumbnail, write_description, concurrent_fragments):
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
            'quiet':                         True,
            'no_warnings':                   True,
            'concurrent_fragment_downloads': concurrent_fragments,
        }

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

        self._apply_cookie_opts(ydl_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                with self._ydl_lock:
                    self._ydl = ydl
                info = ydl.extract_info(url, download=True)
                if self._cancel_flag:
                    self.on_error("Cancelled")
                    return
                self.on_complete(info)
        except DownloadError as e:
            err = str(e)
            if self._cancel_flag or "Download cancelled" in err:
                self.on_error("Cancelled")
            elif "Could not copy" in err and "cookie" in err.lower():
                self.on_error("COOKIE_DB_LOCKED")
            else:
                self.on_error(err)
        except (ExtractorError, PostProcessingError) as e:
            self.on_error(str(e))
        except Exception as e:
            err = str(e)
            if self._cancel_flag or "Download cancelled" in err:
                self.on_error("Cancelled")
            elif "Could not copy" in err and "cookie" in err.lower():
                self.on_error("COOKIE_DB_LOCKED")
            else:
                self.on_error(err)
        finally:
            with self._ydl_lock:
                self._ydl = None