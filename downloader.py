import yt_dlp
import threading
import os
import sys

# Paketlenmiş .exe içindeki FFmpeg'i bul
if getattr(sys, 'frozen', False):
    # PyInstaller ile paketlenmiş
    _base = sys._MEIPASS
else:
    # Normal Python
    _base = os.path.dirname(os.path.abspath(__file__))

_ffmpeg = os.path.join(_base, "ffmpeg.exe")
_ffprobe = os.path.join(_base, "ffprobe.exe")

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


class Downloader:
    def __init__(self, on_progress, on_complete, on_error):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error    = on_error
        self._cancel_flag = False
        self._ydl         = None

        self.cookie_browser         = None
        self.cookie_browser_profile = None
        self.cookie_file            = None

    # ─────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────

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
              playlist_items=None):
        self._cancel_flag = False
        threading.Thread(
            target=self._download,
            args=(url, quality, fmt, output_dir,
                  subtitles, audio_quality, playlist_items),
            daemon=True
        ).start()

    def cancel(self):
        self._cancel_flag = True

    def get_info(self, url, flat_playlist=False):
        opts = {'quiet': True, 'no_warnings': True}
        if flat_playlist:
            opts['extract_flat'] = 'in_playlist'
        self._apply_cookie_opts(opts)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            return None

    def get_browser_profile_path(self, browser):
        paths = BROWSER_PROFILE_PATHS.get(browser.lower(), [])
        for p in paths:
            if os.path.isdir(p):
                return p
        return None

    # ─────────────────────────────────────────────
    #  Internal
    # ─────────────────────────────────────────────

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
            # downloaded_bytes / total_bytes üzerinden hesapla — %9000 sorununu önler
            downloaded = d.get('downloaded_bytes') or 0
            total      = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if total > 0:
                percent = min(100.0, (downloaded / total) * 100.0)
            else:
                # fallback: _percent_str'dan parse et, yine de 100 ile sınırla
                pstr = d.get('_percent_str', '0%').strip()
                try:
                    clean   = ''.join(c for c in pstr if c.isdigit() or c == '.')
                    percent = min(100.0, float(clean)) if clean else 0.0
                except Exception:
                    percent = 0.0

            speed_str = d.get('_speed_str', '0 KB/s').strip()
            eta_str   = d.get('_eta_str',   '00:00').strip()
            self.on_progress(percent, speed_str, eta_str)

        elif d['status'] == 'finished':
            self.on_progress(100.0, 'Done', '00:00')

    def _download(self, url, quality, fmt, output_dir,
                  subtitles, audio_quality, playlist_items):
        is_audio = (quality == "Audio Only")

        format_map = {
            "Best Quality": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "1080p":  "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "720p":   "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "480p":   "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
            "360p":   "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best",
            "Audio Only": "bestaudio/best",
        }

        fmt_str = format_map.get(quality, "best")

        ydl_opts = {
            'format':         fmt_str,
            'outtmpl':        os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'quiet':          True,
            'no_warnings':    True,
        }

        if playlist_items:
            ydl_opts['playlist_items'] = playlist_items

        if is_audio:
            # Ses kalitesi: "best" → preferredquality "0" (en yüksek)
            pq = "0" if audio_quality == "best" else audio_quality
            ydl_opts['postprocessors'] = [{
                'key':              'FFmpegExtractAudio',
                'preferredcodec':   fmt,
                'preferredquality': pq,
            }]
        else:
            ydl_opts['merge_output_format'] = fmt
            if subtitles:
                ydl_opts.update({
                    'writesubtitles':    True,
                    'subtitleslangs':    ['en', 'tr'],
                    'allsubtitles':      False,
                    'writeautomaticsub': True,
                })

        self._apply_cookie_opts(ydl_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._ydl = ydl
                info = ydl.extract_info(url, download=True)
                self.on_complete(info)
        except Exception as e:
            err = str(e)
            if "Download cancelled" in err:
                self.on_error("Cancelled")
            elif "Could not copy" in err and "cookie" in err.lower():
                self.on_error("COOKIE_DB_LOCKED")
            else:
                self.on_error(err)