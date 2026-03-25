from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QComboBox, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal
from workers.simulation_thread import SimulationWorker, FastMathWorker
from core.utils import read_json
from components.chart_widget import MonteCarloChartView
from core.path_manager import PathManager
from core.logger import app_logger

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
    simulation_started = Signal()
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
        self.cached_metrics = None
        self.cached_gbm_data = None
        self.cached_merton_data = None
        self.time_steps = None
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

        # ── Model Toggle Selector ───────────────────────
        lbl_model = QLabel("Model:")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Merton Stress Test", "Standard GBM"])
        self.combo_model.currentIndexChanged.connect(self.update_view)

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
        controls_layout.addWidget(lbl_model)
        controls_layout.addWidget(self.combo_model)
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
            
        self.simulation_started.emit()
        app_logger.info("Starting background Monte Carlo preload...")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Preloading in background...")
        
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        self.worker = SimulationWorker(years, simulations)
        
        self.worker.progress_update.connect(lambda msg: self.run_btn.setText(f"Background: {msg}"))
        self.worker.data_fetched.connect(self.on_simulation_complete)
        self.worker.error_occurred.connect(self.on_simulation_error)
        
        self.worker.start()
    
    def on_simulation_complete(self, payload):
        """
        Callback executed when the initial background simulation completes.

        Parses the payload received from the SimulationWorker, caches the 
        risk metrics, GBM, and Merton model data, and triggers a view update.

        Args:
            payload (dict): A dictionary containing 'metrics', 'gbm', 
                'merton', and 'time_steps' data from the simulation.
        """
        self.cached_metrics = payload["metrics"]
        self.cached_gbm_data = payload["gbm"]
        self.cached_merton_data = payload["merton"]
        self.time_steps = payload["time_steps"]
        
        self.update_view()
        self.simulation_finished.emit(self.get_sim_data())
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")

    def update_view(self):
        """
        Switches the UI text and chart between the two models instantly based on the dropdown.

        Updates the summary cards (Worst, Median, Best) and redraws the chart 
        using the currently selected model (Standard GBM or Merton Stress Test). 
        Finally, emits the updated data via the `simulation_finished` signal.
        """
        active_data = self.get_active_data()
        if not active_data:
            return

        scenarios = active_data["scenarios"]
        
        cur = "€"
        self.worst_label.setText(f"{cur} {scenarios['Worst (5%)']:,.2f}")
        self.median_label.setText(f"{cur} {scenarios['Median (50%)']:,.2f}")
        self.best_label.setText(f"{cur} {scenarios['Best (95%)']:,.2f}")
        
        self.chart_view.update_graph(
            self.time_steps, 
            active_data["worst"], 
            active_data["median"], 
            active_data["best"], 
            active_data["background"]
        )

    def on_fast_math_complete(self, payload):
        """Callback executed upon completion of the FastMathWorker calculations."""
        self.cached_gbm_data = payload["gbm"]
        self.cached_merton_data = payload["merton"]
        self.time_steps = payload["time_steps"]
        
        self.update_view()
        self.simulation_finished.emit(self.get_sim_data())
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")

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
        app_logger.error(f"Simulation Error UI Popup: {error_msg}")
        self.simulation_finished.emit({})
        QMessageBox.critical(self, "Simulation Error", f"An error occurred:\n{error_msg}")

    def on_run_clicked(self):
        """
        Handles the click event on the "Run Simulation" button.
        Starts a FastMathWorker to execute new simulations based on user parameters.
        """
        if getattr(self, "cached_metrics", None) is None:
            self.run_btn.setText("Still downloading background data...")
            return
        
        self.simulation_started.emit()
            
        # ── UI Updates ───────────────────────────────────────────
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Calculating scenarios...")
        
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        app_logger.info(f"Starting FastMathWorker: {years}Y, {simulations} sims...")
        
        # ── Launch the thread ────────────────────────────────────
        self.fast_worker = FastMathWorker(
            metrics=self.cached_metrics,
            years=years,
            simulations=simulations
        )
        
        # ── Connect the signals ──────────────────────────────────
        self.fast_worker.data_calculated.connect(self.on_fast_math_complete)
        self.fast_worker.error_occurred.connect(self.on_simulation_error)
        
        self.fast_worker.start()
    
    def get_active_data(self):
        """Returns the data block for the currently selected model."""
        if not self.cached_gbm_data or not self.cached_merton_data:
            return None
            
        if self.combo_model.currentText() == "Standard GBM":
            return self.cached_gbm_data
        return self.cached_merton_data

    def get_sim_data(self):
        """Compiles and returns the current simulation results as a dictionary."""
        active_data = self.get_active_data()
        if not active_data or not getattr(self, "cached_metrics", None):
            return {}

        scenarios = active_data["scenarios"]
        return {
            "total_value": self.cached_metrics["risky_capital"] + self.cached_metrics["cash_capital"],
            "mu": self.cached_metrics["total_mu"] * 100,
            "sigma": self.cached_metrics["total_vol"] * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"],
            "metrics": self.cached_metrics
        }