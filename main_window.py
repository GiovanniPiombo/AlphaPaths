import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QLabel
from PySide6.QtCore import Qt

# Import the pages
from pages.settings_page import SettingsPage
from pages.dashboard_page import DashboardPage
from pages.simulation_page import SimulationPage
from pages.ai_page import AIPage
from core.utils import read_json

class MainWindow(QMainWindow):
    """
    The primary application window for the IBKR Portfolio Analyzer.

    This class manages the high-level application state, handles navigation 
    between different analysis modules, and acts as a central data hub 
    for portfolio information.

    Attributes:
        shared_portfolio_data (dict): A centralized cache storing portfolio 
            metrics, tickers, and prices accessible by all child pages.
        sidebar (QWidget): The navigation container on the left.
        stacked_widget (QStackedWidget): The main content area that swaps 
            between Dashboard, Simulation, AI, and Settings views.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBKR Portfolio Analyzer")
        self.resize(1200, 800)

        # Cache to hold data across pages
        self.shared_portfolio_data = {}

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """
        Initializes the user interface components, including the sidebar and the stacked widget for page navigation.
        """
        # ── Main Layout ─────────────────────────────────────────────
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ───────────────────────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        # ── Logo / Title ───────────────────────────────────────
        logo_label = QLabel("IBKR ANALYZER")
        logo_label.setObjectName("logo_label")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(20)

        # ── Navigation Buttons ─────────────────────────────────
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)

        self.btn_simulation = QPushButton("Monte Carlo")
        self.btn_simulation.setCheckable(True)

        self.btn_ai = QPushButton("AI Insights")
        self.btn_ai.setCheckable(True)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setCheckable(True)

        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_simulation)
        sidebar_layout.addWidget(self.btn_ai)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()

        main_layout.addWidget(self.sidebar)

        # ── STACKED WIDGET (PAGES) ────────────────────────────
        self.stacked_widget = QStackedWidget()
        
        self.dashboard_page = DashboardPage()
        self.simulation_page = SimulationPage()
        self.ai_page = AIPage()
        self.settings_page = SettingsPage()

        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.simulation_page)
        self.stacked_widget.addWidget(self.ai_page)
        self.stacked_widget.addWidget(self.settings_page)

        main_layout.addWidget(self.stacked_widget)

    def connect_signals(self):
        """Connects signals from the sidebar buttons and the pages to their respective handlers for navigation and data flow coordination."""
        # ── Sidebar Navigation Signals ─────────────────────────────
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0, self.btn_dashboard))
        self.btn_simulation.clicked.connect(lambda: self.switch_page(1, self.btn_simulation))
        self.btn_ai.clicked.connect(lambda: self.switch_page(2, self.btn_ai))
        self.btn_settings.clicked.connect(lambda: self.switch_page(3, self.btn_settings))

        # ── Navigation and Data Flow Signals from Pages ─────────────────────────────
        self.dashboard_page.dashboard_refreshed.connect(self.on_dashboard_ready)
        self.simulation_page.simulation_finished.connect(self.on_simulation_ready)

    def switch_page(self, index, active_button):
        """Switches the visible page and updates sidebar button states."""
        self.stacked_widget.setCurrentIndex(index)
        
        # Uncheck all buttons except the active one
        for btn in [self.btn_dashboard, self.btn_simulation, self.btn_ai, self.btn_settings]:
            if btn != active_button:
                btn.setChecked(False)
        active_button.setChecked(True)

    def on_dashboard_ready(self):
        """Called when IBKR data is successfully loaded in the dashboard."""
        self.shared_portfolio_data.update(self.dashboard_page.cached_data)
        self.simulation_page.start_background_preload()

    def on_simulation_ready(self, sim_data: dict):
        """
        Called when Monte Carlo math finishes.

        param: sim_data: A dictionary containing the results of the Monte Carlo simulation, including mu, sigma, and scenario outcomes.
        """
        # Merge the simulation math (mu, sigma, scenarios) into our shared dictionary
        self.shared_portfolio_data.update(sim_data)
        
        # Feed the combined data to the AI page so it can generate insights based on the full picture and language preference
        ai_language = read_json("config.json", "AI_LANGUAGE") or "English"
        self.shared_portfolio_data["language"] = ai_language
        
        self.ai_page.set_portfolio_data(self.shared_portfolio_data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Load Stylesheet
    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("[WARNING] style.qss not found. Running with default UI.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())