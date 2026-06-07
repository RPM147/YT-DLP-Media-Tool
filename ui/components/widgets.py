
import os, subprocess, sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from utils.theme import *
from core.config import *
from downloader import AUDIO_FORMATS, VIDEO_FORMATS, AUDIO_QUALITIES, VIDEO_QUALITIES, SUPPORTED_BROWSERS, THUMBNAIL_EMBED_SUPPORTED, BROWSER_PROFILE_PATHS
def hdivider() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{rgba(SURFACE1, 0.5)};")
    return f


def vdivider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{rgba(SURFACE1, 0.5)};")
    return f


def make_accent_btn(text: str, color: str = BLUE) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("accentBtn")
    btn.setStyleSheet(f"""
        QPushButton#accentBtn {{
            background-color: {rgba(color, 0.15)};
            color: {color};
            border: 1.5px solid {rgba(color, 0.4)};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton#accentBtn:hover {{
            background-color: {rgba(color, 0.28)};
            color: white;
            border-color: {color};
        }}
        QPushButton#accentBtn:disabled {{
            color: {TEXT3};
            background-color: {INPUT_BG};
            border-color: {BORDER};
        }}
    """)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def label(text: str, size: int = 13, color: str = TEXT,
          bold: bool = False, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    weight = "700" if bold else "400"
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px; font-weight:{weight};")
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def card(layout=None) -> QWidget:
    w = QWidget()
    w.setObjectName("card")
    if layout is not None:
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        w.setLayout(layout)
    return w


# ═══════════════════════════════════════════════════════════
#  OPTIONS CARD  (DownloadPage + PlayerPage ortak seçenek kartı)
# ═══════════════════════════════════════════════════════════
class OptionsCard(QWidget):
    """Kalite/format/ses/klasör/zaman aralığı/checkbox alanlarını içeren,
    DownloadPage ve PlayerPage tarafından paylaşılan indirme seçenekleri kartı."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        c_lay = QVBoxLayout()
        c     = card(c_lay)

        c_lay.addWidget(label("⚙ İndirme Seçenekleri", 12, TEXT2, bold=True))

        row1 = QHBoxLayout(); row1.setSpacing(12)

        # Kalite
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

        # Ses Kalitesi
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

        # Kayıt klasörü
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

        # Zaman aralığı / kırpma
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

        # Onay kutuları
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

        outer.addWidget(c)
        self._on_quality_changed(self.quality_combo.currentText())

    # ── Internal ──────────────────────────────────────────
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
        """webm gibi desteklenmeyen formatlarda 'Küçük resim göm' seçeneğini gizle."""
        can_embed = fmt in THUMBNAIL_EMBED_SUPPORTED
        self.thumb_check.setVisible(can_embed)
        if not can_embed:
            self.thumb_check.setChecked(False)

    # ── Public ────────────────────────────────────────────
    def update_settings(self, s: dict):
        self._settings = s
        self.quality_combo.setCurrentText(s.get("default_quality", "Best Quality"))
        self.subs_check.setChecked(s.get("embed_subtitles", False))
        self.thumb_check.setChecked(s.get("embed_thumbnail", False))
        self.desc_check.setChecked(s.get("write_description", False))
        self._on_quality_changed(self.quality_combo.currentText())

    def values(self) -> dict:
        """Geçerli seçimleri QueueItem kwargs'ına uygun bir sözlük olarak döndürür."""
        return {
            "quality":           self.quality_combo.currentText(),
            "fmt":               self.format_combo.currentText(),
            "output_dir":        self.path_entry.text(),
            "subtitles":         self.subs_check.isChecked(),
            "audio_quality":     self.aq_combo.currentText(),
            "embed_thumbnail":   self.thumb_check.isChecked(),
            "write_description": self.desc_check.isChecked(),
            "start_time":        self.start_time.text().strip(),
            "end_time":          self.end_time.text().strip(),
            "embed_metadata":    self._settings.get("embed_metadata", True),
        }


# ═══════════════════════════════════════════════════════════
#  SPEED GRAPH
# ═══════════════════════════════════════════════════════════
class SpeedGraph(QWidget):
    MAX_POINTS = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: list[float] = []
        self.setFixedHeight(56)
        self.setMinimumWidth(100)
        self._color      = QColor(BLUE)
        self._empty_text = "Download speed graph"

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)
        self.update()

    def add_sample(self, kbps: float):
        self._samples.append(max(0.0, kbps))
        if len(self._samples) > self.MAX_POINTS:
            self._samples.pop(0)
        self.update()

    def reset(self):
        self._samples.clear()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()

            p.setBrush(QBrush(QColor(SURFACE0)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 0, w, h, 6, 6)

            if len(self._samples) < 2:
                p.setPen(QPen(QColor(TEXT3)))
                p.setFont(QFont("Segoe UI", 10))
                p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._empty_text)
                return

            mx  = max(self._samples) or 1.0
            n   = len(self._samples)
            pts = []
            for i, v in enumerate(self._samples):
                x = w * i / (n - 1)
                y = h - (v / mx) * (h - 6) - 3
                pts.append(QPointF(x, y))

            fill = [QPointF(0, h)] + pts + [QPointF(w, h)]
            fc   = QColor(self._color)
            fc.setAlpha(45)
            p.setBrush(QBrush(fc))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygonF(fill))

            pen = QPen(self._color)
            pen.setWidth(2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF(pts))
        finally:
            p.end()


# ═══════════════════════════════════════════════════════════
#  ANIMATED DOWNLOAD BUTTON
# ═══════════════════════════════════════════════════════════
class DownloadButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self._pressed = False
        self._phase   = 0.0
        self._c1 = QColor(DL_A)
        self._c2 = QColor(DL_B)
        self._c3 = QColor(DL_C)
        self.setMinimumHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(25)

    def _tick(self):
        self._phase = (self._phase + 0.003) % 1.0
        if self._hovered:
            self.update()

    def enterEvent(self, e):        self._hovered = True;  self.update(); super().enterEvent(e)
    def leaveEvent(self, e):        self._hovered = False; self.update(); super().leaveEvent(e)
    def mousePressEvent(self, e):   self._pressed = True;  self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self, e): self._pressed = False; self.update(); super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r      = self.rect().adjusted(1, 1, -1, -1) if self._pressed else self.rect()
            radius = 12

            g = QLinearGradient(0, 0, r.width(), 0)
            if self._hovered:
                o = self._phase * 0.25
                g.setColorAt(0.0, QColor("#1e3a8a"))
                g.setColorAt(min(0.55, 0.3 + o), QColor("#2563eb"))
                g.setColorAt(0.75, QColor("#0891b2"))
                g.setColorAt(1.0,  QColor("#06b6d4"))
            else:
                g.setColorAt(0.0, self._c1)
                g.setColorAt(0.5, self._c2)
                g.setColorAt(1.0, self._c3)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(r, radius, radius)

            hi = QLinearGradient(0, r.top(), 0, r.top() + r.height() * 0.45)
            hi.setColorAt(0, QColor(255, 255, 255, 30 if self._hovered else 15))
            hi.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(hi))
            p.drawRoundedRect(r, radius, radius)

            p.setPen(QPen(QColor("white")))
            f = QFont("Segoe UI", 13, QFont.Weight.Bold)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
            p.setFont(f)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        finally:
            p.end()


# ═══════════════════════════════════════════════════════════
#  SIDEBAR BUTTON
# ═══════════════════════════════════════════════════════════
class SidebarButton(QPushButton):
    def __init__(self, icon_text: str, label_text: str, parent=None):
        super().__init__(parent)
        self._icon_text  = icon_text
        self._label_text = label_text
        self._active     = False
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setActive(self, v: bool):
        self._active = v
        self.setChecked(v)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r = self.rect()

            if self._active:
                bg = QColor(BLUE); bg.setAlpha(35)
                p.setBrush(QBrush(bg))
            elif self.underMouse():
                bg = QColor(SURFACE0); bg.setAlpha(180)
                p.setBrush(QBrush(bg))
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)

            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 10, 10)

            if self._active:
                bar = QColor(BLUE)
                p.setBrush(QBrush(bar))
                p.drawRoundedRect(0, (r.height() - 24) // 2, 3, 24, 2, 2)

            ic_color = QColor(BLUE if self._active else TEXT2)
            p.setPen(QPen(ic_color))
            f = QFont("Segoe UI", 16)
            p.setFont(f)
            p.drawText(QRect(14, 0, 30, r.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                       self._icon_text)

            lbl_color = QColor(BLUE if self._active else TEXT2)
            p.setPen(QPen(lbl_color))
            f2 = QFont("Segoe UI", 12,
                       QFont.Weight.Bold if self._active else QFont.Weight.Normal)
            p.setFont(f2)
            p.drawText(QRect(50, 0, r.width() - 58, r.height()),
                       Qt.AlignmentFlag.AlignVCenter, self._label_text)
        finally:
            p.end()


# ═══════════════════════════════════════════════════════════
#  TOAST NOTIFICATION
# ═══════════════════════════════════════════════════════════
class Toast(QWidget):
    def __init__(self, parent, text: str, color: str = GREEN, duration: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._parent = parent

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:10px;")
        lay.addWidget(dot)

        txt = QLabel(text)
        txt.setStyleSheet(f"color:{TEXT}; font-size:13px;")
        lay.addWidget(txt)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG0};
                border: 1px solid {color};
                border-radius: 10px;
            }}
        """)
        self.adjustSize()

        self._reposition()

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._anim_out = QTimer(self)
        self._anim_out.setSingleShot(True)
        self._anim_out.timeout.connect(self.close)  # deleteLater yerine close
        self._anim_out.start(duration)

    def _reposition(self):
        if self._parent:
            geo = self._parent.geometry()
            x   = geo.x() + geo.width()  - self.width()  - 24
            y   = geo.y() + geo.height() - self.height() - 48
            self.move(x, y)


# ═══════════════════════════════════════════════════════════
#  PLAYLIST DIALOG
# ═══════════════════════════════════════════════════════════
class PlaylistDialog(QDialog):
    def __init__(self, entries: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playlist Seçimi")
        self.setMinimumSize(620, 520)
        self.setStyleSheet(build_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(label(f"🎵 {len(entries)} video bulundu", 16, TEXT, bold=True))
        hdr.addStretch()
        self.count_lbl = label("", 12, TEXT3)
        hdr.addWidget(self.count_lbl)
        root.addLayout(hdr)

        root.addWidget(label("İndirmek istediğiniz videoları seçin:", 12, TEXT2))

        tb = QHBoxLayout()
        for txt, fn in [("Tümünü Seç", self._select_all), ("Hiçbirini Seçme", self._select_none)]:
            b = make_accent_btn(txt, BLUE)
            b.setFixedHeight(30)
            b.clicked.connect(fn)
            tb.addWidget(b)
        tb.addStretch()

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrele…")
        self._filter.setFixedWidth(180)
        self._filter.setFixedHeight(30)
        self._filter.textChanged.connect(self._apply_filter)
        tb.addWidget(self._filter)
        root.addLayout(tb)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._entries = entries
        self._populate(entries)
        self.list_widget.itemChanged.connect(self._update_count)
        root.addWidget(self.list_widget)
        self._update_count()

        root.addWidget(hdivider())
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        c = QPushButton("İptal")
        c.setFixedWidth(90)
        c.clicked.connect(self.reject)
        btn_row.addWidget(c)
        btn_row.addSpacing(8)
        ok = make_accent_btn("Seçilenleri İndir", GREEN)
        ok.clicked.connect(self.accept)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _populate(self, entries):
        self.list_widget.clear()
        for i, e in enumerate(entries, 1):
            t    = e.get('title') or e.get('url') or f"Video {i}"
            dur  = e.get('duration')
            ds   = f"  [{int(dur//60)}:{int(dur%60):02d}]" if dur else ""
            item = QListWidgetItem(f"{i:>3}. {t}{ds}")
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_widget.addItem(item)

    def _apply_filter(self, text):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _update_count(self):
        n = sum(1 for i in range(self.list_widget.count())
                if self.list_widget.item(i).checkState() == Qt.CheckState.Checked)
        self.count_lbl.setText(f"{n} seçili")

    def selected_indices(self) -> list:
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list_widget.count())
                if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
                and not self.list_widget.item(i).isHidden()]

    def playlist_items_str(self) -> str:
        return ",".join(str(x) for x in self.selected_indices())


# ═══════════════════════════════════════════════════════════
#  COOKIE DIALOG
# ═══════════════════════════════════════════════════════════
class CookieDialog(QDialog):
    def __init__(self, current_browser, current_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Çerez Ayarları")
        self.setMinimumWidth(500)
        self.setStyleSheet(build_stylesheet())
        self._browser = current_browser
        self._file    = current_file

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(14)

        root.addWidget(label("🍪 Çerez Ayarları", 17, TEXT, bold=True))
        root.addWidget(label(
            "Kimlik doğrulaması gerektiren içerikler için çerez kullanabilirsiniz.",
            12, TEXT3, wrap=True
        ))
        root.addWidget(hdivider())

        self.rb_none    = QRadioButton("Çerez kullanma")
        self.rb_browser = QRadioButton("Tarayıcıdan oku")
        self.rb_file    = QRadioButton("Dosyadan yükle (.txt — Netscape formatı)")
        root.addWidget(self.rb_none)
        root.addWidget(hdivider())

        root.addWidget(self.rb_browser)
        warn = label(
            "⚠  Chromium tabanlı tarayıcılar çalışırken çerezleri kilitler — kullanmadan önce kapatın.",
            11, YELLOW, wrap=True
        )
        warn.setContentsMargins(26, 0, 0, 0)
        root.addWidget(warn)

        br_row = QHBoxLayout()
        br_row.setContentsMargins(26, 0, 0, 0)
        br_lbl = label("Tarayıcı:", 12, TEXT2)
        br_lbl.setFixedWidth(70)
        br_row.addWidget(br_lbl)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems([b.capitalize() for b in SUPPORTED_BROWSERS])
        if current_browser and current_browser.lower() in SUPPORTED_BROWSERS:
            self.browser_combo.setCurrentIndex(SUPPORTED_BROWSERS.index(current_browser.lower()))
        br_row.addWidget(self.browser_combo)
        br_row.addStretch()
        root.addLayout(br_row)
        root.addWidget(hdivider())

        root.addWidget(self.rb_file)
        hint = label(
            "'Get cookies.txt LOCALLY' eklentisiyle dışa aktarın. Tarayıcı açıkken de çalışır.",
            11, TEXT3, wrap=True
        )
        hint.setContentsMargins(26, 0, 0, 0)
        root.addWidget(hint)

        fl_row = QHBoxLayout()
        fl_row.setContentsMargins(26, 0, 0, 0)
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText("Dosya seçilmedi…")
        self.file_entry.setReadOnly(True)
        if current_file:
            self.file_entry.setText(current_file)
        fl_row.addWidget(self.file_entry, stretch=1)
        browse_btn = QPushButton("Gözat")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        fl_row.addWidget(browse_btn)
        root.addLayout(fl_row)

        if current_browser:   self.rb_browser.setChecked(True)
        elif current_file:    self.rb_file.setChecked(True)
        else:                 self.rb_none.setChecked(True)

        for rb in (self.rb_none, self.rb_browser, self.rb_file):
            rb.toggled.connect(self._sync)
        self._sync()

        root.addWidget(hdivider())
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        c = QPushButton("İptal"); c.setFixedWidth(90); c.clicked.connect(self.reject)
        btn_row.addWidget(c)
        btn_row.addSpacing(8)
        ok = make_accent_btn("Uygula", BLUE); ok.setFixedWidth(90); ok.clicked.connect(self._apply)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _sync(self):
        self.browser_combo.setEnabled(self.rb_browser.isChecked())
        self.file_entry.setEnabled(self.rb_file.isChecked())

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Çerez Dosyası Seç", "", "Cookie files (*.txt);;All (*)"
        )
        if path:
            self.file_entry.setText(path)
            self.rb_file.setChecked(True)

    def _apply(self):
        if self.rb_browser.isChecked():
            chosen = SUPPORTED_BROWSERS[self.browser_combo.currentIndex()]
            paths  = BROWSER_PROFILE_PATHS.get(chosen, [])
            profile_found = any(os.path.isdir(p) for p in paths)
            if not profile_found and not hasattr(self, '_warn_added'):
                self._browser_warning = label(
                    f"⚠ {chosen.capitalize()} profili bu sistemde bulunamadı.",
                    11, YELLOW, wrap=True
                )
                lay = self.layout()
                if lay:
                    lay.insertWidget(lay.count() - 1, self._browser_warning)
                    self._warn_added = True
            self._browser = chosen
            self._file    = None
        elif self.rb_file.isChecked():
            p = self.file_entry.text().strip()
            if not p or not os.path.isfile(p):
                self.file_entry.setStyleSheet(f"border-color:{RED};")
                return
            self._browser = None
            self._file    = p
        else:
            self._browser = None
            self._file    = None
        self.accept()

    def result_browser(self): return self._browser
    def result_file(self):    return self._file


# ═══════════════════════════════════════════════════════════
#  COOKIE LOCKED DIALOG
# ═══════════════════════════════════════════════════════════
class CookieLockedDialog(QDialog):
    def __init__(self, browser: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Çerez Erişim Hatası")
        self.setMinimumWidth(480)
        self.setStyleSheet(build_stylesheet())
        self._choice    = None
        self._file_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(14)

        root.addWidget(label("🔒 Tarayıcı çerezlerine erişilemiyor", 15, RED, bold=True))
        root.addWidget(label(
            f"<b>{browser.capitalize()}</b> açık ya da çerez veritabanı kilitli.<br>"
            "Chromium tabanlı tarayıcılar çalışırken çerezleri şifreler.",
            12, TEXT2, wrap=True
        ))
        root.addWidget(hdivider())

        root.addWidget(label("Seçenek 1 — Tarayıcıyı kapat ve tekrar dene", 13, TEXT, bold=True))
        retry = make_accent_btn("Tarayıcı çereziyle tekrar dene", BLUE)
        retry.setFixedHeight(38)
        retry.clicked.connect(self._retry)
        root.addWidget(retry)
        root.addWidget(hdivider())

        root.addWidget(label("Seçenek 2 — Çerez dosyası kullan (önerilen)", 13, TEXT, bold=True))
        root.addWidget(label("'Get cookies.txt LOCALLY' eklentisiyle dışa aktarın:", 12, TEXT3))

        links = QHBoxLayout()
        for name, url in [
            ("Chrome/Brave/Edge", "https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"),
            ("Firefox",           "https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/"),
        ]:
            b = make_accent_btn(f"↗ {name}", SAPPHIRE)
            b.setFixedHeight(30)
            b.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            links.addWidget(b)
        links.addStretch()
        root.addLayout(links)

        fl = QHBoxLayout()
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText(".txt dosyası seçin…")
        self.file_entry.setReadOnly(True)
        self.file_entry.setFixedHeight(36)
        fl.addWidget(self.file_entry, stretch=1)
        br = QPushButton("Gözat"); br.setFixedSize(80, 36); br.clicked.connect(self._browse)
        fl.addWidget(br)
        use = make_accent_btn("Bu dosyayı kullan", GREEN)
        use.setFixedSize(120, 36)
        use.clicked.connect(self._use_file)
        fl.addWidget(use)
        root.addLayout(fl)
        root.addWidget(hdivider())

        cr = QHBoxLayout()
        cr.addStretch()
        cancel = QPushButton("İndirmeyi iptal et")
        cancel.setObjectName("ghostBtn")
        cancel.clicked.connect(self.reject)
        cr.addWidget(cancel)
        root.addLayout(cr)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Çerez Dosyası", "", "Cookie (*.txt);;All (*)")
        if p:
            self.file_entry.setText(p)
            self._file_path = p

    def _retry(self):    self._choice = "retry"; self.accept()

    def _use_file(self):
        p = self.file_entry.text().strip()
        if not p or not os.path.isfile(p):
            self.file_entry.setStyleSheet(f"border-color:{RED};")
            return
        self._file_path = p
        self._choice    = "file"
        self.accept()

    def choice(self):    return self._choice
    def file_path(self): return self._file_path


# ═══════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════
class YtDlpUpdater(QRunnable):
    class Signals(QObject):
        log = pyqtSignal(str)
        status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.signals = self.Signals()

    def run(self):
        try:
            if getattr(sys, 'frozen', False):
                self.signals.status.emit("Paketlenmiş sürümde desteklenmiyor", YELLOW)
                self.signals.log.emit("Bu uygulama .exe olarak paketlenmiş.")
                self.signals.log.emit("yt-dlp exe içine gömülüdür, güncellenemez.")
                return

            import shutil
            pip = shutil.which("pip") or shutil.which("pip3")
            if pip:
                cmd = [pip, "install", "--upgrade", "yt-dlp"]
            else:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            self.signals.log.emit(f"$ {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            for line in (result.stdout + result.stderr).splitlines():
                if line.strip():
                    self.signals.log.emit(line)
            if result.returncode == 0:
                self.signals.status.emit("Güncellendi ✓", GREEN)
            else:
                self.signals.status.emit("Başarısız", RED)
        except subprocess.TimeoutExpired:
            self.signals.status.emit("Zaman aşımı", RED)
        except Exception as ex:
            self.signals.status.emit(f"Hata: {str(ex)[:40]}", RED)


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setMinimumSize(560, 600)
        self.setStyleSheet(build_stylesheet())
        self._s = settings.copy()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        from PyQt6.QtWidgets import QSlider
        self._QSlider = QSlider

        tabs = QTabWidget()
        tabs.setStyleSheet(build_stylesheet())
        root.addWidget(tabs, stretch=1)

        tabs.addTab(self._tab_general(),  "⚙  Genel")
        tabs.addTab(self._tab_advanced(), "🔧 Gelişmiş")
        tabs.addTab(self._tab_transcripts(), "T  Transkript")
        tabs.addTab(self._tab_update(),   "🔄 Güncelleme")

        root.addWidget(hdivider())
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(20, 12, 20, 16)
        btn_row.addStretch()
        c = QPushButton("İptal"); c.setFixedWidth(90); c.clicked.connect(self.reject)
        btn_row.addWidget(c)
        btn_row.addSpacing(8)
        ok = make_accent_btn("Kaydet", BLUE); ok.setFixedWidth(90); ok.clicked.connect(self._save)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _tab_general(self) -> QWidget:
        w   = QWidget(); w.setObjectName("dialog")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(label("İndirme Klasörü", 12, TEXT2))
        fl = QHBoxLayout()
        self.path_entry = QLineEdit(self._s["download_path"])
        self.path_entry.setReadOnly(True)
        fl.addWidget(self.path_entry, stretch=1)
        br = QPushButton("Gözat"); br.setFixedWidth(80); br.clicked.connect(self._browse)
        fl.addWidget(br)
        lay.addLayout(fl)
        lay.addWidget(hdivider())

        grid = QHBoxLayout(); grid.setSpacing(12)
        for lbl_txt, attr, items, key in [
            ("Varsayılan Kalite",   "quality_combo", VIDEO_QUALITIES,             "default_quality"),
            ("Varsayılan Format",   "format_combo",  VIDEO_FORMATS + AUDIO_FORMATS,"default_format"),
            ("Ses Kalitesi (kbps)", "aq_combo",      AUDIO_QUALITIES,             "default_audio_quality"),
        ]:
            col = QVBoxLayout()
            col.addWidget(label(lbl_txt, 12, TEXT2))
            cb = QComboBox(); cb.addItems(items); cb.setCurrentText(self._s.get(key, items[0]))
            setattr(self, attr, cb)
            col.addWidget(cb)
            grid.addLayout(col)
        lay.addLayout(grid)
        lay.addWidget(hdivider())

        lay.addWidget(label("Varsayılan Seçenekler", 12, TEXT2))
        self.subs_check  = QCheckBox("Altyazıları göm (EN & TR)")
        self.thumb_check = QCheckBox("Küçük resmi göm")
        self.desc_check  = QCheckBox("Açıklamayı kaydet (.description)")
        self.metadata_check = QCheckBox("Ses/Video Meta Verilerini göm (ID3 Tags)")
        for cb, key in [
            (self.subs_check,  "embed_subtitles"),
            (self.thumb_check, "embed_thumbnail"),
            (self.desc_check,  "write_description"),
            (self.metadata_check, "embed_metadata"),
        ]:
            cb.setChecked(self._s.get(key, False))
            lay.addWidget(cb)

        lay.addStretch()
        return w

    def _tab_advanced(self) -> QWidget:
        from PyQt6.QtWidgets import QSlider
        w   = QWidget(); w.setObjectName("dialog")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(label("Eşzamanlı Parça İndirme", 12, TEXT2))
        frag_row = QHBoxLayout()
        self.frag_slider = QSlider(Qt.Orientation.Horizontal)
        self.frag_slider.setRange(1, 16)
        self.frag_slider.setValue(self._s.get("concurrent_fragments", 4))
        self.frag_val = label(str(self.frag_slider.value()), 13, BLUE, bold=True)
        self.frag_val.setFixedWidth(28)
        self.frag_slider.valueChanged.connect(lambda v: self.frag_val.setText(str(v)))
        frag_row.addWidget(self.frag_slider, stretch=1)
        frag_row.addWidget(self.frag_val)
        lay.addLayout(frag_row)
        lay.addWidget(label(
            "Daha yüksek değer = hızlı ama daha fazla CPU kullanımı", 11, TEXT3
        ))
        lay.addWidget(hdivider())

        lay.addWidget(label("Geçmiş Limiti", 12, TEXT2))
        hist_row = QHBoxLayout()
        self.hist_limit = QSpinBox()
        self.hist_limit.setRange(10, 500)
        self.hist_limit.setValue(self._s.get("max_history", 50))
        self.hist_limit.setFixedWidth(80)
        self.hist_limit.setStyleSheet(
            f"background:{INPUT_BG}; border:1.5px solid {BORDER}; "
            f"border-radius:8px; padding:6px; color:{TEXT};"
        )
        hist_row.addWidget(self.hist_limit)
        hist_row.addStretch()
        lay.addLayout(hist_row)
        lay.addWidget(hdivider())

        lay.addWidget(label("Ayarları Sıfırla", 12, TEXT2))
        rst = QPushButton("Varsayılanlara Dön")
        rst.setObjectName("dangerBtn")
        rst.setFixedWidth(180)
        rst.clicked.connect(self._reset_defaults)
        lay.addWidget(rst)

        lay.addStretch()
        return w

    def _tab_transcripts(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("dialog")

        inner = QWidget()
        inner.setObjectName("dialog")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(label("Transcript Output", 12, TEXT2))
        out_row = QHBoxLayout()
        self.transcript_output_entry = QLineEdit(
            self._s.get("transcript_output_path", DEFAULT_SETTINGS["transcript_output_path"])
        )
        self.transcript_output_entry.setReadOnly(True)
        out_row.addWidget(self.transcript_output_entry, stretch=1)
        out_btn = QPushButton("Gozat")
        out_btn.setFixedWidth(80)
        out_btn.clicked.connect(self._browse_transcript_output)
        out_row.addWidget(out_btn)
        lay.addLayout(out_row)
        lay.addWidget(hdivider())

        row = QHBoxLayout()
        row.setSpacing(12)

        lang_col = QVBoxLayout()
        lang_col.addWidget(label("Language Priority", 12, TEXT2))
        self.transcript_languages_entry = QLineEdit(
            self._s.get("transcript_languages", DEFAULT_SETTINGS["transcript_languages"])
        )
        lang_col.addWidget(self.transcript_languages_entry)
        row.addLayout(lang_col, stretch=1)

        fmt_col = QVBoxLayout()
        fmt_col.addWidget(label("Output Format", 12, TEXT2))
        self.transcript_format_combo = QComboBox()
        self.transcript_format_combo.addItems(["both", "txt", "md"])
        self.transcript_format_combo.setCurrentText(
            self._s.get("transcript_output_format", DEFAULT_SETTINGS["transcript_output_format"])
        )
        fmt_col.addWidget(self.transcript_format_combo)
        row.addLayout(fmt_col)
        lay.addLayout(row)
        lay.addWidget(hdivider())

        lay.addWidget(label("Transcript Defaults", 12, TEXT2))
        self.transcript_manual_only_check = QCheckBox("Manual only")
        self.transcript_auto_fallback_check = QCheckBox("Auto fallback")
        self.transcript_keep_cues_check = QCheckBox("Keep cues")
        self.transcript_timestamps_check = QCheckBox("Timestamps")
        self.transcript_metadata_only_check = QCheckBox("Metadata only")
        for cb, key in [
            (self.transcript_manual_only_check, "transcript_manual_only"),
            (self.transcript_auto_fallback_check, "transcript_auto_fallback"),
            (self.transcript_keep_cues_check, "transcript_keep_cues"),
            (self.transcript_timestamps_check, "transcript_timestamps"),
            (self.transcript_metadata_only_check, "transcript_metadata_only"),
        ]:
            cb.setChecked(self._s.get(key, DEFAULT_SETTINGS[key]))
            lay.addWidget(cb)
        lay.addWidget(hdivider())

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.transcript_retries_spin = self._settings_spin(
            1, 20, self._s.get("transcript_retries", DEFAULT_SETTINGS["transcript_retries"])
        )
        self.transcript_progress_interval_spin = self._settings_spin(
            1,
            10000,
            self._s.get(
                "transcript_progress_interval",
                DEFAULT_SETTINGS["transcript_progress_interval"],
            ),
        )
        self.transcript_delay_spin = self._settings_double_spin(
            0.0, 120.0, self._s.get("transcript_delay", DEFAULT_SETTINGS["transcript_delay"])
        )
        self.transcript_retry_delay_spin = self._settings_double_spin(
            0.0,
            120.0,
            self._s.get("transcript_retry_delay", DEFAULT_SETTINGS["transcript_retry_delay"]),
        )

        fields = [
            ("Retries", self.transcript_retries_spin),
            ("Progress interval", self.transcript_progress_interval_spin),
            ("Delay", self.transcript_delay_spin),
            ("Retry delay", self.transcript_retry_delay_spin),
        ]
        for i, (text, widget) in enumerate(fields):
            row_idx = i // 2
            col_idx = (i % 2) * 2
            grid.addWidget(label(text, 12, TEXT2), row_idx, col_idx)
            grid.addWidget(widget, row_idx, col_idx + 1)
        lay.addLayout(grid)
        lay.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)
        return w

    def _tab_update(self) -> QWidget:
        w   = QWidget(); w.setObjectName("dialog")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(label("yt-dlp Güncellemesi", 14, TEXT, bold=True))
        lay.addWidget(label(
            "yt-dlp'yi en son sürüme güncelleyin. Yeni site desteği ve hata düzeltmeleri için önerilir.",
            12, TEXT3, wrap=True
        ))
        lay.addWidget(hdivider())

        self.upd_lbl = label("", 12, TEXT3)
        upd_row = QHBoxLayout()
        upd_btn = make_accent_btn("yt-dlp'yi Güncelle", YELLOW)
        upd_btn.setFixedHeight(36)
        upd_btn.clicked.connect(self._update_ytdlp)
        upd_row.addWidget(upd_btn)
        upd_row.addWidget(self.upd_lbl)
        upd_row.addStretch()
        lay.addLayout(upd_row)

        self.upd_log = QTextEdit()
        self.upd_log.setReadOnly(True)
        self.upd_log.setPlaceholderText("Güncelleme çıktısı burada görünecek…")
        self.upd_log.setFixedHeight(140)
        lay.addWidget(self.upd_log)

        lay.addStretch()
        return w

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self._s["download_path"])
        if folder:
            self._s["download_path"] = folder
            self.path_entry.setText(folder)

    def _browse_transcript_output(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Transcript klasoru",
            self.transcript_output_entry.text(),
        )
        if folder:
            self._s["transcript_output_path"] = folder
            self.transcript_output_entry.setText(folder)

    @staticmethod
    def _settings_spin(min_value: int, max_value: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setValue(value)
        spin.setFixedWidth(90)
        return spin

    @staticmethod
    def _settings_double_spin(
        min_value: float,
        max_value: float,
        value: float,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_value, max_value)
        spin.setDecimals(2)
        spin.setSingleStep(0.25)
        spin.setValue(value)
        spin.setFixedWidth(90)
        return spin

    def _reset_defaults(self):
        for k, v in DEFAULT_SETTINGS.items():
            self._s[k] = v
        self.accept()



    def _update_ytdlp(self):
        self.upd_lbl.setText("Güncelleniyor…")
        self.upd_lbl.setStyleSheet(f"color:{YELLOW}; font-size:12px;")
        self.upd_log.clear()

        self._updater = YtDlpUpdater()
        self._updater.signals.log.connect(self.upd_log.append)
        
        def set_status(txt, color):
            self.upd_lbl.setText(txt)
            self.upd_lbl.setStyleSheet(f"color:{color}; font-size:12px;")
            
        self._updater.signals.status.connect(set_status)
        QThreadPool.globalInstance().start(self._updater)

    def _save(self):
        self._s["default_quality"]       = self.quality_combo.currentText()
        self._s["default_format"]        = self.format_combo.currentText()
        self._s["default_audio_quality"] = self.aq_combo.currentText()
        self._s["embed_subtitles"]       = self.subs_check.isChecked()
        self._s["embed_thumbnail"]       = self.thumb_check.isChecked()
        self._s["write_description"]     = self.desc_check.isChecked()
        self._s["embed_metadata"]        = self.metadata_check.isChecked()
        self._s["concurrent_fragments"]  = self.frag_slider.value()
        self._s["max_history"]           = self.hist_limit.value()
        self._s["transcript_output_path"] = (
            self.transcript_output_entry.text().strip()
            or DEFAULT_SETTINGS["transcript_output_path"]
        )
        self._s["transcript_languages"] = (
            self.transcript_languages_entry.text().strip()
            or DEFAULT_SETTINGS["transcript_languages"]
        )
        self._s["transcript_output_format"] = self.transcript_format_combo.currentText()
        self._s["transcript_timestamps"] = self.transcript_timestamps_check.isChecked()
        self._s["transcript_metadata_only"] = self.transcript_metadata_only_check.isChecked()
        self._s["transcript_auto_fallback"] = self.transcript_auto_fallback_check.isChecked()
        self._s["transcript_manual_only"] = self.transcript_manual_only_check.isChecked()
        self._s["transcript_keep_cues"] = self.transcript_keep_cues_check.isChecked()
        self._s["transcript_retries"] = self.transcript_retries_spin.value()
        self._s["transcript_retry_delay"] = self.transcript_retry_delay_spin.value()
        self._s["transcript_progress_interval"] = self.transcript_progress_interval_spin.value()
        self._s["transcript_delay"] = self.transcript_delay_spin.value()
        self.accept()

    def result_settings(self) -> dict:
        return self._s


# ═══════════════════════════════════════════════════════════
#  BRIDGE  (thread → UI)
# ═══════════════════════════════════════════════════════════
