from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
from PySide6.QtCore import Qt

from workers.ibkr_thread import IBKRWorker

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- HEADER ---
        header_label = QLabel("Portfolio Dashboard")
        main_layout.addWidget(header_label)

        # --- SUMMARY CARDS ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        nlv_card, self.nlv_label = self.create_summary_card("Net Liquidation Value", "€ 0.00")
        cash_card, self.cash_label = self.create_summary_card("Total Cash", "€ 0.00")
        pnl_card, self.pnl_label = self.create_summary_card("Daily P&L", "€ 0.00")
        
        cards_layout.addWidget(nlv_card)
        cards_layout.addWidget(cash_card)
        cards_layout.addWidget(pnl_card)
        
        main_layout.addLayout(cards_layout)

        # --- CONTROLS BAR ---
        controls_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh IBKR Data")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setMinimumWidth(150)
        
        # Connect the button click to the function
        self.refresh_btn.clicked.connect(self.start_refresh)
        
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # --- POSITIONS TABLE ---
        table_label = QLabel("Your Positions")
        main_layout.addWidget(table_label)

        self.positions_table = QTableWidget(0, 4)
        self.positions_table.setHorizontalHeaderLabels(["Asset", "Quantity", "Current Price", "Market Value"])
        
        header = self.positions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        
        main_layout.addWidget(self.positions_table)

    def create_summary_card(self, title, initial_value):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel(title)
        
        value_label = QLabel(initial_value)
        value_label.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card, value_label

    def start_refresh(self):
        print("\n[UI DEBUG] 1. Button clicked! Starting function...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Connecting to IBKR...")

        print("[UI DEBUG] 2. Creating IBKRWorker thread...")
        self.worker = IBKRWorker()
        
        self.worker.progress_update.connect(lambda msg: self.refresh_btn.setText(msg))
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_error)
        
        print("[UI DEBUG] 3. Starting the thread...")
        self.worker.start()
        print("[UI DEBUG] 4. start_refresh function finished, passing control to the thread.")

    def on_data_fetched(self, data):
        """Receives data from the thread and populates the UI."""
        print("[UI DEBUG] 5. Data received from thread! Updating UI...")
        
        self.nlv_label.setText(f"{data['currency']} {data['nlv']:,.2f}")
        self.cash_label.setText(f"{data['currency']} {data['cash']:,.2f}")
        self.pnl_label.setText(f"{data['currency']} {data['pnl']:,.2f}")
        
        positions = data['positions']
        self.positions_table.setRowCount(len(positions))
        for row, pos in enumerate(positions):
            self.positions_table.setItem(row, 0, QTableWidgetItem(str(pos[0])))
            self.positions_table.setItem(row, 1, QTableWidgetItem(str(pos[1])))
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{data['currency']} {pos[2]:,.2f}"))
            self.positions_table.setItem(row, 3, QTableWidgetItem(f"{data['currency']} {pos[3]:,.2f}"))

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh IBKR Data")

    def on_error(self, error_msg):
        """Handles any errors during data download."""
        print(f"[UI DEBUG] Error received: {error_msg}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh IBKR Data")
        QMessageBox.critical(self, "IBKR Error", f"An error occurred:\n{error_msg}")