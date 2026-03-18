# IBKR Portfolio Analyzer (Temporary Name)

Desktop application for risk analysis and financial portfolio simulation. It fetches data from the broker, calculates future projections using stochastic models, and provides intelligent feedback via AI. 
Built with a clean, Object-Oriented architecture separating UI components, asynchronous background tasks, and pure core business logic.

## MVP Features
* **Broker Integration:** Automatic download of positions, balances, currencies, and historical data from Interactive Brokers.
* **Risk Analysis:** Calculation of the covariance matrix and annualized portfolio volatility.
* **Monte Carlo Simulation:** Probabilistic forecasting based on Geometric Brownian Motion to calculate future scenarios (Worst 5%, Median 50%, Best 95%).
* **Data Visualization:** Interactive charts to display the simulation cone (Matplotlib).
* **AI Feedback:** Integration with the Gemini API for results analysis and portfolio insights.

## Project Structure
The codebase is organized following a strict separation of concerns, dividing the UI layers, background threads, and pure mathematical/API logic:

```text
├── main.py                   # App entry point 
├── main_window.py            # Main UI initialization (PySide6)
├── pages/                    # UI Components for individual screens (Dashboard, Simulation, etc.)
│   └── dashboard_page.py
├── workers/                  # Asynchronous task management and Qt Threads
│   └── ibkr_thread.py        # QThread acting as a bridge between the UI and the Core logic
├── core/                     # Pure core business logic (No GUI dependencies)
│   ├── portfolio.py          # PortfolioManager class (IBKR connection, state, risk metrics)
│   ├── montecarlo.py         # Mathematical simulation engine
│   ├── ai_review.py          # AI chat and feedback management
│   ├── graph.py              # Matplotlib visualization functions
│   └── utils.py              # Support functions (JSON parsing, etc.)
├── tests/                    # Pytest testing suite (Isolated Unit Tests)
├── config.json               # API Credentials (Gemini) / Risk Free Rate
├── app.spec                  # PyInstaller build setup
└── requirements.txt          # Python dependencies

## Tech Stack
- Core: Python
- Graphical Interface: PySide6 + QSS + MatplotLib
- Data & Math: Pandas, Numpy 
- Integrations: IBKR API (ib_async), Gemini API
- Testing: Pytest, unittest.mock
