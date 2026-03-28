from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Signal
from workers.ai_thread import AIWorker
from core.logger import app_logger

class AIInsightWidget(QWidget):
    """
    A reusable widget that handles the Gemini AI fetching and HTML rendering.
    Can be embedded into any page.
    """
    analysis_started = Signal()
    analysis_finished = Signal()
    analysis_failed = Signal(str)

    def __init__(self, default_text="Awaiting data..."):
        super().__init__()
        self.worker = None
        self.setup_ui(default_text)

    def setup_ui(self, default_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.display = QTextBrowser()
        self.display.setOpenExternalLinks(True)
        self.display.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #C8D0DC;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        self.display.setHtml(f"<p style='color: #8A99A8;'>{default_text}</p>")
        layout.addWidget(self.display)

    def start_analysis(self, data: dict):
        if self.worker is not None and self.worker.isRunning():
            app_logger.warning("AI analysis already running. Skipping duplicate request.")
            return

        self.analysis_started.emit()
        self.display.setHtml("<p style='color: #F0A500; font-weight: bold;'>Generating AI Insights...</p>")
        
        self.worker = AIWorker(data)
        self.worker.analysis_fetched.connect(self.on_complete)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_complete(self, result: dict):
        html_content = ""
        for key, value in result.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, list):
                html_content += f"<h4 style='color: #E8EDF5; margin-bottom: 4px;'>{formatted_key}</h4><ul style='margin-top: 0; padding-left: 20px;'>"
                for item in value: html_content += f"<li style='margin-bottom: 4px;'>{item}</li>"
                html_content += "</ul>"
            elif isinstance(value, dict):
                html_content += f"<h4 style='color: #E8EDF5; margin-bottom: 4px;'>{formatted_key}</h4><ul style='list-style-type: none; padding-left: 0; margin-top: 0;'>"
                for sub_key, sub_val in value.items(): html_content += f"<li style='margin-bottom: 4px;'><b>{sub_key}:</b> {sub_val}</li>"
                html_content += "</ul>"
            else:
                html_content += f"<h4 style='color: #E8EDF5; margin-bottom: 4px;'>{formatted_key}</h4><p style='margin-top: 0;'>{value}</p>"
        
        self.display.setHtml(html_content)
        self.analysis_finished.emit()

    def on_error(self, error_msg):
        self.display.setHtml(f"<p style='color: #E05252;'><b>AI Error:</b> {error_msg}</p>")
        self.analysis_failed.emit(error_msg)