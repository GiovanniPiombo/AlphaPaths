from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QMessageBox
from PySide6.QtCore import Qt
from workers.ai_thread import AIWorker
from core.logger import app_logger

class AIPage(QWidget):
    """
    User interface for requesting and displaying AI-generated portfolio insights.

    This page receives simulation data (metrics and scenarios) and uses an 
    `AIWorker` background thread to query the Gemini API. It handles state 
    management to prevent concurrent API calls and dynamically renders the 
    returned JSON data into a styled HTML format for the user.

    Attributes:
        portfolio_data (dict | None): Cached data containing simulation results 
            (e.g., mu, sigma, scenarios) required for the AI prompt.
        worker (AIWorker | None): The background thread managing the API request.
    """
    def __init__(self):
        """
        Initializes the AIPage and prepares the internal state.

        Sets the portfolio data cache and background worker to None before 
        invoking the UI construction.
        """
        super().__init__()
        # Cache for the data coming from the simulation (mu, sigma, scenarios, etc.)
        self.portfolio_data = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        """
        Constructs the user interface layout and components.

        Builds the header, the control bar containing the analysis trigger button, 
        and the primary `QTextBrowser` used to display the AI's report. 
        Applies specific inline CSS to the text browser to ensure it matches 
        the application's broader dark/Bloomberg-style theme.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        # ── HEADER ───────────────────────────────────────────
        header_label = QLabel("AI Portfolio Insights")
        header_label.setObjectName("page_header")
        main_layout.addWidget(header_label)

        # ── CONTROLS BAR ─────────────────────────────────────
        controls_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Generate AI Analysis")
        self.analyze_btn.setObjectName("primary_btn")
        self.analyze_btn.setMinimumHeight(38)
        self.analyze_btn.setMinimumWidth(180)
        self.analyze_btn.setToolTip("Requests a detailed portfolio analysis from Gemini")
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        self.analyze_btn.setEnabled(False)

        controls_layout.addWidget(self.analyze_btn)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # ── OUTPUT DISPLAY ───────────────────────────────────
        section_label = QLabel("ARTIFICIAL INTELLIGENCE REPORT")
        section_label.setObjectName("section_label")
        main_layout.addWidget(section_label)

        self.report_display = QTextBrowser()
        self.report_display.setOpenExternalLinks(True)
        self.report_display.setStyleSheet("""
            QTextBrowser {
                background-color: #111820;
                border: 1px solid #1E2733;
                border-radius: 6px;
                padding: 16px;
                color: #C8D0DC;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        
        # Default text
        self.report_display.setHtml(
            "<p style='color: #5A6878; font-style: italic;'>"
            "Run a Monte Carlo Simulation first to gather the necessary data, "
            "then click on 'Generate AI Analysis' to get the report."
            "</p>"
        )
        main_layout.addWidget(self.report_display)

    def set_portfolio_data(self, data: dict):
        """
        Populates the internal cache with new simulation data and triggers analysis.

        This is a public method typically called by the `MainWindow` immediately 
        after a Monte Carlo simulation concludes. It caches the data and 
        automatically initiates the AI request without requiring a manual user click.

        Args:
            data (dict): The portfolio metrics and simulation results.
        """
        self.portfolio_data = data
        self.on_analyze_clicked()

    def on_analyze_clicked(self):
        """
        Initiates the background AI analysis process.

        Performs safety checks to ensure portfolio data exists and that an 
        existing worker thread is not already running (preventing duplicate 
        API calls from rapid button clicks). Updates the UI to a loading state 
        and starts the `AIWorker`.
        """
        if not self.portfolio_data:
            QMessageBox.warning(self, "Missing Data", "There is no portfolio data to analyze.")
            return

        if self.worker is not None and self.worker.isRunning():
            app_logger.warning("AI analysis is already running. Skipping duplicate request.")
            return

        app_logger.info("Starting AIWorker for portfolio analysis...")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analysis in progress...")
        
        self.report_display.setHtml(
            "<p style='color: #F0A500; font-size: 15px; font-weight: bold;'>"
            "Connecting to AI. Generating insights...</p>"
        )

        # ── Start Background Worker ──────────────────────────
        self.worker = AIWorker(self.portfolio_data)
        self.worker.analysis_fetched.connect(self.on_analysis_complete)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_analysis_complete(self, result: dict):
        """
        Parses the AI's JSON response and renders it as styled HTML.

        Iterates through the structured dictionary returned by the Gemini API 
        and dynamically generates HTML headers, lists, and paragraphs based 
        on the data types (lists, dicts, strings). Updates the text browser 
        and restores the button state.

        Args:
            result (dict): The parsed JSON response containing the AI's 
                structured insights and recommendations.
        """
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Refresh AI Analysis")
        
        html_content = ""
        
        for key, value in result.items():
            formatted_key = key.replace("_", " ").title()
            
            if isinstance(value, list):
                html_content += f"<h3 style='color: #E8EDF5;'>{formatted_key}</h3><ul>"
                for item in value:
                    html_content += f"<li style='margin-bottom: 8px;'>{item}</li>"
                html_content += "</ul>"
            elif isinstance(value, dict):
                html_content += f"<h3 style='color: #E8EDF5;'>{formatted_key}</h3><ul style='list-style-type: none; padding-left: 0;'>"
                for sub_key, sub_val in value.items():
                    html_content += f"<li style='margin-bottom: 6px;'><b>{sub_key}:</b> {sub_val}</li>"
                html_content += "</ul>"
            else:
                html_content += f"<h3 style='color: #E8EDF5;'>{formatted_key}</h3><p>{value}</p>"

        self.report_display.setHtml(html_content)

    def on_error(self, error_msg):
        """
        Handles exceptions raised by the AI background worker.

        Restores the UI state (re-enabling the analysis button for retries), 
        displays the error inline within the text browser using error styling, 
        and opens a critical dialog box for the user.

        Args:
            error_msg (str): The details of the encountered error.
        """
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Retry Analysis")
        self.report_display.setHtml(f"<p style='color: #E05252;'><b>Error:</b> {error_msg}</p>")
        app_logger.error(f"AI Error UI Popup: {error_msg}")
        QMessageBox.critical(self, "AI Error", f"An error occurred:\n{error_msg}")