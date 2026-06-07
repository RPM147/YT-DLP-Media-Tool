
import os, datetime
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from utils.theme import *
from core.config import *
from ui.components.widgets import *
class Bridge(QObject):
    progress       = pyqtSignal(float, str, str, int, int, object, object)
    complete       = pyqtSignal(object)
    error          = pyqtSignal(str)
    thumb          = pyqtSignal(object)
    playlist_ready = pyqtSignal(object)
    info_fetched   = pyqtSignal(object)
    postprocess    = pyqtSignal()
    log            = pyqtSignal(str, str)


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
        self.options.update_settings(s)

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
        self.options = OptionsCard(self._settings)
        self._lay.addWidget(self.options)
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

    def _make_item(self) -> QueueItem | None:
        url = self.url_entry.text().strip()
        if not url:
            return None
        return QueueItem(url=url, **self.options.values())

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
#  TRANSCRIPT PAGE
# ═══════════════════════════════════════════════════════════
class TranscriptPage(QWidget):
    request_start = pyqtSignal(object)
    request_cancel = pyqtSignal()
    request_open_path = pyqtSignal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._build()

    def _setting(self, key: str):
        return self._settings.get(key, DEFAULT_SETTINGS[key])

    def _default_output_dir(self) -> str:
        return self._settings.get(
            "transcript_output_path",
            self._settings.get("download_path", DEFAULT_SETTINGS["transcript_output_path"]),
        )

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner.setObjectName("root")
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(28, 24, 28, 28)
        self._lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(label("Transkriptler", 16, TEXT, bold=True))
        hdr.addStretch()
        self.status_lbl = label("Hazir", 12, TEXT3)
        hdr.addWidget(self.status_lbl)
        self._lay.addLayout(hdr)

        self._build_source_card()
        self._build_options_card()
        self._build_run_card()
        self._build_progress_card()
        self._lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    def _build_source_card(self):
        c_lay = QVBoxLayout()
        c = card(c_lay)
        c_lay.addWidget(label("Kaynak", 12, TEXT2, bold=True))

        url_row = QHBoxLayout()
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("YouTube kanal, playlist veya video URL")
        self.url_entry.setFixedHeight(40)
        url_row.addWidget(self.url_entry, stretch=1)
        paste = QPushButton("Yapistir")
        paste.setFixedHeight(40)
        paste.clicked.connect(self._paste_url)
        url_row.addWidget(paste)
        c_lay.addLayout(url_row)

        out_row = QHBoxLayout()
        self.output_entry = QLineEdit(self._default_output_dir())
        self.output_entry.setReadOnly(True)
        self.output_entry.setFixedHeight(36)
        out_row.addWidget(self.output_entry, stretch=1)
        browse = QPushButton("Gozat")
        browse.setFixedSize(80, 36)
        browse.clicked.connect(self._browse_output)
        out_row.addWidget(browse)
        c_lay.addLayout(out_row)

        self._lay.addWidget(c)

    def _build_options_card(self):
        c_lay = QVBoxLayout()
        c = card(c_lay)
        c_lay.addWidget(label("Ayarlar", 12, TEXT2, bold=True))

        row1 = QHBoxLayout()
        row1.setSpacing(12)

        lang_col = QVBoxLayout()
        lang_col.addWidget(label("Dil onceligi", 11, TEXT3))
        self.lang_entry = QLineEdit(self._setting("transcript_languages"))
        self.lang_entry.setFixedHeight(36)
        lang_col.addWidget(self.lang_entry)
        row1.addLayout(lang_col, stretch=1)

        fmt_col = QVBoxLayout()
        fmt_col.addWidget(label("Cikti", 11, TEXT3))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["both", "txt", "md"])
        self.format_combo.setCurrentText(self._setting("transcript_output_format"))
        self.format_combo.setFixedHeight(36)
        fmt_col.addWidget(self.format_combo)
        row1.addLayout(fmt_col)

        c_lay.addLayout(row1)
        c_lay.addWidget(hdivider())

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self.manual_only_check = QCheckBox("Manual only")
        self.auto_fallback_check = QCheckBox("Auto fallback")
        self.keep_cues_check = QCheckBox("Cue koru")
        self.timestamps_check = QCheckBox("Timestamp")
        self.metadata_only_check = QCheckBox("Metadata only")
        self.dry_run_check = QCheckBox("Dry-run")
        self.force_check = QCheckBox("Force")
        for cb in [
            self.manual_only_check,
            self.auto_fallback_check,
            self.keep_cues_check,
            self.timestamps_check,
            self.metadata_only_check,
            self.dry_run_check,
            self.force_check,
        ]:
            row2.addWidget(cb)
        self.manual_only_check.setChecked(self._setting("transcript_manual_only"))
        self.auto_fallback_check.setChecked(self._setting("transcript_auto_fallback"))
        self.keep_cues_check.setChecked(self._setting("transcript_keep_cues"))
        self.timestamps_check.setChecked(self._setting("transcript_timestamps"))
        self.metadata_only_check.setChecked(self._setting("transcript_metadata_only"))
        row2.addStretch()
        c_lay.addLayout(row2)
        c_lay.addWidget(hdivider())

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.max_videos_spin = self._make_spin(0, 999999, 0)
        self.start_index_spin = self._make_spin(0, 999999, 0)
        self.end_index_spin = self._make_spin(0, 999999, 0)
        self.retries_spin = self._make_spin(1, 20, self._setting("transcript_retries"))
        self.progress_interval_spin = self._make_spin(
            1,
            10000,
            self._setting("transcript_progress_interval"),
        )
        self.delay_spin = self._make_double_spin(
            0.0,
            120.0,
            self._setting("transcript_delay"),
        )
        self.retry_delay_spin = self._make_double_spin(
            0.0,
            120.0,
            self._setting("transcript_retry_delay"),
        )

        fields = [
            ("Max videos", self.max_videos_spin),
            ("Start", self.start_index_spin),
            ("End", self.end_index_spin),
            ("Retries", self.retries_spin),
            ("Progress interval", self.progress_interval_spin),
            ("Delay", self.delay_spin),
            ("Retry delay", self.retry_delay_spin),
        ]
        for i, (text, widget) in enumerate(fields):
            row = i // 4
            col = (i % 4) * 2
            grid.addWidget(label(text, 11, TEXT3), row, col)
            grid.addWidget(widget, row, col + 1)
        c_lay.addLayout(grid)

        self._lay.addWidget(c)

    def _build_run_card(self):
        c_lay = QHBoxLayout()
        c = card(c_lay)
        self.start_btn = make_accent_btn("Baslat", GREEN)
        self.start_btn.setFixedHeight(46)
        self.start_btn.clicked.connect(self._emit_start)
        c_lay.addWidget(self.start_btn, stretch=1)

        self.cancel_btn = QPushButton("Iptal")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setFixedHeight(46)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.request_cancel.emit)
        c_lay.addWidget(self.cancel_btn)
        self._lay.addWidget(c)

    def _build_progress_card(self):
        c_lay = QVBoxLayout()
        c = card(c_lay)

        top = QHBoxLayout()
        self.summary_lbl = label("Bekliyor", 12, TEXT3)
        top.addWidget(self.summary_lbl)
        top.addStretch()
        self.count_lbl = label("0/0", 13, BLUE, bold=True)
        top.addWidget(self.count_lbl)
        c_lay.addLayout(top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        c_lay.addWidget(self.progress_bar)

        self.progress_list = QListWidget()
        self.progress_list.setMinimumHeight(180)
        c_lay.addWidget(self.progress_list)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.open_output_btn = QPushButton("Open Folder")
        self.open_primary_btn = QPushButton("Open Report")
        self.open_secondary_btn = QPushButton("Open Index")
        for btn in [
            self.open_output_btn,
            self.open_primary_btn,
            self.open_secondary_btn,
        ]:
            btn.setFixedHeight(34)
            btn.setEnabled(False)
            btn.clicked.connect(lambda _checked=False, b=btn: self._emit_open_path(b))
            actions.addWidget(btn)
        actions.addStretch()
        c_lay.addLayout(actions)

        self._lay.addWidget(c)

    @staticmethod
    def _make_spin(min_value: int, max_value: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setValue(value)
        spin.setFixedWidth(84)
        return spin

    @staticmethod
    def _make_double_spin(min_value: float, max_value: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_value, max_value)
        spin.setDecimals(2)
        spin.setSingleStep(0.25)
        spin.setValue(value)
        spin.setFixedWidth(84)
        return spin

    def _paste_url(self):
        txt = QApplication.clipboard().text().strip()
        if txt:
            self.url_entry.setText(txt)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Cikti klasoru", self.output_entry.text())
        if folder:
            self.output_entry.setText(folder)

    @staticmethod
    def _optional_int(spin: QSpinBox) -> int | None:
        return spin.value() or None

    @staticmethod
    def _parent_path(path_text: str | None) -> str:
        return str(Path(path_text).parent) if path_text else ""

    def _set_result_button(self, button: QPushButton, text: str, path_text: str | None):
        button.setText(text)
        button.setProperty("path", path_text or "")
        button.setEnabled(bool(path_text))

    def _disable_result_actions(self):
        self._set_result_button(self.open_output_btn, "Open Folder", None)
        self._set_result_button(self.open_primary_btn, "Open Report", None)
        self._set_result_button(self.open_secondary_btn, "Open Index", None)

    def _emit_open_path(self, button: QPushButton):
        path_text = button.property("path")
        if path_text:
            self.request_open_path.emit(str(path_text))

    def update_settings(self, settings: dict):
        self._settings = settings
        if self.cancel_btn.isEnabled():
            return
        self.output_entry.setText(self._default_output_dir())
        self.lang_entry.setText(self._setting("transcript_languages"))
        self.format_combo.setCurrentText(self._setting("transcript_output_format"))
        self.manual_only_check.setChecked(self._setting("transcript_manual_only"))
        self.auto_fallback_check.setChecked(self._setting("transcript_auto_fallback"))
        self.keep_cues_check.setChecked(self._setting("transcript_keep_cues"))
        self.timestamps_check.setChecked(self._setting("transcript_timestamps"))
        self.metadata_only_check.setChecked(self._setting("transcript_metadata_only"))
        self.retries_spin.setValue(self._setting("transcript_retries"))
        self.retry_delay_spin.setValue(self._setting("transcript_retry_delay"))
        self.delay_spin.setValue(self._setting("transcript_delay"))
        self.progress_interval_spin.setValue(self._setting("transcript_progress_interval"))

    def values(self) -> dict:
        languages = tuple(
            part.strip()
            for part in self.lang_entry.text().split(",")
            if part.strip()
        )
        return {
            "url": self.url_entry.text().strip(),
            "output_dir": self.output_entry.text().strip(),
            "languages": languages,
            "output_format": self.format_combo.currentText(),
            "manual_only": self.manual_only_check.isChecked(),
            "auto_fallback": self.auto_fallback_check.isChecked(),
            "keep_cues": self.keep_cues_check.isChecked(),
            "timestamps": self.timestamps_check.isChecked(),
            "metadata_only": self.metadata_only_check.isChecked(),
            "dry_run": self.dry_run_check.isChecked(),
            "force": self.force_check.isChecked(),
            "max_videos": self._optional_int(self.max_videos_spin),
            "start_index": self._optional_int(self.start_index_spin),
            "end_index": self._optional_int(self.end_index_spin),
            "retries": self.retries_spin.value(),
            "retry_delay": self.retry_delay_spin.value(),
            "delay": self.delay_spin.value(),
            "progress_interval": self.progress_interval_spin.value(),
        }

    def _emit_start(self):
        data = self.values()
        if not data["url"]:
            self.set_status("URL gerekli", RED)
            return
        if not data["output_dir"]:
            self.set_status("Cikti klasoru gerekli", RED)
            return
        self.request_start.emit(data)

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for widget in [
            self.url_entry,
            self.output_entry,
            self.lang_entry,
            self.format_combo,
            self.max_videos_spin,
            self.start_index_spin,
            self.end_index_spin,
            self.retries_spin,
            self.retry_delay_spin,
            self.delay_spin,
            self.progress_interval_spin,
        ]:
            widget.setEnabled(not running)
        for cb in [
            self.manual_only_check,
            self.auto_fallback_check,
            self.keep_cues_check,
            self.timestamps_check,
            self.metadata_only_check,
            self.dry_run_check,
            self.force_check,
        ]:
            cb.setEnabled(not running)

    def set_status(self, text: str, color: str = TEXT3):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color:{color}; font-size:12px;")

    def reset_progress(self):
        self.progress_bar.setValue(0)
        self.progress_list.clear()
        self.summary_lbl.setText("Bekliyor")
        self.count_lbl.setText("0/0")
        self._disable_result_actions()

    def add_progress(self, progress):
        total = max(1, int(getattr(progress, "total", 1) or 1))
        index = int(getattr(progress, "index", 0) or 0)
        self.progress_bar.setValue(int(min(index / total, 1.0) * 1000))
        self.count_lbl.setText(f"{index}/{total}")
        action = getattr(progress, "action", "")
        title = getattr(progress, "title", "")
        message = getattr(progress, "message", "")
        item = QListWidgetItem(f"{index:03d}  {action}  {title}  {message}")
        color_map = {
            "saved": GREEN,
            "skip": YELLOW,
            "repair": YELLOW,
            "error": RED,
            "metadata": BLUE,
            "process": BLUE,
        }
        item.setForeground(QColor(color_map.get(action, TEXT2)))
        self.progress_list.addItem(item)
        self.progress_list.scrollToBottom()

    def set_result(self, report: dict):
        self._configure_result_actions(report)
        if report.get("metadata_only"):
            count = report.get("selected_count", 0)
            self.summary_lbl.setText(f"Metadata tamamlandi: {count} video")
            self.progress_bar.setValue(1000)
            self.count_lbl.setText(f"{count}/{count}")
            return
        if report.get("dry_run"):
            count = len(report.get("planned", []))
            self.summary_lbl.setText(f"Dry-run tamamlandi: {count} plan")
            self.progress_bar.setValue(1000)
            return
        processed = report.get("processed_count", 0)
        skipped = report.get("skipped_count", 0)
        self.summary_lbl.setText(f"Tamamlandi: {processed} kayit, {skipped} skip")
        self.progress_bar.setValue(1000)

    def _configure_result_actions(self, report: dict):
        if report.get("dry_run"):
            self._disable_result_actions()
            return

        if report.get("metadata_only"):
            videos_json_path = report.get("videos_json_path")
            videos_csv_path = report.get("videos_csv_path")
            self._set_result_button(
                self.open_output_btn,
                "Open Folder",
                report.get("output_path") or self._parent_path(videos_json_path),
            )
            self._set_result_button(self.open_primary_btn, "Open JSON", videos_json_path)
            self._set_result_button(self.open_secondary_btn, "Open CSV", videos_csv_path)
            return

        self._set_result_button(self.open_output_btn, "Open Folder", report.get("output_path"))
        self._set_result_button(self.open_primary_btn, "Open Report", report.get("report_path"))
        self._set_result_button(self.open_secondary_btn, "Open Index", report.get("index_path"))


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
    def __init__(self, parent=None, max_history=50):
        super().__init__(parent)
        self._history: list[dict] = load_history()
        self._build()
        # Başlangıçta yüklenen geçmişi kullanıcının max_history ayarıyla kırp
        if len(self._history) > max_history:
            self._history = self._history[:max_history]
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

    @staticmethod
    def _format_duration(seconds):
        if seconds in (None, ""):
            return "Bilinmiyor"
        try:
            seconds = int(float(seconds))
        except (TypeError, ValueError):
            return "Bilinmiyor"
        if seconds <= 0:
            return "Bilinmiyor"

        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

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
            dur_str = self._format_duration(r.get('duration'))
            uploader = r.get('uploader') or "Bilinmiyor"
            info_lbl = label(f"Kanal: {uploader} | Süre: {dur_str}", 12, TEXT3)
            
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

        self.options = OptionsCard(self._settings)
        lay.addWidget(self.options)

        dl_btn = make_accent_btn("⬇ İndir", GREEN)
        dl_btn.setFixedHeight(44)
        dl_btn.clicked.connect(self._do_download)
        lay.addWidget(dl_btn)

        self.status_lbl = label("Hazır.", 12, TEXT3)
        lay.addWidget(self.status_lbl)

        lay.addStretch()

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
        if not url:
            return
        item = QueueItem(url=url, playlist_items="", **self.options.values())
        self.request_download.emit(item)

# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
