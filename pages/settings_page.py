from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QFormLayout, QMessageBox, QComboBox, QCheckBox, QTabWidget, QScrollArea
from PySide6.QtCore import Qt
from core.utils import read_json, write_json
from core.path_manager import PathManager
from core.logger import app_logger

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

        # Main Broker Settings
        self.active_broker_input = QComboBox()
        self.active_broker_input.addItems(["Interactive Brokers", "Alpaca", "Crypto Exchange", "Manual (Yahoo Finance)"])
        self.active_broker_input.currentTextChanged.connect(self.toggle_broker_fields)
        
        self.currency_input = QComboBox()
        self.currency_input.addItems(["AUTO (Broker Default)", "USD", "EUR", "GBP", "CHF", "USDT"])

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
        self.alpaca_testnet_input = QCheckBox("Enable Paper Trading")

        # Crypto Fields
        self.crypto_exchange_input = QLineEdit()
        self.crypto_api_input = QLineEdit()
        self.crypto_api_input.setEchoMode(QLineEdit.Password)
        self.crypto_secret_input = QLineEdit()
        self.crypto_secret_input.setEchoMode(QLineEdit.Password)
        self.crypto_testnet_input = QCheckBox("Enable Sandbox/Testnet")
        self.crypto_dust_input = QDoubleSpinBox()
        self.crypto_dust_input.setDecimals(4)
        self.crypto_dust_input.setRange(0.0, 10.0)
        self.crypto_dust_input.setSingleStep(0.0001)

        layout_broker.addRow(QLabel("Active Broker:"), self.active_broker_input)
        layout_broker.addRow(QLabel("Display Currency:"), self.currency_input)
        
        # Separator for IBKR
        ibkr_label = QLabel("Interactive Brokers")
        ibkr_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        layout_broker.addRow(ibkr_label)
        layout_broker.addRow(QLabel("Host (IP):"), self.ibkr_host_input)
        layout_broker.addRow(QLabel("Port:"), self.ibkr_port_input)
        layout_broker.addRow(QLabel("Client ID:"), self.ibkr_client_id_input)
        layout_broker.addRow(QLabel("Data Timeout:"), self.ibkr_timeout_input)
        layout_broker.addRow(QLabel("Pacing Limit:"), self.pacing_limit)

        # Separator for Alpaca
        alpaca_label = QLabel("Alpaca")
        alpaca_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        layout_broker.addRow(alpaca_label)
        layout_broker.addRow(QLabel("API Key:"), self.alpaca_api_input)
        layout_broker.addRow(QLabel("Secret Key:"), self.alpaca_secret_input)
        layout_broker.addRow(QLabel("Paper Trading:"), self.alpaca_testnet_input)

        # Separator for Crypto
        crypto_label = QLabel("Crypto Exchange")
        crypto_label.setStyleSheet("color: gray; font-style: italic; margin-top: 10px; margin-bottom: 5px;")
        layout_broker.addRow(crypto_label)
        layout_broker.addRow(QLabel("CCXT Exchange ID:"), self.crypto_exchange_input)
        layout_broker.addRow(QLabel("API Key:"), self.crypto_api_input)
        layout_broker.addRow(QLabel("Secret:"), self.crypto_secret_input)
        layout_broker.addRow(QLabel("Testnet:"), self.crypto_testnet_input)
        layout_broker.addRow(QLabel("Dust Threshold:"), self.crypto_dust_input)

        tab_broker.setWidget(broker_content)
        self.tabs.addTab(tab_broker, "Broker Settings")

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

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumWidth(300)

        self.model_input = QLineEdit()
        
        self.language_input = QComboBox()
        self.language_input.addItems(["English", "Italiano", "Español", "Français", "Deutsch"])

        layout_ai.addRow(QLabel("Gemini API Key:"), self.api_key_input)
        layout_ai.addRow(QLabel("AI Model:"), self.model_input)
        layout_ai.addRow(QLabel("AI Output Language:"), self.language_input)

        tab_ai.setWidget(ai_content)
        self.tabs.addTab(tab_ai, "AI Configuration")

        main_layout.addSpacing(20)

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
            self.api_key_input.setText(config.get("GEMINI_API_KEY", ""))
            self.model_input.setText(config.get("GEMINI_MODEL", "gemini-1.5-pro"))
            self.language_input.setCurrentText(config.get("AI_LANGUAGE", "English"))
            self.risk_free_input.setValue(config.get("RISK_FREE_RATE", 0.0) * 100)
            self.pacing_limit.setValue(config.get("PACING_LIMIT", 5))
            self.lookback_period.setValue(config.get("LOOKBACK_PERIOD", 5))
            self.currency_input.setCurrentText(config.get("DISPLAY_CURRENCY", "AUTO (Broker Default)"))
            
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

            self.toggle_broker_fields(self.active_broker_input.currentText())

    def save_settings(self):
        """
        Gathers user inputs, formats them, and writes them to `config.json`.

        Converts UI-specific formatting (like percentage values from the 
        risk-free rate spinbox) back into standard decimal formats for storage. 
        Upon successful write, it prompts the user with a dialog recommending 
        an application restart to apply changes globally.
        """
        config = read_json(PathManager.CONFIG_FILE)
        if not isinstance(config, dict):
            config = {}
            
        config["GEMINI_API_KEY"] = self.api_key_input.text().strip()
        config["GEMINI_MODEL"] = self.model_input.text().strip()
        config["AI_LANGUAGE"] = self.language_input.currentText()
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

    def toggle_broker_fields(self, text: str):
        """Disables specific broker inputs if they are not the currently selected active broker."""
        is_ibkr = (text == "Interactive Brokers")
        self.ibkr_host_input.setEnabled(is_ibkr)
        self.ibkr_port_input.setEnabled(is_ibkr)
        self.ibkr_client_id_input.setEnabled(is_ibkr)
        self.ibkr_timeout_input.setEnabled(is_ibkr)
        self.pacing_limit.setEnabled(is_ibkr)

        is_alpaca = (text == "Alpaca")
        self.alpaca_api_input.setEnabled(is_alpaca)
        self.alpaca_secret_input.setEnabled(is_alpaca)
        self.alpaca_testnet_input.setEnabled(is_alpaca)

        is_crypto = (text == "Crypto Exchange")
        self.crypto_exchange_input.setEnabled(is_crypto)
        self.crypto_api_input.setEnabled(is_crypto)
        self.crypto_secret_input.setEnabled(is_crypto)
        self.crypto_testnet_input.setEnabled(is_crypto)
        self.crypto_dust_input.setEnabled(is_crypto)