from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal, QTimer
from workers.ibkr_thread import IBKRWorker

class DashboardPage(QWidget):
    """The DashboardPage class provides a user interface for displaying the user's IBKR portfolio summary and open positions. It includes a refresh button to fetch the latest data from the IBKR API using a background thread (IBKRWorker) to avoid freezing the UI. The class also emits a custom signal (dashboard_refreshed) when the data fetching and UI update process is complete, allowing other components (like the SimulationPage) to react accordingly, such as starting Monte Carlo simulations with the newly fetched data."""
    dashboard_refreshed = Signal()

    def __init__(self):
        """Initializes the DashboardPage, sets up the UI, and prepares for background data loading."""
        super().__init__()
        self.worker = None
        self.setup_ui()
        QTimer.singleShot(100, self.start_refresh)

    def setup_ui(self):
        """Sets up the user interface components of the DashboardPage, including summary cards, a refresh button, and a table for open positions."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        # ── HEADER ───────────────────────────────────────────
        header_label = QLabel("Portfolio Dashboard")
        header_label.setObjectName("page_header")
        main_layout.addWidget(header_label)

        # ── SUMMARY CARDS ────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        nlv_card, self.nlv_label = self.create_summary_card("NET LIQUIDATION VALUE", "€ 0.00", "neutral")
        cash_card, self.cash_label = self.create_summary_card("TOTAL CASH", "€ 0.00", "neutral")
        pnl_card, self.pnl_label = self.create_summary_card("DAILY P&L", "€ 0.00", "neutral")

        cards_layout.addWidget(nlv_card)
        cards_layout.addWidget(cash_card)
        cards_layout.addWidget(pnl_card)
        main_layout.addLayout(cards_layout)

        # ── CONTROLS BAR ─────────────────────────────────────
        controls_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh IBKR Data")
        self.refresh_btn.setObjectName("primary_btn")
        self.refresh_btn.setMinimumHeight(38)
        self.refresh_btn.setMinimumWidth(160)
        self.refresh_btn.clicked.connect(self.start_refresh)

        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # ── POSITIONS TABLE ───────────────────────────────────
        section_label = QLabel("OPEN POSITIONS")
        section_label.setObjectName("section_label")
        main_layout.addWidget(section_label)

        self.positions_table = QTableWidget(0, 4)
        self.positions_table.setHorizontalHeaderLabels(
            ["Asset", "Quantity", "Current Price", "Market Value"]
        )
        header = self.positions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.setShowGrid(False)
        self.positions_table.verticalHeader().setVisible(False)
        self.positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.positions_table.setEditTriggers(QTableWidget.NoEditTriggers)

        main_layout.addWidget(self.positions_table)

    def create_summary_card(self, title: str, initial_value: str, value_type: str):
        """Creates a styled summary card with a title and a value label. The value label's color is determined by the value_type (positive, negative, neutral). Returns the card widget and the value label for later updates."""
        card = QFrame()
        card.setObjectName("summary_card")
        card.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("card_title")

        value_label = QLabel(initial_value)
        value_label.setObjectName("card_value")
        value_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return card, value_label

    VALUE_COLORS = {
        "positive": "#2ECC8A",
        "negative": "#E05252",
        "neutral":  "#E8EDF5",
    }

    def _set_card_value(self, label: QLabel, text: str, value_type: str):
        """Updates the text and color of a summary card's value label based on the value_type (positive, negative, neutral)."""
        color = self.VALUE_COLORS.get(value_type, "#E8EDF5")
        label.setText(text)
        label.setStyleSheet(
            f"color: {color};"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 24px;"
            "font-weight: 700;"
            "letter-spacing: -0.5px;"
        )

    def start_refresh(self):
        """Starts the process of refreshing IBKR data by creating and running an IBKRWorker thread. It also updates the refresh button's state and text to provide feedback to the user."""
        print("\n[UI DEBUG] 1. Button clicked! Starting function...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Connecting...")

        print("[UI DEBUG] 2. Creating IBKRWorker thread...")
        self.worker = IBKRWorker()
        self.worker.progress_update.connect(lambda msg: self.refresh_btn.setText(msg))
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_error)

        print("[UI DEBUG] 3. Starting the thread...")
        self.worker.start()

    def on_data_fetched(self, data):
        """Handles the data received from the IBKRWorker thread, updates the UI with the new portfolio summary and positions, and emits a signal to notify that the dashboard has been refreshed and simulations can start."""
        print("[UI DEBUG] 5. Data received from thread! Updating UI...")

        cur = data['currency']
        self._set_card_value(self.nlv_label, f"{cur} {data['nlv']:,.2f}", "neutral")
        self._set_card_value(self.cash_label, f"{cur} {data['cash']:,.2f}", "neutral")

        pnl = data['pnl']
        pnl_type = "positive" if pnl >= 0 else "negative"
        pnl_sign = "+" if pnl >= 0 else ""
        self._set_card_value(self.pnl_label, f"{cur} {pnl_sign}{pnl:,.2f}", pnl_type)

        positions = data['positions']
        self.positions_table.setRowCount(len(positions))
        for row, pos in enumerate(positions):
            self.positions_table.setItem(row, 0, QTableWidgetItem(str(pos[0])))
            self.positions_table.setItem(row, 1, QTableWidgetItem(str(pos[1])))
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{cur} {pos[2]:,.2f}"))
            self.positions_table.setItem(row, 3, QTableWidgetItem(f"{cur} {pos[3]:,.2f}"))

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh IBKR Data")
        
        print("[UI DEBUG] 6. Dashboard finished. Emitting signal to start Monte Carlo...")
        self.dashboard_refreshed.emit()

    def on_error(self, error_msg):
        """Handles errors emitted by the IBKRWorker thread, updates the refresh button's state and text, and shows a critical message box to inform the user about the error."""
        print(f"[UI DEBUG] Error received: {error_msg}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh IBKR Data")
        QMessageBox.critical(self, "IBKR Error", f"An error occurred:\n{error_msg}")