import sys
import ctypes
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from ui.main_window import MainWindow
from utils.theme import BG1, TEXT, BG2, BG0, SURFACE0, BLUE

# Windows görev çubuğunda ikonun doğru görünmesini sağlar
if os.name == 'nt':
    myappid = 'rpms.mediatool.downloader.2.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

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