import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QPushButton, QStackedWidget, QLabel)
from PySide6.QtCore import Qt

# Import the pages
from pages.dashboard_page import DashboardPage
from pages.simulation_page import SimulationPage
from pages.ai_page import AIPage
from core.utils import read_json

class MainWindow(QMainWindow):
        """The MainWindow class is the central hub of the application, managing the overall layout, navigation, and data flow between the different pages (Dashboard, Simulation, AI Insights). It initializes the sidebar for navigation and a stacked widget to hold the pages. The class also handles signals emitted by the pages to coordinate actions such as starting simulations after fetching IBKR data and updating the AI page with new data from the simulation results."""
        def __init__(self):
        super().__init__()
        self.setWindowTitle("IBKR Portfolio Analyzer")
        self.resize(1200, 800)

        # Cache to hold data across pages
        self.shared_portfolio_data = {}

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Sets up the main user interface, including the sidebar for navigation and the stacked widget for displaying different pages."""
        # Main Widget and Layout
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

        # Logo / Title
        logo_label = QLabel("IBKR ANALYZER")
        logo_label.setObjectName("logo_label")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(20)

        # Navigation Buttons
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)

        self.btn_simulation = QPushButton("Monte Carlo")
        self.btn_simulation.setCheckable(True)

        self.btn_ai = QPushButton("AI Insights")
        self.btn_ai.setCheckable(True)

        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_simulation)
        sidebar_layout.addWidget(self.btn_ai)
        sidebar_layout.addStretch()

        main_layout.addWidget(self.sidebar)

        # ── STACKED WIDGET (PAGES) ────────────────────────────
        self.stacked_widget = QStackedWidget()
        
        self.dashboard_page = DashboardPage()
        self.simulation_page = SimulationPage()
        self.ai_page = AIPage()

        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.simulation_page)
        self.stacked_widget.addWidget(self.ai_page)

        main_layout.addWidget(self.stacked_widget)

    def connect_signals(self):
        """Connects signals from the sidebar buttons and the pages to their respective handlers for navigation and data flow coordination."""
        # Sidebar Navigation
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0, self.btn_dashboard))
        self.btn_simulation.clicked.connect(lambda: self.switch_page(1, self.btn_simulation))
        self.btn_ai.clicked.connect(lambda: self.switch_page(2, self.btn_ai))

        # Core Application Flow
        # 1. When Dashboard finishes, automatically trigger Simulation background load
        self.dashboard_page.dashboard_refreshed.connect(self.on_dashboard_ready)

        # 2. When Simulation finishes, update the AI Page with the combined data
        self.simulation_page.simulation_finished.connect(self.on_simulation_ready)

    def switch_page(self, index, active_button):
        """Switches the visible page and updates sidebar button states."""
        self.stacked_widget.setCurrentIndex(index)
        
        # Uncheck all buttons except the active one
        for btn in [self.btn_dashboard, self.btn_simulation, self.btn_ai]:
            if btn != active_button:
                btn.setChecked(False)
        active_button.setChecked(True)

    def on_dashboard_ready(self):
        """Called when IBKR data is successfully loaded in the dashboard."""
        
        # Save base data (currency, weights) from Dashboard
        self.shared_portfolio_data.update(self.dashboard_page.cached_data)
        
        # Trigger the Monte Carlo preload
        self.simulation_page.start_background_preload()

    def on_simulation_ready(self, sim_data: dict):
        """Called when Monte Carlo math finishes."""
        # Merge the simulation math (mu, sigma, scenarios) into our shared dictionary
        self.shared_portfolio_data.update(sim_data)
        
        # Feed the complete dictionary to the AI Page
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