
import os, json, datetime, weakref, subprocess, sys, threading
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from utils.theme import *
from core.config import *
from ui.components.widgets import *
from ui.pages.pages import *
from downloader import Downloader, AUDIO_FORMATS, VIDEO_FORMATS, AUDIO_QUALITIES, VIDEO_QUALITIES, SUPPORTED_BROWSERS, THUMBNAIL_EMBED_SUPPORTED, BROWSER_PROFILE_PATHS
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPM's Media Tool")
        self.setMinimumSize(1000, 680)
        self.resize(1100, 760)

        self.settings = load_settings()
        self.setStyleSheet(build_stylesheet(self.settings.get("theme_accent", BLUE)))

        icon_path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
            'icon.ico'
        )
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._is_downloading = False
        self._queue: list[QueueItem] = []
        self._queue_running  = False
        self._pending: QueueItem | None = None

        self.bridge = Bridge()
        self.bridge.progress.connect(self._on_progress)
        self.bridge.complete.connect(self._on_complete)
        self.bridge.error.connect(self._on_error)
        self.bridge.thumb.connect(self._on_thumb)
        self.bridge.playlist_ready.connect(self._on_playlist_ready)
        self.bridge.info_fetched.connect(self._on_info_fetched)
        self.bridge.postprocess.connect(self._on_postprocess)

        self.downloader = Downloader()
        self.downloader.progress.connect(self.bridge.progress.emit)
        self.downloader.complete.connect(self.bridge.complete.emit)
        self.downloader.error.connect(self.bridge.error.emit)
        self.downloader.postprocess.connect(self.bridge.postprocess.emit)
        self.downloader.search_complete.connect(self._on_search_complete)
        self.downloader.search_error.connect(self._on_search_error)

        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self._check_schedule)
        self.target_time = None

        self.setAcceptDrops(True)
        self._build_ui()

    def closeEvent(self, event):
        if self._is_downloading:
            self.downloader.cancel()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    filepath = url.toLocalFile()
                    if filepath.endswith('.txt'):
                        urls.extend(self._extract_urls_from_file(filepath))
                else:
                    urls.append(url.toString())
        elif event.mimeData().hasText():
            text = event.mimeData().text()
            urls.extend(self._extract_urls_from_text(text))
        
        self._add_urls_to_queue(urls)
        event.acceptProposedAction()

    def _extract_urls_from_text(self, text: str) -> list[str]:
        return [w.strip() for w in text.split() if w.strip().startswith("http")]

    def _extract_urls_from_file(self, path: str) -> list[str]:
        urls = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip()
                    if w.startswith("http"):
                        urls.append(w)
        except Exception as e:
            self.logs_page.append(f"Dosya okuma hatası: {e}", RED)
        return urls

    def _add_urls_to_queue(self, urls: list[str]):
        if not urls:
            return
        for u in urls:
            item = QueueItem(
                url=u,
                quality=self.settings.get("default_quality", "Best Quality"),
                fmt=self.settings.get("default_format", "mp4"),
                output_dir=self.settings.get("download_path", os.path.expanduser("~/Downloads")),
                subtitles=self.settings.get("embed_subtitles", False),
                audio_quality=self.settings.get("default_audio_quality", "192"),
                embed_thumbnail=self.settings.get("embed_thumbnail", False),
                write_description=self.settings.get("write_description", False),
                embed_metadata=self.settings.get("embed_metadata", True)
            )
            self._queue.append(item)
            self.logs_page.append(f"Kuyruğa eklendi: {u}")
        self.q_page.refresh(self._queue)
        self._toast(f"{len(urls)} bağlantı kuyruğa eklendi", GREEN)
        self._switch_page("Kuyruk")

    def _import_batch(self):
        path, _ = QFileDialog.getOpenFileName(self, "Toplu İçe Aktar", "", "Metin Dosyaları (*.txt)")
        if path:
            urls = self._extract_urls_from_file(path)
            self._add_urls_to_queue(urls)

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_lay  = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 20, 12, 20)
        sb_lay.setSpacing(4)

        title_lbl = QLabel("RPM's Media Tool")
        title_lbl.setStyleSheet(
            f"color:{BLUE}; font-size:18px; font-weight:800; padding:0 8px 16px 8px;"
        )
        sb_lay.addWidget(title_lbl)

        self._pages = QStackedWidget()
        self._sidebar_btns: list[SidebarButton] = []

        nav_items = [
            ("⬇", "İndir",     self._make_download_page()),
            ("⏳", "Kuyruk",    self._make_queue_page()),
            ("🔍", "Arama",     self._make_search_page()),
            ("▶", "Oynatıcı",  self._make_player_page()),
            ("📋", "Geçmiş",    self._make_history_page()),
            ("📄", "Günlükler", self._make_logs_page()),
        ]
        for icon, name, page in nav_items:
            btn = SidebarButton(icon, name)
            btn.clicked.connect(lambda _, n=name: self._switch_page(n))
            sb_lay.addWidget(btn)
            self._sidebar_btns.append(btn)
            self._pages.addWidget(page)

        sb_lay.addStretch()
        sb_lay.addWidget(hdivider())
        sb_lay.addSpacing(6)

        self.cookie_btn = QPushButton("🍪 Çerezler")
        self.cookie_btn.setObjectName("ghostBtn")
        self.cookie_btn.setFixedHeight(36)
        self.cookie_btn.clicked.connect(self._open_cookie_dialog)
        sb_lay.addWidget(self.cookie_btn)

        self.cookie_status = QLabel("Çerez: Yok")
        self.cookie_status.setStyleSheet(
            f"color:{TEXT3}; font-size:10px; padding:2px 4px;"
        )
        self.cookie_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_lay.addWidget(self.cookie_status)
        sb_lay.addSpacing(6)

        settings_btn = QPushButton("⚙ Ayarlar")
        settings_btn.setObjectName("ghostBtn")
        settings_btn.setFixedHeight(36)
        settings_btn.clicked.connect(self._open_settings)
        sb_lay.addWidget(settings_btn)

        ver = QLabel("V2.3")
        ver.setStyleSheet(f"color:{TEXT3}; font-size:10px; padding:4px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_lay.addWidget(ver)

        main.addWidget(sidebar)
        main.addWidget(vdivider())
        main.addWidget(self._pages, stretch=1)

        self._switch_page("İndir")

    def _make_download_page(self) -> DownloadPage:
        self.dl_page = DownloadPage(self.settings)
        self.dl_page.request_download.connect(self._start_download)
        self.dl_page.request_queue.connect(self._add_to_queue)
        self.dl_page.request_info.connect(self._get_info)
        self.dl_page.cancel_btn.clicked.connect(self._cancel)
        return self.dl_page

    def _make_queue_page(self) -> QueuePage:
        self.q_page = QueuePage()
        self.q_page.request_start.connect(self._start_queue)
        self.q_page.request_clear.connect(self._clear_queue)
        self.q_page.remove_requested.connect(self._remove_from_queue)
        self.q_page.request_import.connect(self._import_batch)
        self.q_page.request_schedule.connect(self._schedule_queue)
        return self.q_page

    def _make_search_page(self) -> SearchPage:
        self.search_page = SearchPage()
        self.search_page.request_search.connect(self._do_search)
        self.search_page.request_queue_url.connect(self._add_search_url_to_queue)
        return self.search_page

    def _make_player_page(self) -> PlayerPage:
        self.player_page = PlayerPage(self.settings)
        self.player_page.request_play.connect(self._play_video)
        self.player_page.request_download.connect(self._download_from_player)
        return self.player_page

    def _play_video(self, url):
        self.logs_page.append(f"Oynatıcı için bilgi alınıyor: {url}")
        
        def run():
            try:
                info = self.downloader.get_info(url, flat_playlist=False)
                if not info:
                    self.bridge.error.emit("Video bilgisi alınamadı.")
                    return
                
                stream_url = info.get('url')
                if not stream_url:
                    formats = info.get('formats', [])
                    best_format = None
                    for f in reversed(formats):
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                            best_format = f
                            break
                    if best_format and 'url' in best_format:
                        stream_url = best_format['url']
                    elif formats:
                        stream_url = formats[-1].get('url')

                if stream_url:
                    import subprocess
                    import os
                    import sys
                    if getattr(sys, 'frozen', False):
                        base = sys._MEIPASS
                    else:
                        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    ffplay_path = os.path.join(base, "ffplay.exe")
                    
                    if not os.path.exists(ffplay_path):
                        ffplay_path = "ffplay"
                    
                    cmd = [ffplay_path, "-window_title", "YT-DLP Media Tool Oynatıcı", "-autoexit", stream_url]
                    self.logs_page.append(f"ffplay başlatılıyor...", BLUE)
                    subprocess.Popen(cmd)
                else:
                    self.bridge.error.emit("Akış bağlantısı bulunamadı.")
            except Exception as e:
                self.bridge.error.emit(f"Oynatıcı hatası: {str(e)}")
                
        import threading
        threading.Thread(target=run, daemon=True).start()

    def _download_from_player(self, item: QueueItem):
        self._queue.append(item)
        self.q_page.refresh(self._queue)
        self.logs_page.append(f"Oynatıcıdan kuyruğa eklendi: {item.url}", GREEN)
        self._toast("Oynatıcıdan kuyruğa eklendi", GREEN)
        self._switch_page("Kuyruk")

    def _do_search(self, query):
        self.logs_page.append(f"Arama başlatıldı: {query}")
        self.downloader.search(query, limit=10)

    def _on_search_complete(self, results):
        self.search_page.set_results(results)
        self.logs_page.append(f"Arama tamamlandı: {len(results)} sonuç", GREEN)

    def _on_search_error(self, err):
        self.search_page.list_widget.clear()
        self.search_page.list_widget.addItem(f"Hata: {err}")
        self.logs_page.append(f"Arama hatası: {err}", RED)

    def _add_search_url_to_queue(self, url):
        self._add_urls_to_queue([url])

    def _schedule_queue(self):
        time_str, ok = QInputDialog.getText(self, "İndirmeyi Zamanla", "Başlama saatini girin (SS:DD, örn. 03:00):")
        if ok and time_str:
            t = QTime.fromString(time_str.strip(), "hh:mm")
            if t.isValid():
                self.target_time = t
                self.schedule_timer.start(60000) # Check every minute
                self.q_page.schedule_btn.setText(f"⏳ {t.toString('hh:mm')}'da başlayacak")
                self.logs_page.append(f"Kuyruk başlatılması saat {t.toString('hh:mm')} için zamanlandı.", GREEN)
            else:
                self._toast("Geçersiz saat formatı!", RED)

    def _check_schedule(self):
        if self.target_time:
            now = QTime.currentTime()
            if now.hour() == self.target_time.hour() and now.minute() == self.target_time.minute():
                self.schedule_timer.stop()
                self.target_time = None
                self.q_page.schedule_btn.setText("⏰ Zamanla")
                self.logs_page.append("Zamanlanan indirme başlatılıyor!", GREEN)
                self._start_queue()

    def _make_history_page(self) -> HistoryPage:
        self.hist_page = HistoryPage()
        return self.hist_page

    def _make_logs_page(self) -> LogsPage:
        self.logs_page = LogsPage()
        return self.logs_page

    def _switch_page(self, name: str):
        names = ["İndir", "Kuyruk", "Arama", "Oynatıcı", "Geçmiş", "Günlükler"]
        idx   = names.index(name) if name in names else 0
        self._pages.setCurrentIndex(idx)
        for i, btn in enumerate(self._sidebar_btns):
            btn.setActive(i == idx)

    # ═══════════════════════════════════════════════════════
    #  DOWNLOAD FLOW
    # ═══════════════════════════════════════════════════════

    def _get_info(self, url: str):
        self.dl_page.set_status("Bilgi alınıyor…", TEXT3)
        self.dl_page.enable_info_btn(False)
        self.logs_page.append(f"Bilgi alınıyor: {url}")

        def run():
            try:
                info = self.downloader.get_info(url, flat_playlist=False)
            except RuntimeError as e:
                if "COOKIE_DB_LOCKED" in str(e):
                    self.bridge.error.emit("COOKIE_DB_LOCKED")
                    return
                self.bridge.complete.emit({"_type": "info_only", "info": None})
                return
            if not info:
                self.bridge.complete.emit({"_type": "info_only", "info": None})
                return
            if info.get("_type") in ("playlist", "multi_video") or "entries" in info:
                self.bridge.playlist_ready.emit(list(info.get("entries") or []))
            else:
                self.bridge.complete.emit({"_type": "info_only", "info": info})

        threading.Thread(target=run, daemon=True).start()

    def _start_download(self, item: QueueItem):
        if self._is_downloading:
            self._toast("Zaten bir indirme devam ediyor", YELLOW)
            return
        self._pending        = item
        self._is_downloading = True
        self.dl_page.show_cancel()
        self.dl_page.reset_progress()
        self.dl_page.set_status("İndiriliyor…", BLUE)
        self.logs_page.append(f"İndirme başladı: {item.url}")
        self.downloader.start(
            item.url, item.quality, item.fmt, item.output_dir,
            subtitles            = item.subtitles,
            audio_quality        = item.audio_quality,
            playlist_items       = item.playlist_items,
            embed_thumbnail      = item.embed_thumbnail,
            write_description    = item.write_description,
            concurrent_fragments = self.settings.get("concurrent_fragments", 4),
            start_time           = item.start_time,
            end_time             = item.end_time,
            embed_metadata       = getattr(item, "embed_metadata", True)
        )

    def _cancel(self):
        self.downloader.cancel()
        self.dl_page.set_status("İptal ediliyor…", TEXT3)

    def _add_to_queue(self, item: QueueItem):
        self.dl_page.set_status("Kuyruk için bilgi alınıyor…", TEXT3)

        def fetch():
            try:
                info = self.downloader.get_info(item.url, flat_playlist=False)
            except RuntimeError:
                info = None
            title = ""
            if info:
                title = info.get("title") or item.url
            item.title = title or item.url
            self.bridge.info_fetched.emit(item)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_info_fetched(self, item: QueueItem):
        self._queue.append(item)
        self.q_page.refresh(self._queue)
        self.dl_page.set_status(f"Kuyruğa eklendi ({len(self._queue)} öğe)", GREEN)
        self.logs_page.append(f"Kuyruğa eklendi: {item.title}")
        self._toast(f"Kuyruğa eklendi: {item.title[:40]}", GREEN)

    def _start_queue(self):
        if self._queue_running:
            return
        pending = [q for q in self._queue if q.status == "queued"]
        if not pending:
            self._toast("Kuyruk boş veya tamamlandı", YELLOW)
            return
        self._queue_running = True
        self._switch_page("İndir")
        self._run_next_in_queue()

    def _clear_queue(self):
        self._queue.clear()
        self.q_page.refresh(self._queue)

    def _remove_from_queue(self, idx: int):
        """QueuePage'den gelen silme isteğini MainWindow._queue üzerinde uygula."""
        if 0 <= idx < len(self._queue):
            self._queue.pop(idx)
            self.q_page.refresh(self._queue)

    def _run_next_in_queue(self):
        pending = [q for q in self._queue if q.status == "queued"]
        if not pending:
            self._queue_running = False
            self.dl_page.set_status("Kuyruk tamamlandı ✓", GREEN)
            self._toast("Tüm kuyruk tamamlandı!", GREEN)
            self.logs_page.append("Kuyruk tamamlandı")
            return
        item        = pending[0]
        item.status = "downloading"
        self.q_page.refresh(self._queue)
        self._start_download(item)

    # ═══════════════════════════════════════════════════════
    #  BRIDGE CALLBACKS
    # ═══════════════════════════════════════════════════════

    def _on_progress(self, pct, speed, eta, dl, total, fi, fc):
        self.dl_page.set_progress(pct, speed, eta, dl, total, fi, fc)

    def _on_postprocess(self):
        self.dl_page.show_postprocess(True)

    def _on_complete(self, info):
        # ── Get Info only ──────────────────────────────────
        if isinstance(info, dict) and info.get("_type") == "info_only":
            self.dl_page.enable_info_btn(True)
            data = info.get("info")
            if not data:
                self.dl_page.set_status("Bilgi alınamadı", RED)
                self.logs_page.append("Bilgi alınamadı", RED)
                return
            self.dl_page.show_info(data)
            self.dl_page.set_status("Bilgi yüklendi", GREEN)
            thumb_url = data.get('thumbnail')
            if thumb_url:
                def load():
                    try:
                        import urllib.request
                        req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=6) as resp:
                            img_data = resp.read()
                        img  = QImage()
                        img.loadFromData(img_data)
                        px   = QPixmap.fromImage(img).scaled(
                            180, 101,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        self.bridge.thumb.emit(px)
                    except Exception:
                        pass
                threading.Thread(target=load, daemon=True).start()
            return

        # ── Download complete ──────────────────────────────
        self._is_downloading = False
        self.dl_page.show_download()
        self.dl_page.show_postprocess(False)
        self.dl_page.progress_bar.setValue(1000)
        self.dl_page.pct_lbl.setText("100%")

        if isinstance(info, dict):
            # Playlist indirmesinde bireysel video bilgisi entries içinde olabilir
            entries = info.get("entries")
            if entries:
                # Playlist: her entry'yi ayrı geçmiş kaydı olarak ekle
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    title   = entry.get('title', 'Bilinmiyor')
                    ext     = entry.get('ext', '')
                    size_mb = (entry.get('filesize') or entry.get('filesize_approx') or 0) / (1024 * 1024)
                    url     = entry.get('webpage_url') or entry.get('url', '')
                    ts      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    self.hist_page.add_entry({
                        "title":      title,
                        "ext":        ext,
                        "size_mb":    round(size_mb, 2),
                        "url":        url,
                        "timestamp":  ts,
                        "output_dir": self._pending.output_dir if self._pending else "",
                    }, self.settings.get("max_history", 50))
                    self.logs_page.append(f"Tamamlandı: {title}", GREEN)
            else:
                title   = info.get('title', 'Bilinmiyor')
                ext     = info.get('ext', '')
                size_mb = (info.get('filesize') or info.get('filesize_approx') or 0) / (1024 * 1024)
                url     = info.get('webpage_url') or info.get('url', '')
                ts      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                self.hist_page.add_entry({
                    "title":      title,
                    "ext":        ext,
                    "size_mb":    round(size_mb, 2),
                    "url":        url,
                    "timestamp":  ts,
                    "output_dir": self._pending.output_dir if self._pending else "",
                }, self.settings.get("max_history", 50))
                self.logs_page.append(f"Tamamlandı: {title}", GREEN)

        if self._queue_running:
            for q in self._queue:
                if q.status == "downloading":
                    q.status = "done"
                    break
            self.q_page.refresh(self._queue)
            self.dl_page.reset_progress()
            self.dl_page.reset_preview()
            self._run_next_in_queue()
        else:
            self.dl_page.set_status("Tamamlandı ✓", GREEN)
            self._toast("İndirme tamamlandı!", GREEN)
            QTimer.singleShot(1500, self.dl_page.reset_preview)

    def _on_error(self, msg: str):
        self._is_downloading = False
        self.dl_page.show_download()
        self.dl_page.show_postprocess(False)

        if self._queue_running:
            for q in self._queue:
                if q.status == "downloading":
                    q.status = "error"
                    break
            self.q_page.refresh(self._queue)

        if msg == "Cancelled":
            self.dl_page.set_status("İptal edildi", TEXT3)
            self.dl_page.reset_progress()
            self._queue_running = False
            self.logs_page.append("İndirme iptal edildi", YELLOW)
            return

        if msg == "COOKIE_DB_LOCKED":
            browser = self.downloader.cookie_browser or "browser"
            dlg     = CookieLockedDialog(browser, parent=self)
            if dlg.exec():
                choice = dlg.choice()
                if self._pending is None:
                    self.dl_page.set_status("Tekrar denenecek indirme bulunamadı", RED)
                    self._queue_running = False
                    return
                if choice == "retry":
                    self.dl_page.set_status("Tekrar deneniyor…", BLUE)
                    self.dl_page.reset_progress()
                    self._is_downloading = False
                    self._start_download(self._pending)
                elif choice == "file":
                    self._apply_cookie(None, dlg.file_path())
                    self.dl_page.set_status("Çerez dosyasıyla tekrar deneniyor…", BLUE)
                    self.dl_page.reset_progress()
                    self._is_downloading = False
                    self._start_download(self._pending)
            else:
                self._queue_running = False
            return

        self.dl_page.set_status(f"Hata: {msg[:80]}", RED)
        self.logs_page.append(f"Hata: {msg}", RED)
        self._toast(f"Hata: {msg[:50]}", RED)

        if self._queue_running:
            self._run_next_in_queue()

    def _on_thumb(self, px: QPixmap):
        self.dl_page.show_thumb(px)

    def _on_playlist_ready(self, entries: list):
        self.dl_page.enable_info_btn(True)
        if not entries:
            self.dl_page.set_status("Oynatma listesinde video bulunamadı", RED)
            return
        dlg = PlaylistDialog(entries, parent=self)
        if dlg.exec():
            pl_str = dlg.playlist_items_str()
            if not pl_str:
                self.dl_page.set_status("Video seçilmedi", TEXT3)
                return
            n = len(dlg.selected_indices())
            self.logs_page.append(f"Oynatma listesi: {n} video seçildi")

            # Mevcut _pending varsa playlist_items güncelle,
            # yoksa URL'den yeni bir QueueItem oluştur
            url = self.dl_page.url_entry.text().strip()
            if self._pending:
                self._pending.playlist_items = pl_str
                item = self._pending
            else:
                item = self.dl_page._make_item()
                if not item:
                    self.dl_page.set_status("İndirme öğesi oluşturulamadı", RED)
                    return
                item.playlist_items = pl_str
            
            self.dl_page.set_status(
                f"Oynatma listesi hazır — {n} video seçildi, indirme başlıyor…", GREEN
            )
            self._start_download(item)
        else:
            self.dl_page.set_status("Oynatma listesi seçimi iptal edildi", TEXT3)

    # ═══════════════════════════════════════════════════════
    #  SETTINGS / COOKIES
    # ═══════════════════════════════════════════════════════

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, parent=self)
        if dlg.exec():
            self.settings = dlg.result_settings()
            save_settings(self.settings)
            self.setStyleSheet(build_stylesheet(self.settings.get("theme_accent", BLUE)))
            self.dl_page.update_settings(self.settings)
            self._toast("Ayarlar kaydedildi", GREEN)

    def _open_cookie_dialog(self):
        dlg = CookieDialog(
            self.downloader.cookie_browser,
            self.downloader.cookie_file,
            parent=self
        )
        if dlg.exec():
            self._apply_cookie(dlg.result_browser(), dlg.result_file())

    def _apply_cookie(self, browser, file):
        if browser:
            self.downloader.set_cookie_browser(browser)
            self.cookie_status.setText(f"🍪 {browser.capitalize()}")
            self.cookie_status.setStyleSheet(
                f"color:{GREEN}; font-size:10px; padding:2px 4px;"
            )
        elif file:
            self.downloader.set_cookie_file(file)
            self.cookie_status.setText(f"🍪 {os.path.basename(file)}")
            self.cookie_status.setStyleSheet(
                f"color:{GREEN}; font-size:10px; padding:2px 4px;"
            )
        else:
            self.downloader.cookie_browser = None
            self.downloader.cookie_file    = None
            self.cookie_status.setText("Çerez: Yok")
            self.cookie_status.setStyleSheet(
                f"color:{TEXT3}; font-size:10px; padding:2px 4px;"
            )

    # ═══════════════════════════════════════════════════════
    #  TOAST
    # ═══════════════════════════════════════════════════════

    def _toast(self, text: str, color: str = GREEN):
        t = Toast(self, text, color)
        t.show()

