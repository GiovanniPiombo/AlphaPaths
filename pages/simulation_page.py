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
from PySide6.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QFrame, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal
from workers.simulation_thread import SimulationWorker, FastMathWorker
from components.ai_widget import AIInsightWidget
from core.utils import read_json
from components.chart_widget import MonteCarloChartView
from core.path_manager import PathManager
from core.logger import app_logger

class SimulationPage(QWidget):
    """
    A page component that performs and visualizes Monte Carlo simulations.

    Signals:
        simulation_started: Emitted when a simulation begins.
        simulation_finished (dict): Emitted when a simulation concludes, containing
            'total_value', 'mu', 'sigma', and percentile results.

    Attributes:
        cached_metrics (dict | None): Risk metrics calculated from historical data.
        cached_gbm_data (dict | None): Cached simulation results using Standard GBM.
        cached_merton_data (dict | None): Cached simulation results using Merton Stress Test.
        time_steps (list | None): Array of time increments for the simulation chart.
        dashboard_data (dict): Contextual portfolio data passed from the dashboard.
        sims_map (list): Mapping of slider steps to simulation counts.
    """
    simulation_started = Signal()
    simulation_finished = Signal(dict)
    
    def __init__(self):
        """
        Initializes the simulation page and prepares the internal cache.

        Sets the cache variables to None before they are populated by the
        background thread, preventing accidental calculations without valid
        historical data.
        """
        super().__init__()
        
        self.cached_metrics = None
        self.cached_gbm_data = None
        self.cached_merton_data = None
        self.time_steps = None
        
        self.dashboard_data = {} 
        
        self.sims_map = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000, 21000, 22000, 23000, 24000, 25000, 26000, 27000, 28000, 29000, 30000, 31000, 32000, 33000, 34000, 35000, 36000, 37000, 38000, 39000, 40000, 41000, 42000, 43000, 44000, 45000, 46000, 47000, 48000, 49000, 50000, 51000, 52000, 53000, 54000, 55000, 56000, 57000, 58000, 59000, 60000, 61000, 62000, 63000, 64000, 65000, 66000, 67000, 68000, 69000, 70000, 71000, 72000, 73000, 74000, 75000, 76000, 77000, 78000, 79000, 80000, 81000, 82000, 83000, 84000, 85000, 86000, 87000, 88000, 89000, 90000, 91000, 92000, 93000, 94000, 95000, 96000, 97000, 98000, 99000, 100000]
        self.setup_ui()

    def setup_ui(self):
        """
        Constructs the layout, control bar, summary cards, and chart view.

        Configures user inputs for simulation duration (years) and iteration count
        using custom sliders, and sets up dynamic KPI and scenario outcome cards.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(28, 20, 28, 20)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(40)
        
        page_title = QLabel("Monte Carlo\nSimulation")
        page_title.setObjectName("sim_page_title")
        top_bar.addWidget(page_title)

        kpi_container = QHBoxLayout()
        kpi_container.setSpacing(35)

        self.lay_nlv, self.nlv_label = self.create_minimal_kpi("NET LIQUIDATION VALUE", "#E8EDF5")
        self.lay_cash, self.cash_label = self.create_minimal_kpi("AVAILABLE CASH", "#E8EDF5")
        self.lay_pnl, self.pnl_label = self.create_minimal_kpi("DAILY P&L", "#E8EDF5")

        kpi_container.addLayout(self.lay_nlv)
        kpi_container.addLayout(self.lay_cash)
        kpi_container.addLayout(self.lay_pnl)
        
        top_bar.addLayout(kpi_container)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(20)

        chart_frame = QFrame()
        chart_frame.setObjectName("summary_card")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        
        self.chart_view = MonteCarloChartView(self)
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_view.setMinimumSize(450, 350)
        
        chart_layout.addWidget(self.chart_view, stretch=1)
        
        middle_layout.addWidget(chart_frame, stretch=7)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        scenarios_frame = QFrame()
        scenarios_frame.setObjectName("summary_card")
        scenarios_layout = QVBoxLayout(scenarios_frame)
        scenarios_layout.setContentsMargins(20, 16, 20, 16)
        scenarios_layout.setSpacing(12)
        
        sim_title = QLabel("SIMULATED OUTCOMES")
        sim_title.setObjectName("scenario_section_title")
        scenarios_layout.addWidget(sim_title)
        
        self.row_best, self.lbl_best = self.create_custom_scenario_row("Best Case (95%)", "#82B37B", "")
        self.row_median, self.lbl_median = self.create_custom_scenario_row("Median Case (50%)", "#54ABC2", "")
        self.row_worst, self.lbl_worst = self.create_custom_scenario_row("Worst Case (5%)", "#CC7662", "")

        scenarios_layout.addWidget(self.row_best)
        scenarios_layout.addWidget(self.row_median)
        scenarios_layout.addWidget(self.row_worst)
        
        right_panel.addWidget(scenarios_frame, stretch=0)

        ai_frame = QFrame()
        ai_frame.setObjectName("summary_card")
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setContentsMargins(20, 20, 20, 20)
        
        ai_title = QLabel("AI INSIGHT")
        ai_title.setObjectName("ai_section_title")
        
        self.ai_widget = AIInsightWidget("Awaiting simulation data...")
        self.ai_widget.analysis_started.connect(self.on_ai_started)
        self.ai_widget.analysis_finished.connect(self.on_ai_complete)
        self.ai_widget.analysis_failed.connect(self.on_ai_error)

        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_widget)

        right_panel.addWidget(ai_frame, stretch=1)
        middle_layout.addLayout(right_panel, stretch=3)
        main_layout.addLayout(middle_layout, stretch=1)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(5, 10, 5, 0)
        bottom_bar.setSpacing(35)

        default_years = read_json(PathManager.CONFIG_FILE, "DEFAULT_YEARS") or 5
        self.slider_years = QSlider(Qt.Horizontal)
        self.slider_years.setRange(1, 30)
        self.slider_years.setValue(default_years)
        self.slider_years.setMinimumWidth(150)
        lay_years, self.lbl_years_val = self.create_slider_group("SIMULATION YEARS", f"{default_years}.0", self.slider_years)
        self.slider_years.valueChanged.connect(lambda v: self.lbl_years_val.setText(f"{v}.0"))

        default_sims_str = str(read_json(PathManager.CONFIG_FILE, "DEFAULT_SIMS") or "10000")
        default_sims_idx = self.sims_map.index(int(default_sims_str)) if int(default_sims_str) in self.sims_map else 1
        self.slider_sims = QSlider(Qt.Horizontal)
        self.slider_sims.setRange(0, len(self.sims_map) - 1)
        self.slider_sims.setValue(default_sims_idx)
        self.slider_sims.setMinimumWidth(150)
        lay_sims, self.lbl_sims_val = self.create_slider_group("SIMULATIONS", f"{self.sims_map[default_sims_idx]:,}", self.slider_sims)
        self.slider_sims.valueChanged.connect(lambda v: self.lbl_sims_val.setText(f"{self.sims_map[v]:,}"))

        lay_model = QVBoxLayout()
        lay_model.setSpacing(5)
        lbl_model = QLabel("MODEL TYPE")
        lbl_model.setObjectName("control_label")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Standard GBM", "Merton Stress Test"])
        self.combo_model.currentIndexChanged.connect(self.update_view)
        lay_model.addWidget(lbl_model)
        lay_model.addWidget(self.combo_model)

        self.run_btn = QPushButton("RUN SIMULATION")
        self.run_btn.setObjectName("primary_btn") 
        self.run_btn.setMinimumHeight(42)
        self.run_btn.clicked.connect(self.on_run_clicked)
        
        bottom_bar.addLayout(lay_years)
        bottom_bar.addLayout(lay_sims)
        bottom_bar.addLayout(lay_model)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.run_btn)

        main_layout.addLayout(bottom_bar)

    def create_minimal_kpi(self, title, color):
        """
        Helper function to create minimal KPI indicators for the top bar.

        Args:
            title (str): The label title for the KPI.
            color (str): The hex color code for the value text.

        Returns:
            tuple: A tuple containing (layout, value_label) where:
                - layout (QVBoxLayout): The vertical layout containing the texts.
                - value_label (QLabel): The updatable label holding the KPI value.
        """
        layout = QVBoxLayout()
        layout.setSpacing(2)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("kpi_title")
        
        val_lbl = QLabel("0.00")
        val_lbl.setObjectName("kpi_value")
        val_lbl.setStyleSheet(f"color: {color};")
        
        layout.addWidget(title_lbl)
        layout.addWidget(val_lbl)
        return layout, val_lbl

    def create_slider_group(self, title, initial_val, slider_widget):
        """
        Creates a labeled group containing a horizontal slider and its current value.

        Args:
            title (str): The title of the control group.
            initial_val (str): The initial string value to display.
            slider_widget (QSlider): The slider instance to embed.

        Returns:
            tuple: A tuple containing (layout, value_label) where:
                - layout (QVBoxLayout): The vertical layout containing the control.
                - value_label (QLabel): The updatable label reflecting the slider value.
        """
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        top_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("control_label")
        val_lbl = QLabel(initial_val)
        val_lbl.setObjectName("control_value")
        
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        top_row.addWidget(val_lbl)
        
        layout.addLayout(top_row)
        layout.addWidget(slider_widget)
        return layout, val_lbl

    def create_custom_scenario_row(self, title, color_theme, icon_char):
        """
        Helper function to create a stylized row for scenario outcomes.

        Args:
            title (str): The scenario name (e.g., "Best Case (95%)").
            color_theme (str): The hex color code for the theme line and text.
            icon_char (str): A unicode character or emoji for visual emphasis.

        Returns:
            tuple: A tuple containing (widget, value_label) where:
                - widget (QWidget): The container widget for the row.
                - value_label (QLabel): The updatable label holding the outcome value.
        """
        widget = QWidget()
        layout = QHBoxLayout(widget) 
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        line = QFrame()
        line.setFixedWidth(3)
        line.setStyleSheet(f"background-color: {color_theme}; border-radius: 1px;")
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0) 
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("scenario_row_title")
        title_lbl.setStyleSheet(f"color: {color_theme};")
        
        val_lbl = QLabel("0.00")
        val_lbl.setObjectName("scenario_row_val")
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(val_lbl)
        
        icon_lbl = QLabel(icon_char)
        icon_lbl.setObjectName("scenario_row_icon")
        icon_lbl.setStyleSheet(f"color: {color_theme};")
        icon_lbl.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(line)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(icon_lbl)
        
        return widget, val_lbl

    def set_dashboard_data(self, data: dict):
        """
        Updates the top bar KPIs with current portfolio data.

        Args:
            data (dict): A dictionary containing 'currency', 'nlv', 'cash', and 'pnl'.
        """
        self.dashboard_data = data  
        cur = data.get('currency', '€')
        nlv = data.get('nlv', 0.0)
        cash = data.get('cash', 0.0)
        pnl = data.get('pnl', 0.0)

        self.nlv_label.setText(f"{cur} {nlv:,.2f}")
        self.cash_label.setText(f"{cur} {cash:,.2f}")
        
        pnl_color = "#82B37B" if pnl >= 0 else "#CC7662"
        pnl_sign = "+" if pnl >= 0 else ""
        self.pnl_label.setText(f"{pnl_sign}{cur} {pnl:,.2f}")
        self.pnl_label.setStyleSheet(f"color: {pnl_color};")

    def start_background_preload(self):
        """
        Starts the data loading and the initial background simulation.

        This is typically triggered automatically when the Dashboard finishes
        loading, using a `SimulationWorker` to prevent freezing the UI
        during the initial fetch of historical data.
        """
        if not self.run_btn.isEnabled(): return
        
        self.simulation_started.emit()
        app_logger.info("Starting background Monte Carlo preload...")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("PRELOADING...")
        
        years = self.slider_years.value()
        simulations = self.sims_map[self.slider_sims.value()]
        
        self.worker = SimulationWorker(years, simulations)
        
        if hasattr(self.worker, 'progress_update'):
            self.worker.progress_update.connect(lambda msg: self.run_btn.setText(f"BACKGROUND: {msg.upper()}"))
            
        self.worker.data_fetched.connect(self.on_simulation_complete)
        self.worker.error_occurred.connect(self.on_simulation_error)
        self.worker.start()

    def on_simulation_complete(self, payload):
        """
        Callback executed when the initial background simulation completes.

        Parses the payload received from the SimulationWorker, caches the
        risk metrics, GBM, and Merton model data, triggers a view update,
        and requests the initial AI analysis.

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
        self.request_ai_feedback()

    def on_fast_math_complete(self, payload):
        """
        Callback executed upon completion of the FastMathWorker calculations.

        Updates the local cache with the newly calculated simulation arrays,
        refreshes the UI, and triggers a new AI analysis based on the results.

        Args:
            payload (dict): A dictionary containing 'gbm', 'merton',
                and 'time_steps' generated by the fast math thread.
        """
        self.cached_gbm_data = payload["gbm"]
        self.cached_merton_data = payload["merton"]
        self.time_steps = payload["time_steps"]
        
        self.update_view()
        self.simulation_finished.emit(self.get_sim_data())
        self.request_ai_feedback()

    def update_view(self):
        """
        Switches the UI text and chart between the two models based on the dropdown.

        Updates the scenario rows (Worst, Median, Best) and redraws the chart
        using the currently selected model (Standard GBM or Merton Stress Test).
        """
        active_data = self.get_active_data()
        if not active_data: return

        scenarios = active_data["scenarios"]
        target_currency = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "AUTO").split()[0]
        cur = target_currency if target_currency != "AUTO" else "$"
    
        self.lbl_worst.setText(f"{cur}{scenarios['Worst (5%)']:,.2f}")
        self.lbl_median.setText(f"{cur}{scenarios['Median (50%)']:,.2f}")
        self.lbl_best.setText(f"{cur}{scenarios['Best (95%)']:,.2f}")

        self.chart_view.update_graph(
            self.time_steps, active_data["worst"], active_data["median"], 
            active_data["best"], active_data["background"]
        )

    def on_run_clicked(self):
        """
        Handles the click event on the "Run Simulation" button.

        Starts a FastMathWorker to execute new simulations based on user
        parameters from the sliders without re-downloading historical data.
        """
        if getattr(self, "cached_metrics", None) is None: return
        self.simulation_started.emit()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("CALCULATING...")
        
        years = self.slider_years.value()
        simulations = self.sims_map[self.slider_sims.value()]
        
        app_logger.info(f"Starting FastMathWorker: {years}Y, {simulations} sims...")
        
        self.fast_worker = FastMathWorker(self.cached_metrics, years, simulations)
        self.fast_worker.data_calculated.connect(self.on_fast_math_complete)
        self.fast_worker.error_occurred.connect(self.on_simulation_error)
        self.fast_worker.start()

    def request_ai_feedback(self):
        """
        Compiles current simulation data and triggers the AI Insight widget.
        
        Fetches the user's preferred language from the configuration and passes
        the current scenario data to the LLM for analysis.
        """
        sim_data = self.get_sim_data()
        if not sim_data: return
        ai_language = read_json(PathManager.CONFIG_FILE, "AI_LANGUAGE") or "English"
        sim_data["language"] = ai_language
        self.ai_widget.start_analysis(sim_data)

    def on_ai_started(self):
        """
        Callback executed when the AI begins generating insights.
        
        Disables the run button and updates its text to reflect the AI processing state.
        """
        self.run_btn.setEnabled(False)
        self.run_btn.setText("AI ANALYZING...")

    def on_ai_complete(self):
        """
        Callback executed when the AI finishes generating insights.
        
        Re-enables the run button for further user interaction.
        """
        self.run_btn.setEnabled(True)
        self.run_btn.setText("RUN SIMULATION")

    def on_ai_error(self, error_msg):
        """
        Handles exceptions raised by the AI Insight generation process.

        Logs the error and re-enables the run button.

        Args:
            error_msg (str): The error message returned by the AI widget.
        """
        app_logger.error(f"AI Insight Error: {error_msg}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("RUN SIMULATION")

    def on_simulation_error(self, error_msg):
        """
        Handles exceptions raised by the background simulation threads.

        Logs the error, re-enables the UI controls, and displays a critical
        dialog box to the user with the error details.

        Args:
            error_msg (str): The error message returned by the worker.
        """
        app_logger.error(f"Simulation Error UI Popup: {error_msg}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("RUN SIMULATION")
        self.simulation_finished.emit({})
        QMessageBox.critical(self, "Simulation Error", f"An error occurred:\n{error_msg}")

    def get_active_data(self):
        """
        Retrieves the cached simulation data block for the currently selected model.

        Returns:
            dict | None: The active scenario dictionary (GBM or Merton), or None if
                the background preload hasn't finished yet.
        """
        if not self.cached_gbm_data or not self.cached_merton_data: return None
        if self.combo_model.currentText() == "Standard GBM": return self.cached_gbm_data
        return self.cached_merton_data

    def get_sim_data(self):
        """
        Compiles and returns the current simulation results alongside dashboard data.

        Returns:
            dict: A payload containing total value, expected return (mu),
                volatility (sigma), calculated percentile scenarios, and
                current portfolio dashboard data.
        """
        active_data = self.get_active_data()
        if not active_data or not getattr(self, "cached_metrics", None): return {}

        scenarios = active_data["scenarios"]
        sim_results = {
            "total_value": self.cached_metrics["risky_capital"] + self.cached_metrics["cash_capital"],
            "mu": self.cached_metrics["total_mu"] * 100,
            "sigma": self.cached_metrics["total_vol"] * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"],
            "metrics": self.cached_metrics,
            "years": self.slider_years.value()
        }
        
        if hasattr(self, 'dashboard_data'):
            sim_results.update(self.dashboard_data)
            
        return sim_results