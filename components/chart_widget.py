from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

class MonteCarloChartView(QChartView):
    """Custom QChartView for displaying Monte Carlo simulations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.chart = QChart()
        self.setChart(self.chart)
        
        # Apply dark theme
        self.chart.setBackgroundBrush(QColor('#0D1117'))
        self.chart.setTitleBrush(QColor('#E8EDF5'))
        self.chart.legend().setLabelColor(QColor('#C8D0DC'))
        self.chart.legend().setAlignment(Qt.AlignBottom)
        
        # Remove unnecessary chart margins
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.setBackgroundRoundness(0)
        
        # Antialiasing for smoother lines
        self.setRenderHint(QPainter.Antialiasing)

    def update_graph(self, time_steps, worst, median, best, background_lines):
        """Updates the graph with the newly calculated data."""
        self.chart.removeAllSeries()
        
        # Remove old axes
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        # Find max and min values to scale the axes
        max_val = float(best.max())
        min_val = float(worst.min())
        max_time = float(time_steps[-1])

        # --- 1. Background Lines ---
        num_bg_lines = min(100, background_lines.shape[0] if len(background_lines.shape) > 1 else 0)
        
        bg_pen = QPen(QColor(128, 128, 128, 20))
        bg_pen.setWidth(1)

        for i in range(num_bg_lines):
            series = QLineSeries()
            series.setPen(bg_pen)
            points = [QPointF(float(x), float(y)) for x, y in zip(time_steps, background_lines[i])]
            series.append(points)
            self.chart.addSeries(series)

        # --- 2. Main Lines (Worst, Median, Best) ---
        self._add_main_series(time_steps, worst, "Worst (5%)", "#E05252")
        self._add_main_series(time_steps, median, "Median (50%)", "#4A90E2")
        self._add_main_series(time_steps, best, "Best (95%)", "#2ECC8A")

        # --- 3. Axes Configuration ---
        axis_x = QValueAxis()
        axis_x.setTitleText("Trading Days")
        axis_x.setLabelFormat("%i")
        axis_x.setRange(0, max_time)
        axis_x.setLabelsColor(QColor('#C8D0DC'))
        axis_x.setTitleBrush(QColor('#C8D0DC'))
        axis_x.setGridLineColor(QColor(200, 208, 220, 25))

        axis_y = QValueAxis()
        axis_y.setTitleText("Portfolio Value (€)")
        axis_y.setLabelFormat("%.0f")
        axis_y.setRange(min_val * 0.95, max_val * 1.05)
        axis_y.setLabelsColor(QColor('#C8D0DC'))
        axis_y.setTitleBrush(QColor('#C8D0DC'))
        axis_y.setGridLineColor(QColor(200, 208, 220, 25))

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)

        for series in self.chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

        simulated_years = int(max_time // 252)
        self.chart.setTitle(f"Portfolio Value Projection ({simulated_years} Years)")

    def _add_main_series(self, x_data, y_data, name, hex_color):
        """Helper to add main series."""
        series = QLineSeries()
        series.setName(name)
        
        pen = QPen(QColor(hex_color))
        pen.setWidth(2)
        series.setPen(pen)
        
        points = [QPointF(float(x), float(y)) for x, y in zip(x_data, y_data)]
        series.append(points)
        self.chart.addSeries(series)