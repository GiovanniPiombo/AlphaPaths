from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QFormLayout, QMessageBox, QComboBox, QScrollArea
from PySide6.QtCore import Qt
from core.utils import read_json, write_json
from core.path_manager import PathManager
from core.logger import app_logger

class SettingsPage(QWidget):
    """
    User interface component for configuring global application settings.

    This page manages user preferences including Gemini API credentials, 
    Monte Carlo simulation defaults, and Interactive Brokers (IBKR) connection 
    parameters. It handles loading existing configurations from `config.json`, 
    displaying them in categorized form fields, and saving user modifications 
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
        Constructs and arranges the UI elements using a QFormLayout wrapped inside a QScrollArea.

        Organizes input fields into three distinct semantic sections that can be scrolled, 
        while keeping the primary action buttons (Save Settings) fixed at the bottom:
        1. AI & MATH CONFIGURATION (API keys, models, language, risk-free rate, pacing limit)
        2. MONTE CARLO DEFAULTS (Years, simulation counts)
        3. IBKR CONNECTION SETTINGS (Host, port, client ID, timeout)
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        header_label = QLabel("System Settings")
        header_label.setObjectName("page_header")
        main_layout.addWidget(header_label)

        # ─── SETUP SCROLL AREA ─────────────────────────────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # CRITICAL: Allows internal widget to expand
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        form_layout = QFormLayout(scroll_content)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 0, 15, 0)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ── AI & Math Configuration ────────────────────────────────────
        ai_section = QLabel("AI & MATH CONFIGURATION")
        ai_section.setObjectName("section_label")
        form_layout.addRow(ai_section)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumWidth(300)

        self.model_input = QLineEdit()
        
        self.language_input = QComboBox()
        self.language_input.addItems(["English", "Italiano", "Español", "Français", "Deutsch"])

        self.risk_free_input = QDoubleSpinBox()
        self.risk_free_input.setRange(-10.0, 20.0)
        self.risk_free_input.setSingleStep(0.1)
        self.risk_free_input.setSuffix(" %")

        self.pacing_limit = QSpinBox()
        self.pacing_limit.setRange(1, 20)

        self.lookback_period = QSpinBox()
        self.lookback_period.setRange(1, 20.0)
        self.lookback_period.setSuffix(" Years")

        form_layout.addRow(QLabel("Gemini API Key:"), self.api_key_input)
        form_layout.addRow(QLabel("AI Model:"), self.model_input)
        form_layout.addRow(QLabel("AI Output Language:"), self.language_input)
        form_layout.addRow(QLabel("Risk-Free Rate:"), self.risk_free_input)
        form_layout.addRow(QLabel("Pacing Limit:"), self.pacing_limit)
        form_layout.addRow(QLabel("Lookback Period:"), self.lookback_period)

        # ─── Monte Carlo Defaults ──────────────────────────────────────
        mc_section = QLabel("MONTE CARLO DEFAULTS")
        mc_section.setObjectName("section_label")
        mc_section.setStyleSheet("margin-top: 10px;")
        form_layout.addRow(mc_section)

        self.mc_years_input = QSpinBox()
        self.mc_years_input.setRange(1, 30)
        
        self.mc_sims_input = QComboBox()
        self.mc_sims_input.addItems(["1000", "10000", "50000", "100000"])

        self.jump_threshold_input = QDoubleSpinBox()
        self.jump_threshold_input.setRange(1.0, 10.0)
        self.jump_threshold_input.setSingleStep(0.5)
        self.jump_threshold_input.setSuffix(" \u03c3 (Sigma)")
        self.jump_threshold_input.setToolTip("Sets the standard deviation multiplier to identify historical market crashes (Merton Jumps). Lower = more sensitive.")

        form_layout.addRow(QLabel("Default Years:"), self.mc_years_input)
        form_layout.addRow(QLabel("Default Simulations:"), self.mc_sims_input)
        form_layout.addRow(QLabel("Jump Threshold:"), self.jump_threshold_input)

        # ─── Broker Settings ───────────────────────────────────────────
        broker_section = QLabel("IBKR CONNECTION SETTINGS")
        broker_section.setObjectName("section_label")
        broker_section.setStyleSheet("margin-top: 10px;") 
        form_layout.addRow(broker_section)

        self.ibkr_host_input = QLineEdit()
        self.ibkr_port_input = QSpinBox()
        self.ibkr_port_input.setRange(1000, 9999)
        self.ibkr_client_id_input = QSpinBox()
        self.ibkr_client_id_input.setRange(1, 999)
        
        self.ibkr_timeout_input = QDoubleSpinBox()
        self.ibkr_timeout_input.setRange(1.0, 30.0)
        self.ibkr_timeout_input.setSingleStep(0.5)
        self.ibkr_timeout_input.setSuffix(" sec")
        self.ibkr_timeout_input.setToolTip("Max time to wait for PnL data to settle from the broker.")

        form_layout.addRow(QLabel("Host (IP):"), self.ibkr_host_input)
        form_layout.addRow(QLabel("Port:"), self.ibkr_port_input)
        form_layout.addRow(QLabel("Client ID:"), self.ibkr_client_id_input)
        form_layout.addRow(QLabel("Data Timeout:"), self.ibkr_timeout_input)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # ── CONTROLS ─────────────────────────────────────────
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
            
            self.mc_years_input.setValue(config.get("DEFAULT_YEARS", 5))
            self.mc_sims_input.setCurrentText(str(config.get("DEFAULT_SIMS", 10000)))

            self.jump_threshold_input.setValue(config.get("JUMP_THRESHOLD", 3.0))

            self.ibkr_host_input.setText(config.get("IBKR_HOST", "127.0.0.1"))
            self.ibkr_port_input.setValue(config.get("IBKR_PORT", 4001))
            self.ibkr_client_id_input.setValue(config.get("IBKR_CLIENT_ID", 1))
            self.ibkr_timeout_input.setValue(config.get("IBKR_TIMEOUT", 5.0))

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

        config["IBKR_HOST"] = self.ibkr_host_input.text().strip()
        config["IBKR_PORT"] = self.ibkr_port_input.value()
        config["IBKR_CLIENT_ID"] = self.ibkr_client_id_input.value()
        config["IBKR_TIMEOUT"] = self.ibkr_timeout_input.value()

        if write_json(PathManager.CONFIG_FILE, config):
            app_logger.info("User settings saved successfully.")
            QMessageBox.information(
                self, 
                "Restart Recommended", 
                "Settings saved successfully!\n\nPlease restart the application for all changes to take full effect."
            )
        else:
            app_logger.error("Could not save the config.json file from UI.")
            QMessageBox.critical(self, "Error", "Could not save the config.json file.")