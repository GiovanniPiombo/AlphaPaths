from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QComboBox, QFrame, QMessageBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from workers.simulation_thread import SimulationWorker, FastMathWorker

class MplCanvas(FigureCanvas):
    """Custom canvas to integrate Matplotlib in PySide6 with a dark theme."""
    def __init__(self, parent=None, width=8, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # Apply dark theme
        self.fig.patch.set_facecolor('#0D1117')
        self.axes.set_facecolor('#0D1117')
        self.axes.tick_params(colors='#C8D0DC')
        self.axes.xaxis.label.set_color('#C8D0DC')
        self.axes.yaxis.label.set_color('#C8D0DC')
        self.axes.title.set_color('#E8EDF5')
        
        for spine in self.axes.spines.values():
            spine.set_edgecolor('#1E2733')
            
        super().__init__(self.fig)


class SimulationPage(QWidget):
    """The SimulationPage class provides a user interface for running Monte Carlo simulations on the user's portfolio. It includes controls for selecting the number of years and simulations, summary cards for displaying key metrics, and an embedded Matplotlib graph to visualize the simulation results. The class uses background threads to perform calculations without freezing the UI, and it caches certain variables to optimize performance for subsequent runs."""
    def __init__(self):
        """Initializes the SimulationPage, sets up the UI, and prepares for background data loading."""
        super().__init__()
        
        # --- CACHE VARIABLES FOR OPTIMIZATION ---
        # These are populated once by the background thread, 
        # allowing instant recalculations later.
        self.cached_mu = None
        self.cached_sigma = None
        self.cached_capital = None
        
        self.setup_ui()

    def setup_ui(self):
        """Sets up the user interface components of the SimulationPage, including controls, summary cards, and the Matplotlib canvas."""
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

        # Years Selector
        lbl_years = QLabel("Years:")
        self.spin_years = QSpinBox()
        self.spin_years.setRange(1, 30)
        self.spin_years.setValue(5)
        
        # Simulations Selector
        lbl_sims = QLabel("Simulations:")
        self.combo_sims = QComboBox()
        self.combo_sims.addItems(["1000", "10000", "50000", "100000"])
        self.combo_sims.setCurrentText("10000")

        # Run Button
        self.run_btn = QPushButton("Run Simulation")
        self.run_btn.setObjectName("primary_btn")
        self.run_btn.setMinimumHeight(38)
        self.run_btn.clicked.connect(self.on_run_clicked)

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

        # ── MATPLOTLIB CANVAS ────────────────────────────────
        self.canvas = MplCanvas(self, width=8, height=5, dpi=100)
        main_layout.addWidget(self.canvas)

    def create_summary_card(self, title: str, initial_value: str, color: str):
        """Helper function to create styled summary cards."""
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

    def update_graph(self, time_steps, worst, median, best, background_lines):
        """Draws the results using the pre-calculated data from the worker."""
        self.canvas.axes.clear()
        
        # Plot the 100 background simulations (transposed back for Matplotlib)
        self.canvas.axes.plot(time_steps, background_lines.T, color='grey', alpha=0.1, linewidth=1)
        
        # Plot the percentiles
        self.canvas.axes.plot(time_steps, worst, color='#E05252', linestyle='-', linewidth=2, label='Worst (5%)')
        self.canvas.axes.plot(time_steps, median, color='#4A90E2', linestyle='-', linewidth=2, label='Median (50%)')
        self.canvas.axes.plot(time_steps, best, color='#2ECC8A', linestyle='-', linewidth=2, label='Best (95%)')
        
        # Calculate years for the title
        simulated_years = len(time_steps) // 252
        self.canvas.axes.set_title(f"Portfolio Value Projection ({simulated_years} Years)", color='#E8EDF5')
        
        self.canvas.axes.set_xlabel('Trading Days', color='#C8D0DC')
        self.canvas.axes.set_ylabel('Portfolio Value', color='#C8D0DC')
        self.canvas.axes.legend(facecolor='#111820', edgecolor='#1E2733', labelcolor='#C8D0DC')
        self.canvas.axes.grid(True, alpha=0.1, color='#C8D0DC')
        
        # Y-axis formatting
        self.canvas.axes.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
        
        self.canvas.draw()

    def start_background_preload(self):
        """Triggered automatically when the Dashboard finishes loading."""
        # If it's already running, don't start it again
        if not self.run_btn.isEnabled():
            return
            
        print("[UI DEBUG] Starting background Monte Carlo preload...")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Preloading in background...")
        
        # Use the current values in the UI (e.g., 5 years, 10,000 sims)
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        self.worker = SimulationWorker(years, simulations)
        
        # Update the button text to show what's happening in the background
        self.worker.progress_update.connect(lambda msg: self.run_btn.setText(f"Background: {msg}"))
        self.worker.data_fetched.connect(self.on_simulation_complete)
        self.worker.error_occurred.connect(self.on_simulation_error)
        
        self.worker.start()

    def on_simulation_complete(self, scenarios, mu, sigma, capital, time_steps, worst_line, median_line, best_line, background_lines):
        """Triggered when the background thread successfully finishes the initial load."""
        # 1. Store the metrics in the cache!
        self.cached_mu = mu
        self.cached_sigma = sigma
        self.cached_capital = capital
        
        # 2. Update the Summary Cards
        cur = "€"
        self.worst_label.setText(f"{cur} {scenarios['Worst (5%)']:,.2f}")
        self.median_label.setText(f"{cur} {scenarios['Median (50%)']:,.2f}")
        self.best_label.setText(f"{cur} {scenarios['Best (95%)']:,.2f}")
        
        # 3. Draw the embedded graph using the pre-calculated lines
        self.update_graph(time_steps, worst_line, median_line, best_line, background_lines)
        
        # 4. Reset the button
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")

    def on_simulation_error(self, error_msg):
        """Triggered if something breaks in the thread."""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")
        QMessageBox.critical(self, "Simulation Error", f"An error occurred:\n{error_msg}")

    def on_run_clicked(self):
        """Uses the FastMathWorker to calculate in the background without freezing the UI."""
        if self.cached_capital is None:
            self.run_btn.setText("Still downloading background data...")
            return
            
        # UI updates
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Calculating scenarios...")
        
        years = self.spin_years.value()
        simulations = int(self.combo_sims.currentText())
        
        print(f"[UI DEBUG] Starting FastMathWorker: {years}Y, {simulations} sims...")
        
        # Launch the lightweight thread
        self.fast_worker = FastMathWorker(
            capital=self.cached_capital,
            mu=self.cached_mu,
            sigma=self.cached_sigma,
            years=years,
            simulations=simulations
        )
        
        # Connect the signals
        self.fast_worker.data_calculated.connect(self.on_fast_math_complete)
        self.fast_worker.error_occurred.connect(self.on_simulation_error)
        
        self.fast_worker.start()

    def on_fast_math_complete(self, scenarios, time_steps, worst_line, median_line, best_line, background_lines):
        """Receives the results from the FastMathWorker and updates the UI."""
        cur = "€"
        self.worst_label.setText(f"{cur} {scenarios['Worst (5%)']:,.2f}")
        self.median_label.setText(f"{cur} {scenarios['Median (50%)']:,.2f}")
        self.best_label.setText(f"{cur} {scenarios['Best (95%)']:,.2f}")
        
        # Pass the pre-calculated lines straight to the graph
        self.update_graph(time_steps, worst_line, median_line, best_line, background_lines)
        
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Simulation")