import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from core.path_manager import PathManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if PathManager.STYLE_FILE.exists():
        with open(PathManager.STYLE_FILE, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"[WARNING] Style file not found at {PathManager.STYLE_FILE}")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
