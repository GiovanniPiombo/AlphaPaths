from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QComboBox, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal
from workers.simulation_thread import SimulationWorker, FastMathWorker
from core.utils import read_json
from components.chart_widget import MonteCarloChartView
from core.path_manager import PathManager

class SimulationPage(QWidget):
    """
    A page component that performs and visualizes Monte Carlo simulations.

    Signals:
        simulation_finished (dict): Emitted when a simulation concludes. 
            Contains 'total_value', 'mu', 'sigma', and percentile results.

    Attributes:
        cached_mu (float): The mean return calculated from historical data.
        cached_sigma (float): The volatility calculated from historical data.
        cached_capital (float): The initial investment amount to simulate.
    """
    simulation_finished = Signal(dict)
    def __init__(self):
        """
        Initializes the simulation page and prepares the internal cache.
        
        Sets the cache variables to None before they are populated by the 
        background thread, preventing accidental calculations without 
        valid historical data.
        """
        super().__init__()
        
        # ── CACHE VARIABLES FOR OPTIMIZATION ─────────────────
        self.cached_mu = None
        self.cached_sigma = None
        self.cached_capital = None
        
        self.setup_ui()

    def setup_ui(self):
        """
        Constructs the layout, control bar, summary cards, and chart view.
        
        Configures user inputs for simulation duration (years) and 
        iteration count, while setting up the dynamic summary cards 
        for Worst, Median, and Best case scenarios.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 24, 28, 24)

        # ── HEADER ───────────────────────────────────────────
        header_label = QLabel("Monte Carlo Simulation")
        header_label.setObjectName("page_header")
        main_layout.addWidget(header_label)

        # ── CONTROLS BAR ─────────────────────────────────────
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # ── Years Selector ───────────────────────────────────
        lbl_years = QLabel("Years:")
        self.spin_years = QSpinBox()
        self.spin_years.setRange(1, 30)
        self.spin_years.setValue(read_json(PathManager.CONFIG_FILE, "DEFAULT_YEARS") or 5)
        
        # ── Simulations Selector ─────────────────────────────
        lbl_sims = QLabel("Simulations:")
        self.combo_sims = QComboBox()
        self.combo_sims.addItems(["1000", "10000", "50000", "100000"])
        default_sims = str(read_json(PathManager.CONFIG_FILE, "DEFAULT_SIMS") or "10000")
        self.combo_sims.setCurrentText(default_sims)

        # ── Run Button ───────────────────────────────────────
        self.run_btn = QPushButton("Run Simulation")
        self.run_btn.setObjectName("primary_btn")
        self.run_btn.setMinimumHeight(38)
        self.run_btn.clicked.connect(self.on_run_clicked)

        # ── Control Layout ───────────────────────────────────
        controls_layout.addWidget(lbl_years)
        controls_layout.addWidget(self.spin_years)
        controls_layout.addWidget(lbl_sims)
        controls_layout.addWidget(self.combo_sims)
        controls_layout.addStretch()
        controls_layout.addWidget(self.run_btn)
        
        main_layout.addLayout(controls_layout)

        # ── SUMMARY CARDS ────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        worst_card, self.worst_label = self.create_summary_card("WORST CASE (5%)", "€ 0.00", "#E05252")
        median_card, self.median_label = self.create_summary_card("MEDIAN CASE (50%)", "€ 0.00", "#E8EDF5")
        best_card, self.best_label = self.create_summary_card("BEST CASE (95%)", "€ 0.00", "#2ECC8A")

        cards_layout.addWidget(worst_card)
        cards_layout.addWidget(median_card)
        cards_layout.addWidget(best_card)
        
        main_layout.addLayout(cards_layout)

        # ── INITIALIZE THE SEPARATED CHART WIDGET ────────────────
        self.chart_view = MonteCarloChartView(self)
        self.chart_view.setMinimumHeight(400) 
        main_layout.addWidget(self.chart_view)

    def create_summary_card(self, title: str, initial_value: str, color: str):
        """
        Helper function to create summary cards.

        Args:
            title (str): The card's header.
            initial_value (str): The starting value to display.
            color (str): The hex color code for the value text.

        Returns:
            tuple: A tuple containing (card_widget, value_label) where:
                - card_widget (QFrame): The visual container of the card.
                - value_label (QLabel): The updatable label holding the results.
        """
        card = QFrame()
        card.setObjectName("summary_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("card_title")

        value_label = QLabel(initial_value)
        value_label.setObjectName("card_value")
        value_label.setStyleSheet(
            f"color: {color};"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 24px; font-weight: 700; letter-spacing: -0.5px;"
        )

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def start_background_preload(self):
        """
        Starts the data loading and the initial background simulation.

        This is typically triggered automatically when the Dashboard finishes 
        loading, using a `SimulationWorker` to prevent freezing the UI 
        during the initial fetch of historical data.
        """
        if not self.run_btn.isEnabled():
            return
            
        print("[UI DEBUG] Starting background Monte Carlo preload...")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Preloading in background...")
        
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        self.worker = SimulationWorker(years, simulations)
        
        self.worker.progress_update.connect(lambda msg: self.run_btn.setText(f"Background: {msg}"))
        self.worker.data_fetched.connect(self.on_simulation_complete)
        self.worker.error_occurred.connect(self.on_simulation_error)
        
        self.worker.start()

    def on_simulation_complete(self, scenarios, mu, sigma, capital, time_steps, worst_line, median_line, best_line, background_lines):
        """
        Callback executed upon successful completion of the SimulationWorker.

        Saves the fundamental parameters to the class cache, updates the 
        monetary values in the summary cards, and passes the paths to the 
        chart. Finally, it emits the `simulation_finished` signal.

        Args:
            scenarios (dict): Dictionary with the calculated percentile results.
            mu (float): Annualized mean return (drift).
            sigma (float): Annualized volatility.
            capital (float): Initial capital value.
            time_steps (np.ndarray): X-axis for the chart (months or years).
            worst_line (np.ndarray): 5th percentile path.
            median_line (np.ndarray): 50th percentile path.
            best_line (np.ndarray): 95th percentile path.
            background_lines (list): Sample of individual paths for the background.
        """
        # ── Store Metrics ────────────────────────────────────────
        self.cached_mu = mu
        self.cached_sigma = sigma
        self.cached_capital = capital
        
        # ── Update Summary Cards ─────────────────────────────────
        cur = "€"
        self.worst_label.setText(f"{cur} {scenarios['Worst (5%)']:,.2f}")
        self.median_label.setText(f"{cur} {scenarios['Median (50%)']:,.2f}")
        self.best_label.setText(f"{cur} {scenarios['Best (95%)']:,.2f}")
        
        # ── Pass the pre-calculated lines to the graph ───────────
        self.chart_view.update_graph(time_steps, worst_line, median_line, best_line, background_lines)
        
        # ── Reset the button ─────────────────────────────────────
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")

        sim_data = {
            "total_value": capital,
            "mu": mu * 100,
            "sigma": sigma * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"]
        }
        self.simulation_finished.emit(sim_data)

    def on_simulation_error(self, error_msg):
        """
        Handles exceptions raised by the background threads.

        Re-enables the UI controls and displays a critical dialog 
        box to the user with the error details.

        Args:
            error_msg (str): The error message returned by the worker.
        """
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")
        QMessageBox.critical(self, "Simulation Error", f"An error occurred:\n{error_msg}")

    def on_run_clicked(self):
        """
        Handles the click event on the "Run Simulation" button.

        Checks that the base data is already cached; if present, it starts 
        a `FastMathWorker` to execute new simulations based on the user's 
        chosen parameters (years and iterations) without re-downloading 
        the financial data.
        """
        if self.cached_capital is None:
            self.run_btn.setText("Still downloading background data...")
            return
            
        # ── UI Updates ───────────────────────────────────────────
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Calculating scenarios...")
        
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        print(f"[UI DEBUG] Starting FastMathWorker: {years}Y, {simulations} sims...")
        
        # ── Launch the thread ────────────────────────────────────
        self.fast_worker = FastMathWorker(
            capital=self.cached_capital,
            mu=self.cached_mu,
            sigma=self.cached_sigma,
            years=years,
            simulations=simulations
        )
        
        # ── Connect the signals ──────────────────────────────────
        self.fast_worker.data_calculated.connect(self.on_fast_math_complete)
        self.fast_worker.error_occurred.connect(self.on_simulation_error)
        
        self.fast_worker.start()

    def on_fast_math_complete(self, scenarios, time_steps, worst_line, median_line, best_line, background_lines):
        """
        Callback executed upon completion of the FastMathWorker calculations.

        Updates the UI with the newly calculated scenarios and updates the chart
        using the `mu`, `sigma`, and `capital` parameters already in the cache.
        Emits the newly updated data via the `simulation_finished` signal.

        Args:
            scenarios (dict): The newly calculated percentile results.
            time_steps (np.ndarray): Updated X-axis for the chart.
            worst_line (np.ndarray): New 5th percentile path.
            median_line (np.ndarray): New 50th percentile path.
            best_line (np.ndarray): New 95th percentile path.
            background_lines (list): New background paths.
        """
        cur = "€"
        self.worst_label.setText(f"{cur} {scenarios['Worst (5%)']:,.2f}")
        self.median_label.setText(f"{cur} {scenarios['Median (50%)']:,.2f}")
        self.best_label.setText(f"{cur} {scenarios['Best (95%)']:,.2f}")
    
        self.chart_view.update_graph(time_steps, worst_line, median_line, best_line, background_lines)
        
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")
        sim_data = {
            "total_value": self.cached_capital,
            "mu": self.cached_mu * 100,
            "sigma": self.cached_sigma * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"]
        }
        self.simulation_finished.emit(sim_data)