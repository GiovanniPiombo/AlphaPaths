from PySide6.QtCore import QThread, Signal
from core.ai_review import get_portfolio_analysis

class AIWorker(QThread):
    """
    A dedicated background thread for handling asynchronous Gemini API requests.

    This worker prevents the main PySide6 GUI from freezing while waiting for 
    the AI model to generate a response over the network. It receives the 
    portfolio metrics, calls the core AI review module, and safely emits the 
    parsed JSON results or error messages back to the main user interface.

    Signals:
        analysis_fetched (dict): Emitted upon successful generation of the AI report. 
            Contains the parsed JSON dictionary returned by Gemini.
        error_occurred (str): Emitted if the API request fails, times out, or 
            returns invalid JSON data. Contains the specific error message.

    Attributes:
        portfolio_data (dict): The portfolio metrics and simulation results 
            required to populate the AI prompt.
    """
    analysis_fetched = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, portfolio_data: dict):
        """
        Initializes the AI background worker.

        Args:
            portfolio_data (dict): A dictionary containing key metrics like 
                'total_value', 'mu', 'sigma', and percentile scenarios to be 
                analyzed by the AI.
        """
        super().__init__()
        self.portfolio_data = portfolio_data

    def run(self):
        """
        Executes the thread's primary workload.

        This method is automatically invoked when `worker.start()` is called 
        from the main thread. It delegates the network call to `get_portfolio_analysis`. 
        If the returned dictionary contains an explicit "error" key (gracefully 
        handled by the core module), it emits the `error_occurred` signal. 
        Otherwise, it emits the `analysis_fetched` signal with the successful 
        payload. It also acts as a final safety net, catching and emitting 
        any completely unhandled exceptions.
        """
        try:
            print("[DEBUG] AIWorker: Sending data to Gemini...")
            result = get_portfolio_analysis(self.portfolio_data)
            
            if "error" in result:
                self.error_occurred.emit(result["error"])
            else:
                self.analysis_fetched.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error during AI analysis: {str(e)}")