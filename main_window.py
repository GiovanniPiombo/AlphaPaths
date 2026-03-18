from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,QPushButton, QStackedWidget, QLabel
from PySide6.QtCore import Qt

from pages.dashboard_page import DashboardPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBKR Portfolio Analyzer")
        self.resize(1100, 700) #Window size
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Sidebar + Content Area
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # SIDEBAR
        # ==========================================
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(0)

        # Sidebar Logo and Title
        logo_label = QLabel("Portfolio\nAnalyzer")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)

        # Buttons
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        
        self.btn_simulation = QPushButton("Simulazione")
        self.btn_simulation.setCheckable(True)
        
        self.btn_ai_review = QPushButton("AI Review")
        self.btn_ai_review.setCheckable(True)

        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_simulation)
        sidebar_layout.addWidget(self.btn_ai_review)
        sidebar_layout.addStretch()

        # ==========================================
        # Content Area (QStackedWidget)
        # ==========================================
        self.stacked_widget = QStackedWidget()
        
        self.dashboard_page = DashboardPage()
        self.stacked_widget.addWidget(self.dashboard_page)

        # Simulation Page Placeholder
        self.simulation_page = QWidget()
        sim_layout = QVBoxLayout(self.simulation_page)
        sim_layout.addWidget(QLabel("<h1>Work in Progress...</h1>"))
        self.stacked_widget.addWidget(self.simulation_page)

        # AI Review Page Placeholder
        self.ai_page = QWidget()
        ai_layout = QVBoxLayout(self.ai_page)
        ai_layout.addWidget(QLabel("<h1>Work in Progress...</h1>"))
        self.stacked_widget.addWidget(self.ai_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stacked_widget)

        # ==========================================
        # SIGNAL-SLOT CONNECTIONS
        # ==========================================
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0, self.btn_dashboard))
        self.btn_simulation.clicked.connect(lambda: self.switch_page(1, self.btn_simulation))
        self.btn_ai_review.clicked.connect(lambda: self.switch_page(2, self.btn_ai_review))


    def switch_page(self, index, button):
        """Switch page and update button states."""

        self.stacked_widget.setCurrentIndex(index)

        self.btn_dashboard.setChecked(False)
        self.btn_simulation.setChecked(False)
        self.btn_ai_review.setChecked(False)
        
        button.setChecked(True)