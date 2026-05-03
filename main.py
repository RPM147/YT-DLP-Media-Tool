import sys
import os
import json
import threading
import subprocess
import weakref
import datetime
import ctypes

import requests

# Windows görev çubuğunda ikonun doğru görünmesini sağlar
if os.name == 'nt':
    myappid = 'rpms.mediatool.downloader.2.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QProgressBar, QFileDialog, QFrame, QScrollArea, QSizePolicy,
    QDialog, QRadioButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QStackedWidget, QTabWidget,
    QTextEdit, QToolButton, QGraphicsDropShadowEffect, QSplitter,
    QSlider, QSpinBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QObject, QTimer, QUrl, QPointF,
    QPropertyAnimation, QEasingCurve, QRect, QSize
)
from PyQt6.QtGui import (
    QPixmap, QImage, QColor, QPalette, QLinearGradient, QRadialGradient,
    QPainter, QBrush, QPen, QFont, QDesktopServices, QPolygonF,
    QFontMetrics, QIcon, QCursor
)

from downloader import (
    Downloader, AUDIO_FORMATS, VIDEO_FORMATS,
    AUDIO_QUALITIES, VIDEO_QUALITIES, SUPPORTED_BROWSERS
)

# ═══════════════════════════════════════════════════════════
#  THEME  — Catppuccin Mocha inspired
# ═══════════════════════════════════════════════════════════
BG0      = "#11111b"   # crust
BG1      = "#1e1e2e"   # base
BG2      = "#181825"   # mantle
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
SURFACE2 = "#585b70"
OVERLAY0 = "#6c7086"
OVERLAY1 = "#7f849c"
TEXT     = "#cdd6f4"
TEXT2    = "#a6adc8"
TEXT3    = "#6c7086"
LAVENDER = "#b4befe"
BLUE     = "#89b4fa"
SAPPHIRE = "#74c7ec"
SKY      = "#89dceb"
TEAL     = "#94e2d5"
GREEN    = "#a6e3a1"
YELLOW   = "#f9e2af"
PEACH    = "#fab387"
RED      = "#f38ba8"
MAUVE    = "#cba6f7"
PINK     = "#f5c2e7"
FLAMINGO = "#f2cdcd"

ACCENT   = BLUE
ACCENT2  = LAVENDER
BORDER   = SURFACE0
HOVER    = SURFACE1
INPUT_BG = BG2

DL_A = "#1d4ed8"
DL_B = "#2563eb"
DL_C = "#0891b2"

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mediafetch_settings.json")
HISTORY_FILE  = os.path.join(os.path.expanduser("~"), ".mediafetch_history.json")

DEFAULT_SETTINGS = {
    "download_path":        os.path.join(os.path.expanduser("~"), "Downloads"),
    "default_quality":      "Best Quality",
    "default_format":       "mp4",
    "default_audio_quality":"192",
    "embed_subtitles":      False,
    "embed_thumbnail":      False,
    "write_description":    False,
    "max_history":          50,
    "theme_accent":         BLUE,
    "concurrent_fragments": 4,
}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Settings file is not a JSON object")
        result = DEFAULT_SETTINGS.copy()
        for k, default_v in DEFAULT_SETTINGS.items():
            raw = data.get(k, default_v)
            # Enforce same type as default; fall back to default on mismatch
            if not isinstance(raw, type(default_v)):
                raw = default_v
            result[k] = raw
        return result
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(s: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_history() -> list:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(h: list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(h, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  STYLESHEET
# ═══════════════════════════════════════════════════════════
def build_stylesheet(accent=BLUE) -> str:
    return f"""
* {{
    font-family: 'Segoe UI', 'Inter', sans-serif;
    color: {TEXT};
    background: transparent;
    border: none;
    outline: none;
}}
QMainWindow, QDialog {{
    background-color: {BG1};
}}
QWidget#root, QWidget#panel, QWidget#dialog {{
    background-color: {BG1};
}}
QWidget#sidebar {{
    background-color: {BG0};
    border-right: 1px solid {BORDER};
}}
QWidget#card {{
    background-color: {BG2};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QWidget#cardFlat {{
    background-color: {SURFACE0};
    border-radius: 8px;
}}
QLineEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {rgba(accent, 0.3)};
}}
QLineEdit:focus {{
    border-color: {accent};
    background-color: {BG1};
}}
QLineEdit:read-only {{
    color: {TEXT2};
}}
QPushButton {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {HOVER};
    border-color: {rgba(accent, 0.5)};
    color: white;
}}
QPushButton:pressed {{
    background-color: {SURFACE1};
}}
QPushButton:disabled {{
    color: {TEXT3};
    background-color: {INPUT_BG};
    border-color: {BORDER};
}}
QPushButton#accentBtn {{
    background-color: {rgba(accent, 0.15)};
    color: {accent};
    border: 1.5px solid {rgba(accent, 0.4)};
    border-radius: 8px;
    font-weight: 600;
}}
QPushButton#accentBtn:hover {{
    background-color: {rgba(accent, 0.28)};
    color: white;
    border-color: {accent};
}}
QPushButton#dangerBtn {{
    background-color: {rgba(RED, 0.1)};
    color: {RED};
    border: 1.5px solid {rgba(RED, 0.3)};
    font-weight: 700;
    font-size: 14px;
    border-radius: 10px;
    padding: 12px 20px;
    letter-spacing: 1px;
}}
QPushButton#dangerBtn:hover {{
    background-color: {rgba(RED, 0.2)};
    border-color: {rgba(RED, 0.6)};
}}
QPushButton#ghostBtn {{
    background: transparent;
    border: none;
    color: {TEXT3};
    font-size: 12px;
    padding: 4px 8px;
}}
QPushButton#ghostBtn:hover {{
    color: {RED};
}}
QPushButton#sideBtn {{
    background: transparent;
    border: none;
    border-radius: 10px;
    color: {TEXT2};
    font-size: 13px;
    font-weight: 500;
    padding: 12px 16px;
    text-align: left;
}}
QPushButton#sideBtn:hover {{
    background-color: {SURFACE0};
    color: {TEXT};
}}
QPushButton#sideBtnActive {{
    background-color: {rgba(accent, 0.18)};
    border: none;
    border-radius: 10px;
    color: {accent};
    font-size: 13px;
    font-weight: 700;
    padding: 12px 16px;
    text-align: left;
}}
QComboBox {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-width: 100px;
}}
QComboBox:hover {{ border-color: {rgba(accent, 0.5)}; }}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT3};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG2};
    color: {TEXT};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {rgba(accent, 0.2)};
    outline: none;
    padding: 4px;
}}
QCheckBox {{
    color: {TEXT};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 2px solid {BORDER};
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT2}; }}
QRadioButton {{
    color: {TEXT};
    spacing: 8px;
    font-size: 13px;
}}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border-radius: 8px;
    border: 2px solid {BORDER};
    background: {INPUT_BG};
}}
QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QProgressBar {{
    background-color: {SURFACE0};
    border: none;
    border-radius: 5px;
    height: 10px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {accent}, stop:1 {SKY});
    border-radius: 5px;
}}
QListWidget {{
    background-color: {INPUT_BG};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    color: {TEXT};
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{ padding: 8px 12px; border-radius: 6px; }}
QListWidget::item:selected {{
    background-color: {rgba(accent, 0.2)};
    color: {TEXT};
}}
QListWidget::item:hover {{ background-color: {rgba(accent, 0.1)}; }}
QTabWidget::pane {{
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    background: {BG2};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT3};
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {accent};
    border-bottom: 2px solid {accent};
    font-weight: 700;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTextEdit {{
    background-color: {INPUT_BG};
    color: {TEXT2};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 8px;
    font-size: 12px;
    font-family: 'Consolas', monospace;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {SURFACE1}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {OVERLAY0}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 6px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {SURFACE1}; border-radius: 3px; min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QToolTip {{
    background-color: {BG0};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
QMenu {{
    background: {BG2};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
    color: {TEXT};
}}
QMenu::item {{ padding: 8px 20px; border-radius: 6px; font-size: 13px; }}
QMenu::item:selected {{ background: {rgba(BLUE, 0.2)}; color: white; }}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {SURFACE0};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}
"""


# ═══════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ═══════════════════════════════════════════════════════════

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


def card(layout: QVBoxLayout | QHBoxLayout | None = None) -> QWidget:
    w = QWidget()
    w.setObjectName("card")
    if layout is not None:
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        w.setLayout(layout)
    return w


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
        self._color = QColor(BLUE)
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

            # background
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
        self._hovered  = False
        self._pressed  = False
        self._phase    = 0.0
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

    def enterEvent(self, e):  self._hovered = True;  self.update(); super().enterEvent(e)
    def leaveEvent(self, e):  self._hovered = False; self.update(); super().leaveEvent(e)
    def mousePressEvent(self, e):   self._pressed = True;  self.update(); super().mousePressEvent(e)
    def mouseReleaseEvent(self, e): self._pressed = False; self.update(); super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r = self.rect().adjusted(1, 1, -1, -1) if self._pressed else self.rect()
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

            # top gloss
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
            p.drawText(QRect(14, 0, 30, r.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter, self._icon_text)

            lbl_color = QColor(BLUE if self._active else TEXT2)
            p.setPen(QPen(lbl_color))
            f2 = QFont("Segoe UI", 12, QFont.Weight.Bold if self._active else QFont.Weight.Normal)
            p.setFont(f2)
            p.drawText(QRect(50, 0, r.width() - 58, r.height()), Qt.AlignmentFlag.AlignVCenter, self._label_text)
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


        self._anim_out = QTimer(self)
        self._anim_out.setSingleShot(True)
        self._anim_out.timeout.connect(lambda: self.deleteLater())
        self._anim_out.start(duration)



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

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(label(f"🎵 {len(entries)} video bulundu", 16, TEXT, bold=True))
        hdr.addStretch()
        self.count_lbl = label("", 12, TEXT3)
        hdr.addWidget(self.count_lbl)
        root.addLayout(hdr)

        root.addWidget(label("İndirmek istediğiniz videoları seçin:", 12, TEXT2))

        # Toolbar
        tb = QHBoxLayout()
        for txt, fn in [("Tümünü Seç", self._select_all), ("Hiçbirini Seçme", self._select_none)]:
            b = make_accent_btn(txt, BLUE)
            b.setFixedHeight(30)
            b.clicked.connect(fn)
            tb.addWidget(b)
        tb.addStretch()

        # Filter
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
            t   = e.get('title') or e.get('url') or f"Video {i}"
            dur = e.get('duration')
            ds  = f"  [{int(dur//60)}:{int(dur%60):02d}]" if dur else ""
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
        root.addWidget(label("Kimlik doğrulaması gerektiren içerikler için çerez kullanabilirsiniz.", 12, TEXT3, wrap=True))
        root.addWidget(hdivider())

        self.rb_none    = QRadioButton("Çerez kullanma")
        self.rb_browser = QRadioButton("Tarayıcıdan oku")
        self.rb_file    = QRadioButton("Dosyadan yükle (.txt — Netscape formatı)")
        root.addWidget(self.rb_none)
        root.addWidget(hdivider())

        root.addWidget(self.rb_browser)
        warn = label("⚠  Chromium tabanlı tarayıcılar çalışırken çerezleri kilitler — kullanmadan önce kapatın.", 11, YELLOW, wrap=True)
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
        hint = label("'Get cookies.txt LOCALLY' eklentisiyle dışa aktarın. Tarayıcı açıkken de çalışır.", 11, TEXT3, wrap=True)
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

        # set initial
        if current_browser:    self.rb_browser.setChecked(True)
        elif current_file:     self.rb_file.setChecked(True)
        else:                  self.rb_none.setChecked(True)

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
        path, _ = QFileDialog.getOpenFileName(self, "Çerez Dosyası Seç", "", "Cookie files (*.txt);;All (*)")
        if path:
            self.file_entry.setText(path)
            self.rb_file.setChecked(True)

    def _apply(self):
        if self.rb_browser.isChecked():
            chosen = SUPPORTED_BROWSERS[self.browser_combo.currentIndex()]
            # Warn if the browser profile directory cannot be found on this system
            from downloader import Downloader as _DL, BROWSER_PROFILE_PATHS
            paths = BROWSER_PROFILE_PATHS.get(chosen, [])
            profile_found = any(os.path.isdir(p) for p in paths)
            if not profile_found:
                self.browser_combo.setStyleSheet(f"border-color:{YELLOW};")
                # Show an inline warning but still allow the user to proceed
                # (the profile might be in a non-standard location)
                self._browser_warning = label(
                    f"⚠ {chosen.capitalize()} profili bu sistemde bulunamadı.",
                    11, YELLOW, wrap=True
                )
                # Only add the warning once
                lay = self.layout()
                if lay and not hasattr(self, '_warn_added'):
                    lay.insertWidget(lay.count() - 1, self._browser_warning)
                    self._warn_added = True
                # Do not block — let the user proceed anyway
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
        use = make_accent_btn("Bu dosyayı kullan", GREEN); use.setFixedSize(120, 36); use.clicked.connect(self._use_file)
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

    def _retry(self):   self._choice = "retry"; self.accept()
    def _use_file(self):
        p = self.file_entry.text().strip()
        if not p or not os.path.isfile(p):
            self.file_entry.setStyleSheet(f"border-color:{RED};"); return
        self._file_path = p; self._choice = "file"; self.accept()

    def choice(self):    return self._choice
    def file_path(self): return self._file_path


# ═══════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════
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

        tabs = QTabWidget()
        tabs.setStyleSheet(build_stylesheet())
        root.addWidget(tabs, stretch=1)

        tabs.addTab(self._tab_general(),  "⚙  Genel")
        tabs.addTab(self._tab_advanced(), "🔧 Gelişmiş")
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

    # ── Tabs ──────────────────────────────────────────────

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
            ("Varsayılan Kalite",  "quality_combo", VIDEO_QUALITIES,            "default_quality"),
            ("Varsayılan Format",  "format_combo",  VIDEO_FORMATS+AUDIO_FORMATS,"default_format"),
            ("Ses Kalitesi (kbps)","aq_combo",      AUDIO_QUALITIES,            "default_audio_quality"),
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
        for cb, key in [(self.subs_check,"embed_subtitles"), (self.thumb_check,"embed_thumbnail"), (self.desc_check,"write_description")]:
            cb.setChecked(self._s.get(key, False))
            lay.addWidget(cb)

        lay.addStretch()
        return w

    def _tab_advanced(self) -> QWidget:
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
        lay.addWidget(label("Daha yüksek değer = hızlı ama daha fazla CPU kullanımı", 11, TEXT3))
        lay.addWidget(hdivider())

        lay.addWidget(label("Geçmiş Limiti", 12, TEXT2))
        hist_row = QHBoxLayout()
        self.hist_limit = QSpinBox()
        self.hist_limit.setRange(10, 500)
        self.hist_limit.setValue(self._s.get("max_history", 50))
        self.hist_limit.setFixedWidth(80)
        self.hist_limit.setStyleSheet(f"background:{INPUT_BG}; border:1.5px solid {BORDER}; border-radius:8px; padding:6px; color:{TEXT};")
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

    def _tab_update(self) -> QWidget:
        w   = QWidget(); w.setObjectName("dialog")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(label("yt-dlp Güncellemesi", 14, TEXT, bold=True))
        lay.addWidget(label("yt-dlp'yi en son sürüme güncelleyin. Yeni site desteği ve hata düzeltmeleri için önerilir.", 12, TEXT3, wrap=True))
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

    # ── Actions ───────────────────────────────────────────

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self._s["download_path"])
        if folder:
            self._s["download_path"] = folder
            self.path_entry.setText(folder)

    def _reset_defaults(self):
        for k, v in DEFAULT_SETTINGS.items():
            self._s[k] = v
        self.accept()

    def _update_ytdlp(self):
        self.upd_lbl.setText("Güncelleniyor…")
        self.upd_lbl.setStyleSheet(f"color:{YELLOW}; font-size:12px;")
        self.upd_log.clear()
        self_ref = weakref.ref(self)

        def _set(txt, color):
            obj = self_ref()
            if obj is None:
                return
            QTimer.singleShot(0, lambda t=txt, c=color, o=obj: _apply(o, t, c))

        def _apply(obj, txt, color):
            try:
                obj.upd_lbl.setText(txt)
                obj.upd_lbl.setStyleSheet(f"color:{color}; font-size:12px;")
            except RuntimeError:
                pass

        def _log(txt):
            obj = self_ref()
            if obj is None:
                return
            QTimer.singleShot(0, lambda t=txt, o=obj: _append_log(o, t))

        def _append_log(obj, txt):
            try:
                obj.upd_log.append(txt)
            except RuntimeError:
                pass

        def run():
            try:
                # Frozen (PyInstaller .exe) ortamında yt-dlp güncellenemez:
                # sys.executable Python değil exe'nin kendisidir ve yt-dlp
                # zaten exe içine gömülüdür; sisteme pip kurulumu exe'yi etkilemez.
                if getattr(sys, 'frozen', False):
                    _set("Paketlenmiş sürümde güncelleme desteklenmiyor", YELLOW)
                    _log("Bu uygulama .exe olarak paketlenmiş.")
                    _log("yt-dlp, exe içine gömülüdür ve pip ile güncellenemez.")
                    _log("Güncel sürüm için yeni bir .exe derleyin.")
                    return

                import shutil
                pip = shutil.which("pip") or shutil.which("pip3")
                if pip:
                    cmd = [pip, "install", "--upgrade", "yt-dlp"]
                else:
                    # sys.executable burada gerçek Python yorumlayıcısıdır (frozen değil)
                    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
                _log(f"$ {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                for line in (result.stdout + result.stderr).splitlines():
                    _log(line)
                if result.returncode == 0:
                    _set("Güncellendi ✓", GREEN)
                else:
                    _set("Başarısız", RED)
            except subprocess.TimeoutExpired:
                _set("Zaman aşımı", RED)
            except Exception as ex:
                _set(f"Hata: {str(ex)[:40]}", RED)

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        self._s["default_quality"]       = self.quality_combo.currentText()
        self._s["default_format"]        = self.format_combo.currentText()
        self._s["default_audio_quality"] = self.aq_combo.currentText()
        self._s["embed_subtitles"]       = self.subs_check.isChecked()
        self._s["embed_thumbnail"]       = self.thumb_check.isChecked()
        self._s["write_description"]     = self.desc_check.isChecked()
        self._s["concurrent_fragments"]  = self.frag_slider.value()
        self._s["max_history"]           = self.hist_limit.value()
        self.accept()

    def result_settings(self) -> dict:
        return self._s


# ═══════════════════════════════════════════════════════════
#  BRIDGE  (thread → UI)
# ═══════════════════════════════════════════════════════════
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
                 embed_thumbnail=False, write_description=False):
        self.url               = url
        self.quality           = quality
        self.fmt               = fmt
        self.output_dir        = output_dir
        self.subtitles         = subtitles
        self.audio_quality     = audio_quality
        self.playlist_items    = playlist_items
        self.embed_thumbnail   = embed_thumbnail
        self.write_description = write_description
        self.title             = title or url
        self.status            = "queued"   # queued | downloading | done | error


# ═══════════════════════════════════════════════════════════
#  DOWNLOAD PAGE  (left panel)
# ═══════════════════════════════════════════════════════════
class DownloadPage(QWidget):
    request_download = pyqtSignal(object)   # emits QueueItem
    request_queue    = pyqtSignal(object)   # emits QueueItem
    request_info     = pyqtSignal(str)      # emits url

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

    # ── URL Card ──────────────────────────────────────────

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

    # ── Preview Card ──────────────────────────────────────

    def _build_preview_card(self):
        c_lay = QHBoxLayout()
        c_lay.setContentsMargins(16, 14, 16, 14)
        c_lay.setSpacing(16)
        c = card()
        c.setLayout(c_lay)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(180, 101)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(f"background:{BG0}; border-radius:8px; color:{TEXT3}; font-size:11px;")
        self.thumb_label.setText("Önizleme")
        c_lay.addWidget(self.thumb_label)

        info_col = QVBoxLayout(); info_col.setSpacing(6)
        self.info_title = label("URL girin ve 'Bilgi Al'a tıklayın", 13, TEXT3, wrap=True)
        info_col.addWidget(self.info_title)
        self.info_meta  = label("", 11, TEXT3)
        info_col.addWidget(self.info_meta)
        self.info_tags  = label("", 11, MAUVE)
        info_col.addWidget(self.info_tags)
        info_col.addStretch()

        open_btn = QPushButton("↗ Aç")
        open_btn.setObjectName("ghostBtn")
        open_btn.setFixedWidth(60)
        open_btn.clicked.connect(self._open_url)
        info_col.addWidget(open_btn)
        c_lay.addLayout(info_col, stretch=1)

        self._lay.addWidget(c)

    # ── Options Card ──────────────────────────────────────

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
        fcol.addWidget(self.format_combo)
        row1.addLayout(fcol)

        # Audio Quality (hidden initially)
        acol = QVBoxLayout(); acol.setSpacing(4)
        acol.addWidget(label("Ses Kalitesi", 11, TEXT3))
        self.aq_combo = QComboBox()
        self.aq_combo.addItems(AUDIO_QUALITIES)
        self.aq_combo.setCurrentText(self._settings.get("default_audio_quality", "192"))
        acol.addWidget(self.aq_combo)
        self._aq_widget = QWidget(); self._aq_widget.setLayout(acol)
        sp = self._aq_widget.sizePolicy(); sp.setRetainSizeWhenHidden(False)
        self._aq_widget.setSizePolicy(sp); self._aq_widget.hide()
        row1.addWidget(self._aq_widget)

        # Save path
        pcol = QVBoxLayout(); pcol.setSpacing(4)
        pcol.addWidget(label("Kayıt Klasörü", 11, TEXT3))
        prow = QHBoxLayout(); prow.setSpacing(6)
        self.path_entry = QLineEdit(self._settings.get("download_path", os.path.expanduser("~/Downloads")))
        self.path_entry.setReadOnly(True)
        self.path_entry.setFixedHeight(36)
        prow.addWidget(self.path_entry, stretch=1)
        br = QPushButton("📁"); br.setFixedSize(36, 36); br.clicked.connect(self._browse_path)
        prow.addWidget(br)
        pcol.addLayout(prow)
        row1.addLayout(pcol, stretch=1)

        c_lay.addLayout(row1)
        c_lay.addWidget(hdivider())

        # Checkboxes row
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

    # ── Download Button ───────────────────────────────────

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

    # ── Progress Card ─────────────────────────────────────

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

        self.pp_bar = QProgressBar()    # postprocess (merge) bar
        self.pp_bar.setRange(0, 0)      # indeterminate
        self.pp_bar.setFixedHeight(4)
        self.pp_bar.setTextVisible(False)
        self.pp_bar.hide()
        c_lay.addWidget(self.pp_bar)

        self.speed_graph = SpeedGraph()
        c_lay.addWidget(self.speed_graph)

        stats_row = QHBoxLayout()
        self.stats_lbl = label("Hız: —  ·  ETA: —", 11, TEXT3)
        self.stats_lbl.setStyleSheet(f"color:{TEXT3}; font-size:11px; font-family:'Consolas',monospace;")
        stats_row.addWidget(self.stats_lbl)
        stats_row.addStretch()
        self.size_lbl = label("", 11, TEXT3)
        self.size_lbl.setStyleSheet(f"color:{TEXT3}; font-size:11px; font-family:'Consolas',monospace;")
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

    def _make_item(self) -> QueueItem | None:
        url = self.url_entry.text().strip()
        if not url:
            return None
        return QueueItem(
            url            = url,
            quality        = self.quality_combo.currentText(),
            fmt            = self.format_combo.currentText(),
            output_dir     = self.path_entry.text(),
            subtitles      = self.subs_check.isChecked(),
            audio_quality  = self.aq_combo.currentText(),
            embed_thumbnail= self.thumb_check.isChecked(),
            write_description=self.desc_check.isChecked(),
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
        sp  = f"Hız: {speed or '—'}  ·  ETA: {eta or '—'}"
        if fi and fc:
            sp += f"  ·  Parça: {fi}/{fc}"
        self.stats_lbl.setText(sp)
        if total > 0:
            dl_mb  = dl   / (1024*1024)
            tot_mb = total/ (1024*1024)
            self.size_lbl.setText(f"{dl_mb:.1f} / {tot_mb:.1f} MB")
        # speed graph
        try:
            spd = speed.replace(" ", "")
            if "MiB/s" in spd or "MB/s" in spd:
                val = float(spd.replace("MiB/s","").replace("MB/s","")) * 1024
            elif "KiB/s" in spd or "KB/s" in spd:
                val = float(spd.replace("KiB/s","").replace("KB/s",""))
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
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def refresh(self, queue: list[QueueItem]):
        self._queue = queue
        self.list_widget.clear()
        self.count_lbl.setText(f"{len(queue)} öğe")
        if not queue:
            ph = QListWidgetItem("Kuyruk boş  —  İndir sayfasında '+ Kuyruğa Ekle'ye tıklayın")
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
        menu = QMenu(self)
        remove = menu.addAction("🗑  Kuyruktan kaldır")
        act    = menu.exec(self.list_widget.mapToGlobal(pos))
        if act == remove:
            self._queue.pop(idx)
            self.refresh(self._queue)


# ═══════════════════════════════════════════════════════════
#  HISTORY PAGE
# ═══════════════════════════════════════════════════════════
class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = load_history()
        self._build()

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

        self._refresh_list(self._history)

    def add_entry(self, entry: dict, max_items: int = 50):
        self._history.insert(0, entry)
        if len(self._history) > max_items:
            self._history = self._history[:max_items]
        save_history(self._history)
        self._refresh_list(self._history)

    def _refresh_list(self, entries: list[dict]):
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
        clear = QPushButton("Temizle"); clear.setObjectName("ghostBtn")
        clear.clicked.connect(self._clear)
        hdr.addWidget(clear)
        lay.addLayout(hdr)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Günlükler burada görünecek…")
        lay.addWidget(self.log_box, stretch=1)

    def append(self, text: str, color: str = TEXT2):
        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f'<span style="color:{TEXT3};">[{ts}]</span> <span style="color:{color};">{text}</span>')

    def _clear(self):
        self.log_box.clear()


# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPM's Media Tool")
        self.setMinimumSize(1000, 680)
        self.resize(1100, 760)

        self.settings = load_settings()
        self.setStyleSheet(build_stylesheet(self.settings.get("theme_accent", BLUE)))

        # icon
        icon_path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
            'icon.ico'
        )
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # state
        self._is_downloading   = False
        self._queue: list[QueueItem] = []
        self._queue_running    = False
        self._pending: QueueItem | None = None
        self._pending_url_for_cookie = ""

        # bridge + downloader
        self.bridge = Bridge()
        self.bridge.progress.connect(self._on_progress)
        self.bridge.complete.connect(self._on_complete)
        self.bridge.error.connect(self._on_error)
        self.bridge.thumb.connect(self._on_thumb)
        self.bridge.playlist_ready.connect(self._on_playlist_ready)
        self.bridge.info_fetched.connect(self._on_info_fetched)
        self.bridge.postprocess.connect(self._on_postprocess)

        self.downloader = Downloader(
            on_progress   = lambda p,s,e,d,t,fi,fc: self.bridge.progress.emit(p,s,e,d,t,fi,fc),
            on_complete   = lambda i: self.bridge.complete.emit(i),
            on_error      = lambda m: self.bridge.error.emit(m),
            on_postprocess= lambda: self.bridge.postprocess.emit(),
        )

        self._build_ui()

    # ═══════════════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════════════

    def closeEvent(self, event):
        """Ensure any active download is cancelled before the window closes."""
        if self._is_downloading:
            self.downloader.cancel()
        event.accept()

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_lay  = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 20, 12, 20)
        sb_lay.setSpacing(4)

        # App title
        title_lbl = QLabel("RPM's Media Tool")
        title_lbl.setStyleSheet(f"color:{BLUE}; font-size:18px; font-weight:800; padding:0 8px 16px 8px;")
        sb_lay.addWidget(title_lbl)

        self._pages = QStackedWidget()
        self._sidebar_btns: list[SidebarButton] = []

        nav_items = [
            ("⬇", "İndir",    self._make_download_page()),
            ("⏳", "Kuyruk",   self._make_queue_page()),
            ("📋", "Geçmiş",   self._make_history_page()),
            ("📄", "Günlükler",self._make_logs_page()),
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

        # Cookie button
        self.cookie_btn = QPushButton("🍪 Çerezler")
        self.cookie_btn.setObjectName("ghostBtn")
        self.cookie_btn.setFixedHeight(36)
        self.cookie_btn.clicked.connect(self._open_cookie_dialog)
        sb_lay.addWidget(self.cookie_btn)

        self.cookie_status = QLabel("Çerez: Yok")
        self.cookie_status.setStyleSheet(f"color:{TEXT3}; font-size:10px; padding:2px 4px;")
        self.cookie_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_lay.addWidget(self.cookie_status)

        sb_lay.addSpacing(6)

        # Settings button
        settings_btn = QPushButton("⚙ Ayarlar")
        settings_btn.setObjectName("ghostBtn")
        settings_btn.setFixedHeight(36)
        settings_btn.clicked.connect(self._open_settings)
        sb_lay.addWidget(settings_btn)

        ver = QLabel("v2.0  ·  yt-dlp")
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
        return self.q_page

    def _make_history_page(self) -> HistoryPage:
        self.hist_page = HistoryPage()
        return self.hist_page

    def _make_logs_page(self) -> LogsPage:
        self.logs_page = LogsPage()
        return self.logs_page

    def _switch_page(self, name: str):
        names = ["İndir", "Kuyruk", "Geçmiş", "Günlükler"]
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
            info = self.downloader.get_info(url, flat_playlist=False)
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
        self._pending = item
        self._is_downloading = True
        self.dl_page.show_cancel()
        self.dl_page.reset_progress()
        self.dl_page.set_status("İndiriliyor…", BLUE)
        self.logs_page.append(f"İndirme başladı: {item.url}")
        self.downloader.start(
            item.url, item.quality, item.fmt, item.output_dir,
            subtitles      = item.subtitles,
            audio_quality  = item.audio_quality,
            playlist_items = item.playlist_items,
            embed_thumbnail= item.embed_thumbnail,
            write_description=item.write_description,
        )

    def _cancel(self):
        self.downloader.cancel()
        self.dl_page.set_status("İptal ediliyor…", TEXT3)

    def _add_to_queue(self, item: QueueItem):
        self.dl_page.set_status("Kuyruk için bilgi alınıyor…", TEXT3)

        def fetch():
            info  = self.downloader.get_info(item.url, flat_playlist=False)
            title = ""
            if info:
                if info.get("_type") in ("playlist", "multi_video") or "entries" in info:
                    title = info.get("title") or item.url
                else:
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
            # load thumbnail
            thumb_url = data.get('thumbnail')
            if thumb_url:
                def load():
                    try:
                        resp = requests.get(thumb_url, timeout=6)
                        img  = QImage(); img.loadFromData(resp.content)
                        px   = QPixmap.fromImage(img).scaled(
                            180, 101, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
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

        # History
        if isinstance(info, dict):
            title    = info.get('title', 'Bilinmiyor')
            ext      = info.get('ext', '')
            size_mb  = (info.get('filesize') or info.get('filesize_approx') or 0) / (1024*1024)
            url      = info.get('webpage_url') or info.get('url', '')
            ts       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            entry    = {
                "title":      title,
                "ext":        ext,
                "size_mb":    round(size_mb, 2),
                "url":        url,
                "timestamp":  ts,
                "output_dir": self._pending.output_dir if self._pending else "",
            }
            self.hist_page.add_entry(entry, self.settings.get("max_history", 50))
            self.logs_page.append(f"Tamamlandı: {title}", GREEN)

        if self._queue_running:
            for q in self._queue:
                if q.status == "downloading":
                    q.status = "done"; break
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
                    q.status = "error"; break
            self.q_page.refresh(self._queue)

        if msg == "Cancelled":
            self.dl_page.set_status("İptal edildi", TEXT3)
            self.dl_page.reset_progress()
            self._queue_running = False
            self.logs_page.append("İndirme iptal edildi", YELLOW)
            return

        if msg == "COOKIE_DB_LOCKED":
            browser = self.downloader.cookie_browser or "browser"
            dlg = CookieLockedDialog(browser, parent=self)
            if dlg.exec():
                choice = dlg.choice()
                if choice == "retry":
                    self.dl_page.set_status("Tekrar deneniyor…", BLUE)
                    self.dl_page.reset_progress()
                    self._start_download(self._pending)
                elif choice == "file":
                    self._apply_cookie(None, dlg.file_path())
                    self.dl_page.set_status("Çerez dosyasıyla tekrar deneniyor…", BLUE)
                    self.dl_page.reset_progress()
                    self._start_download(self._pending)
                else:
                    self._queue_running = False
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
            if self._pending:
                self._pending.playlist_items = pl_str
            self.dl_page.set_status(
                f"Oynatma listesi hazır — {len(dlg.selected_indices())} video seçildi", GREEN
            )
            self.logs_page.append(f"Oynatma listesi: {len(dlg.selected_indices())} video seçildi")
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
        dlg = CookieDialog(self.downloader.cookie_browser, self.downloader.cookie_file, parent=self)
        if dlg.exec():
            self._apply_cookie(dlg.result_browser(), dlg.result_file())

    def _apply_cookie(self, browser, file):
        if browser:
            self.downloader.set_cookie_browser(browser)
            self.cookie_status.setText(f"🍪 {browser.capitalize()}")
            self.cookie_status.setStyleSheet(f"color:{GREEN}; font-size:10px; padding:2px 4px;")
        elif file:
            self.downloader.set_cookie_file(file)
            self.cookie_status.setText(f"🍪 {os.path.basename(file)}")
            self.cookie_status.setStyleSheet(f"color:{GREEN}; font-size:10px; padding:2px 4px;")
        else:
            self.downloader.cookie_browser = None
            self.downloader.cookie_file    = None
            self.cookie_status.setText("Çerez: Yok")
            self.cookie_status.setStyleSheet(f"color:{TEXT3}; font-size:10px; padding:2px 4px;")

    # ═══════════════════════════════════════════════════════
    #  TOAST
    # ═══════════════════════════════════════════════════════

    def _toast(self, text: str, color: str = GREEN):
        t = Toast(self, text, color)
        win_geo = self.geometry()
        tw = t.width()
        th = t.height()
        x  = win_geo.x() + win_geo.width()  - tw - 24
        y  = win_geo.y() + win_geo.height() - th - 48
        t.move(x, y)
        t.show()
        


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG1))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(BG2))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG0))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(SURFACE0))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(BLUE))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())