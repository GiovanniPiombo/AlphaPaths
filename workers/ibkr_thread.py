import asyncio
from PySide6.QtCore import QThread, Signal
from core.portfolio import PortfolioManager

class IBKRWorker(QThread):
    """A QThread that connects to the IBKR API, fetches the portfolio summary and positions, and returns the data in a dictionary format suitable for the UI. It also emits progress updates at each step."""
    data_fetched = Signal(dict)
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def run(self):
        """This method is called when the thread starts. It creates a new event loop and runs the asynchronous data fetching method."""
        print("\n[DEBUG] 1. THREAD STARTED: Creating event loop...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("[DEBUG] 2. THREAD: Starting fetch_data_from_manager...")
            data = loop.run_until_complete(self.fetch_data_from_manager())
            
            print("[DEBUG] 8. THREAD: Data successfully fetched, emitting signal...")
            self.data_fetched.emit(data)
        except Exception as e:
            print(f"\n[CRITICAL THREAD ERROR]: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()
            print("[DEBUG] THREAD FINISHED.\n")

    async def fetch_data_from_manager(self):
        """This method connects to the IBKR API, fetches the portfolio summary and positions, and returns the data in a dictionary format suitable for the UI. It also emits progress updates at each step."""
        manager = PortfolioManager(host='127.0.0.1', port=4002, client_id=1)
        
        self.progress_update.emit("Connecting to IBKR...")
        await manager.connect()
        print("[DEBUG] IBKR: Connected successfully!")
        
        try:
            self.progress_update.emit("Analyzing assets and converting currencies (FX)...")
            
            # Phase 1: Call the method that fetches balances and positions (Fast)
            portfolio_data = await manager.fetch_summary_and_positions()
            
            # --- FAST DATA RETURN FOR UI ---
            # We use dummy placeholders for risk metrics here to keep the Dashboard fast.
            # Downloading 5-year historical data for real mu and sigma will be delegated 
            # to the Simulation page.
            print("[DEBUG] IBKR: Returning formatted data for the UI...")
            
            portfolio_data["mu"] = 0.05    # Placeholder expected return (5%)
            portfolio_data["sigma"] = 0.15 # Placeholder volatility (15%)
            
            self.progress_update.emit("Operation completed successfully!")
            return portfolio_data

        finally:
            print("[DEBUG] IBKR: Disconnecting...")
            manager.disconnect()