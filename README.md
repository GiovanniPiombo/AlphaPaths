# AlphaPaths

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green)]()
[![Multi-Broker](https://img.shields.io/badge/Broker-IBKR%20%7C%20Alpaca%20%7C%20Crypto%20%7C%20Manual-orange)]()
[![Yahoo Finance](https://img.shields.io/badge/yfinance-Market%20Data-blueviolet)]()
[![Tests](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

AlphaPaths is a professional-grade desktop application for advanced risk analysis, Monte Carlo simulation, and portfolio optimization. It features a modular multi-broker architecture that supports direct connections to Interactive Brokers (IBKR), Alpaca, and major Crypto Exchanges (via CCXT), or a fully functional Manual Mode using Yahoo Finance—making it accessible to any investor, regardless of their brokerage.

The platform projects future portfolio values using stochastic models (Geometric Brownian Motion & Merton Jump-Diffusion), applies Modern Portfolio Theory (MPT) to generate efficient frontiers with Core-Satellite constraints, and provides intelligent conversational feedback via Google's Gemini AI.

## Preview

<p align="center">
  <img src="assets/app_demo.gif" alt="IBKR Portfolio Analyzer App Demo" width="800">
</p>

## Key Features

*   **Universal Broker Architecture:** Connect to your real account via Interactive Brokers, Alpaca (stocks & crypto), or any CCXT-compatible crypto exchange (Binance, Kraken, etc.). For those without a brokerage account, the Manual Broker reads a simple JSON file and fetches real-time prices and historical data from Yahoo Finance, with automatic FX conversion.
*   **Multi-Broker Settings:** A dedicated settings page allows you to manage credentials for all brokers and switch between them seamlessly without editing configuration files manually.
*   **Monte Carlo Simulation:** Uses Geometric Brownian Motion to project thousands of possible future portfolio paths. Calculates key scenarios: Worst Case (5th percentile), Median (50th), and Best Case (95th).
*   **Merton Jump-Diffusion Stress Testing:** Extends standard GBM by incorporating discrete price jumps (Poisson processes) to model sudden market crashes and extreme tail events, providing a more conservative risk assessment. Parameters are automatically calibrated from your portfolio's historical data using a configurable Jump Threshold.
*   **Core-Satellite Portfolio Optimization:** Applies Modern Portfolio Theory (MPT) to calculate the Efficient Frontier and Maximum Sharpe Ratio portfolio. The unique "Core-Satellite" feature allows you to "lock" strategic core assets (e.g., a broad-market ETF) at their current weight, forcing the optimizer to only reallocate the remaining "satellite" positions, perfect for maintaining long-term strategic allocations while tactically optimizing the rest.
*   **AI-Powered Insights:** Sends your portfolio composition and simulation results to Google's Gemini API, generating a structured, natural language report with personalized observations and suggestions. The prompt template is fully customizable and supports multiple languages.
*   **Optimized Performance:** Employs a multi-threaded architecture (QThread) to keep the UI responsive. Uses a FastMathWorker to instantly recalculate simulations from cached risk metrics without re-fetching historical data.
*   **Professional UI:** Clean, dark-themed interface, built with PySide6 and custom QSS styling.
*   **Interactive Visualizations:** Dynamic QCharts embedded in the UI display the simulation cone (with background paths and highlighted percentile lines) and the Efficient Frontier. The simulation graph supports zoom clamping, rubber-band selection, and mouse wheel zoom for detailed analysis of projection paths.

## Project Structure

The codebase is meticulously organized following the **Separation of Concerns** principle. This makes the application maintainable, testable, and scalable.

```text
.
├── .gitignore                       # gitignore
├── main.py                          # Application entry point. Initializes QApplication and MainWindow.
├── main_window.py                   # Sets up the main window, the sidebar navigation, and the stacked widget for pages.
│
├── pages/                           # UI SCREENS: Each file represents a tab in the application.
│   ├── dashboard_page.py            # Displays portfolio summary (NLV, Cash, PnL) and open positions. Triggers IBKRWorker.
│   ├── simulation_page.py           # Monte Carlo controls (years, simulations). Displays results and AI's feedback. Manages SimulationWorker and FastMathWorker.
│   ├── settings_page.py             # Settings Page
│   └── optimization_page.py         # Portfolio optimization interface. Displays Efficient Frontier and actionable trade recommendations.
│
├── workers/                         # BACKGROUND THREADS: Bridge between the UI and the Core logic.
│   ├── data_sync_thread.py          # DataSyncWorker: Fetches live portfolio data via the active broker.
│   ├── simulation_thread.py         # SimulationWorker & FastMathWorker: Handle full simulation setup.
│   ├── optimization_thread.py       # OptimizationWorker: Runs Markowitz optimization.
│   └── ai_thread.py                 # AIWorker: Manages communication with the Gemini API.
│
├── core/                            # PURE BUSINESS LOGIC: No Qt dependencies. Can be tested independently.
│   ├── brokers/                     # BROKER ADAPTERS: Multi-broker architecture via Factory Pattern.
│   │   ├── factory.py               # BrokerFactory: Instantiates the correct broker dynamically.
│   │   ├── base_broker.py           # BaseBroker: Abstract interface for all broker adapters.
│   │   ├── ibkr_broker.py           # IBKRBroker: Adapter for Interactive Brokers API.
│   │   ├── alpaca_broker.py         # Alpaca API (stocks & crypto via fallback) implementation.
│   │   ├── crypto_broker.py         # Generic crypto exchange (CCXT) implementation.
│   │   └── manual_broker.py         # ManualBroker: Adapter for Yahoo Finance & local JSON.
│   ├── portfolio.py                 # PortfolioManager: The brain of the app. Agnostic to the specific broker.
│   ├── gbm_model.py                 # GBMSimulator: The mathematical engine. Runs vectorized GBM simulations using NumPy.
│   ├── merton_model.py              # MJDSimulator: The mathematical engine. Runs vectorized MJD simulations using NumPy.
│   ├── ai_review.py                 # Handles prompting and communication with the Google Gemini API.
│   ├── graph.py                     # Standalone plotting functions (used for debugging, as the UI uses its own canvas).
│   ├── path_manager.py              # Centralized path management for assets, configs, and prompts across the application.
│   ├── markowitz_model.py           # MarkowitzOptimizer: Implements Modern Portfolio Theory for efficient frontier and Sharpe maximization.
│   └── utils.py                     # Shared utility functions (e.g., reading JSON files).
│
├── tests/                           # UNIT TESTS
│   ├── conftest.py                  # Pytest configuration and fixtures
│   ├── test_gbm.py                  # Pytest suite for the GBMSimulator, testing edge cases and statistical properties.
│   └── test_merton_model.py         # Pytest suite for the MJDSimulator, testing edge cases and statistical properties.
│
├── assets/                          # ASSETS
│   ├── Icon.ico                     # Application icon (Windows .ico format)
│   ├── Icon.png                     # Application icon (PNG format for cross-platform use)
│   ├── SetupIcon.ico                # Setup Icon 
│   └── style.qss                    # Qt Style Sheet for the application's dark theme.
│
├── components/                      # Components
│   ├── chart_widget                 # Montecarlo Simulation QChart
│   ├── markowitz_chart.py           # MarkowitzChartView: Custom QChartView for Efficient Frontier rendering.
│   └── ai_widget.py                 # AIInsightWidget: Reusable component for displaying AI analysis.
│
├── .github/                         # GITHUB ACTIONS
│   └── workflows/
│       └── tests.yml                # CI pipeline: Runs tests on Python 3.10, 3.11, 3.12
│
├── pytest.ini                       # Pytest configuration (asyncio_mode = auto)
├── config.template.json             # Template for app configuration (API keys, settings). Rename to config.json.
├── manual_portfolio.template.json   # Template for the Manual Broker (Yahoo Finance). Rename to manual_portfolio.json.
├── prompts.json                     # Contains the system instructions and user prompt templates for the AI.
├── LICENSE                          # GPLv3 License
├── THIRDPARTY-NOTICES.txt           # Open-source licenses for third-party libraries
├── build.spec                       # Pyinstaller spec file
└── requirements.txt                 # Python package dependencies.
```

## Technology Stack

- Core Language: Python 3.9+
- GUI Framework: PySide6 (Qt for Python)
- Data & Math: Pandas, NumPy, SciPy
- Visualization: Qt Charts (PySide6)
- Broker Integration:
  - Interactive Brokers: ib_async
  - Alpaca: alpaca-py
  - Crypto Exchanges: ccxt
- Market Data (Manual Mode): Yahoo Finance (yfinance)
- Artificial Intelligence: Google Gemini API (google-generativeai)
- Testing: Pytest

## Installation and Setup

You can install the application using the standalone Windows installer or set up the development environment to run and build it from the source code.

### Option 1: Windows Installer (Recommended for Users)

If you are on Windows and want a quick setup without dealing with Python environments, use the standalone installer.

1. Download the latest setup executable from the project's **Releases** page.
2. Run the installer and follow the on-screen instructions provided by Inno Setup.
3. Launch the application directly from your Start Menu or Desktop shortcut.

*Note: You will need an API key for your chosen broker(s) and a Google AI Studio API key to configure the app after installation.*

### Option 2: Development & Building from Source

Follow these steps if you want to run the application directly from the source code, contribute to the development, or build the standalone executable yourself.

#### Prerequisites

- Python 3.9 or higher installed on your system.
- A Google AI Studio API key for the Gemini features.
- Credentials for your preferred broker(s) (IBKR, Alpaca, Crypto Exchange) if you intend to use them.

#### 1. Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/GiovanniPiombo/AlphaPaths.git
   cd AlphaPaths
   ```
   
2. **Create and activate a virtual environment (recommended):**

   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate

   # On macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the required dependencies:**
   
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Configure the application:**
   
   Edit config.json (or use the Settings page in the app) to configure:
   - **Gemini API Key:** Your Google AI Studio API key (required for AI Insights).
   - **Active Broker:** Select from "Interactive Brokers", "Alpaca", "Crypto Exchange", or "Manual (Yahoo Finance)".
   - **Broker Credentials:** Enter the specific API keys and settings for your chosen broker.
   - **Simulation Defaults:** Adjust risk-free rate, lookback period, jump threshold, etc.

   Edit manual_portfolio.json (if using Manual Broker) to define your holdings using Yahoo Finance tickers.
     
5. **Run the application:**
   
   ```bash
   python main.py
   ```

#### 2. Build the Executable PyInstaller

The application can be packaged into a standalone directory containing the executable using PyInstaller. This ensures compliance with PySide6's LGPLv3 dynamic linking requirements while making it easy to distribute and run without a Python environment.

##### Prerequisites

- PyInstaller installed (`pip install pyinstaller`)

##### Build Instructions

1. **Ensure all dependencies are installed:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run PyInstaller with the provided spec file:**

   ```bash
   pyinstaller build.spec --clean
   ```

3. **Locate the executable:**
   
   - The built executable will be in the dist/ folder.
   - On Windows: dist/AlphaPaths.exe
   - The build includes application icons (Icon.ico, Icon.png, IconSetup.ico) embedded in the executable and used for the window icon.
     
##### What the Build Includes

- All Python dependencies bundled with the executable
- Application assets (icons, stylesheets) embedded via the spec file
- Configuration files (config.json, prompts.json) - these must be present in the same directory as the executable at runtime
- Optimized build with --clean flag to ensure a fresh compilation

#### Post-Build Configuration

**Important**: After building the executable, you must configure the application settings:
1. Launch the executable - The application will start with default placeholder values.
2. Navigate to the Settings page - Access the dedicated settings interface
3. Configure required parameters:
   - **Gemini API Key:** Your Google AI Studio API key (required for AI Insights).
   - **Active Broker:** Select from "Interactive Brokers", "Alpaca", "Crypto Exchange", or "Manual (Yahoo Finance)".
   - **Broker Credentials:** Enter the specific API keys and settings for your chosen broker.
   - **Simulation Defaults:** Adjust risk-free rate, lookback period, jump threshold, etc.
4. Save settings - The configuration is automatically saved to config.json in the executable's directory.
   
**Note**: The first-time user must supply their own Gemini API key. The application does not include any pre-configured keys

### How to use

#### Choosing your Broker
Navigate to the Settings tab. Select your preferred broker from the "Active Broker" dropdown and fill in the required credentials for that specific connection. The app will use this selection for all subsequent data fetches.
- Interactive Brokers: Requires a running instance of TWS or IB Gateway. Configure the host, port, and client ID.
- Alpaca: Enter your API and Secret keys. Check "Paper Trading" for testnet mode.
- Crypto Exchange: Enter the CCXT exchange ID (e.g., binance, kraken), your API key, and secret. The app will automatically handle asset classification (cash vs. risky) and cross-pair price resolution.
- Manual (Yahoo Finance): Define your portfolio in manual_portfolio.json. The app will fetch real-time prices and historical data directly from Yahoo Finance and perform automatic FX conversions.

#### Interface Navigation
- **Dashboard:** Upon starting, the app automatically connects to the active broker and fetches your portfolio data. Click "Refresh Data" to manually update.
- **Simulation:** Navigate to the "Monte Carlo" tab. After the initial preload, adjust the years and number of simulations (using the intuitive sliders) and select the model type (Standard GBM or Merton Stress Test). Click "Run Simulation" to instantly see new projections.
- **Optimization:** After loading portfolio data, go to the "Optimization" tab. Lock any assets you wish to keep as your core strategic holdings by checking the box in the table. Click "Run Optimization" to calculate the constrained Efficient Frontier and the optimal Max Sharpe portfolio. The page will display the improvement in Sharpe ratio and a detailed action table with Buy/Sell/Hold recommendations for each asset.
- **AI Insights:** The AI analysis is displayed directly on the Simulation page. It automatically triggers after each simulation run, providing a detailed report on your portfolio's risk and potential in your preferred language.

## Core-Satellite Optimization

The optimization module implements a **Core-Satellite** investment strategy:

- **Core Assets (Locked):** When you check the "Lock" checkbox next to an asset in the optimization table, its current portfolio weight is frozen. The optimizer treats these assets as untouchable strategic holdings (e.g., a broad-market ETF that defines your baseline allocation).
- **Satellite Assets (Optimized):** All unlocked assets are free to be reallocated by the Markowitz optimizer. The mathematical engine (SLSQP) redistributes the remaining portfolio weight among these satellite positions to maximize the Sharpe Ratio while respecting the locked core weights.

This approach allows you to maintain your long-term strategic allocations while tactically optimizing the tactical or speculative portion of your portfolio.

## Simulation Models: GBM vs. Merton

The application offers two distinct Monte Carlo simulation models:

| Model | Description | Best Used For |
|-------|-------------|---------------|
| **Standard GBM** (Geometric Brownian Motion) | Assumes continuous, normally distributed price movements with constant drift and volatility. | Standard market conditions, baseline projections, and when you expect relatively stable markets. |
| **Merton Stress Test** (Jump-Diffusion) | Extends GBM by adding discrete price jumps (Poisson process) to model sudden, discontinuous events like market crashes or flash crashes. | Stress testing, bear market scenarios, and when you want a more conservative risk assessment that accounts for tail risk. |

The Merton model parameters (`λ` for jump frequency, `m` for average jump size, `ν` for jump volatility) are automatically calibrated from your portfolio's historical data using the configurable **Jump Threshold** setting in the Settings page.

## Running Tests

The core mathematical logic is thoroughly tested. To run the test suite:
```bash
   pytest tests/ -v
```

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on our code of conduct and the process for submitting pull requests, including mandatory CLA agreement for our dual-licensing model.

## Disclaimer

**AlphaPaths is NOT financial advice.** This software is provided for educational and analytical purposes only. Quantitative models, Monte Carlo simulations, and portfolio optimizations are based on historical data and mathematical assumptions that do not guarantee future results. Investing in financial markets involves significant risk of loss. Always consult with a qualified financial advisor before making any investment decisions. The author is not responsible for any financial losses incurred through the use of this software.

## License & Commercial Use

**Copyright © 2026 Giovanni Piombo Nicoli**

AlphaPaths is strictly distributed under the **GNU General Public License v3.0 (GPLv3)**. 

This means you are free to use, modify, and distribute this software for personal, academic, or open-source projects, provided that any derivative works are also open-sourced under the exact same GPLv3 license.

### Dual Licensing (Commercial Use)
If you represent a company, hedge fund, or software house and wish to use, integrate, or distribute AlphaPaths (or its internal quantitative models) within a **closed-source or proprietary software/service**, the GPLv3 license does not permit this. 

To use AlphaPaths commercially without the obligation to open-source your proprietary code, you must obtain a separate **Commercial License**. 

Please contact me to discuss commercial licensing options and B2B integrations.

---
*Note: This software uses PySide6, which is licensed under the LGPLv3. For a full list of third-party libraries and their respective licenses, please refer to the [THIRDPARTY-NOTICES.txt](THIRDPARTY-NOTICES.txt) file included in this repository.*