# IBKR Portfolio Analyzer (Temporary Name)

Desktop application for risk analysis and financial portfolio simulation. It fetches data from the broker, calculates future projections using stochastic models, and provides intelligent feedback via AI.

## MVP Features
* **Broker Integration:** Automatic download of positions, currencies, and historical data from Interactive Brokers.
* **Risk Analysis:** Calculation of the covariance matrix and annualized portfolio volatility.
* **Monte Carlo Simulation:** Probabilistic forecasting based on Geometric Brownian Motion to calculate future scenarios (Worst 5%, Median 50%, Best 95%).
* **Data Visualization:** Interactive charts to display the simulation cone (PySide / Matplotlib) [TODO].
* **AI Feedback:** Integration with the Gemini API for results analysis and portfolio insights [TODO].

## Project Structure
The codebase will be organized into separate modules like this:

```
├── main.py                   # App entry point 
├── main_windows.py           # Main UI initialization
├── pages/                    # Modules for individual UI screens
├── core/                     # Core business logic
│   ├── portfolio.py          # IBKR connection and data fetching
│   ├── montecarlo.py         # Mathematical simulation engine
│   ├── ai_review.py          # AI chat and feedback management
│   └── config_api.py         # API keys reader from JSON
├── utils/                    # Utilities
│   └── paths.py              # Absolute/relative paths management
├── tests/                    # Testing suite
├── config.json               # API Credentials (Gemini)
├── app.spec                  # PyInstaller build setup
└── requirements.txt          # Python dependencies
```

## Tech Stack
- Core: Python
- Graphical Interface: PySide6 + QSS
- Data & Math: Pandas, Numpy 
- Integrations: IBKR API (ib_async), Gemini API
