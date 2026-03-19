from PySide6.QtCore import QThread, Signal
from core.ai_review import get_portfolio_analysis

class AIWorker(QThread):
    """
    A lightweight QThread that manages communication with the Gemini API 
    via the core.ai_review module, preventing the UI from freezing.
    """
    analysis_fetched = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, portfolio_data: dict):
        super().__init__()
        self.portfolio_data = portfolio_data

    def run(self):
        """This method is called when the thread starts. It calls the get_portfolio_analysis function and emits the results or any errors."""
        try:
            print("[DEBUG] AIWorker: Sending data to Gemini...")
            result = get_portfolio_analysis(self.portfolio_data)
            
            if "error" in result:
                self.error_occurred.emit(result["error"])
            else:
                self.analysis_fetched.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error during AI analysis: {str(e)}")