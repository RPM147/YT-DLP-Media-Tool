import sys
import os
import json
import threading
import subprocess
import requests

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QProgressBar, QFileDialog, QFrame, QScrollArea, QSizePolicy,
    QDialog, QRadioButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QUrl, QPointF
from PyQt6.QtGui import (
    QPixmap, QImage, QColor, QPalette, QLinearGradient,
    QPainter, QBrush, QPen, QFont, QDesktopServices, QPolygonF
)
from downloader import Downloader, AUDIO_FORMATS, VIDEO_FORMATS, AUDIO_QUALITIES

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COLORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BG       = "#1a1b26"
INPUT_BG = "#24263a"
BORDER   = "#33365a"
HOVER    = "#2a2d45"

ACCENT   = "#7aa2f7"
ACCENT2  = "#7dcfff"
GREEN    = "#9ece6a"
RED      = "#f7768e"
AMBER    = "#e0af68"

TEXT     = "#c0caf5"
TEXT2    = "#a9b1d6"
TEXT3    = "#565f89"

DL_A = "#1d4ed8"
DL_B = "#3b82f6"
DL_C = "#06b6d4"

SUPPORTED_BROWSERS = [
    "brave", "chrome", "firefox", "edge",
    "opera", "chromium", "vivaldi", "safari"
]

SETTINGS_FILE = os.path.join(
    os.path.expanduser("~"), ".rpm_downloader_settings.json"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RGBA HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_SETTINGS = {
    "download_path":         os.path.join(os.path.expanduser("~"), "Downloads"),
    "default_quality":       "Best Quality",
    "default_format":        "mp4",
    "default_audio_quality": "192",
    "embed_subtitles":       False,
}

def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STYLESHEET
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STYLESHEET = f"""
* {{
    font-family: 'Segoe UI', sans-serif;
    background: transparent;
    color: {TEXT};
    border: none;
}}
QMainWindow {{
    background-color: {BG};
}}
QWidget#root, QWidget#dialog {{
    background-color: {BG};
}}
QLineEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
    selection-background-color: {rgba(ACCENT, 0.25)};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QPushButton {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {HOVER};
    border-color: {rgba(ACCENT, 0.31)};
}}
QPushButton:pressed {{
    background-color: {BORDER};
}}
QPushButton#cancelBtn {{
    background-color: {rgba(RED, 0.08)};
    color: {RED};
    border: 1px solid {rgba(RED, 0.25)};
    font-weight: 700;
    font-size: 15px;
    border-radius: 12px;
    padding: 14px 24px;
    letter-spacing: 2px;
}}
QPushButton#cancelBtn:hover {{
    background-color: {rgba(RED, 0.15)};
    border-color: {rgba(RED, 0.38)};
}}
QComboBox {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {rgba(ACCENT, 0.31)};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT3};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {rgba(ACCENT, 0.19)};
    selection-color: white;
    outline: none;
    padding: 4px;
}}
QCheckBox {{
    color: {TEXT};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {BORDER};
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT2};
}}
QRadioButton {{
    color: {TEXT};
    spacing: 8px;
    font-size: 13px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {BORDER};
    background: {INPUT_BG};
}}
QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QRadioButton::indicator:hover {{
    border-color: {ACCENT2};
}}
QProgressBar {{
    background-color: {INPUT_BG};
    border: none;
    border-radius: 4px;
    height: 8px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 {ACCENT2});
    border-radius: 4px;
}}
QListWidget {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {rgba(ACCENT, 0.2)};
    color: {TEXT};
}}
QListWidget::item:hover {{
    background-color: {rgba(ACCENT, 0.1)};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT3};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def divider():
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background-color: {rgba(BORDER, 0.4)};")
    return f


def accent_btn(text, color=None):
    c      = color or ACCENT
    bg     = rgba(c, 0.12)
    bg_hov = rgba(c, 0.25)
    border = rgba(c, 0.35)
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            color: {c};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {bg_hov};
            color: white;
        }}
        QPushButton:disabled {{
            color: {TEXT3};
            background-color: {INPUT_BG};
            border-color: {BORDER};
        }}
    """)
    return btn


def make_labeled_widget(label_text: str, ctrl: QWidget, ctrl_height: int = 38) -> QWidget:
    ctrl.setFixedHeight(ctrl_height)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
    lbl.setFixedHeight(16)
    container = QWidget()
    lay = QVBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    lay.addWidget(lbl)
    lay.addWidget(ctrl)
    return container

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SPEED GRAPH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SpeedGraph(QWidget):
    MAX_POINTS = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: list = []
        self.setFixedHeight(48)
        self.setStyleSheet("background: transparent;")

    def add_sample(self, kbps: float):
        self._samples.append(max(0.0, kbps))
        if len(self._samples) > self.MAX_POINTS:
            self._samples.pop(0)
        self.update()

    def reset(self):
        self._samples.clear()
        self.update()

    def paintEvent(self, event):
        if len(self._samples) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mx   = max(self._samples) or 1.0
        n    = len(self._samples)

        pts = []
        for i, v in enumerate(self._samples):
            x = w * i / (n - 1)
            y = h - (v / mx) * (h - 4) - 2
            pts.append(QPointF(x, y))

        fill_pts   = [QPointF(0, h)] + pts + [QPointF(w, h)]
        fill_color = QColor(ACCENT2)
        fill_color.setAlpha(40)
        p.setBrush(QBrush(fill_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF(fill_pts))

        pen = QPen(QColor(ACCENT2))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(QPolygonF(pts))
        p.end()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GRADIENT DOWNLOAD BUTTON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GradientButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._hovered = False
        self._pressed = False
        self._t = 0.0
        self.setMinimumHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(30)

    def _tick(self):
        self._t += 0.004
        if self._t > 1.0:
            self._t = 0.0
        if self._hovered:
            self.update()

    def enterEvent(self, e):
        self._hovered = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False; self.update(); super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True; self.update(); super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False; self.update(); super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        if self._pressed:
            r = r.adjusted(1, 1, -1, -1)

        g = QLinearGradient(0, 0, r.width(), 0)
        if self._hovered:
            o = self._t * 0.3
            g.setColorAt(0.0, QColor("#1e40af"))
            g.setColorAt(min(0.6, 0.3 + o), QColor("#2563eb"))
            g.setColorAt(0.7, QColor("#0891b2"))
            g.setColorAt(1.0, QColor("#06b6d4"))
        else:
            g.setColorAt(0.0, QColor(DL_A))
            g.setColorAt(0.5, QColor(DL_B))
            g.setColorAt(1.0, QColor(DL_C))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 12, 12)

        hi = QLinearGradient(0, r.top(), 0, r.top() + r.height() * 0.4)
        hi.setColorAt(0, QColor(255, 255, 255, 30 if self._hovered else 15))
        hi.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(hi))
        p.drawRoundedRect(r, 12, 12)

        p.setPen(QPen(QColor("white")))
        f = QFont("Segoe UI", 14, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PLAYLIST DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PlaylistDialog(QDialog):
    def __init__(self, entries: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playlist / Channel")
        self.setObjectName("dialog")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(STYLESHEET)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)

        title = QLabel(f"Found {len(entries)} videos — select which to download")
        title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700;")
        root.addWidget(title)

        tb = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.setFixedHeight(32)
        sel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_all.clicked.connect(self._select_all)
        tb.addWidget(sel_all)

        sel_none = QPushButton("Select None")
        sel_none.setFixedHeight(32)
        sel_none.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_none.clicked.connect(self._select_none)
        tb.addWidget(sel_none)

        tb.addStretch()
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
        tb.addWidget(self.count_lbl)
        root.addLayout(tb)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for i, entry in enumerate(entries, 1):
            title_text = entry.get('title') or entry.get('url') or f"Video {i}"
            duration   = entry.get('duration')
            dur_str    = f"  [{int(duration//60)}:{int(duration%60):02d}]" if duration else ""
            item = QListWidgetItem(f"{i}.  {title_text}{dur_str}")
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_widget.addItem(item)
        self.list_widget.itemChanged.connect(self._update_count)
        root.addWidget(self.list_widget)
        self._update_count()

        root.addWidget(divider())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(90)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        ok = accent_btn("Download Selected", ACCENT)
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.clicked.connect(self.accept)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _update_count(self):
        checked = sum(
            1 for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
        )
        self.count_lbl.setText(f"{checked} selected")

    def selected_indices(self) -> list:
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    def playlist_items_str(self) -> str:
        return ",".join(str(i) for i in self.selected_indices())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETTINGS DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setObjectName("dialog")
        self.setMinimumWidth(480)
        self.setStyleSheet(STYLESHEET)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._settings = settings.copy()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        root.addWidget(divider())

        fl_lbl = QLabel("Default download folder")
        fl_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(fl_lbl)

        fl_row = QHBoxLayout()
        self.path_entry = QLineEdit(self._settings["download_path"])
        self.path_entry.setReadOnly(True)
        fl_row.addWidget(self.path_entry, stretch=1)
        br = QPushButton("Browse")
        br.setFixedWidth(80)
        br.setCursor(Qt.CursorShape.PointingHandCursor)
        br.clicked.connect(self._browse)
        fl_row.addWidget(br)
        root.addLayout(fl_row)

        root.addWidget(divider())

        q_lbl = QLabel("Default quality")
        q_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(q_lbl)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(
            ["Best Quality", "1080p", "720p", "480p", "360p", "Audio Only"]
        )
        self.quality_combo.setCurrentText(self._settings["default_quality"])
        self.quality_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.quality_combo)

        root.addWidget(divider())

        fmt_lbl = QLabel("Default format")
        fmt_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(fmt_lbl)
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS + AUDIO_FORMATS)
        self.format_combo.setCurrentText(self._settings["default_format"])
        self.format_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.format_combo)

        root.addWidget(divider())

        aq_lbl = QLabel("Default audio quality (kbps)")
        aq_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(aq_lbl)
        self.aq_combo = QComboBox()
        self.aq_combo.addItems(AUDIO_QUALITIES)
        self.aq_combo.setCurrentText(self._settings.get("default_audio_quality", "192"))
        self.aq_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.aq_combo)

        root.addWidget(divider())

        self.subs_check = QCheckBox("Embed subtitles by default")
        self.subs_check.setChecked(self._settings.get("embed_subtitles", False))
        self.subs_check.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.subs_check)

        root.addWidget(divider())

        ydlp_lbl = QLabel("yt-dlp")
        ydlp_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(ydlp_lbl)

        self.update_status_lbl = QLabel("")
        self.update_status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 11px;")

        upd_row = QHBoxLayout()
        upd_btn = accent_btn("Update yt-dlp", AMBER)
        upd_btn.setFixedHeight(34)
        upd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        upd_btn.clicked.connect(self._update_ytdlp)
        upd_row.addWidget(upd_btn)
        upd_row.addWidget(self.update_status_lbl)
        upd_row.addStretch()
        root.addLayout(upd_row)

        root.addWidget(divider())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(90)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        ok = accent_btn("Save", ACCENT)
        ok.setFixedWidth(90)
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.clicked.connect(self._save)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self._settings["download_path"]
        )
        if folder:
            self._settings["download_path"] = folder
            self.path_entry.setText(folder)

    def _update_ytdlp(self):
        self.update_status_lbl.setText("Updating…")
        self.update_status_lbl.setStyleSheet(f"color: {AMBER}; font-size: 11px;")

        # Dialog kapanmış mı kontrolü için weak reference
        import weakref
        self_ref = weakref.ref(self)

        def set_label(text, color):
            # Dialog hâlâ hayatta mı kontrol et
            obj = self_ref()
            if obj is not None:
                QTimer.singleShot(0, lambda: _apply(obj, text, color))

        def _apply(obj, text, color):
            # Widget hâlâ geçerli mi?
            try:
                obj.update_status_lbl.setText(text)
                obj.update_status_lbl.setStyleSheet(
                    f"color: {color}; font-size: 11px;"
                )
            except RuntimeError:
                # Widget zaten silinmiş, sessizce geç
                pass

        def run():
            try:
                # pip yolunu önce doğrudan bulmayı dene
                import shutil
                pip_exec = shutil.which("pip") or shutil.which("pip3")

                if pip_exec:
                    cmd = [pip_exec, "install", "--upgrade", "yt-dlp"]
                else:
                    cmd = [sys.executable, "-m", "pip",
                        "install", "--upgrade", "yt-dlp"]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30       # 60'tan 30'a indirdik — daha makul
                )

                if result.returncode == 0:
                    set_label("Updated ✓", GREEN)
                else:
                    err_line = result.stderr.strip().splitlines()[-1] \
                            if result.stderr.strip() else "Unknown error"
                    set_label(f"Failed: {err_line[:35]}", RED)

            except subprocess.TimeoutExpired:
                set_label("Timed out — check connection", RED)
            except FileNotFoundError:
                set_label("pip not found", RED)
            except Exception as ex:
                set_label(f"Error: {str(ex)[:35]}", RED)

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        self._settings["default_quality"]       = self.quality_combo.currentText()
        self._settings["default_format"]        = self.format_combo.currentText()
        self._settings["default_audio_quality"] = self.aq_combo.currentText()
        self._settings["embed_subtitles"]       = self.subs_check.isChecked()
        self.accept()

    def result_settings(self) -> dict:
        return self._settings

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COOKIE LOCKED DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CookieLockedDialog(QDialog):
    def __init__(self, browser: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookie Access Error")
        self.setObjectName("dialog")
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLESHEET)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._choice    = None
        self._file_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(16)

        title = QLabel("Cannot access browser cookies")
        title.setStyleSheet(f"color: {RED}; font-size: 15px; font-weight: 700;")
        root.addWidget(title)

        desc = QLabel(
            f"<b>{browser.capitalize()}</b> is either open or its cookie database "
            f"is locked.<br>Chromium-based browsers encrypt and lock cookies while running."
        )
        desc.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(desc)

        root.addWidget(divider())

        opt1 = QLabel("Option 1 — Close the browser and retry")
        opt1.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
        root.addWidget(opt1)

        retry_btn = accent_btn("Retry with browser cookies", ACCENT)
        retry_btn.setFixedHeight(38)
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._retry)
        root.addWidget(retry_btn)

        root.addWidget(divider())

        opt2 = QLabel("Option 2 — Export cookies to a file (recommended)")
        opt2.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
        root.addWidget(opt2)

        opt2_desc = QLabel(
            "Install <b>Get cookies.txt LOCALLY</b> extension, export as .txt:"
        )
        opt2_desc.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
        opt2_desc.setWordWrap(True)
        opt2_desc.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(opt2_desc)

        links_row = QHBoxLayout()
        for name, url in [
            ("Chrome / Brave / Edge",
             "https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"),
            ("Firefox",
             "https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/"),
        ]:
            b = accent_btn(f"↗  {name}", ACCENT2)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_row.addWidget(b)
        links_row.addStretch()
        root.addLayout(links_row)

        file_row = QHBoxLayout()
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText("Select exported .txt file…")
        self.file_entry.setReadOnly(True)
        self.file_entry.setFixedHeight(38)
        file_row.addWidget(self.file_entry, stretch=1)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(80, 38)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        use_file_btn = accent_btn("Use this file", GREEN)
        use_file_btn.setFixedSize(100, 38)
        use_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        use_file_btn.clicked.connect(self._use_file)
        file_row.addWidget(use_file_btn)
        root.addLayout(file_row)

        root.addWidget(divider())

        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        cancel_btn = QPushButton("Cancel download")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {TEXT3}; font-size: 12px;
            }}
            QPushButton:hover {{ color: {RED}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        cancel_row.addWidget(cancel_btn)
        root.addLayout(cancel_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cookie File", "", "Cookie files (*.txt);;All files (*)"
        )
        if path:
            self.file_entry.setText(path)
            self._file_path = path

    def _retry(self):
        self._choice = "retry"
        self.accept()

    def _use_file(self):
        path = self.file_entry.text().strip()
        if not path or not os.path.isfile(path):
            self.file_entry.setStyleSheet(
                f"border: 1px solid {RED}; background-color: {INPUT_BG};"
            )
            return
        self._file_path = path
        self._choice    = "file"
        self.accept()

    def choice(self):    return self._choice
    def file_path(self): return self._file_path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COOKIE CONFIG DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CookieDialog(QDialog):
    def __init__(self, current_browser, current_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookie Settings")
        self.setObjectName("dialog")
        self.setMinimumWidth(480)
        self.setStyleSheet(STYLESHEET)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._selected_browser = current_browser
        self._selected_file    = current_file

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(16)

        title = QLabel("Cookie Settings")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        desc = QLabel(
            "Some content requires authentication.\n"
            "yt-dlp can read cookies from your browser or a cookie file."
        )
        desc.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        root.addWidget(divider())

        self.rb_none = QRadioButton("Don't use cookies")
        root.addWidget(self.rb_none)

        root.addWidget(divider())

        self.rb_browser = QRadioButton("Read cookies from browser")
        root.addWidget(self.rb_browser)

        warn = QLabel(
            "⚠  Chromium-based browsers must be fully closed before cookies can be read."
        )
        warn.setStyleSheet(f"color: {AMBER}; font-size: 11px; padding-left: 26px;")
        warn.setWordWrap(True)
        root.addWidget(warn)

        br_row = QHBoxLayout()
        br_row.setContentsMargins(26, 0, 0, 0)
        br_lbl = QLabel("Browser:")
        br_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        br_lbl.setFixedWidth(65)
        br_row.addWidget(br_lbl)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems([b.capitalize() for b in SUPPORTED_BROWSERS])
        if current_browser and current_browser.lower() in SUPPORTED_BROWSERS:
            self.browser_combo.setCurrentIndex(
                SUPPORTED_BROWSERS.index(current_browser.lower())
            )
        self.browser_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        br_row.addWidget(self.browser_combo)
        br_row.addStretch()
        root.addLayout(br_row)

        root.addWidget(divider())

        self.rb_file = QRadioButton("Load from cookie file  (.txt — Netscape format)")
        root.addWidget(self.rb_file)

        file_hint = QLabel(
            "Use 'Get cookies.txt LOCALLY' extension to export. "
            "Works while browser is open."
        )
        file_hint.setStyleSheet(f"color: {TEXT3}; font-size: 11px; padding-left: 26px;")
        file_hint.setWordWrap(True)
        root.addWidget(file_hint)

        fl_row = QHBoxLayout()
        fl_row.setContentsMargins(26, 0, 0, 0)
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText("No file selected…")
        self.file_entry.setReadOnly(True)
        if current_file:
            self.file_entry.setText(current_file)
        fl_row.addWidget(self.file_entry, stretch=1)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        fl_row.addWidget(browse_btn)
        root.addLayout(fl_row)

        if current_browser:
            self.rb_browser.setChecked(True)
        elif current_file:
            self.rb_file.setChecked(True)
        else:
            self.rb_none.setChecked(True)

        self.rb_none.toggled.connect(self._sync)
        self.rb_browser.toggled.connect(self._sync)
        self.rb_file.toggled.connect(self._sync)
        self._sync()

        root.addWidget(divider())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(90)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        ok = accent_btn("Apply", ACCENT)
        ok.setFixedWidth(90)
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.clicked.connect(self._apply)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _sync(self):
        self.browser_combo.setEnabled(self.rb_browser.isChecked())
        self.file_entry.setEnabled(self.rb_file.isChecked())

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cookie File", "", "Cookie files (*.txt);;All files (*)"
        )
        if path:
            self.file_entry.setText(path)
            self.rb_file.setChecked(True)

    def _apply(self):
        if self.rb_browser.isChecked():
            self._selected_browser = SUPPORTED_BROWSERS[
                self.browser_combo.currentIndex()
            ]
            self._selected_file = None
        elif self.rb_file.isChecked():
            path = self.file_entry.text().strip()
            if not path or not os.path.isfile(path):
                self.file_entry.setStyleSheet(f"border: 1px solid {RED};")
                return
            self._selected_browser = None
            self._selected_file    = path
        else:
            self._selected_browser = None
            self._selected_file    = None
        self.accept()

    def result_browser(self): return self._selected_browser
    def result_file(self):    return self._selected_file

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BRIDGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Bridge(QObject):
    progress       = pyqtSignal(float, str, str)
    complete       = pyqtSignal(object)
    error          = pyqtSignal(str)
    thumb          = pyqtSignal(object)
    playlist_ready = pyqtSignal(object)
    info_fetched   = pyqtSignal(object)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  QUEUE ITEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class QueueItem:
    def __init__(self, url, quality, fmt, output_dir,
                 subtitles, audio_quality,
                 playlist_items=None, title=""):
        self.url            = url
        self.quality        = quality
        self.fmt            = fmt
        self.output_dir     = output_dir
        self.subtitles      = subtitles
        self.audio_quality  = audio_quality
        self.playlist_items = playlist_items
        self.title          = title or url
        self.status         = "queued"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN WINDOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Furkan's Media Download Tool")
        self.setMinimumSize(800, 640)
        self.resize(940, 760)
        self.setStyleSheet(STYLESHEET)
        from PyQt6.QtGui import QIcon
        icon_path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
            'icon.ico'
        )
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings      = load_settings()
        self.download_path = self.settings["download_path"]

        self.hist_placeholder  = None
        self._pending_url      = ""
        self._pending_quality  = ""
        self._pending_fmt      = ""
        self._pending_subs     = False
        self._pending_aq       = "192"
        self._pending_pl_items = None
        self._is_downloading   = False

        self._queue: list        = []
        self._queue_running      = False
        self._scroll_area        = None

        self.bridge = Bridge()
        self.bridge.progress.connect(self._on_progress)
        self.bridge.complete.connect(self._on_complete)
        self.bridge.error.connect(self._on_error)
        self.bridge.thumb.connect(self._on_thumb)
        self.bridge.playlist_ready.connect(self._on_playlist_ready)
        self.bridge.info_fetched.connect(self._on_queue_info_fetched)

        self.downloader = Downloader(
            on_progress=lambda p, s, e: self.bridge.progress.emit(p, s, e),
            on_complete=lambda i: self.bridge.complete.emit(i),
            on_error=lambda m: self.bridge.error.emit(m),
        )

        self._build_ui()

    # ─────────────────────────────────────────────
    #  UI BUILD
    # ─────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main_v = QVBoxLayout(root)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        page.setObjectName("root")
        self.body = QVBoxLayout(page)
        self.body.setContentsMargins(36, 28, 36, 28)
        self.body.setSpacing(0)

        self._build_header()
        self.body.addSpacing(24)
        self._build_url_row()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_preview()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_settings_row()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_cookie_row()
        self.body.addSpacing(24)
        self._build_download_btn()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_progress()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_queue_section()
        self.body.addSpacing(20)
        self.body.addWidget(divider())
        self.body.addSpacing(20)
        self._build_history()
        self.body.addStretch()

        self._scroll_area.setWidget(page)
        main_v.addWidget(self._scroll_area)

    def _build_header(self):
        row = QHBoxLayout()
        title = QLabel("Furkan's Media Download Tool")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 20px; font-weight: 800; letter-spacing: 0.5px;"
        )
        row.addWidget(title)
        row.addStretch()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setFixedHeight(34)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        row.addWidget(settings_btn)
        ver = QLabel("v1.0")
        ver.setStyleSheet(f"color: {TEXT3}; font-size: 11px; padding-left: 12px;")
        row.addWidget(ver)
        self.body.addLayout(row)

    def _build_url_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText(
            "Paste a URL — YouTube, Instagram, TikTok, X & more…"
        )
        self.url_entry.setFixedHeight(44)
        row.addWidget(self.url_entry, stretch=1)

        paste = QPushButton("Paste")
        paste.setFixedHeight(44)
        paste.setCursor(Qt.CursorShape.PointingHandCursor)
        paste.clicked.connect(self._paste)
        row.addWidget(paste)

        self.info_btn = accent_btn("Get Info →", ACCENT)
        self.info_btn.setFixedHeight(44)
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_btn.clicked.connect(self._get_info)
        row.addWidget(self.info_btn)

        self.body.addLayout(row)

    def _build_preview(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        self.thumb_label = QLabel("No Preview")
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"background-color: {INPUT_BG}; border-radius: 8px; "
            f"color: {TEXT3}; font-size: 11px;"
        )
        row.addWidget(self.thumb_label)

        col = QVBoxLayout()
        col.setSpacing(6)
        self.info_title = QLabel("Enter a URL and click 'Get Info' to see details")
        self.info_title.setStyleSheet(f"color: {TEXT3}; font-size: 13px;")
        self.info_title.setWordWrap(True)
        col.addWidget(self.info_title)

        self.info_meta = QLabel("")
        self.info_meta.setStyleSheet(f"color: {TEXT3}; font-size: 11px;")
        col.addWidget(self.info_meta)

        col.addStretch()
        row.addLayout(col, stretch=1)
        self.body.addLayout(row)

    def _build_settings_row(self):
        row = QHBoxLayout()
        row.setSpacing(20)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        CTRL_H = 38

        # Quality
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(
            ["Best Quality", "1080p", "720p", "480p", "360p", "Audio Only"]
        )
        self.quality_combo.setCurrentText(self.settings["default_quality"])
        self.quality_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        row.addWidget(make_labeled_widget("Quality", self.quality_combo, CTRL_H))

        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        self.format_combo.setCurrentText(
            self.settings["default_format"]
            if self.settings["default_format"] in VIDEO_FORMATS else "mp4"
        )
        self.format_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(make_labeled_widget("Format", self.format_combo, CTRL_H))

        # Audio Quality
        self.aq_combo = QComboBox()
        self.aq_combo.addItems(AUDIO_QUALITIES)
        self.aq_combo.setCurrentText(
            self.settings.get("default_audio_quality", "192")
        )
        self.aq_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._aq_block = make_labeled_widget("Audio Quality", self.aq_combo, CTRL_H)
        sp = self._aq_block.sizePolicy()
        sp.setRetainSizeWhenHidden(False)
        self._aq_block.setSizePolicy(sp)
        self._aq_block.setVisible(False)
        row.addWidget(self._aq_block)

        # Subtitles
        self.subs_check = QCheckBox("Embed subtitles")
        self.subs_check.setChecked(self.settings.get("embed_subtitles", False))
        self.subs_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._subs_block = make_labeled_widget("Subtitles", self.subs_check, CTRL_H)
        sp2 = self._subs_block.sizePolicy()
        sp2.setRetainSizeWhenHidden(False)
        self._subs_block.setSizePolicy(sp2)
        self._subs_block.setVisible(True)
        row.addWidget(self._subs_block)

        row.addStretch()

        # Save to
        self.path_entry = QLineEdit(self.download_path)
        self.path_entry.setReadOnly(True)
        self.path_entry.setMinimumWidth(180)
        self.path_entry.setStyleSheet(
            f"background-color: {INPUT_BG}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; color: {TEXT3}; font-size: 11px; padding: 0 10px;"
        )

        browse = QPushButton("Browse")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse)

        path_row_widget = QWidget()
        path_row_lay = QHBoxLayout(path_row_widget)
        path_row_lay.setContentsMargins(0, 0, 0, 0)
        path_row_lay.setSpacing(6)
        path_row_lay.addWidget(self.path_entry)
        path_row_lay.addWidget(browse)

        save_block = QWidget()
        save_lay = QVBoxLayout(save_block)
        save_lay.setContentsMargins(0, 0, 0, 0)
        save_lay.setSpacing(6)
        save_lbl = QLabel("Save to")
        save_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        save_lbl.setFixedHeight(16)
        save_lay.addWidget(save_lbl)
        path_row_widget.setFixedHeight(CTRL_H)
        save_lay.addWidget(path_row_widget)
        row.addWidget(save_block)

        self.body.addLayout(row)
        self._on_quality_changed(self.quality_combo.currentText())

    def _on_quality_changed(self, quality: str):
        is_audio = (quality == "Audio Only")
        self._aq_block.setVisible(is_audio)
        self._subs_block.setVisible(not is_audio)

        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        if is_audio:
            self.format_combo.addItems(AUDIO_FORMATS)
            df = self.settings.get("default_format", "mp3")
            self.format_combo.setCurrentText(df if df in AUDIO_FORMATS else "mp3")
        else:
            self.format_combo.addItems(VIDEO_FORMATS)
            df = self.settings.get("default_format", "mp4")
            self.format_combo.setCurrentText(df if df in VIDEO_FORMATS else "mp4")
        self.format_combo.blockSignals(False)

    def _build_cookie_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        c_lbl = QLabel("Cookies")
        c_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        row.addWidget(c_lbl)
        self.cookie_status_lbl = QLabel("Not configured")
        self.cookie_status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
        row.addWidget(self.cookie_status_lbl)
        row.addStretch()
        cfg_btn = accent_btn("Configure Cookies", AMBER)
        cfg_btn.setFixedHeight(36)
        cfg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cfg_btn.clicked.connect(self._open_cookie_dialog)
        row.addWidget(cfg_btn)
        self.body.addLayout(row)

    def _build_download_btn(self):
        self._btn_stack = QStackedWidget()
        self._btn_stack.setFixedHeight(54)

        self.dl_btn = GradientButton("⬇  DOWNLOAD")
        self.dl_btn.clicked.connect(self._toggle_download)
        self._btn_stack.addWidget(self.dl_btn)      # index 0

        self.cancel_btn = QPushButton("■  CANCEL")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setMinimumHeight(54)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cancel_btn.clicked.connect(self._toggle_download)
        self._btn_stack.addWidget(self.cancel_btn)  # index 1

        self._btn_stack.setCurrentIndex(0)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self._btn_stack, stretch=1)

        add_q_btn = accent_btn("+ Add to Queue", TEXT2)
        add_q_btn.setFixedHeight(54)
        add_q_btn.setFixedWidth(140)
        add_q_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_q_btn.clicked.connect(self._add_to_queue)
        btn_row.addWidget(add_q_btn)

        self.body.addLayout(btn_row)

    def _build_progress(self):
        top = QHBoxLayout()
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 13px;")
        top.addWidget(self.status_lbl)
        top.addStretch()
        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setStyleSheet(
            f"color: {ACCENT2}; font-weight: 700; font-size: 17px; "
            f"font-family: 'Consolas', monospace;"
        )
        top.addWidget(self.pct_lbl)
        self.body.addLayout(top)
        self.body.addSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.body.addWidget(self.progress_bar)
        self.body.addSpacing(6)

        self.speed_graph = SpeedGraph()
        self.body.addWidget(self.speed_graph)
        self.body.addSpacing(4)

        self.stats_lbl = QLabel("Speed: —  ·  ETA: —")
        self.stats_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        self.body.addWidget(self.stats_lbl)

    def _build_queue_section(self):
        hdr = QHBoxLayout()
        q_title = QLabel("Download Queue")
        q_title.setStyleSheet(f"color: {TEXT2}; font-size: 13px; font-weight: 600;")
        hdr.addWidget(q_title)
        hdr.addStretch()

        clear_q_btn = QPushButton("Clear Queue")
        clear_q_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_q_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {TEXT3}; font-size: 11px; padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {RED}; }}
        """)
        clear_q_btn.clicked.connect(self._clear_queue)
        hdr.addWidget(clear_q_btn)

        start_q_btn = accent_btn("▶  Start Queue", GREEN)
        start_q_btn.setFixedHeight(30)
        start_q_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_q_btn.clicked.connect(self._start_queue)
        hdr.addWidget(start_q_btn)

        self.body.addLayout(hdr)
        self.body.addSpacing(8)

        self.queue_list = QListWidget()
        self.queue_list.setFixedHeight(110)
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._queue_context_menu)

        ph = QListWidgetItem("Queue is empty")
        ph.setForeground(QColor(TEXT3))
        ph.setFlags(Qt.ItemFlag.NoItemFlags)
        self.queue_list.addItem(ph)
        self.body.addWidget(self.queue_list)

    def _build_history(self):
        hdr = QHBoxLayout()
        h_title = QLabel("Download History")
        h_title.setStyleSheet(f"color: {TEXT2}; font-size: 13px; font-weight: 600;")
        hdr.addWidget(h_title)
        hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {TEXT3}; font-size: 11px; padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {RED}; }}
        """)
        clear_btn.clicked.connect(self._clear_history)
        hdr.addWidget(clear_btn)
        self.body.addLayout(hdr)
        self.body.addSpacing(8)

        self.hist_container = QWidget()
        self.hist_layout    = QVBoxLayout(self.hist_container)
        self.hist_layout.setContentsMargins(0, 0, 0, 0)
        self.hist_layout.setSpacing(6)

        self.hist_placeholder = QLabel("No downloads yet")
        self.hist_placeholder.setStyleSheet(
            f"color: {TEXT3}; font-size: 12px; font-style: italic;"
        )
        self.hist_layout.addWidget(self.hist_placeholder)
        self.body.addWidget(self.hist_container)

    # ─────────────────────────────────────────────
    #  PREVIEW RESET
    # ─────────────────────────────────────────────

    def _reset_preview(self):
        """İndirme tamamlanınca info alanını ve URL kutusunu sıfırla."""
        self.thumb_label.clear()
        self.thumb_label.setText("No Preview")
        self.info_title.setText("Enter a URL and click 'Get Info' to see details")
        self.info_title.setStyleSheet(f"color: {TEXT3}; font-size: 13px;")
        self.info_meta.setText("")
        self.url_entry.clear()

    # ─────────────────────────────────────────────
    #  HISTORY
    # ─────────────────────────────────────────────

    def _clear_history(self):
        while self.hist_layout.count():
            item = self.hist_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.hist_placeholder = QLabel("No downloads yet")
        self.hist_placeholder.setStyleSheet(
            f"color: {TEXT3}; font-size: 12px; font-style: italic;"
        )
        self.hist_layout.addWidget(self.hist_placeholder)

    def _add_to_history(self, info):
        if not isinstance(info, dict):
            return
        title      = info.get('title', 'Unknown')
        ext        = info.get('ext', '')
        filename   = f"{title}.{ext}"
        size_bytes = info.get('filesize') or info.get('filesize_approx') or 0
        size_mb    = size_bytes / (1024 * 1024)

        if self.hist_placeholder and self.hist_placeholder.parent():
            self.hist_placeholder.deleteLater()
            self.hist_placeholder = None

        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row_widget)
        rl.setContentsMargins(0, 2, 0, 2)
        rl.setSpacing(10)

        tick = QLabel("✓")
        tick.setStyleSheet(f"color: {GREEN}; font-weight: bold; font-size: 13px;")
        tick.setFixedWidth(18)
        rl.addWidget(tick)

        name = QLabel(filename)
        name.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        name.setToolTip(filename)
        rl.addWidget(name, stretch=1)

        if size_mb > 0:
            sz = QLabel(f"{size_mb:.1f} MB")
            sz.setStyleSheet(f"color: {TEXT3}; font-size: 11px;")
            rl.addWidget(sz)

        self.hist_layout.insertWidget(0, row_widget)

    # ─────────────────────────────────────────────
    #  QUEUE
    # ─────────────────────────────────────────────

    def _refresh_queue_list(self):
        self.queue_list.clear()
        if not self._queue:
            ph = QListWidgetItem("Queue is empty")
            ph.setForeground(QColor(TEXT3))
            ph.setFlags(Qt.ItemFlag.NoItemFlags)
            self.queue_list.addItem(ph)
            return
        icons  = {"queued": "○", "downloading": "⬇", "done": "✓", "error": "✗"}
        colors = {"queued": TEXT3, "downloading": ACCENT, "done": GREEN, "error": RED}
        for i, q in enumerate(self._queue, 1):
            icon     = icons.get(q.status, "○")
            fmt_info = f"{q.quality} / {q.fmt}"
            label    = f"  {icon}  {i}. {q.title[:45]}  [{fmt_info}]"
            litem    = QListWidgetItem(label)
            litem.setForeground(QColor(colors.get(q.status, TEXT3)))
            self.queue_list.addItem(litem)

    def _clear_queue(self):
        self._queue.clear()
        self._refresh_queue_list()

    def _queue_context_menu(self, pos):
        idx = self.queue_list.currentRow()
        if idx < 0 or idx >= len(self._queue):
            return
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {INPUT_BG}; border: 1px solid {BORDER};
                color: {TEXT}; padding: 4px;
            }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{ background: {rgba(ACCENT, 0.2)}; }}
        """)
        remove_act = menu.addAction("Remove from queue")
        action = menu.exec(self.queue_list.mapToGlobal(pos))
        if action == remove_act:
            self._queue.pop(idx)
            self._refresh_queue_list()

    def _add_to_queue(self):
        url = self.url_entry.text().strip()
        if not url:
            self._status("URL is empty", RED)
            return

        quality       = self.quality_combo.currentText()
        fmt           = self.format_combo.currentText()
        output_dir    = self.download_path
        subtitles     = self.subs_check.isChecked()
        audio_quality = self.aq_combo.currentText()

        self._status("Fetching info for queue…", TEXT3)

        def fetch():
            info  = self.downloader.get_info(url, flat_playlist=False)
            title = ""
            if info:
                if info.get("_type") in ("playlist", "multi_video") or "entries" in info:
                    title = info.get("title") or info.get("playlist_title") or url
                else:
                    title = info.get("title") or url
            item = QueueItem(
                url=url, quality=quality, fmt=fmt,
                output_dir=output_dir, subtitles=subtitles,
                audio_quality=audio_quality,
                title=title or url,
            )
            self.bridge.info_fetched.emit(item)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_queue_info_fetched(self, item):
        self._queue.append(item)
        self._refresh_queue_list()
        self._status(f"Added to queue ({len(self._queue)} items)", GREEN)

    def _start_queue(self):
        if self._queue_running:
            return
        pending = [q for q in self._queue if q.status == "queued"]
        if not pending:
            self._status("Queue is empty or all done", TEXT3)
            return
        self._queue_running = True
        self._run_next_in_queue()

    def _run_next_in_queue(self):
        pending = [q for q in self._queue if q.status == "queued"]
        if not pending:
            self._queue_running = False
            self._status("Queue completed ✓", GREEN)
            return

        item        = pending[0]
        item.status = "downloading"
        self._refresh_queue_list()

        self._pending_url      = item.url
        self._pending_quality  = item.quality
        self._pending_fmt      = item.fmt
        self._pending_subs     = item.subtitles
        self._pending_aq       = item.audio_quality
        self._pending_pl_items = item.playlist_items

        self._status(f"Downloading: {item.title[:50]}…", ACCENT)
        self.progress_bar.setValue(0)
        self.pct_lbl.setText("0%")
        self.speed_graph.reset()

        if not self._is_downloading:
            self._is_downloading = True
            self._swap_to_cancel()

        self.downloader.start(
            item.url, item.quality, item.fmt, item.output_dir,
            subtitles=item.subtitles,
            audio_quality=item.audio_quality,
            playlist_items=item.playlist_items
        )

    # ─────────────────────────────────────────────
    #  SWAP DOWNLOAD ↔ CANCEL
    # ─────────────────────────────────────────────

    def _swap_to_cancel(self):
        self._btn_stack.setCurrentIndex(1)

    def _restore_dl(self):
        self._is_downloading = False
        self._btn_stack.setCurrentIndex(0)

    def _start_download_with_cancel_btn(self):
        if not self._is_downloading:
            self._is_downloading = True
        self._swap_to_cancel()

    # ─────────────────────────────────────────────
    #  ACTIONS
    # ─────────────────────────────────────────────

    def _paste(self):
        clip = QApplication.clipboard().text()
        if clip:
            self.url_entry.setText(clip)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.download_path
        )
        if folder:
            self.download_path = folder
            self.path_entry.setText(folder)
            self.settings["download_path"] = folder
            save_settings(self.settings)

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, parent=self)
        if dlg.exec():
            self.settings = dlg.result_settings()
            save_settings(self.settings)
            self.download_path = self.settings["download_path"]
            self.path_entry.setText(self.download_path)
            self.quality_combo.setCurrentText(self.settings["default_quality"])
            self._on_quality_changed(self.settings["default_quality"])
            self.subs_check.setChecked(self.settings.get("embed_subtitles", False))
            self.aq_combo.setCurrentText(
                self.settings.get("default_audio_quality", "192")
            )

    def _open_cookie_dialog(self):
        dlg = CookieDialog(
            current_browser=self.downloader.cookie_browser,
            current_file=self.downloader.cookie_file,
            parent=self
        )
        if dlg.exec():
            self._apply_cookie_choice(dlg.result_browser(), dlg.result_file())

    def _apply_cookie_choice(self, browser, file):
        if browser:
            self.downloader.set_cookie_browser(browser)
            self.cookie_status_lbl.setText(f"Browser: {browser.capitalize()}")
            self.cookie_status_lbl.setStyleSheet(f"color: {GREEN}; font-size: 12px;")
        elif file:
            self.downloader.set_cookie_file(file)
            self.cookie_status_lbl.setText(f"File: {os.path.basename(file)}")
            self.cookie_status_lbl.setStyleSheet(f"color: {GREEN}; font-size: 12px;")
        else:
            self.downloader.set_cookie_browser(None)
            self.downloader.set_cookie_file(None)
            self.cookie_status_lbl.setText("Not configured")
            self.cookie_status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")

    def _get_info(self):
        url = self.url_entry.text().strip()
        if not url:
            self._status("URL is empty", RED)
            return
        self._status("Fetching info…", TEXT3)
        self.info_btn.setEnabled(False)

        def run():
            info = self.downloader.get_info(url, flat_playlist=False)
            if not info:
                self.bridge.complete.emit({"_type": "info_only", "info": None})
                return
            if info.get("_type") in ("playlist", "multi_video") or "entries" in info:
                entries = list(info.get("entries") or [])
                self.bridge.playlist_ready.emit(entries)
            else:
                self.bridge.complete.emit({"_type": "info_only", "info": info})

        threading.Thread(target=run, daemon=True).start()

    def _toggle_download(self):
        url = self.url_entry.text().strip()
        if not url:
            self._status("URL is empty", RED)
            return

        if not self._is_downloading:
            self._pending_url      = url
            self._pending_quality  = self.quality_combo.currentText()
            self._pending_fmt      = self.format_combo.currentText()
            self._pending_subs     = self.subs_check.isChecked()
            self._pending_aq       = self.aq_combo.currentText()
            self._pending_pl_items = None

            self._is_downloading = True
            self._swap_to_cancel()

            self._status("Downloading…", ACCENT)
            self.progress_bar.setValue(0)
            self.pct_lbl.setText("0%")
            self.speed_graph.reset()

            self.downloader.start(
                url,
                self._pending_quality,
                self._pending_fmt,
                self.download_path,
                subtitles=self._pending_subs,
                audio_quality=self._pending_aq,
                playlist_items=self._pending_pl_items
            )
        else:
            self.downloader.cancel()
            self._status("Cancelling…", TEXT3)

    # ─────────────────────────────────────────────
    #  CALLBACKS
    # ─────────────────────────────────────────────

    def _on_progress(self, pct, speed, eta):
        pct = max(0.0, min(100.0, pct))
        self.progress_bar.setValue(int(pct * 10))
        self.pct_lbl.setText(f"{int(pct)}%")
        self.stats_lbl.setText(f"Speed: {speed or '—'}  ·  ETA: {eta or '—'}")

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

    def _on_complete(self, info):
        # Get Info response
        if isinstance(info, dict) and info.get("_type") == "info_only":
            self.info_btn.setEnabled(True)
            data = info.get("info")
            if not data:
                self._status("Could not fetch info", RED)
                return
            self._show_info(data)
            self._status("Info loaded", GREEN)
            return

        # Queue mode
        if self._queue_running:
            for q in self._queue:
                if q.status == "downloading":
                    q.status = "done"
                    break
            self._refresh_queue_list()
            self._restore_dl()
            self._add_to_history(info)
            self.speed_graph.reset()
            self.progress_bar.setValue(1000)
            self.pct_lbl.setText("100%")
            # Queue modunda preview sıfırlama — her video arasında temiz ekran
            self._reset_preview()
            self._run_next_in_queue()
            return

        # Normal download complete
        self._restore_dl()
        self._status("Completed ✓", GREEN)
        self.progress_bar.setValue(1000)
        self.pct_lbl.setText("100%")
        self.stats_lbl.setText("Speed: —  ·  ETA: —")
        self.speed_graph.reset()
        self._add_to_history(info)
        # İndirme bitince preview ve URL alanını sıfırla
        self._reset_preview()

    def _on_error(self, msg):
        if self._queue_running:
            for q in self._queue:
                if q.status == "downloading":
                    q.status = "error"
                    break
            self._refresh_queue_list()

        self._restore_dl()

        if msg == "Cancelled":
            self._status("Cancelled", TEXT3)
            self.progress_bar.setValue(0)
            self.pct_lbl.setText("0%")
            self._queue_running = False
            return

        if msg == "COOKIE_DB_LOCKED":
            browser = self.downloader.cookie_browser or "browser"
            dlg     = CookieLockedDialog(browser, parent=self)
            if dlg.exec():
                choice = dlg.choice()
                if choice == "retry":
                    self._status("Retrying…", ACCENT)
                    self.progress_bar.setValue(0)
                    self.pct_lbl.setText("0%")
                    self.speed_graph.reset()
                    self._start_download_with_cancel_btn()
                    self.downloader.start(
                        self._pending_url, self._pending_quality,
                        self._pending_fmt, self.download_path,
                        subtitles=self._pending_subs,
                        audio_quality=self._pending_aq,
                        playlist_items=self._pending_pl_items
                    )
                elif choice == "file":
                    self._apply_cookie_choice(None, dlg.file_path())
                    self._status("Retrying with cookie file…", ACCENT)
                    self.progress_bar.setValue(0)
                    self.pct_lbl.setText("0%")
                    self.speed_graph.reset()
                    self._start_download_with_cancel_btn()
                    self.downloader.start(
                        self._pending_url, self._pending_quality,
                        self._pending_fmt, self.download_path,
                        subtitles=self._pending_subs,
                        audio_quality=self._pending_aq,
                        playlist_items=self._pending_pl_items
                    )
            else:
                self._status("Download cancelled", TEXT3)
                self._queue_running = False
            return

        self._status(f"Error: {msg[:80]}", RED)
        if self._queue_running:
            self._run_next_in_queue()

    def _on_playlist_ready(self, entries: list):
        self.info_btn.setEnabled(True)
        if not entries:
            self._status("No videos found in playlist", RED)
            return
        dlg = PlaylistDialog(entries, parent=self)
        if dlg.exec():
            pl_str = dlg.playlist_items_str()
            if not pl_str:
                self._status("No videos selected", TEXT3)
                return
            self._pending_pl_items = pl_str
            self._status(
                f"Playlist ready — {len(dlg.selected_indices())} videos selected", GREEN
            )
        else:
            self._status("Playlist selection cancelled", TEXT3)

    def _show_info(self, info):
        title    = info.get('title', 'Unknown')
        uploader = info.get('uploader', '')
        dur      = info.get('duration')
        dur_str  = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else ""
        meta     = "  ·  ".join(filter(None, [uploader, dur_str]))

        self.info_title.setText(title)
        self.info_title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600;")
        self.info_meta.setText(meta)
        self.info_meta.setStyleSheet(f"color: {TEXT3}; font-size: 11px;")

        thumb_url = info.get('thumbnail')
        if thumb_url:
            def load():
                try:
                    resp = requests.get(thumb_url, timeout=5)
                    img  = QImage()
                    img.loadFromData(resp.content)
                    px   = QPixmap.fromImage(img).scaled(
                        160, 90,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.bridge.thumb.emit(px)
                except Exception:
                    pass
            threading.Thread(target=load, daemon=True).start()

    def _on_thumb(self, pixmap):
        self.thumb_label.setPixmap(pixmap)
        self.thumb_label.setText("")

    def _status(self, text, color):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 13px;")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(BG))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(INPUT_BG))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())