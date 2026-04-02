# AlphaPaths - Advanced risk analysis, Monte Carlo simulation, and portfolio optimization.
# Copyright (C) 2026 Giovanni Piombo Nicoli
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
