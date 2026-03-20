from ib_async import *
import pandas as pd
import numpy as np
import asyncio
from core.montecarlo import MonteCarloSimulator
from core.ai_review import get_portfolio_analysis
from core.utils import read_json, format_json

class PortfolioManager:
    """
    Manages communication with IBKR, historical data fetching, 
    risk metrics calculation, and integration with AI and simulations.
    """
    TRADING_DAYS = 252

    def __init__(self, host='127.0.0.1', port=4001, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.fx_cache = {}

        # Portfolio state (populated in fetch_summary_and_positions)
        self.total_value = 0.0
        self.base_currency = ""
        self.cash_value_base = 0.0
        self.cash_weight = 0.0
        self.sum_risky_weights = 0.0
        self.risky_assets = []
        self.weights_dict = {}
        
        # Risk metrics (populated in calculate_risk_metrics)
        self.total_portfolio_mu = 0.0
        self.total_portfolio_vol = 0.0

    # ==========================================
    # CONNECTION AND UTILITIES
    # ==========================================
    async def connect(self) -> bool:
        await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
        return self.ib.isConnected()

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        if from_currency == to_currency:
            return 1.0
            
        pair = f"{from_currency}{to_currency}"
        if pair in self.fx_cache:
            return self.fx_cache[pair]
            
        contract = Forex(pair)
        bars = await self.ib.reqHistoricalDataAsync(
            contract, endDateTime='', durationStr='1 D',
            barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=False
        )
        
        if bars:
            rate = bars[-1].close
            self.fx_cache[pair] = rate
            return rate
        else:
            # Try the inverse pair
            inv_pair = f"{to_currency}{from_currency}"
            inv_contract = Forex(inv_pair)
            bars = await self.ib.reqHistoricalDataAsync(
                inv_contract, endDateTime='', durationStr='1 D',
                barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=False
            )
            if bars:
                rate = 1.0 / bars[-1].close
                self.fx_cache[pair] = rate
                return rate
                
        raise ValueError(f"Exchange rate not found for {pair}")

    @staticmethod
    def annualize(daily_variance: float, trading_days: int = 252) -> float:
        return daily_variance * trading_days

    @staticmethod
    def get_annual_volatility(annual_variance: float) -> float:
        return np.sqrt(annual_variance)

    # ==========================================
    # PHASE 1: CURRENT BALANCES AND POSITIONS
    # ==========================================
    async def fetch_summary_and_positions(self) -> dict:
        """--- 1 & 2. Fetch Base Currency, Total Value, Cash, P&L & Weights ---"""
        summary = await self.ib.accountSummaryAsync()
        
        account_id = ""
        for item in summary:
            # Grab the account ID dynamically (e.g., DU123456) for the PnL request
            if not account_id:
                account_id = item.account 
                
            if item.tag == "NetLiquidation":
                self.total_value = float(item.value)
                self.base_currency = item.currency
            elif item.tag == "TotalCashValue":
                self.cash_value_base = float(item.value)

        # --- Fetch Daily P&L with Settling Time ---
        daily_pnl = 0.0
        if account_id:
            pnl_sub = self.ib.reqPnL(account_id)
            
            timeout = float(read_json("config.json", "IBKR_TIMEOUT") or 5.0)
            elapsed = 0.0
            
            while elapsed < timeout:
                await asyncio.sleep(0.2)
                elapsed += 0.2
                
                # Check if we got the FIRST valid tick (e.g., the "3")
                if pnl_sub and pnl_sub.dailyPnL is not None and not np.isnan(pnl_sub.dailyPnL):
                    
                    # We got a number! Now, wait an extra 1.5 seconds to let the data "settle"
                    # This gives IBKR time to send the finalized calculation (the "30")
                    await asyncio.sleep(1.5)
                    
                    # Grab the most recent value after the dust has settled
                    daily_pnl = float(pnl_sub.dailyPnL)
                    print(f"[DEBUG] P&L successfully settled at: {daily_pnl}")
                    break
            
            if elapsed >= timeout and daily_pnl == 0.0:
                print("[WARNING] Timeout: Valid P&L not received within 5 seconds.")
                
            self.ib.cancelPnL(account_id) # Clean up the subscription

        # --- Fetch Portfolio Positions ---
        portfolio_items = self.ib.portfolio()
        self.weights_dict = {}
        self.risky_assets = []
        positions_for_ui = []

        for item in portfolio_items:
            if item.contract.secType == 'CASH':
                continue 
                
            self.risky_assets.append(item)
            symbol = item.contract.symbol
            
            # Fetch the FX rate to convert the asset's value to the base currency
            fx_rate = await self.get_fx_rate(item.contract.currency, self.base_currency)
            market_value_base = item.marketValue * fx_rate
            
            weight = (market_value_base / self.total_value) if self.total_value > 0 else 0
            self.weights_dict[symbol] = weight
            
            positions_for_ui.append([
                symbol, getattr(item, 'position', 0), 
                getattr(item, 'marketPrice', 0.0), market_value_base
            ])

        self.cash_weight = (self.cash_value_base / self.total_value) if self.total_value > 0 else 0
        self.sum_risky_weights = sum(self.weights_dict.values())

        return {
            "nlv": self.total_value,
            "cash": self.cash_value_base,
            "currency": self.base_currency,
            "pnl": daily_pnl,
            "positions": positions_for_ui,
            "risky_weight": self.sum_risky_weights * 100,
            "cash_weight": self.cash_weight * 100
        }
    # ==========================================
    # PHASE 2: HISTORICAL DATA AND MATH
    # ==========================================
    async def fetch_historical_data(self) -> pd.DataFrame:
        """--- 3 & 4. Download Historical Data (Total Return) & Cleansing ---"""
        all_prices = pd.DataFrame()
        
        for item in self.risky_assets:
            symbol = item.contract.symbol
            await self.ib.qualifyContractsAsync(item.contract)
            
            bars = await self.ib.reqHistoricalDataAsync(
                item.contract, endDateTime='', durationStr='5 Y',
                barSizeSetting='1 day', whatToShow='ADJUSTED_LAST', useRTH=True
            )
            
            if bars:
                df = util.df(bars)
                df['date'] = pd.to_datetime(df['date']).dt.normalize()
                df.set_index('date', inplace=True) 
                all_prices = all_prices.join(df['close'].rename(symbol), how='outer')
                
            await asyncio.sleep(1) # Pacing to respect IBKR API limits

        all_prices.ffill(inplace=True) 
        all_prices.dropna(inplace=True) 
        return all_prices

    def calculate_risk_metrics(self, all_prices: pd.DataFrame) -> tuple:
        """--- 5 & 6. Risk Metrics Calculation & Cash Buffer Integration ---"""
        valid_symbols = all_prices.columns.tolist()
        
        # Re-normalize weights (for risky assets only)
        normalized_risky_weights = np.array([
            self.weights_dict[sym] / self.sum_risky_weights for sym in valid_symbols
        ])
        
        all_returns = all_prices.pct_change().dropna()
        cov_matrix = all_returns.cov()
        
        port_variance = np.dot(normalized_risky_weights.T, np.dot(cov_matrix.values, normalized_risky_weights))
        annual_volatility = self.get_annual_volatility(self.annualize(port_variance, self.TRADING_DAYS))
        
        mean_daily_returns = all_returns.mean()
        daily_mu = np.dot(normalized_risky_weights, mean_daily_returns.values)
        annual_mu = daily_mu * self.TRADING_DAYS
        
        # Cash Buffer Integration
        risk_free_rate = read_json("config.json", "RISK_FREE_RATE")
        self.total_portfolio_mu = (annual_mu * self.sum_risky_weights) + (risk_free_rate * self.cash_weight) 
        self.total_portfolio_vol = annual_volatility * self.sum_risky_weights 
        
        return self.total_portfolio_mu, self.total_portfolio_vol

    # ==========================================
    # PHASE 3: SIMULATION AND AI
    # ==========================================
    def run_montecarlo_simulation(self, years: int = 5, simulations: int = 100000) -> tuple:
        """--- 7 & 8. Monte Carlo Execution & Visualization ---"""
        simulator = MonteCarloSimulator(
            capital=self.total_value, 
            mu=self.total_portfolio_mu, 
            sigma=self.total_portfolio_vol, 
            years=years, 
            simulations=simulations
        )
        simulated_prices = simulator.simulate()
        scenarios = simulator.get_scenarios(simulated_prices)
        
        # Visualization (can be disconnected when you use a Qt canvas)
        #plot_portfolio_montecarlo(simulated_prices)
        
        return scenarios, simulated_prices

    def get_ai_feedback(self, scenarios: dict) -> dict:
        """--- 9. AI Analysis ---"""
        portfolio_data = {
            "total_value": self.total_value,
            "currency": self.base_currency,
            "risky_weight": self.sum_risky_weights * 100,
            "cash_weight": self.cash_weight * 100,
            "mu": self.total_portfolio_mu * 100,
            "sigma": self.total_portfolio_vol * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"]
        }
        
        return get_portfolio_analysis(portfolio_data)