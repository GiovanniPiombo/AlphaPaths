from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView)
from PySide6.QtCore import Qt

class ManualPortfolioWidget(QWidget):
    """
    A widget that allows users to manually input their portfolio positions.
    """
    def __init__(self, parent=None):
        """Initializes the ManualPortfolioWidget with a table for ticker and quantity input, and buttons to add/remove rows."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Sets up the user interface components of the widget, including the table and control buttons."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Ticker", "Quantity"])
        self.table.setFixedHeight(250)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Row")
        self.btn_remove = QPushButton("- Remove Row")
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove.clicked.connect(self.remove_row)

    def add_row(self, ticker: str = "", quantity: str = "0.0"):
        """
        Adds a new row to the table with optional default values for ticker and quantity.

        Args:
            ticker (str): The stock ticker symbol to pre-fill in the new row. Defaults to an empty string.
            quantity (str): The initial quantity for the new row. Defaults to "0.0".
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        ticker_item = QTableWidgetItem(ticker)
        ticker_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        qty_item = QTableWidgetItem(quantity)
        qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.table.setItem(row, 0, ticker_item)
        self.table.setItem(row, 1, qty_item)

    def remove_row(self):
        """Removes the currently selected row from the table."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            
    def clear(self):
        """Clears all rows from the table."""
        self.table.setRowCount(0)

    def get_positions(self):
        """
        Returns a list of dictionaries with the table data.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing 'ticker' and 'quantity' keys representing the user's input from the table.
        """
        positions = []
        for row in range(self.table.rowCount()):
            t_item = self.table.item(row, 0)
            q_item = self.table.item(row, 1)
            ticker = t_item.text().strip().upper() if t_item else ""
            if ticker:
                try:
                    qty = float(q_item.text()) if q_item else 0.0
                except ValueError:
                    qty = 0.0
                positions.append({"ticker": ticker, "quantity": qty})
        return positions