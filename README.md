# IBKR Portfolio Analyzer

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green)]()
[![IBKR](https://img.shields.io/badge/IBKR-API-orange)]()
[![Tests](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Desktop application for advanced risk analysis and Monte Carlo simulation of financial portfolios. It connects directly to Interactive Brokers (IBKR) to fetch real positions, calculates future projections using stochastic models (Geometric Brownian Motion), and provides intelligent, conversational feedback via Google's Gemini AI.

Built with a clean, modular architecture that strictly separates the UI (PySide6), background threads (QThread), and pure business logic, ensuring a responsive user experience even during complex calculations.

## Key Features

*   **Direct IBKR Integration:** Automatically downloads real portfolio data (Net Liquidation Value, Cash, Positions, Daily P&L) via the `ib_async` library. Supports multi-currency portfolios with automatic FX conversion.
*   **Monte Carlo Simulation:** Uses Geometric Brownian Motion to project thousands of possible future portfolio paths. Calculates key scenarios: Worst Case (5th percentile), Median (50th), and Best Case (95th).
*   **Interactive Visualizations:** Dynamic Matplotlib charts embedded in the UI display the simulation cone, with background paths and clearly highlighted percentile lines.
*   **AI-Powered Insights:** Sends your portfolio composition and simulation results to Google's Gemini API, generating a structured, natural language report with personalized observations and suggestions.
*   **Optimized Performance:** Employs a multi-threaded architecture to keep the UI responsive. Uses a "FastMathWorker" to instantly recalculate simulations from cached risk metrics without re-fetching historical data.
*   **Professional UI:** Clean, dark-themed interface inspired by Bloomberg terminals, built with PySide6 and custom QSS styling.

## Project Structure

The codebase is meticulously organized following the **Separation of Concerns** principle. This makes the application maintainable, testable, and scalable.

```text
.
├── main.py                       # Application entry point. Initializes QApplication and MainWindow.
├── main_window.py                # Sets up the main window, the sidebar navigation, and the stacked widget for pages.
│
├── pages/                        # UI SCREENS: Each file represents a tab in the application.
│   ├── dashboard_page.py         # Displays portfolio summary (NLV, Cash, PnL) and open positions. Triggers IBKRWorker.
│   ├── simulation_page.py        # Monte Carlo controls (years, simulations). Displays results on a graph. Manages SimulationWorker and FastMathWorker.
│   └── ai_page.py                # Displays the AI-generated report. Triggers AIWorker.
│
├── workers/                      # BACKGROUND THREADS: Bridge between the UI and the Core logic.
│   ├── ibkr_thread.py            # IBKRWorker: Fetches live portfolio data without freezing the UI.
│   ├── simulation_thread.py      # SimulationWorker & FastMathWorker: Handle full simulation setup and fast recalculations.
│   └── ai_thread.py              # AIWorker: Manages communication with the Gemini API.
│
├── core/                         # PURE BUSINESS LOGIC: No Qt dependencies. Can be tested independently.
│   ├── portfolio.py              # PortfolioManager: The brain of the app. Manages IBKR connection, fetches data, calculates risk metrics (mu, sigma), and integrates all core functions.
│   ├── montecarlo.py             # MonteCarloSimulator: The mathematical engine. Runs vectorized GBM simulations using NumPy.
│   ├── ai_review.py              # Handles prompting and communication with the Google Gemini API.
│   ├── graph.py                  # Standalone plotting functions (used for debugging, as the UI uses its own canvas).
│   └── utils.py                  # Shared utility functions (e.g., reading JSON files).
│
├── tests/                        # UNIT TESTS
│   ├── conftest.py               # Pytest configuration and fixtures
│   └── test_montecarlo.py        # Pytest suite for the MonteCarloSimulator, testing edge cases and statistical properties.
│
├── assets/                       # ASSETS
│   └── style.qss                 # Qt Style Sheet for the application's dark theme.
│
├── .github/                      # GITHUB ACTIONS
│   └── workflows/
│       └── tests.yml             # CI pipeline: Runs tests on Python 3.10, 3.11, 3.12
│
├── pytest.ini                    # Pytest configuration (asyncio_mode = auto)
├── config.json                   # Stores configuration like GEMINI_API_KEY, GEMINI_MODEL, and RISK_FREE_RATE.
├── prompts.json                  # Contains the system instructions and user prompt templates for the AI.
└── requirements.txt              # Python package dependencies.
```

## Technology Stack

- Core Language: Python 3.9+
- GUI Framework: PySide6 (Qt for Python)
- Data & Math: Pandas, NumPy
- Visualization: Matplotlib
- Broker Integration: IBKR API (ib_async)
- Artificial Intelligence: Google Gemini API (google-generativeai)
- Testing: Pytest

## Installation and Setup

Follow these steps to get the application running on your local machine.

### Prerequisites

- Python 3.9 or higher installed on your system.
- A running instance of IBKR Trader Workstation (TWS) or IB Gateway, configured to allow API connections on port 4002 (or your preferred port).
- A Google AI Studio API key for the Gemini features.

### Step-by-Step Guide

1. **Clone the repository:**

   ```bash
   git clone https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer.git
   cd ibkr-portfolio-analyzer
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
   
   - Rename `config.example.json` to `config.json` (if an example file is provided, otherwise create it).
   - Edit `config.json` and add your `GEMINI_API_KEY`. You can also adjust the `GEMINI_MODEL` and `RISK_FREE_RATE`.
   - Ensure the `host` and `port` in `workers/ibkr_thread.py` and `workers/simulation_thread.py` match your TWS/IB Gateway settings (default is `4002`).
   - (Optional) Review and customize the prompts in `prompts.json` to change the AI's behavior.
     
5. **Run the application:**
   
   ```bash
   python main.py
   ```
## How to use

* **Dashboard:** Upon starting, the app automatically connects to IBKR and fetches your portfolio data. Click the "Refresh IBKR Data" button to manually update.
* **Simulation:** Navigate to the "Simulation" tab. The first time you visit, it will automatically start a background preload (fetching historical data and calculating base risk metrics). Once preloaded, you can adjust the years and number of simulations and click "Run Simulation" for instant results.
* **AI Insights:** After running a simulation, go to the "AI Insights" tab. The AI analysis will trigger automatically, providing a detailed report on your portfolio's risk and potential.
  
## Running Tests

The core mathematical logic is thoroughly tested. To run the test suite:
```bash
   pytest tests/ -v
```
