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
import os
import sys
import json
import platform
from pathlib import Path
from core.logger import app_logger

def get_appdata_dir() -> Path:
    """Returns the user data folder path (AppData on Windows) for external files."""
    if platform.system() == "Windows":
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / "AlphaPaths"
    # Fallback for macOS/Linux
    return Path.home() / ".AlphaPaths"

class PathManager:
    """
    Centralized path manager for the IBKR Portfolio Analyzer.
    Automatically resolves absolute paths safely from any working directory,
    moving writable files to AppData when the app is bundled.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        BASE_DIR = Path(sys._MEIPASS) 
        EXTERNAL_DIR = get_appdata_dir()
        EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    else:
        BASE_DIR = Path(__file__).resolve().parent.parent
        EXTERNAL_DIR = BASE_DIR

    ASSETS_DIR: Path = BASE_DIR / "assets"
    CORE_DIR: Path = BASE_DIR / "core"
    PAGES_DIR: Path = BASE_DIR / "pages"
    WORKERS_DIR: Path = BASE_DIR / "workers"
    TESTS_DIR: Path = BASE_DIR / "tests"

    DATA_DIR: Path = EXTERNAL_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE: Path = Path(os.getenv("APP_CONFIG_FILE", EXTERNAL_DIR / "config.json"))
    PROMPTS_FILE: Path = Path(os.getenv("APP_PROMPTS_FILE", EXTERNAL_DIR / "prompts.json"))
    MANUAL_PORTFOLIO_FILE: Path = Path(os.getenv("APP_MANUAL_PORTFOLIO_FILE", EXTERNAL_DIR / "manual_portfolio.json"))
    STYLE_FILE: Path = Path(os.getenv("APP_STYLE_FILE", ASSETS_DIR / "style.qss"))
    ICON_FILE: str = str(Path(os.getenv("APP_ICON_FILE", ASSETS_DIR / "Icon.ico" )))
    THIRD_PARTY_NOTICES_FILE: str = str(Path(os.getenv("APP_THIRD_PARTY_NOTICES_FILE", BASE_DIR / "THIRDPARTY-NOTICES.txt")))

    @classmethod
    def get_asset(cls, filename: str) -> Path:
        """
        Returns the absolute path for a file inside the assets directory.
        """
        return cls.ASSETS_DIR / filename

    @classmethod
    def init_configs(cls):
        """
        Checks if configuration files exist in the external directory (AppData). 
        If they are missing, it creates them from scratch with default values.
        """
        if not cls.CONFIG_FILE.exists():
            default_config = {
                "GEMINI_API_KEY": "Your Gemini API Key Here",
                "GEMINI_MODEL": "gemini-3-flash-preview",
                "RISK_FREE_RATE": 0.02,
                "IBKR_HOST": "127.0.0.1",
                "IBKR_PORT": 4002,
                "IBKR_CLIENT_ID": 1,
                "AI_LANGUAGE": "English",
                "DEFAULT_YEARS": 5,
                "DEFAULT_SIMS": 10000,
                "IBKR_TIMEOUT": 5.0
            }
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            app_logger.info(f"Created default config at {cls.CONFIG_FILE}")

        if not cls.PROMPTS_FILE.exists():
            default_prompts = {
                "portfolio_analysis": {
                    "system_instruction": "You are an elite quantitative portfolio manager and financial advisor. Your goal is to analyze the provided portfolio data, identify concentration risks, evaluate the risk/reward profile, and provide actionable, asset-specific feedback. You must output the response STRICTLY as a valid JSON object. Do not include markdown formatting like ```json. Use clear, professional, yet accessible language.",
                    "user_prompt_template": "*** IMPORTANT: YOU MUST PROVIDE YOUR ENTIRE RESPONSE, INCLUDING THE JSON KEYS, IN THIS LANGUAGE: {language} ***\n\nPlease analyze the following portfolio and its 5-year Monte Carlo projections.\n\n--- PORTFOLIO METRICS ---\nBase Currency: {currency}\nTotal Value: {total_value}\nRisky Assets Weight: {risky_weight}%\nCash Buffer: {cash_weight}%\nHistorical Annualized Return (Mu): {mu}%\nAnnualized Volatility (Sigma): {sigma}%\n\n--- 5-YEAR MONTE CARLO PROJECTIONS ---\nWorst Case (5th percentile): {worst_case}\nMedian Case (50th percentile): {median_case}\nBest Case (95th percentile): {best_case}\n\n--- CURRENT HOLDINGS ---\nFormat: [Ticker, Quantity, Current Price, Total Market Value]\n{positions}\n\n--- REQUIRED JSON OUTPUT FORMAT ---\nYou must return a single JSON object containing exactly 4 sections. TRANSLATE the JSON keys into {language} using snake_case (e.g., if Italian, use 'sintesi_esecutiva', 'raccomandazioni_operative').\n\nThe JSON must strictly follow this structure type:\n{{\n  \"<translated_key_for_Executive_Summary>\": \"A short, 2-3 sentence overview of the portfolio's health and risk profile.\",\n  \"<translated_key_for_Holdings_Analysis>\": [\n    \"Provide 3-4 bullet points analyzing the specific tickers held. Infer their sectors, comment on concentration risk, lack of diversification, or specific asset vulnerabilities.\"\n  ],\n  \"<translated_key_for_Monte_Carlo_Interpretation>\": \"Explain what the 5-year projections mean for the user. Is the volatility dragging down the worst-case scenario too much? Is the expected return realistic based on the holdings?\",\n  \"<translated_key_for_Actionable_Recommendations>\": [\n    \"Provide 3-4 specific, actionable steps based on the specific assets held.\"\n  ]\n}}"
                }
            }
            with open(cls.PROMPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_prompts, f, indent=4)
            app_logger.info(f"Created default prompts at {cls.PROMPTS_FILE}")

        if not cls.MANUAL_PORTFOLIO_FILE.exists():
            default_manual_portfolio = {
                "base_currency": "EUR",
                "cash": 12500.00,
                "positions": [
                    {"ticker": "AAPL", "quantity": 15.5},
                    {"ticker": "MSFT", "quantity": 10},
                    {"ticker": "VWCE.DE", "quantity": 125},
                    {"ticker": "CSSPX.MI", "quantity": 30},
                    {"ticker": "BTC-USD", "quantity": 0.5}
                ]
            }
            try:
                with open(cls.MANUAL_PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_manual_portfolio, f, indent=4)
                app_logger.info(f"Created default manual portfolio at {cls.MANUAL_PORTFOLIO_FILE}")
            except Exception as e:
                app_logger.error(f"Failed to create manual portfolio file: {e}")