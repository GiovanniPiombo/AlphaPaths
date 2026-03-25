from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal, QTimer
from workers.ibkr_thread import IBKRWorker
from core.logger import app_logger

class DashboardPage(QWidget):
    """
    Main interface for displaying the user's IBKR portfolio overview.

    This page serves as the entry point for financial data. It displays 
    high-level metrics (Net Liquidation Value, Cash, Daily P&L) and a detailed 
    table of open positions. It utilizes an `IBKRWorker` to fetch data 
    asynchronously, ensuring the UI remains responsive during network calls.

    Signals:
        dashboard_refreshed: Emitted when data fetching completes and the UI 
            is updated. Used to trigger subsequent actions in other modules 
            (e.g., pre-loading Monte Carlo simulations).

    Attributes:
        cached_data (dict): Stores the most recently fetched portfolio data 
            (currency, weights, positions) for use by other application components.
        worker (IBKRWorker): The background thread responsible for API calls.
    """
    dashboard_refreshed = Signal()

    def __init__(self):
        """
        Initializes the DashboardPage.

        Sets up the base state, constructs the UI, and schedules an automatic 
        initial data fetch 100ms after the widget is created.
        """
        self.cached_data = {}
        super().__init__()
        self.worker = None
        self.setup_ui()
        QTimer.singleShot(100, self.start_refresh)

    def setup_ui(self):
        """
        Constructs the graphical user interface for the dashboard.

        Builds the vertical main layout containing:
        1. Header
        2. Summary cards (NLV, Cash, P&L) via a horizontal layout.
        3. A control bar with the manual refresh button.
        4. A formatted `QTableWidget` to display open asset positions.
        """
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

        nlv_card, self.nlv_label = self.create_summary_card("NET LIQUIDATION VALUE", "0.00", "neutral")
        cash_card, self.cash_label = self.create_summary_card("TOTAL CASH", "0.00", "neutral")
        pnl_card, self.pnl_label = self.create_summary_card("DAILY P&L", "0.00", "neutral")

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
        """
        Helper method to create styled summary cards for portfolio metrics.

        Args:
            title (str): The header text of the card (e.g., "DAILY P&L").
            initial_value (str): The placeholder value text (e.g., "€ 0.00").
            value_type (str): Determines the semantic color of the text. 
                Must be one of "positive", "negative", or "neutral".

        Returns:
            tuple: A (QFrame, QLabel) tuple containing the constructed card 
                widget and the updatable value label.
        """
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
        """
        Updates the text and dynamic styling of a specific summary card.

        Args:
            label (QLabel): The target label widget to update.
            text (str): The formatted currency string to display.
            value_type (str): Applies the corresponding color from `VALUE_COLORS`.
        """
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
        """
        Initiates the asynchronous data fetching process.

        Disables the refresh button to prevent overlapping requests, updates 
        the button text to show progress, instantiates a new `IBKRWorker`, 
        connects its signals, and starts the thread.
        """
        app_logger.debug("Button clicked! Starting function...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Connecting...")

        app_logger.debug("Creating IBKRWorker thread...")
        self.worker = IBKRWorker()
        self.worker.progress_update.connect(lambda msg: self.refresh_btn.setText(msg))
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_error)

        app_logger.debug("Starting the thread...")
        self.worker.start()

    def on_data_fetched(self, data):
        """
        Callback triggered when the IBKRWorker successfully returns data.

        Parses the incoming dictionary to update the summary cards (applying 
        positive/negative styling to P&L) and populates the positions table. 
        Finally, caches the data and emits the `dashboard_refreshed` signal.

        Args:
            data (dict): Parsed portfolio data including 'currency', 'nlv', 
                'cash', 'pnl', 'risky_weight', 'cash_weight', and 'positions'.
        """
        app_logger.info("Data received from thread! Updating UI...")

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
        
        app_logger.debug("Dashboard finished. Emitting signal to start Monte Carlo...")
        self.cached_data = {
            "currency": data['currency'],
            "risky_weight": data['risky_weight'],
            "cash_weight": data['cash_weight'],
            "positions": data['positions']
        }
        self.dashboard_refreshed.emit()

    def on_error(self, error_msg):
        """
        Callback triggered if the IBKRWorker encounters an exception.

        Restores the UI state (re-enabling the refresh button) and presents 
        a critical error dialog to the user with the failure details.

        Args:
            error_msg (str): The formatted error string from the worker thread.
        """
        app_logger.error(f"IBKR Error UI Popup: {error_msg}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh IBKR Data")
        QMessageBox.critical(self, "IBKR Error", f"An error occurred:\n{error_msg}")
    
    def set_refresh_enabled(self, is_enabled: bool, message: str = None):
        """
        Enables or disables the refresh button from the outside.
        Useful for locking the UI when other pages are processing data.
        """
        self.refresh_btn.setEnabled(is_enabled)
        if is_enabled:
            self.refresh_btn.setText("Refresh IBKR Data")
        else:
            self.refresh_btn.setText(message if message else "Processing...")