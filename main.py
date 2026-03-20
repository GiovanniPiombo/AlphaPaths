import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def load_stylesheet(app: QApplication, path: str) -> None:
    """
    Loads a QSS stylesheet from the specified path and applies it to the given QApplication instance.
    
    Args:
        app (QApplication): The application instance to which the stylesheet will be applied.
        path (str): The file path to the QSS stylesheet.
    """
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
