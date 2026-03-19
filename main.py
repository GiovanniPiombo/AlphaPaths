import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def load_stylesheet(app: QApplication, path: str) -> None:
    """Load and apply a QSS stylesheet to the application."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"[WARN] Stylesheet not found: {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app, "assets/style.qss")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
