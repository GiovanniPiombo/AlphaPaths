from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QLabel
from PySide6.QtCore import Qt

from pages.dashboard_page import DashboardPage
from pages.simulation_page import SimulationPage

class MainWindow(QMainWindow):
    def __init__(self):
        """Main application window with sidebar navigation and stacked pages."""
        super().__init__()
        self.setWindowTitle("IBKR Portfolio Analyzer")
        self.resize(1100, 700)
        self.setup_ui()

    def setup_ui(self):
        """Sets up the main UI components: sidebar and content area."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(0)

        logo_label = QLabel("Portfolio\nAnalyzer")
        logo_label.setObjectName("logo_label")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)

        self.btn_dashboard = QPushButton("  Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)

        self.btn_simulation = QPushButton("  Simulation")
        self.btn_simulation.setCheckable(True)

        self.btn_ai_review = QPushButton("  AI Review")
        self.btn_ai_review.setCheckable(True)

        for btn in (self.btn_dashboard, self.btn_simulation, self.btn_ai_review):
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # ── CONTENT AREA ─────────────────────────────────────
        self.stacked_widget = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.stacked_widget.addWidget(self.dashboard_page)

        self.simulation_page = SimulationPage()
        self.stacked_widget.addWidget(self.simulation_page)

        # AI Review placeholder
        self.ai_page = QWidget()
        ai_layout = QVBoxLayout(self.ai_page)
        wip2 = QLabel("Work in Progress...")
        wip2.setObjectName("wip_label")
        ai_layout.addWidget(wip2, alignment=Qt.AlignCenter)
        self.stacked_widget.addWidget(self.ai_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stacked_widget)

        # ── SIGNALS ──────────────────────────────────────────
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0, self.btn_dashboard))
        self.btn_simulation.clicked.connect(lambda: self.switch_page(1, self.btn_simulation))
        self.btn_ai_review.clicked.connect(lambda: self.switch_page(2, self.btn_ai_review))
        self.dashboard_page.dashboard_refreshed.connect(self.simulation_page.start_background_preload)

    def switch_page(self, index, button):
        """Switches the visible page in the stacked widget and updates button states."""
        self.stacked_widget.setCurrentIndex(index)
        for btn in (self.btn_dashboard, self.btn_simulation, self.btn_ai_review):
            btn.setChecked(False)
        button.setChecked(True)
