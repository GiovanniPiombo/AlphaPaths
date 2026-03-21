# IBKR Portfolio Analyzer

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green)]()
[![IBKR](https://img.shields.io/badge/IBKR-API-orange)]()
[![Tests](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Desktop application for advanced risk analysis and Monte Carlo simulation of financial portfolios. It connects directly to Interactive Brokers (IBKR) to fetch real positions, calculates future projections using stochastic models (Geometric Brownian Motion), and provides intelligent, conversational feedback via Google's Gemini AI.

Built with a clean, modular architecture that strictly separates the UI (PySide6), background threads (QThread), and pure business logic, ensuring a responsive user experience even during complex calculations.

## Preview

<p align="center">
  <img src="assets/app_demo.gif" alt="IBKR Portfolio Analyzer App Demo" width="800">
</p>

## Key Features

*   **Direct IBKR Integration:** Automatically downloads real portfolio data (Net Liquidation Value, Cash, Positions, Daily P&L) via the `ib_async` library. Supports multi-currency portfolios with automatic FX conversion.
*   **Monte Carlo Simulation:** Uses Geometric Brownian Motion to project thousands of possible future portfolio paths. Calculates key scenarios: Worst Case (5th percentile), Median (50th), and Best Case (95th).
*   **AI-Powered Insights:** Sends your portfolio composition and simulation results to Google's Gemini API, generating a structured, natural language report with personalized observations and suggestions.
*   **Optimized Performance:** Employs a multi-threaded architecture to keep the UI responsive. Uses a "FastMathWorker" to instantly recalculate simulations from cached risk metrics without re-fetching historical data.
*   **Professional UI:** Clean, dark-themed interface inspired by Bloomberg terminals, built with PySide6 and custom QSS styling.
*   **Interactive Visualizations:** Dynamic Qcharts embedded in the UI display the simulation cone, with background paths and clearly highlighted percentile lines. The simulation graph supports interactive features including zoom clamping, rubber-band selection, and mouse wheel zoom for detailed analysis of projection paths.

## Project Structure

The codebase is meticulously organized following the **Separation of Concerns** principle. This makes the application maintainable, testable, and scalable.

```text
.
├── .gitignore                    # gitignore
├── main.py                       # Application entry point. Initializes QApplication and MainWindow.
├── main_window.py                # Sets up the main window, the sidebar navigation, and the stacked widget for pages.
│
├── pages/                        # UI SCREENS: Each file represents a tab in the application.
│   ├── dashboard_page.py         # Displays portfolio summary (NLV, Cash, PnL) and open positions. Triggers IBKRWorker.
│   ├── simulation_page.py        # Monte Carlo controls (years, simulations). Displays results on a graph. Manages SimulationWorker and FastMathWorker.
│   ├── settings_page.py          # Settings Page
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
│   ├── path_manager.py           # Centralized path management for assets, configs, and prompts across the application.
│   └── utils.py                  # Shared utility functions (e.g., reading JSON files).
│
├── tests/                        # UNIT TESTS
│   ├── conftest.py               # Pytest configuration and fixtures
│   └── test_montecarlo.py        # Pytest suite for the MonteCarloSimulator, testing edge cases and statistical properties.
│
├── assets/                       # ASSETS
│   ├── Icon.ico                  # Application icon (Windows .ico format)
│   ├── Icon.png                  # Application icon (PNG format for cross-platform use)
│   ├── SetupIcon.ico             # Setup Icon 
│   └── style.qss                 # Qt Style Sheet for the application's dark theme.

├── components/                   # Components
│   └── chart_widget              # Montecarlo Simulation QChart
│
├── .github/                      # GITHUB ACTIONS
│   └── workflows/
│       └── tests.yml             # CI pipeline: Runs tests on Python 3.10, 3.11, 3.12
│
├── pytest.ini                    # Pytest configuration (asyncio_mode = auto)
├── config.json                   # Stores configuration like GEMINI_API_KEY, GEMINI_MODEL, and RISK_FREE_RATE.
├── prompts.json                  # Contains the system instructions and user prompt templates for the AI.
├── License                       # MIT License
├── build.spec                    # Pyinstaller spec file
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

You can install the application using the standalone Windows installer or set up the development environment to run and build it from the source code.

### Option 1: Windows Installer (Recommended for Users)

If you are on Windows and want a quick setup without dealing with Python environments, use the standalone installer.

1. Download the latest setup executable from the project's **Releases** page.
2. Run the installer and follow the on-screen instructions provided by Inno Setup.
3. Launch the application directly from your Start Menu or Desktop shortcut.

*Note: You will still need a running instance of IBKR Trader Workstation (TWS) or IB Gateway, and a Google AI Studio API key to configure the app after installation.*

### Option 2: Development & Building from Source

Follow these steps if you want to run the application directly from the source code, contribute to the development, or build the standalone executable yourself.

#### Prerequisites

- Python 3.9 or higher installed on your system.
- A running instance of IBKR Trader Workstation (TWS) or IB Gateway, configured to allow API connections
- A Google AI Studio API key for the Gemini features.
- (Optional) Inno Setup installed, if you intend to build the Windows installer.

#### 1. Running from Source

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer.git](https://github.com/GiovanniPiombo/ibkr-portfolio-analyzer.git)
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
   
   - Gemini API Key: Enter your Google AI Studio API key (required for AI Insights feature)
   - IBKR Connection: Verify host (default: 127.0.0.1), port (default: 4002), and client ID (default: 1)
   - Simulation Defaults: Adjust risk-free rate and other parameters as needed
     
5. **Run the application:**
   
   ```bash
   python main.py
   ```

#### 2. Build the Executable PyInstaller

The application can be packaged into a single executable file using PyInstaller, making it easy to distribute and run without a Python environment.

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
   - On Windows: dist/IBKR Portfolio Analyzer.exe
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
   - Gemini API Key: Enter your Google AI Studio API key (required for AI Insights feature)
   - IBKR Connection: Verify host (default: 127.0.0.1), port (default: 4002), and client ID (default: 1)
   - Simulation Defaults: Adjust risk-free rate and other parameters as needed
4. Save settings - The configuration is automatically saved to config.json in the executable's directory.
   
**Note**: The first-time user must supply their own Gemini API key. The application does not include any pre-configured keys

### How to use

* **Dashboard:** Upon starting, the app automatically connects to IBKR and fetches your portfolio data. Click the "Refresh IBKR Data" button to manually update.
* **Simulation:** Navigate to the "Simulation" tab. The first time you visit, it will automatically start a background preload (fetching historical data and calculating base risk metrics). Once preloaded, you can adjust the years and number of simulations and click "Run Simulation" for instant results.
* **AI Insights:** After running a simulation, go to the "AI Insights" tab. The AI analysis will trigger automatically, providing a detailed report on your portfolio's risk and potential.
* **Settings:** A dedicated interface that allows you to configure Gemini API keys, IBKR connection parameters (host, port, client ID), and simulation defaults without manually editing the JSON file.
  
## Running Tests

The core mathematical logic is thoroughly tested. To run the test suite:
```bash
   pytest tests/ -v
```


