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
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QFormLayout, QMessageBox, QComboBox, QCheckBox, QTabWidget, QScrollArea, QDialog, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from components.manual_portfolio_widget import ManualPortfolioWidget
from core.utils import read_json, write_json, get_invalid_tickers
from core.path_manager import PathManager
from core.logger import app_logger
import os

class SettingsPage(QWidget):
    """
    User interface component for configuring global application settings.

    This page manages user preferences including Gemini API credentials, 
    Monte Carlo simulation defaults, and Broker connection parameters. 
    It handles loading existing configurations from `config.json`, 
    displaying them in categorized tabs, and saving user modifications 
    back to the local file system.
    """
    
    def __init__(self):
        """
        Initializes the SettingsPage.

        Calls the UI setup routine and immediately populates the fields 
        by loading the existing configuration from disk.
        """
        super().__init__()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """
        Constructs and arranges the UI elements using a QTabWidget.

        Organizes input fields into four distinct tabs, each wrapped in a 
        QScrollArea to prevent UI squashing when many fields are added:
        1. Broker Settings
        2. Base Mathematics
        3. Monte Carlo
        4. AI Configuration
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        header_label = QLabel("System Settings")
        header_label.setObjectName("page_header")
        main_layout.addWidget(header_label)

        # ─── SETUP TAB WIDGET ─────────────────────────────────────────
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        scroll_style = "QScrollArea { border: none; background: transparent; }"
        content_style = "background: transparent;"

        # ── TAB 1: Broker Settings ────────────────────────────────────
        tab_broker = QScrollArea()
        tab_broker.setWidgetResizable(True)
        tab_broker.setStyleSheet(scroll_style)
        
        broker_content = QWidget()
        broker_content.setStyleSheet(content_style)
        layout_broker = QFormLayout(broker_content)
        layout_broker.setSpacing(15)
        layout_broker.setContentsMargins(15, 15, 15, 15)
        layout_broker.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.active_broker_input = QComboBox()
        self.active_broker_input.addItems(["Interactive Brokers", "Alpaca", "Crypto Exchange", "Manual (Yahoo Finance)"])
        self.active_broker_input.currentTextChanged.connect(self.toggle_broker_fields)
        
        self.currency_input = QComboBox()
        self.currency_input.addItems(["USD", "EUR", "GBP", "CHF"])

        # IBKR Fields
        self.ibkr_host_input = QLineEdit()
        self.ibkr_port_input = QSpinBox()
        self.ibkr_port_input.setRange(1000, 9999)
        self.ibkr_client_id_input = QSpinBox()
        self.ibkr_client_id_input.setRange(1, 999)
        self.ibkr_timeout_input = QDoubleSpinBox()
        self.ibkr_timeout_input.setRange(1.0, 30.0)
        self.ibkr_timeout_input.setSingleStep(0.5)
        self.ibkr_timeout_input.setSuffix(" sec")
        self.pacing_limit = QSpinBox()
        self.pacing_limit.setRange(1, 20)
        
        # Alpaca Fields
        self.alpaca_api_input = QLineEdit()
        self.alpaca_api_input.setEchoMode(QLineEdit.Password)
        self.alpaca_secret_input = QLineEdit()
        self.alpaca_secret_input.setEchoMode(QLineEdit.Password)
        self.alpaca_testnet_input = QCheckBox()

        # Crypto Fields
        self.crypto_exchange_input = QLineEdit()
        self.crypto_api_input = QLineEdit()
        self.crypto_api_input.setEchoMode(QLineEdit.Password)
        self.crypto_secret_input = QLineEdit()
        self.crypto_secret_input.setEchoMode(QLineEdit.Password)
        self.crypto_testnet_input = QCheckBox()
        self.crypto_dust_input = QDoubleSpinBox()
        self.crypto_dust_input.setDecimals(4)
        self.crypto_dust_input.setRange(0.0, 10.0)
        self.crypto_dust_input.setSingleStep(0.0001)

        layout_broker.addRow(QLabel("Active Broker:"), self.active_broker_input)
        layout_broker.addRow(QLabel("Display Currency:"), self.currency_input)
        
        # ─── IBKR CONTAINER ──────────────────────────────────────────
        self.ibkr_container = QWidget()
        ibkr_layout = QFormLayout(self.ibkr_container)
        ibkr_layout.setContentsMargins(0, 0, 0, 0)
        ibkr_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        ibkr_label = QLabel("Interactive Brokers")
        ibkr_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        ibkr_layout.addRow(ibkr_label)
        ibkr_layout.addRow(QLabel("Host (IP):"), self.ibkr_host_input)
        ibkr_layout.addRow(QLabel("Port:"), self.ibkr_port_input)
        ibkr_layout.addRow(QLabel("Client ID:"), self.ibkr_client_id_input)
        ibkr_layout.addRow(QLabel("Data Timeout:"), self.ibkr_timeout_input)
        ibkr_layout.addRow(QLabel("Pacing Limit:"), self.pacing_limit)

        # ─── ALPACA CONTAINER ────────────────────────────────────────
        self.alpaca_container = QWidget()
        alpaca_layout = QFormLayout(self.alpaca_container)
        alpaca_layout.setContentsMargins(0, 0, 0, 0)
        alpaca_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        alpaca_label = QLabel("Alpaca")
        alpaca_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        alpaca_layout.addRow(alpaca_label)
        alpaca_layout.addRow(QLabel("API Key:"), self.alpaca_api_input)
        alpaca_layout.addRow(QLabel("Secret Key:"), self.alpaca_secret_input)
        alpaca_layout.addRow(QLabel("Paper Trading:"), self.alpaca_testnet_input)

        # ─── CRYPTO CONTAINER ────────────────────────────────────────
        self.crypto_container = QWidget()
        crypto_layout = QFormLayout(self.crypto_container)
        crypto_layout.setContentsMargins(0, 0, 0, 0)
        crypto_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        crypto_label = QLabel("Crypto Exchange")
        crypto_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        crypto_layout.addRow(crypto_label)
        crypto_layout.addRow(QLabel("CCXT Exchange ID:"), self.crypto_exchange_input)
        crypto_layout.addRow(QLabel("API Key:"), self.crypto_api_input)
        crypto_layout.addRow(QLabel("Secret:"), self.crypto_secret_input)
        crypto_layout.addRow(QLabel("Testnet:"), self.crypto_testnet_input)
        crypto_layout.addRow(QLabel("Dust Threshold:"), self.crypto_dust_input)

        layout_broker.addRow(self.ibkr_container)
        layout_broker.addRow(self.alpaca_container)
        layout_broker.addRow(self.crypto_container)

        tab_broker.setWidget(broker_content)
        self.tabs.addTab(tab_broker, "Broker Settings")

        # ─── MANUAL CONTAINER ────────────────────────────────────────
        self.manual_container = QWidget()
        manual_layout = QFormLayout(self.manual_container)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        manual_label = QLabel("Manual Portfolio")
        manual_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        manual_layout.addRow(manual_label)

        self.manual_cash = QDoubleSpinBox()
        self.manual_cash.setRange(0.0, 100000000.0)
        self.manual_cash.setDecimals(2)

        manual_layout.addRow(QLabel("Cash Balance:"), self.manual_cash)

        self.manual_portfolio_table = ManualPortfolioWidget()
        manual_layout.addRow(self.manual_portfolio_table)

        layout_broker.addRow(self.manual_container)

        # ── TAB 2: Base Mathematics ───────────────────────────────────
        tab_math = QScrollArea()
        tab_math.setWidgetResizable(True)
        tab_math.setStyleSheet(scroll_style)
        
        math_content = QWidget()
        math_content.setStyleSheet(content_style)
        layout_math = QFormLayout(math_content)
        layout_math.setSpacing(15)
        layout_math.setContentsMargins(15, 15, 15, 15)
        layout_math.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.risk_free_input = QDoubleSpinBox()
        self.risk_free_input.setRange(-10.0, 20.0)
        self.risk_free_input.setSingleStep(0.1)
        self.risk_free_input.setSuffix(" %")
        
        self.lookback_period = QSpinBox()
        self.lookback_period.setRange(1, 20.0)
        self.lookback_period.setSuffix(" Years")

        layout_math.addRow(QLabel("Risk-Free Rate:"), self.risk_free_input)
        layout_math.addRow(QLabel("Lookback Period:"), self.lookback_period)

        tab_math.setWidget(math_content)
        self.tabs.addTab(tab_math, "Base Mathematics")

        # ── TAB 3: Monte Carlo ────────────────────────────────────────
        tab_mc = QScrollArea()
        tab_mc.setWidgetResizable(True)
        tab_mc.setStyleSheet(scroll_style)
        
        mc_content = QWidget()
        mc_content.setStyleSheet(content_style)
        layout_mc = QFormLayout(mc_content)
        layout_mc.setSpacing(15)
        layout_mc.setContentsMargins(15, 15, 15, 15)
        layout_mc.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.mc_years_input = QSpinBox()
        self.mc_years_input.setRange(1, 30)
        
        self.mc_sims_input = QComboBox()
        self.mc_sims_input.addItems(["1000", "10000", "50000", "100000"])
        
        self.jump_threshold_input = QDoubleSpinBox()
        self.jump_threshold_input.setRange(1.0, 10.0)
        self.jump_threshold_input.setSingleStep(0.5)
        self.jump_threshold_input.setSuffix(" \u03c3 (Sigma)")
        self.jump_threshold_input.setToolTip("Sets the standard deviation multiplier to identify historical market crashes. Lower = more sensitive.")

        layout_mc.addRow(QLabel("Default Years:"), self.mc_years_input)
        layout_mc.addRow(QLabel("Default Simulations:"), self.mc_sims_input)
        layout_mc.addRow(QLabel("Jump Threshold:"), self.jump_threshold_input)

        tab_mc.setWidget(mc_content)
        self.tabs.addTab(tab_mc, "Monte Carlo")

        # ── TAB 4: AI Configuration ───────────────────────────────────
        tab_ai = QScrollArea()
        tab_ai.setWidgetResizable(True)
        tab_ai.setStyleSheet(scroll_style)
        
        ai_content = QWidget()
        ai_content.setStyleSheet(content_style)
        layout_ai = QFormLayout(ai_content)
        layout_ai.setSpacing(15)
        layout_ai.setContentsMargins(15, 15, 15, 15)
        layout_ai.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # AI Provider Selector
        self.ai_provider_input = QComboBox()
        self.ai_provider_input.addItems(["Gemini", "Ollama"])
        self.ai_provider_input.currentTextChanged.connect(self.toggle_ai_fields)

        # Gemini Fields
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumWidth(300)
        self.model_input = QLineEdit()
        
        # Ollama Fields
        self.ollama_endpoint_input = QLineEdit()
        self.ollama_endpoint_input.setText("http://localhost:11434")
        self.ollama_model_input = QLineEdit()
        self.ollama_model_input.setPlaceholderText("e.g. llama3, mistral")

        self.language_input = QComboBox()
        self.language_input.addItems(["English", "Italiano", "Español", "Français", "Deutsch"])

        layout_ai.addRow(QLabel("AI Provider:"), self.ai_provider_input)
        
        # Add fields to the layout
        self.lbl_gemini_key = QLabel("Gemini API Key:")
        self.lbl_gemini_model = QLabel("Gemini Model:")
        layout_ai.addRow(self.lbl_gemini_key, self.api_key_input)
        layout_ai.addRow(self.lbl_gemini_model, self.model_input)
        
        self.lbl_ollama_end = QLabel("Ollama Endpoint:")
        self.lbl_ollama_mod = QLabel("Ollama Model:")
        layout_ai.addRow(self.lbl_ollama_end, self.ollama_endpoint_input)
        layout_ai.addRow(self.lbl_ollama_mod, self.ollama_model_input)
        
        layout_ai.addRow(QLabel("AI Output Language:"), self.language_input)

        tab_ai.setWidget(ai_content)
        self.tabs.addTab(tab_ai, "AI Configuration")

        main_layout.addSpacing(20)

        # ── TAB 5: About & Licenses ───────────────────────────────────
        tab_about = QScrollArea()
        tab_about.setWidgetResizable(True)
        tab_about.setStyleSheet(scroll_style)
        
        about_content = QWidget()
        about_content.setStyleSheet(content_style)
        layout_about = QVBoxLayout(about_content)
        layout_about.setSpacing(15)
        layout_about.setContentsMargins(15, 15, 15, 15)
        layout_about.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        about_text = QLabel(
            "<h2>AlphaPaths</h2>"
            "<p>Advanced risk analysis, Monte Carlo simulation, and portfolio optimization.</p>"
            "<p><b>Copyright &copy; 2026 Giovanni Piombo Nicoli</b></p>"
            "<p><b>License:</b> GNU General Public License v3.0 (GPLv3)<br>"
            "<i>For closed-source, commercial, or proprietary use, a separate Commercial License is required.</i></p>"
            "<br><p>Built with <b>PySide6</b> (LGPLv3) and powered by open-source technologies<br>"
            "including <b>NumPy</b>, <b>Pandas</b>, <b>SciPy</b>, <b>CCXT</b>, and <b>yfinance</b>.</p>"
        )
        about_text.setAlignment(Qt.AlignCenter)
        
        self.btn_show_licenses = QPushButton("View Third-Party Licenses")
        self.btn_show_licenses.setFixedWidth(250)
        self.btn_show_licenses.clicked.connect(self.show_licenses_dialog)

        layout_about.addWidget(about_text)
        layout_about.addWidget(self.btn_show_licenses, alignment=Qt.AlignCenter)

        tab_about.setWidget(about_content)
        self.tabs.addTab(tab_about, "About & Licenses")

        # ── BUTTONS ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primary_btn")
        self.save_btn.setMinimumHeight(38)
        self.save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)
        
    def load_settings(self):
        """
        Reads `config.json` and populates the UI input fields.

        If the configuration file is missing, corrupted, or missing specific 
        keys, it automatically falls back to safe default values to ensure 
        the UI renders without throwing exceptions.
        """
        config = read_json(PathManager.CONFIG_FILE)
        if config:
            self.ai_provider_input.setCurrentText(config.get("AI_PROVIDER", "Gemini"))
            self.api_key_input.setText(config.get("GEMINI_API_KEY", ""))
            self.model_input.setText(config.get("GEMINI_MODEL", "gemini-1.5-pro"))
            self.ollama_endpoint_input.setText(config.get("OLLAMA_ENDPOINT", "http://localhost:11434"))
            self.ollama_model_input.setText(config.get("OLLAMA_MODEL", "llama3"))
            self.language_input.setCurrentText(config.get("AI_LANGUAGE", "English"))
            self.toggle_ai_fields(self.ai_provider_input.currentText())
            
            self.risk_free_input.setValue(config.get("RISK_FREE_RATE", 0.0) * 100)
            self.pacing_limit.setValue(config.get("PACING_LIMIT", 5))
            self.lookback_period.setValue(config.get("LOOKBACK_PERIOD", 5))
            self.currency_input.setCurrentText(config.get("DISPLAY_CURRENCY", "EUR"))
            
            self.mc_years_input.setValue(config.get("DEFAULT_YEARS", 5))
            self.mc_sims_input.setCurrentText(str(config.get("DEFAULT_SIMS", 10000)))
            self.jump_threshold_input.setValue(config.get("JUMP_THRESHOLD", 3.0))

            self.active_broker_input.setCurrentText(config.get("ACTIVE_BROKER", "Manual (Yahoo Finance)"))

            self.ibkr_host_input.setText(config.get("IBKR_HOST", "127.0.0.1"))
            self.ibkr_port_input.setValue(config.get("IBKR_PORT", 4001))
            self.ibkr_client_id_input.setValue(config.get("IBKR_CLIENT_ID", 1))
            self.ibkr_timeout_input.setValue(config.get("IBKR_TIMEOUT", 5.0))
            
            self.alpaca_api_input.setText(config.get("ALPACA_API_KEY", ""))
            self.alpaca_secret_input.setText(config.get("ALPACA_SECRET_KEY", ""))
            self.alpaca_testnet_input.setChecked(config.get("USE_TESTNET", True))
            
            self.crypto_exchange_input.setText(config.get("CRYPTO_EXCHANGE", "alpaca"))
            self.crypto_api_input.setText(config.get("CRYPTO_API_KEY", ""))
            self.crypto_secret_input.setText(config.get("CRYPTO_SECRET", ""))
            self.crypto_testnet_input.setChecked(config.get("USE_TESTNET", True))
            self.crypto_dust_input.setValue(config.get("CRYPTO_DUST_THRESHOLD", 0.0001))

            m_data = read_json(PathManager.MANUAL_PORTFOLIO_FILE)
            if m_data:
                self.currency_input.setCurrentText(m_data.get("base_currency", "EUR"))
                self.manual_cash.setValue(float(m_data.get("cash", 0.0)))
        
                self.manual_portfolio_table.clear()
                for pos in m_data.get("positions", []):
                    self.manual_portfolio_table.add_row(pos['ticker'], str(pos['quantity']))

            self.toggle_broker_fields(self.active_broker_input.currentText())

    def save_settings(self):
        """
        Gathers user inputs, formats them, and writes them to `config.json`.

        Converts UI-specific formatting (like percentage values from the 
        risk-free rate spinbox) back into standard decimal formats for storage. 
        Upon successful write, it prompts the user with a dialog recommending 
        an application restart to apply changes globally.
        """
        if self.active_broker_input.currentText() == "Manual (Yahoo Finance)":
            positions = self.manual_portfolio_table.get_positions()
            tickers_to_check = [pos["ticker"] for pos in positions]
            
            if tickers_to_check:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                invalid_tickers = get_invalid_tickers(tickers_to_check)
                QApplication.restoreOverrideCursor()
                
                if invalid_tickers:
                    msg = (f"The following tickers were not found on Yahoo Finance:\n\n"
                           f"{', '.join(invalid_tickers)}\n\n"
                           f"Are you sure you want to save anyway? This might cause errors during calculations.")
                    
                    reply = QMessageBox.warning(self, "Invalid Tickers Found", msg, 
                                                QMessageBox.Yes | QMessageBox.No, 
                                                QMessageBox.No)
                    if reply == QMessageBox.No:
                        return

        config = read_json(PathManager.CONFIG_FILE)
        if not isinstance(config, dict):
            config = {}
            
        config["RISK_FREE_RATE"] = round(self.risk_free_input.value() / 100.0, 4)
        config["PACING_LIMIT"] = self.pacing_limit.value()
        config["LOOKBACK_PERIOD"] = self.lookback_period.value()
        config["LOOK"] = self.mc_years_input.value()
        config["DEFAULT_YEARS"] = self.mc_years_input.value()
        config["DEFAULT_SIMS"] = int(self.mc_sims_input.currentText())
        config["JUMP_THRESHOLD"] = round(self.jump_threshold_input.value(), 2)
        config["DISPLAY_CURRENCY"] = self.currency_input.currentText()

        config["ACTIVE_BROKER"] = self.active_broker_input.currentText()
        
        config["IBKR_HOST"] = self.ibkr_host_input.text().strip()
        config["IBKR_PORT"] = self.ibkr_port_input.value()
        config["IBKR_CLIENT_ID"] = self.ibkr_client_id_input.value()
        config["IBKR_TIMEOUT"] = self.ibkr_timeout_input.value()
        
        # Alpaca Saving
        config["ALPACA_API_KEY"] = self.alpaca_api_input.text().strip()
        config["ALPACA_SECRET_KEY"] = self.alpaca_secret_input.text().strip()
        
        config["CRYPTO_EXCHANGE"] = self.crypto_exchange_input.text().strip()
        config["CRYPTO_API_KEY"] = self.crypto_api_input.text().strip()
        config["CRYPTO_SECRET"] = self.crypto_secret_input.text().strip()
        config["CRYPTO_DUST_THRESHOLD"] = self.crypto_dust_input.value()

        config["AI_PROVIDER"] = self.ai_provider_input.currentText()
        config["GEMINI_API_KEY"] = self.api_key_input.text().strip()
        config["GEMINI_MODEL"] = self.model_input.text().strip()
        config["OLLAMA_ENDPOINT"] = self.ollama_endpoint_input.text().strip()
        config["OLLAMA_MODEL"] = self.ollama_model_input.text().strip()
        config["AI_LANGUAGE"] = self.language_input.currentText()
        
        # Handle shared Testnet key based on the active broker
        if self.active_broker_input.currentText() == "Alpaca":
            config["USE_TESTNET"] = self.alpaca_testnet_input.isChecked()
        else:
            config["USE_TESTNET"] = self.crypto_testnet_input.isChecked()

        if write_json(PathManager.CONFIG_FILE, config):
            app_logger.info("User settings saved successfully.")
            QMessageBox.information(self, "Restart Recommended", "Settings saved successfully!\n\nPlease restart the application.")
        else:
            app_logger.error("Could not save the config.json file from UI.")
            QMessageBox.critical(self, "Error", "Could not save the config.json file.")

        portfolio_to_save = {
            "base_currency": self.currency_input.currentText(),
            "cash": self.manual_cash.value(),
            "positions": self.manual_portfolio_table.get_positions()
        }
        write_json(PathManager.MANUAL_PORTFOLIO_FILE, portfolio_to_save)

    def toggle_broker_fields(self, text: str):
        """Shows or hides containers based on the currently selected broker."""
        self.ibkr_container.setVisible(text == "Interactive Brokers")
        self.alpaca_container.setVisible(text == "Alpaca")
        self.crypto_container.setVisible(text == "Crypto Exchange")
        self.manual_portfolio_table.setVisible(text == "Manual (Yahoo Finance)")

    def show_licenses_dialog(self):
        """Displays a dialog containing the contents of the THIRDPARTY-NOTICES.txt file."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Third-Party Licenses")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-family: Consolas, monospace; background-color: #1e1e1e; color: #d4d4d4;")
        
        file_path = PathManager.THIRD_PARTY_NOTICES_FILE
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                text_edit.setPlainText(f.read())
        else:
            text_edit.setPlainText("Error: 'THIRDPARTY-NOTICES.txt' not found.\nPlease ensure the file is in the application directory.")
            app_logger.error("THIRDPARTY-NOTICES.txt file is missing. Cannot display licenses dialog.")
            
        layout.addWidget(text_edit)
        
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)
        
        dialog.exec()

    def toggle_ai_fields(self, provider: str):
        """Shows/hides fields based on the selected AI provider."""
        is_gemini = (provider == "Gemini")
        
        self.lbl_gemini_key.setVisible(is_gemini)
        self.api_key_input.setVisible(is_gemini)
        self.lbl_gemini_model.setVisible(is_gemini)
        self.model_input.setVisible(is_gemini)
        
        self.lbl_ollama_end.setVisible(not is_gemini)
        self.ollama_endpoint_input.setVisible(not is_gemini)
        self.lbl_ollama_mod.setVisible(not is_gemini)
        self.ollama_model_input.setVisible(not is_gemini)