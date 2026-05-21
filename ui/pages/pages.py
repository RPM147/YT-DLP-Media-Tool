
import os, json, datetime, weakref, subprocess, sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from utils.theme import *
from core.config import *
from ui.components.widgets import *
from downloader import Downloader, AUDIO_FORMATS, VIDEO_FORMATS, AUDIO_QUALITIES, VIDEO_QUALITIES, SUPPORTED_BROWSERS, THUMBNAIL_EMBED_SUPPORTED, BROWSER_PROFILE_PATHS
class Bridge(QObject):
    progress       = pyqtSignal(float, str, str, int, int, object, object)
    complete       = pyqtSignal(object)
    error          = pyqtSignal(str)
    thumb          = pyqtSignal(object)
    playlist_ready = pyqtSignal(object)
    info_fetched   = pyqtSignal(object)
    postprocess    = pyqtSignal()


# ═══════════════════════════════════════════════════════════
#  QUEUE ITEM
# ═══════════════════════════════════════════════════════════
class QueueItem:
    def __init__(self, url, quality, fmt, output_dir, subtitles,
                 audio_quality, playlist_items=None, title="",
                 embed_thumbnail=False, write_description=False,
                 start_time="", end_time="", embed_metadata=True):
        self.url               = url
        self.quality           = quality
        self.fmt               = fmt
        self.output_dir        = output_dir
        self.subtitles         = subtitles
        self.audio_quality     = audio_quality
        self.playlist_items    = playlist_items
        self.embed_thumbnail   = embed_thumbnail
        self.write_description = write_description
        self.start_time        = start_time
        self.end_time          = end_time
        self.embed_metadata    = embed_metadata
        self.title             = title or url
        self.status            = "queued"


# ═══════════════════════════════════════════════════════════
#  DOWNLOAD PAGE
# ═══════════════════════════════════════════════════════════
class DownloadPage(QWidget):
    request_download = pyqtSignal(object)
    request_queue    = pyqtSignal(object)
    request_info     = pyqtSignal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._build()

    def update_settings(self, s: dict):
        self._settings = s
        self.quality_combo.setCurrentText(s.get("default_quality", "Best Quality"))
        self.subs_check.setChecked(s.get("embed_subtitles", False))
        self.thumb_check.setChecked(s.get("embed_thumbnail", False))
        self.desc_check.setChecked(s.get("write_description", False))
        self._on_quality_changed(self.quality_combo.currentText())

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget(); inner.setObjectName("root")
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(28, 24, 28, 28)
        self._lay.setSpacing(16)

        self._build_url_card()
        self._build_preview_card()
        self._build_options_card()
        self._build_dl_button()
        self._build_progress_card()
        self._lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    def _build_url_card(self):
        c_lay = QVBoxLayout()
        c     = card(c_lay)

        top = QHBoxLayout()
        top.addWidget(label("🔗 URL", 12, TEXT2, bold=True))
        top.addStretch()
        self._url_clear = QPushButton("✕")
        self._url_clear.setObjectName("ghostBtn")
        self._url_clear.setFixedSize(24, 24)
        self._url_clear.clicked.connect(lambda: self.url_entry.clear())
        top.addWidget(self._url_clear)
        c_lay.addLayout(top)

        row = QHBoxLayout(); row.setSpacing(8)
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("YouTube, Instagram, TikTok, X, Twitch ve daha fazlası…")
        self.url_entry.setFixedHeight(42)
        self.url_entry.returnPressed.connect(self._emit_info)
        row.addWidget(self.url_entry, stretch=1)

        paste_btn = QPushButton("📋 Yapıştır")
        paste_btn.setFixedHeight(42)
        paste_btn.clicked.connect(self._paste)
        row.addWidget(paste_btn)

        self.info_btn = make_accent_btn("Bilgi Al →", SAPPHIRE)
        self.info_btn.setFixedHeight(42)
        self.info_btn.setFixedWidth(110)
        self.info_btn.clicked.connect(self._emit_info)
        row.addWidget(self.info_btn)
        c_lay.addLayout(row)

        self._lay.addWidget(c)

    def _build_preview_card(self):
        c_lay = QHBoxLayout()
        c_lay.setContentsMargins(16, 14, 16, 14)
        c_lay.setSpacing(16)
        c = card()
        c.setLayout(c_lay)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(180, 101)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"background:{BG0}; border-radius:8px; color:{TEXT3}; font-size:11px;"
        )
        self.thumb_label.setText("Önizleme")
        c_lay.addWidget(self.thumb_label)

        info_col = QVBoxLayout(); info_col.setSpacing(6)
        self.info_title = label("URL girin ve 'Bilgi Al'a tıklayın", 13, TEXT3, wrap=True)
        info_col.addWidget(self.info_title)
        self.info_meta = label("", 11, TEXT3)
        info_col.addWidget(self.info_meta)
        self.info_tags = label("", 11, MAUVE)
        info_col.addWidget(self.info_tags)
        info_col.addStretch()

        open_btn = QPushButton("↗ Aç")
        open_btn.setObjectName("ghostBtn")
        open_btn.setFixedWidth(60)
        open_btn.clicked.connect(self._open_url)
        info_col.addWidget(open_btn)
        c_lay.addLayout(info_col, stretch=1)

        self._lay.addWidget(c)

    def _build_options_card(self):
        c_lay = QVBoxLayout()
        c     = card(c_lay)

        c_lay.addWidget(label("⚙ İndirme Seçenekleri", 12, TEXT2, bold=True))

        row1 = QHBoxLayout(); row1.setSpacing(12)

        # Quality
        qcol = QVBoxLayout(); qcol.setSpacing(4)
        qcol.addWidget(label("Kalite", 11, TEXT3))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(VIDEO_QUALITIES)
        self.quality_combo.setCurrentText(self._settings.get("default_quality", "Best Quality"))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        qcol.addWidget(self.quality_combo)
        row1.addLayout(qcol)

        # Format
        fcol = QVBoxLayout(); fcol.setSpacing(4)
        fcol.addWidget(label("Format", 11, TEXT3))
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        fcol.addWidget(self.format_combo)
        row1.addLayout(fcol)

        # Audio Quality
        acol = QVBoxLayout(); acol.setSpacing(4); acol.setContentsMargins(0, 0, 0, 0)
        acol.addWidget(label("Ses Kalitesi", 11, TEXT3))
        self.aq_combo = QComboBox()
        self.aq_combo.addItems(AUDIO_QUALITIES)
        self.aq_combo.setCurrentText(self._settings.get("default_audio_quality", "192"))
        acol.addWidget(self.aq_combo)
        self._aq_widget = QWidget(); self._aq_widget.setLayout(acol)
        sp = self._aq_widget.sizePolicy()
        sp.setRetainSizeWhenHidden(False)
        self._aq_widget.setSizePolicy(sp)
        self._aq_widget.hide()
        row1.addWidget(self._aq_widget)

        # Save path
        pcol = QVBoxLayout(); pcol.setSpacing(4)
        pcol.addWidget(label("Kayıt Klasörü", 11, TEXT3))
        prow = QHBoxLayout(); prow.setSpacing(6)
        self.path_entry = QLineEdit(
            self._settings.get("download_path", os.path.expanduser("~/Downloads"))
        )
        self.path_entry.setReadOnly(True)
        self.path_entry.setFixedHeight(36)
        prow.addWidget(self.path_entry, stretch=1)
        br = QPushButton("📁"); br.setFixedSize(36, 36); br.clicked.connect(self._browse_path)
        prow.addWidget(br)
        pcol.addLayout(prow)
        row1.addLayout(pcol, stretch=1)

        c_lay.addLayout(row1)
        c_lay.addWidget(hdivider())

        # Time Range
        c_lay.addWidget(label("Zaman Aralığı / Kırpma (Opsiyonel)", 12, TEXT2))
        trow = QHBoxLayout(); trow.setSpacing(12)
        
        scol = QVBoxLayout(); scol.setSpacing(4)
        scol.addWidget(label("Başlangıç (SS:DD:SS)", 11, TEXT3))
        self.start_time = QLineEdit()
        self.start_time.setPlaceholderText("00:00:00")
        self.start_time.setFixedWidth(100)
        scol.addWidget(self.start_time)
        trow.addLayout(scol)

        ecol = QVBoxLayout(); ecol.setSpacing(4)
        ecol.addWidget(label("Bitiş (SS:DD:SS)", 11, TEXT3))
        self.end_time = QLineEdit()
        self.end_time.setPlaceholderText("00:00:00")
        self.end_time.setFixedWidth(100)
        ecol.addWidget(self.end_time)
        trow.addLayout(ecol)
        
        trow.addStretch()
        c_lay.addLayout(trow)
        c_lay.addWidget(hdivider())

        # Checkboxes
        row2 = QHBoxLayout(); row2.setSpacing(20)
        self.subs_check  = QCheckBox("Altyazı göm")
        self.thumb_check = QCheckBox("Küçük resim göm")
        self.desc_check  = QCheckBox("Açıklamayı kaydet")
        for cb, key in [
            (self.subs_check,  "embed_subtitles"),
            (self.thumb_check, "embed_thumbnail"),
            (self.desc_check,  "write_description"),
        ]:
            cb.setChecked(self._settings.get(key, False))
            row2.addWidget(cb)
        row2.addStretch()
        c_lay.addLayout(row2)

        self._lay.addWidget(c)
        self._on_quality_changed(self.quality_combo.currentText())

    def _build_dl_button(self):
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)

        self._btn_stack = QStackedWidget()
        self._btn_stack.setFixedHeight(52)

        self.dl_btn = DownloadButton()
        self.dl_btn.setText("⬇  İNDİR")
        self.dl_btn.clicked.connect(self._emit_download)
        self._btn_stack.addWidget(self.dl_btn)

        self.cancel_btn = QPushButton("■  İPTAL")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setMinimumHeight(52)
        self.cancel_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_stack.addWidget(self.cancel_btn)
        self._btn_stack.setCurrentIndex(0)

        btn_row.addWidget(self._btn_stack, stretch=1)

        add_q = make_accent_btn("+ Kuyruğa Ekle", MAUVE)
        add_q.setFixedHeight(52)
        add_q.setFixedWidth(150)
        add_q.clicked.connect(self._emit_queue)
        btn_row.addWidget(add_q)

        self._lay.addLayout(btn_row)

    def _build_progress_card(self):
        c_lay = QVBoxLayout()
        c     = card(c_lay)
        c_lay.setSpacing(8)

        top = QHBoxLayout()
        self.status_lbl = label("Hazır", 13, TEXT3)
        top.addWidget(self.status_lbl)
        top.addStretch()
        self.pct_lbl = label("0%", 18, BLUE, bold=True)
        top.addWidget(self.pct_lbl)
        c_lay.addLayout(top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        c_lay.addWidget(self.progress_bar)

        self.pp_bar = QProgressBar()
        self.pp_bar.setRange(0, 0)
        self.pp_bar.setFixedHeight(4)
        self.pp_bar.setTextVisible(False)
        self.pp_bar.hide()
        c_lay.addWidget(self.pp_bar)

        self.speed_graph = SpeedGraph()
        c_lay.addWidget(self.speed_graph)

        stats_row = QHBoxLayout()
        self.stats_lbl = label("Hız: —  ·  ETA: —", 11, TEXT3)
        self.stats_lbl.setStyleSheet(
            f"color:{TEXT3}; font-size:11px; font-family:'Consolas',monospace;"
        )
        stats_row.addWidget(self.stats_lbl)
        stats_row.addStretch()
        self.size_lbl = label("", 11, TEXT3)
        self.size_lbl.setStyleSheet(
            f"color:{TEXT3}; font-size:11px; font-family:'Consolas',monospace;"
        )
        stats_row.addWidget(self.size_lbl)
        c_lay.addLayout(stats_row)

        self._lay.addWidget(c)

    # ── Helpers ───────────────────────────────────────────

    def _paste(self):
        txt = QApplication.clipboard().text().strip()
        if txt:
            self.url_entry.setText(txt)

    def _open_url(self):
        u = self.url_entry.text().strip()
        if u:
            QDesktopServices.openUrl(QUrl(u))

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.path_entry.text())
        if folder:
            self.path_entry.setText(folder)
            self._settings["download_path"] = folder
            save_settings(self._settings)

    def _on_quality_changed(self, quality: str):
        is_audio = (quality == "Audio Only")
        self._aq_widget.setVisible(is_audio)
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(AUDIO_FORMATS if is_audio else VIDEO_FORMATS)
        df = self._settings.get("default_format", "mp4")
        if is_audio:
            self.format_combo.setCurrentText(df if df in AUDIO_FORMATS else "mp3")
        else:
            self.format_combo.setCurrentText(df if df in VIDEO_FORMATS else "mp4")
        self.format_combo.blockSignals(False)
        # Thumbnail visibility güncelle
        self._on_format_changed(self.format_combo.currentText())

    def _on_format_changed(self, fmt: str):
        """webm seçiliyken 'Küçük resim göm' seçeneğini gizle."""
        can_embed = fmt in THUMBNAIL_EMBED_SUPPORTED
        self.thumb_check.setVisible(can_embed)
        if not can_embed:
            self.thumb_check.setChecked(False)

    def _make_item(self) -> QueueItem | None:
        url = self.url_entry.text().strip()
        if not url:
            return None
        return QueueItem(
            url              = url,
            quality          = self.quality_combo.currentText(),
            fmt              = self.format_combo.currentText(),
            output_dir       = self.path_entry.text(),
            subtitles        = self.subs_check.isChecked(),
            audio_quality    = self.aq_combo.currentText(),
            embed_thumbnail  = self.thumb_check.isChecked(),
            write_description= self.desc_check.isChecked(),
            start_time       = self.start_time.text().strip(),
            end_time         = self.end_time.text().strip(),
            embed_metadata   = self._settings.get("embed_metadata", True)
        )

    def _emit_download(self):
        item = self._make_item()
        if item:
            self.request_download.emit(item)

    def _emit_queue(self):
        item = self._make_item()
        if item:
            self.request_queue.emit(item)

    def _emit_info(self):
        url = self.url_entry.text().strip()
        if url:
            self.request_info.emit(url)

    # ── Public update methods ─────────────────────────────

    def set_status(self, text: str, color: str = TEXT3):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color:{color}; font-size:13px;")

    def set_progress(self, pct: float, speed: str, eta: str, dl: int, total: int, fi, fc):
        pct = max(0.0, min(100.0, pct))
        self.progress_bar.setValue(int(pct * 10))
        self.pct_lbl.setText(f"{int(pct)}%")
        sp = f"Hız: {speed or '—'}  ·  ETA: {eta or '—'}"
        if fi and fc:
            sp += f"  ·  Parça: {fi}/{fc}"
        self.stats_lbl.setText(sp)
        if total > 0:
            dl_mb  = dl    / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.size_lbl.setText(f"{dl_mb:.1f} / {tot_mb:.1f} MB")
        try:
            spd = speed.replace(" ", "")
            if "MiB/s" in spd or "MB/s" in spd:
                val = float(spd.replace("MiB/s", "").replace("MB/s", "")) * 1024
            elif "KiB/s" in spd or "KB/s" in spd:
                val = float(spd.replace("KiB/s", "").replace("KB/s", ""))
            else:
                val = 0.0
            self.speed_graph.add_sample(val)
        except Exception:
            pass

    def show_postprocess(self, show: bool):
        self.pp_bar.setVisible(show)
        if show:
            self.set_status("İşleniyor (birleştirme)…", YELLOW)

    def reset_progress(self):
        self.progress_bar.setValue(0)
        self.pct_lbl.setText("0%")
        self.stats_lbl.setText("Hız: —  ·  ETA: —")
        self.size_lbl.setText("")
        self.speed_graph.reset()
        self.pp_bar.hide()

    def show_cancel(self):   self._btn_stack.setCurrentIndex(1)
    def show_download(self): self._btn_stack.setCurrentIndex(0)

    def show_thumb(self, pixmap: QPixmap):
        self.thumb_label.setPixmap(pixmap)
        self.thumb_label.setText("")

    def show_info(self, info: dict):
        title    = info.get('title', 'Bilinmiyor')
        uploader = info.get('uploader') or info.get('channel', '')
        dur      = info.get('duration')
        ds       = f"{int(dur//60)}:{int(dur%60):02d}" if dur else ""
        view     = info.get('view_count')
        vs       = f"  ·  {view:,} görüntülenme" if view else ""
        meta     = "  ·  ".join(filter(None, [uploader, ds])) + vs
        self.info_title.setText(title)
        self.info_title.setStyleSheet(f"color:{TEXT}; font-size:14px; font-weight:600;")
        self.info_meta.setText(meta)
        cats = info.get('categories') or info.get('tags') or []
        if cats:
            self.info_tags.setText("  ".join(f"#{t}" for t in cats[:4]))

    def reset_preview(self):
        self.thumb_label.clear()
        self.thumb_label.setText("Önizleme")
        self.info_title.setText("URL girin ve 'Bilgi Al'a tıklayın")
        self.info_title.setStyleSheet(f"color:{TEXT3}; font-size:13px;")
        self.info_meta.setText("")
        self.info_tags.setText("")

    def enable_info_btn(self, v: bool):
        self.info_btn.setEnabled(v)


# ═══════════════════════════════════════════════════════════
#  QUEUE PAGE
# ═══════════════════════════════════════════════════════════
class QueuePage(QWidget):
    request_start = pyqtSignal()
    request_clear = pyqtSignal()
    request_import = pyqtSignal()
    request_schedule = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: list[QueueItem] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        hdr.addWidget(label("⏳ İndirme Kuyruğu", 16, TEXT, bold=True))
        hdr.addStretch()
        self.count_lbl = label("0 öğe", 12, TEXT3)
        hdr.addWidget(self.count_lbl)
        lay.addLayout(hdr)

        lay.addWidget(label("Kuyruğa eklenen URL'ler sırayla indirilir.", 12, TEXT3))
        lay.addWidget(hdivider())

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._ctx_menu)
        lay.addWidget(self.list_widget, stretch=1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        start = make_accent_btn("▶  Kuyruğu Başlat", GREEN)
        start.setFixedHeight(44)
        start.clicked.connect(self.request_start)
        btn_row.addWidget(start)

        clear = QPushButton("🗑  Temizle")
        clear.setFixedHeight(44)
        clear.clicked.connect(self.request_clear)
        btn_row.addWidget(clear)

        import_batch = QPushButton("📂 Toplu İçe Aktar (.txt)")
        import_batch.setFixedHeight(44)
        import_batch.clicked.connect(self.request_import)
        btn_row.addWidget(import_batch)

        schedule_btn = QPushButton("⏰ Zamanla")
        schedule_btn.setFixedHeight(44)
        schedule_btn.clicked.connect(self.request_schedule)
        self.schedule_btn = schedule_btn
        btn_row.addWidget(schedule_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

    def refresh(self, queue: list):
        self._queue = list(queue)  # MainWindow._queue ile senkron kopya
        self.list_widget.clear()
        self.count_lbl.setText(f"{len(queue)} öğe")
        if not queue:
            ph = QListWidgetItem(
                "Kuyruk boş  —  İndir sayfasında '+ Kuyruğa Ekle'ye tıklayın"
            )
            ph.setForeground(QColor(TEXT3))
            ph.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(ph)
            return
        icon_map  = {"queued": "○", "downloading": "⬇", "done": "✓", "error": "✗"}
        color_map = {"queued": TEXT3, "downloading": BLUE, "done": GREEN, "error": RED}
        for i, q in enumerate(queue, 1):
            txt  = f"  {icon_map.get(q.status,'○')}  {i}. {q.title[:55]}   [{q.quality} · {q.fmt}]"
            item = QListWidgetItem(txt)
            item.setForeground(QColor(color_map.get(q.status, TEXT3)))
            self.list_widget.addItem(item)

    def _ctx_menu(self, pos):
        idx = self.list_widget.currentRow()
        if idx < 0 or idx >= len(self._queue):
            return
        menu   = QMenu(self)
        remove = menu.addAction("🗑  Kuyruktan kaldır")
        act    = menu.exec(self.list_widget.mapToGlobal(pos))
        if act == remove:
            # Silme sinyali emit etmek yerine parent'a bildir
            self.remove_requested.emit(idx)

    # Senkronizasyon için sinyal
    remove_requested = pyqtSignal(int)


# ═══════════════════════════════════════════════════════════
#  HISTORY PAGE
# ═══════════════════════════════════════════════════════════
class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = load_history()
        self._build()
        # Başlangıçta yüklenen geçmişi max_history ile kırp (varsayılan 50)
        if len(self._history) > DEFAULT_SETTINGS["max_history"]:
            self._history = self._history[:DEFAULT_SETTINGS["max_history"]]
            save_history(self._history)
        self._refresh_list(self._history)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(label("📋 İndirme Geçmişi", 16, TEXT, bold=True))
        hdr.addStretch()
        clear = QPushButton("Tümünü Sil")
        clear.setObjectName("ghostBtn")
        clear.clicked.connect(self._clear)
        hdr.addWidget(clear)
        lay.addLayout(hdr)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Geçmişte ara…")
        self._filter.setFixedHeight(36)
        self._filter.textChanged.connect(self._apply_filter)
        lay.addWidget(self._filter)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._ctx)
        lay.addWidget(self.list_widget, stretch=1)

    def add_entry(self, entry: dict, max_items: int = 50):
        self._history.insert(0, entry)
        if len(self._history) > max_items:
            self._history = self._history[:max_items]
        save_history(self._history)
        self._refresh_list(self._history)

    def _refresh_list(self, entries: list):
        self.list_widget.clear()
        if not entries:
            ph = QListWidgetItem("Henüz indirme yapılmadı")
            ph.setForeground(QColor(TEXT3))
            ph.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(ph)
            return
        for e in entries:
            title  = e.get("title", "Bilinmiyor")
            ext    = e.get("ext", "")
            size   = e.get("size_mb", 0)
            ts     = e.get("timestamp", "")
            sz_str = f"{size:.1f} MB  " if size else ""
            txt    = f"  ✓  {title}{'.' + ext if ext else ''}   {sz_str}{ts}"
            item   = QListWidgetItem(txt)
            item.setForeground(QColor(TEXT2))
            item.setData(Qt.ItemDataRole.UserRole, e)
            self.list_widget.addItem(item)

    def _apply_filter(self, text: str):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def _clear(self):
        self._history.clear()
        save_history(self._history)
        self._refresh_list(self._history)

    def _ctx(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        e = item.data(Qt.ItemDataRole.UserRole)
        if not e:
            return
        menu   = QMenu(self)
        open_f = menu.addAction("📂 Klasörde Göster")
        copy_u = menu.addAction("🔗 URL'yi Kopyala")
        delete = menu.addAction("🗑  Sil")
        act    = menu.exec(self.list_widget.mapToGlobal(pos))
        if act == open_f:
            path = e.get("output_dir", "")
            if path and os.path.isdir(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif act == copy_u:
            url = e.get("url", "")
            if url:
                QApplication.clipboard().setText(url)
        elif act == delete:
            if e in self._history:
                self._history.remove(e)
                save_history(self._history)
                self._refresh_list(self._history)


# ═══════════════════════════════════════════════════════════
#  LOGS PAGE
# ═══════════════════════════════════════════════════════════
class LogsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(label("📄 Uygulama Günlükleri", 16, TEXT, bold=True))
        hdr.addStretch()
        clear = QPushButton("Temizle")
        clear.setObjectName("ghostBtn")
        clear.clicked.connect(self._clear)
        hdr.addWidget(clear)
        lay.addLayout(hdr)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Günlükler burada görünecek…")
        lay.addWidget(self.log_box, stretch=1)

    def append(self, text: str, color: str = TEXT2):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f'<span style="color:{TEXT3};">[{ts}]</span> '
            f'<span style="color:{color};">{text}</span>'
        )

    def _clear(self):
        self.log_box.clear()


class ThumbLoaderWorker(QObject):
    finished = pyqtSignal(object, bytes)
    
    def fetch(self, label_ref, url):
        def run():
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                self.finished.emit(label_ref, data)
            except:
                pass
        import threading
        threading.Thread(target=run, daemon=True).start()

# ═══════════════════════════════════════════════════════════
#  SEARCH PAGE
# ═══════════════════════════════════════════════════════════
class SearchPage(QWidget):
    request_search = pyqtSignal(str)
    request_queue_url = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumb_loader = ThumbLoaderWorker()
        self.thumb_loader.finished.connect(self._on_thumb_loaded)
        self._build()

    def _on_thumb_loaded(self, label_ref, data):
        img = QImage()
        img.loadFromData(data)
        px = QPixmap.fromImage(img).scaled(120, 67, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label_ref.setPixmap(px)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        hdr.addWidget(label("🔍 YouTube'da Ara", 16, TEXT, bold=True))
        hdr.addStretch()
        lay.addLayout(hdr)

        search_lay = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Aramak istediğiniz kelimeyi yazın ve Enter'a basın...")
        self.search_input.setFixedHeight(44)
        self.search_input.returnPressed.connect(self._do_search)
        search_lay.addWidget(self.search_input, stretch=1)

        search_btn = make_accent_btn("Ara", BLUE)
        search_btn.setFixedHeight(44)
        search_btn.clicked.connect(self._do_search)
        search_lay.addWidget(search_btn)
        lay.addLayout(search_lay)

        self.list_widget = QListWidget()
        lay.addWidget(self.list_widget, stretch=1)

    def _do_search(self):
        q = self.search_input.text().strip()
        if q:
            self.list_widget.clear()
            self.list_widget.addItem("Aranıyor, lütfen bekleyin...")
            self.request_search.emit(q)

    def set_results(self, results: list):
        self.list_widget.clear()
        if not results:
            self.list_widget.addItem("Sonuç bulunamadı.")
            return
        
        for r in results:
            item = QListWidgetItem()
            w = QWidget()
            l = QHBoxLayout(w)
            
            # Thumbnail
            thumb_lbl = QLabel()
            thumb_lbl.setFixedSize(120, 67)
            thumb_lbl.setStyleSheet("background-color: #333333; border-radius: 4px;")
            thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.addWidget(thumb_lbl)
            
            thumbnails = r.get('thumbnails', [])
            thumb_url = None
            if thumbnails and isinstance(thumbnails, list):
                if isinstance(thumbnails[0], dict) and 'url' in thumbnails[0]:
                    thumb_url = thumbnails[0]['url']
                elif isinstance(thumbnails[0], str):
                    thumb_url = thumbnails[0]
                    
            if thumb_url:
                self.thumb_loader.fetch(thumb_lbl, thumb_url)
            
            title_lbl = label(r.get('title', 'Başlık Yok'), 14, TEXT, bold=True)
            title_lbl.setWordWrap(True)
            dur = r.get('duration')
            dur_str = f"{dur}s" if dur else "Bilinmiyor"
            info_lbl = label(f"Kanal: {r.get('uploader')} | Süre: {dur_str}", 12, TEXT3)
            
            v = QVBoxLayout()
            v.addWidget(title_lbl)
            v.addWidget(info_lbl)
            l.addLayout(v, stretch=1)
            
            btn = QPushButton("➕ Kuyruğa Ekle")
            btn.setFixedHeight(36)
            url = r.get('url', '')
            if url and not url.startswith("http"):
                url = "https://www.youtube.com/watch?v=" + url
            btn.clicked.connect(lambda _, u=url: self.request_queue_url.emit(u))
            l.addWidget(btn)
            
            item.setSizeHint(w.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)
# ═══════════════════════════════════════════════════════════
#  PLAYER PAGE
# ═══════════════════════════════════════════════════════════
class PlayerPage(QWidget):
    request_play = pyqtSignal(str)
    request_download = pyqtSignal(object)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        hdr.addWidget(label("▶ Uygulama İçi Oynatıcı", 16, TEXT, bold=True))
        hdr.addStretch()
        lay.addLayout(hdr)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Oynatmak istediğiniz YouTube video bağlantısını yapıştırın...")
        self.url_input.setFixedHeight(44)
        lay.addWidget(self.url_input)

        play_btn = make_accent_btn("▶ Oynat / Önizle", BLUE)
        play_btn.setFixedHeight(44)
        play_btn.clicked.connect(self._do_play)
        lay.addWidget(play_btn)

        lay.addWidget(hdivider())

        self._build_options_card(lay)

        dl_btn = make_accent_btn("⬇ İndir", GREEN)
        dl_btn.setFixedHeight(44)
        dl_btn.clicked.connect(self._do_download)
        lay.addWidget(dl_btn)

        self.status_lbl = label("Hazır.", 12, TEXT3)
        lay.addWidget(self.status_lbl)

        lay.addStretch()

    def _build_options_card(self, parent_lay):
        c_lay = QVBoxLayout()
        c     = card(c_lay)

        c_lay.addWidget(label("⚙ İndirme Seçenekleri", 12, TEXT2, bold=True))

        row1 = QHBoxLayout(); row1.setSpacing(12)

        # Quality
        qcol = QVBoxLayout(); qcol.setSpacing(4)
        qcol.addWidget(label("Kalite", 11, TEXT3))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(VIDEO_QUALITIES)
        self.quality_combo.setCurrentText(self._settings.get("default_quality", "Best Quality"))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        qcol.addWidget(self.quality_combo)
        row1.addLayout(qcol)

        # Format
        fcol = QVBoxLayout(); fcol.setSpacing(4)
        fcol.addWidget(label("Format", 11, TEXT3))
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        fcol.addWidget(self.format_combo)
        row1.addLayout(fcol)

        # Audio Quality
        acol = QVBoxLayout(); acol.setSpacing(4); acol.setContentsMargins(0, 0, 0, 0)
        acol.addWidget(label("Ses Kalitesi", 11, TEXT3))
        self.aq_combo = QComboBox()
        self.aq_combo.addItems(AUDIO_QUALITIES)
        self.aq_combo.setCurrentText(self._settings.get("default_audio_quality", "192"))
        acol.addWidget(self.aq_combo)
        self._aq_widget = QWidget(); self._aq_widget.setLayout(acol)
        sp = self._aq_widget.sizePolicy()
        sp.setRetainSizeWhenHidden(False)
        self._aq_widget.setSizePolicy(sp)
        self._aq_widget.hide()
        row1.addWidget(self._aq_widget)

        # Save path
        pcol = QVBoxLayout(); pcol.setSpacing(4)
        pcol.addWidget(label("Kayıt Klasörü", 11, TEXT3))
        prow = QHBoxLayout(); prow.setSpacing(6)
        self.path_entry = QLineEdit(
            self._settings.get("download_path", os.path.expanduser("~/Downloads"))
        )
        self.path_entry.setReadOnly(True)
        self.path_entry.setFixedHeight(36)
        prow.addWidget(self.path_entry, stretch=1)
        br = QPushButton("📁"); br.setFixedSize(36, 36); br.clicked.connect(self._browse_path)
        prow.addWidget(br)
        pcol.addLayout(prow)
        row1.addLayout(pcol, stretch=1)

        c_lay.addLayout(row1)
        c_lay.addWidget(hdivider())

        # Time Range
        c_lay.addWidget(label("Zaman Aralığı / Kırpma (Opsiyonel)", 12, TEXT2))
        trow = QHBoxLayout(); trow.setSpacing(12)
        
        scol = QVBoxLayout(); scol.setSpacing(4)
        scol.addWidget(label("Başlangıç (SS:DD:SS)", 11, TEXT3))
        self.start_time = QLineEdit()
        self.start_time.setPlaceholderText("00:00:00")
        self.start_time.setFixedWidth(100)
        scol.addWidget(self.start_time)
        trow.addLayout(scol)

        ecol = QVBoxLayout(); ecol.setSpacing(4)
        ecol.addWidget(label("Bitiş (SS:DD:SS)", 11, TEXT3))
        self.end_time = QLineEdit()
        self.end_time.setPlaceholderText("00:00:00")
        self.end_time.setFixedWidth(100)
        ecol.addWidget(self.end_time)
        trow.addLayout(ecol)
        
        trow.addStretch()
        c_lay.addLayout(trow)
        c_lay.addWidget(hdivider())

        # Checkboxes
        row2 = QHBoxLayout(); row2.setSpacing(20)
        self.subs_check  = QCheckBox("Altyazı göm")
        self.thumb_check = QCheckBox("Küçük resim göm")
        self.desc_check  = QCheckBox("Açıklamayı kaydet")
        for cb, key in [
            (self.subs_check,  "embed_subtitles"),
            (self.thumb_check, "embed_thumbnail"),
            (self.desc_check,  "write_description"),
        ]:
            cb.setChecked(self._settings.get(key, False))
            row2.addWidget(cb)
        row2.addStretch()
        c_lay.addLayout(row2)

        parent_lay.addWidget(c)
        self._on_quality_changed(self.quality_combo.currentText())

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.path_entry.text())
        if folder:
            self.path_entry.setText(folder)
            self._settings["download_path"] = folder
            save_settings(self._settings)

    def _on_quality_changed(self, quality: str):
        is_audio = (quality == "Audio Only")
        self._aq_widget.setVisible(is_audio)
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(AUDIO_FORMATS if is_audio else VIDEO_FORMATS)
        df = self._settings.get("default_format", "mp4")
        if is_audio:
            self.format_combo.setCurrentText(df if df in AUDIO_FORMATS else "mp3")
        else:
            self.format_combo.setCurrentText(df if df in VIDEO_FORMATS else "mp4")
        self.format_combo.blockSignals(False)
        self._on_format_changed(self.format_combo.currentText())

    def _on_format_changed(self, fmt: str):
        can_embed = fmt in THUMBNAIL_EMBED_SUPPORTED
        self.thumb_check.setVisible(can_embed)
        if not can_embed:
            self.thumb_check.setChecked(False)

    def set_status(self, txt, color=TEXT3):
        self.status_lbl.setText(txt)
        self.status_lbl.setStyleSheet(f"color: {color};")

    def _do_play(self):
        url = self.url_input.text().strip()
        if url:
            self.set_status("Akış bağlantısı alınıyor, oynatıcı başlatılacak...", BLUE)
            self.request_play.emit(url)

    def _do_download(self):
        url = self.url_input.text().strip()
        if not url: return
        item = QueueItem(
            url              = url,
            quality          = self.quality_combo.currentText(),
            fmt              = self.format_combo.currentText(),
            output_dir       = self.path_entry.text(),
            subtitles        = self.subs_check.isChecked(),
            audio_quality    = self.aq_combo.currentText(),
            playlist_items   = "",
            embed_thumbnail  = self.thumb_check.isChecked(),
            write_description= self.desc_check.isChecked(),
            start_time       = self.start_time.text().strip() or None,
            end_time         = self.end_time.text().strip() or None
        )
        self.request_download.emit(item)

# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
