import asyncio
from PySide6.QtCore import QThread, Signal
from core.portfolio import PortfolioManager
from core.utils import read_json

class IBKRWorker(QThread):
    """
    A dedicated background thread for managing asynchronous Interactive Brokers connections.

    This worker encapsulates the `asyncio` event loop required by the `ib_async` 
    library, ensuring the main PySide6 GUI remains responsive. It fetches 
    high-level portfolio metrics (Net Liquidation Value, P&L, open positions) 
    and pipes the data back to the main UI thread via standard Qt signals.

    Signals:
        data_fetched (dict): Emitted upon successful data retrieval. Contains 
            the formatted portfolio summary and positions.
        error_occurred (str): Emitted if the connection fails or an exception 
            is raised during the fetch process.
        progress_update (str): Emitted at various stages of the API call to 
            update loading states in the UI.
    """
    data_fetched = Signal(dict)
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def run(self):
        """
        Initializes the isolated asyncio event loop and executes the API payload.

        As a `QThread` subclass, this method is invoked automatically when 
        `self.start()` is called from the main UI thread. It manages the full 
        lifecycle of the async loop, runs the `fetch_data_from_manager` coroutine, 
        and acts as a global try/except block to ensure any API crashes are safely 
        emitted as error signals rather than taking down the entire application.
        """
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
        """
        Connects to the IBKR Gateway/TWS and retrieves the account state.

        Dynamically reads connection parameters (host, port, client ID) from 
        `config.json`. It delegates the actual network requests to the 
        `PortfolioManager`. To ensure the dashboard loads instantly, this method 
        deliberately bypasses the lengthy 5-year historical data download, 
        injecting dummy placeholders for drift (`mu`) and volatility (`sigma`). 
        Those metrics are fetched later on-demand by the simulation workers.

        Returns:
            dict: The compiled portfolio data dictionary ready for UI consumption.
        """
        host = read_json("config.json", "IBKR_HOST") or '127.0.0.1'
        port = read_json("config.json", "IBKR_PORT") or 4001
        client_id = read_json("config.json", "IBKR_CLIENT_ID") or 1

        manager = PortfolioManager(host=host, port=port, client_id=client_id)
        
        self.progress_update.emit(f"Connecting to IBKR ({host}:{port})...")
        await manager.connect()
        print("[DEBUG] IBKR: Connected successfully!")
        
        try:
            self.progress_update.emit("Analyzing assets and converting currencies (FX)...")
            
            portfolio_data = await manager.fetch_summary_and_positions()
            
            print("[DEBUG] IBKR: Returning formatted data for the UI...")
            
            portfolio_data["mu"] = 0.05
            portfolio_data["sigma"] = 0.15
            
            self.progress_update.emit("Operation completed successfully!")
            return portfolio_data

        finally:
            print("[DEBUG] IBKR: Disconnecting...")
            manager.disconnect()