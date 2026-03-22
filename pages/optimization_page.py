from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QFrame, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from workers.optimization_thread import OptimizationWorker
from components.markowitz_chart import MarkowitzChartView

class OptimizationPage(QWidget):
    """
    User interface component for Modern Portfolio Theory (MPT) optimization.
    
    This page displays the Efficient Frontier chart and a detailed action table.
    It introduces a "Core-Satellite" approach, allowing the user to lock specific 
    assets (like broad-market ETFs) to their current weight, forcing the 
    mathematical optimizer to only reallocate the remaining "satellite" positions.
    """
    def __init__(self):
        """
        Initializes the OptimizationPage and sets up the blank UI state.
        """
        super().__init__()
        self.metrics = None
        self.positions = None
        self.setup_ui()

    def setup_ui(self):
        """
        Constructs the graphical user interface for the optimization page.

        Builds the vertical main layout containing:
        1. Header and Run control button.
        2. Summary cards comparing Current Sharpe vs Optimal Sharpe.
        3. A split layout featuring the custom MarkowitzChartView on the left 
           and the interactive QTableWidget on the right.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        # ── HEADER & CONTROLS ───────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_label = QLabel("Portfolio Optimization (Core-Satellite)")
        header_label.setObjectName("page_header")
        
        self.run_btn = QPushButton("Run Optimization")
        self.run_btn.setObjectName("primary_btn")
        self.run_btn.setMinimumHeight(38)
        self.run_btn.clicked.connect(self.on_run_clicked)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.run_btn)
        main_layout.addLayout(header_layout)

        # ── SUMMARY CARDS ────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        curr_card, self.curr_label = self.create_summary_card("CURRENT SHARPE", "0.00", "#E05252")
        opt_card, self.opt_label = self.create_summary_card("OPTIMAL SHARPE", "0.00", "#2ECC8A")
        
        cards_layout.addWidget(curr_card)
        cards_layout.addWidget(opt_card)
        main_layout.addLayout(cards_layout)

        # ── CHART & TABLE LAYOUT ────────────────────────────────────
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left: Chart
        self.chart_view = MarkowitzChartView(self)
        self.chart_view.setMinimumHeight(400)
        self.chart_view.setMinimumWidth(450)
        content_layout.addWidget(self.chart_view, stretch=3)

        # Right: Interactive Table
        self.delta_table = QTableWidget(0, 5)
        self.delta_table.setHorizontalHeaderLabels(["Asset", "Current %", "Lock", "Optimal %", "Action"])
        self.delta_table.setMinimumWidth(440)
        
        header = self.delta_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.delta_table.setAlternatingRowColors(True)
        self.delta_table.setShowGrid(False)
        self.delta_table.verticalHeader().setVisible(False)
        self.delta_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        content_layout.addWidget(self.delta_table, stretch=2)
        main_layout.addLayout(content_layout)

    def create_summary_card(self, title: str, initial_value: str, color: str):
        """
        Helper method to create styled summary cards.

        Args:
            title (str): The header text of the card.
            initial_value (str): The starting text to display.
            color (str): The hex color code for the value text.

        Returns:
            tuple: A tuple containing (QFrame, QLabel) representing the card 
                container and the updatable value label.
        """
        card = QFrame()
        card.setObjectName("summary_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        
        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        
        value_label = QLabel(initial_value)
        value_label.setStyleSheet(
            f"color: {color}; font-family: 'Consolas', monospace; font-size: 24px; font-weight: 700;"
        )
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def set_data(self, metrics: dict, positions: list):
        """
        Receives the shared portfolio data from the MainWindow and pre-populates the UI.

        Extracts the list of available tickers and calculates their current weights.
        It then populates the interactive table so the user can review their holdings 
        and select which assets to "Lock" before running the optimization.

        Args:
            metrics (dict): Risk metrics including symbols and covariance.
            positions (list): Raw position data from IBKR.
        """
        self.metrics = metrics
        self.positions = positions
        
        symbols = self.metrics.get("symbols", [])
        
        total_risky_value = sum([pos[3] for pos in self.positions if pos[0] in symbols])
        current_weights = {pos[0]: pos[3] / total_risky_value for pos in self.positions if pos[0] in symbols and total_risky_value > 0}
        
        self.delta_table.setRowCount(len(symbols))
        for row, sym in enumerate(symbols):
            c_weight = current_weights.get(sym, 0.0) * 100
            
            # Asset Name
            asset_item = QTableWidgetItem(sym)
            asset_item.setFlags(Qt.ItemIsEnabled)
            self.delta_table.setItem(row, 0, asset_item)
            
            # Current Weight
            weight_item = QTableWidgetItem(f"{c_weight:.1f}%")
            weight_item.setFlags(Qt.ItemIsEnabled)
            self.delta_table.setItem(row, 1, weight_item)
            
            # Lock Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            self.delta_table.setItem(row, 2, check_item)
            
            # Clear previous optimal data
            self.delta_table.setItem(row, 3, QTableWidgetItem("-"))
            self.delta_table.setItem(row, 4, QTableWidgetItem("-"))

    def get_locked_symbols(self) -> list:
        """
        Scans the interactive table to identify which assets the user has locked.

        Returns:
            list: A list of ticker strings (e.g., ['VWCE', 'AAPL']) that 
                have their corresponding checkbox checked in the UI.
        """
        locked = []
        for row in range(self.delta_table.rowCount()):
            sym = self.delta_table.item(row, 0).text()
            check_item = self.delta_table.item(row, 2)
            if check_item.checkState() == Qt.Checked:
                locked.append(sym)
        return locked

    def on_run_clicked(self):
        """
        Handles the click event on the "Run Optimization" button.
        
        Validates the presence of data, retrieves the locked symbols from the UI, 
        and launches the `OptimizationWorker` background thread to perform the 
        heavy mathematical calculations without freezing the application.
        """
        if not self.metrics or not self.positions:
            QMessageBox.warning(self, "Data Missing", "Please wait for IBKR data to finish loading in the Dashboard.")
            return

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Optimizing...")

        locked = self.get_locked_symbols()
        self.worker = OptimizationWorker(self.metrics, self.positions, locked)
        self.worker.progress_update.connect(lambda msg: self.run_btn.setText(msg))
        self.worker.optimization_finished.connect(self.on_optimization_complete)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_optimization_complete(self, payload: dict):
        """
        Callback executed when the OptimizationWorker successfully finishes.

        Parses the optimization results, updates the Sharpe ratio summary cards, 
        redraws the Efficient Frontier chart, and calculates the required actions 
        (Buy/Sell/Hold) to populate the final columns of the table.

        Args:
            payload (dict): A dictionary containing current and optimal stats, 
                the generated frontier points, and specific asset weights.
        """
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Optimization")

        current = payload["current"]
        optimal = payload["optimal"]
        
        self.curr_label.setText(f"{current['sharpe']:.2f}")
        self.opt_label.setText(f"{optimal['sharpe']:.2f}")

        self.chart_view.update_graph(payload["frontier"], current, optimal)

        symbols = payload["symbols"]
        curr_weights = payload["current_weights"]
        opt_weights = optimal["weights"]

        for row in range(self.delta_table.rowCount()):
            sym = self.delta_table.item(row, 0).text()
            idx = symbols.index(sym)
            
            c_weight = curr_weights.get(sym, 0.0) * 100
            o_weight = opt_weights[idx] * 100
            diff = o_weight - c_weight
            
            action = "Hold"
            if diff > 1.0: action = f"Buy +{diff:.1f}%"
            elif diff < -1.0: action = f"Sell {diff:.1f}%"
            
            if sym in self.get_locked_symbols():
                action = "Locked (Core)"

            self.delta_table.setItem(row, 3, QTableWidgetItem(f"{o_weight:.1f}%"))
            
            action_item = QTableWidgetItem(action)
            if "Buy" in action: action_item.setForeground(QColor("#2ECC8A"))
            elif "Sell" in action: action_item.setForeground(QColor("#E05252"))
            elif "Locked" in action: action_item.setForeground(QColor("#C8D0DC"))
            self.delta_table.setItem(row, 4, action_item)

    def on_error(self, error_msg):
        """
        Handles exceptions raised by the background optimization thread.

        Restores the UI state and displays a critical dialog box with the error details.

        Args:
            error_msg (str): The error string emitted by the worker.
        """
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Optimization")
        QMessageBox.critical(self, "Optimization Error", str(error_msg))