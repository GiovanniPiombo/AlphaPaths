import sys
from core.path_manager import PathManager
PathManager.init_configs() # PEP 8 compliance: 0%. PyInstaller survival rate: 100%. Do not touch. It works               
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from PySide6.QtGui import QIcon
from core.logger import app_logger

if __name__ == "__main__":
    app_logger.info("=== STARTING ALPHAPATH ===")
    app = QApplication(sys.argv)
    if PathManager.STYLE_FILE.exists():
        with open(PathManager.STYLE_FILE, "r") as f:
            app.setStyleSheet(f.read())
        app_logger.debug("Stylesheet loaded successfully.")
    else:
        app_logger.warning(f"Style file not found at {PathManager.STYLE_FILE}. Running with default UI.")
    window = MainWindow()
    app.setWindowIcon(QIcon(PathManager.ICON_FILE))
    window.show()
    
    exit_code = app.exec()
    app_logger.info(f"=== APPLICATION CLOSED WITH CODE {exit_code} ===")
    sys.exit(exit_code)
