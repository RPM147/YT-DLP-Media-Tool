# ═══════════════════════════════════════════════════════════
#  THEME  — Catppuccin Mocha inspired
# ═══════════════════════════════════════════════════════════
BG0      = "#11111b"
BG1      = "#1e1e2e"
BG2      = "#181825"
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

def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

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
