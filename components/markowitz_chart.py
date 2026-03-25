from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QPainter, QCursor
from PySide6.QtWidgets import QToolTip
from PySide6.QtCharts import QChart, QChartView, QSplineSeries, QScatterSeries, QValueAxis
from core.logger import app_logger

class MarkowitzChartView(QChartView):
    """
    A custom PySide6 QChartView specialized for rendering the Efficient Frontier.

    Visualizes the optimization curve (using QSplineSeries for smoothness) and 
    highlights the user's current portfolio versus the optimal Max Sharpe portfolio 
    using QScatterSeries. Matches the dark theme of the application.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.chart = QChart()
        self.setChart(self.chart)
        
        self.chart.setBackgroundBrush(QColor('#0D1117'))
        self.chart.setTitleBrush(QColor('#E8EDF5'))
        self.chart.legend().setLabelColor(QColor('#C8D0DC'))
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.setBackgroundRoundness(0)

        self.setRenderHint(QPainter.Antialiasing)
        
        self.axis_x = None
        self.axis_y = None

    def update_graph(self, frontier_points: list, current_stats: dict, optimal_stats: dict):
        """
        Clears the existing chart and redraws the Efficient Frontier and portfolios.

        Args:
            frontier_points (list): List of dicts with 'volatility' and 'return'.
            current_stats (dict): Stats for the Current Portfolio.
            optimal_stats (dict): Stats for the Max Sharpe Portfolio.
        """
        app_logger.debug(f"Redrawing MarkowitzChartView with {len(frontier_points)} frontier points.")
        self.chart.removeAllSeries()
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        curve_series = QSplineSeries()
        curve_series.setName("Efficient Frontier")
        pen = QPen(QColor("#4A90E2"))
        pen.setWidth(3)
        curve_series.setPen(pen)
        
        x_vals = []
        y_vals = []
        for pt in frontier_points:
            vol = pt["volatility"] * 100
            ret = pt["return"] * 100
            x_vals.append(vol)
            y_vals.append(ret)
            curve_series.append(QPointF(vol, ret))
            
        self.chart.addSeries(curve_series)
        curve_series.hovered.connect(lambda point, state: self._handle_hover(point, state, "Efficient Frontier"))

        current_series = QScatterSeries()
        current_series.setName("Current Portfolio")
        current_series.setMarkerShape(QScatterSeries.MarkerShapeCircle)
        current_series.setMarkerSize(12)
        current_series.setColor(QColor("#E05252"))
        current_series.setBorderColor(QColor("#FFFFFF"))
        
        curr_x = current_stats["volatility"] * 100
        curr_y = current_stats["return"] * 100
        current_series.append(QPointF(curr_x, curr_y))
        x_vals.append(curr_x)
        y_vals.append(curr_y)
        
        self.chart.addSeries(current_series)
        current_series.hovered.connect(lambda point, state: self._handle_hover(point, state, "Current Portfolio"))

        optimal_series = QScatterSeries()
        optimal_series.setName("Max Sharpe (Optimal)")
        optimal_series.setMarkerShape(QScatterSeries.MarkerShapeCircle)
        optimal_series.setMarkerSize(14)
        optimal_series.setColor(QColor("#2ECC8A")) # Green
        optimal_series.setBorderColor(QColor("#FFFFFF"))
        
        opt_x = optimal_stats["volatility"] * 100
        opt_y = optimal_stats["return"] * 100
        optimal_series.append(QPointF(opt_x, opt_y))
        x_vals.append(opt_x)
        y_vals.append(opt_y)
        self.chart.addSeries(optimal_series)
        optimal_series.hovered.connect(lambda point, state: self._handle_hover(point, state, "Max Sharpe (Optimal)"))

        min_x, max_x = min(x_vals), max(x_vals)
        min_y, max_y = min(y_vals), max(y_vals)
        
        pad_x = (max_x - min_x) * 0.1 if max_x != min_x else 1
        pad_y = (max_y - min_y) * 0.1 if max_y != min_y else 1

        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Risk (Annualized Volatility %)")
        self.axis_x.setLabelFormat("%.2f%%")
        self.axis_x.setRange(max(0, min_x - pad_x), max_x + pad_x)
        self.axis_x.setLabelsColor(QColor('#C8D0DC'))
        self.axis_x.setTitleBrush(QColor('#C8D0DC'))
        self.axis_x.setGridLineColor(QColor(200, 208, 220, 25))

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Expected Return (Annualized %)")
        self.axis_y.setLabelFormat("%.2f%%")
        self.axis_y.setRange(min_y - pad_y, max_y + pad_y)
        self.axis_y.setLabelsColor(QColor('#C8D0DC'))
        self.axis_y.setTitleBrush(QColor('#C8D0DC'))
        self.axis_y.setGridLineColor(QColor(200, 208, 220, 25))

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        for series in self.chart.series():
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)

        self.chart.setTitle("Markowitz Efficient Frontier")

    def _handle_hover(self, point: QPointF, state: bool, series_name: str):
        """
        Handles the hover event over the frontier curve or portfolio scatter points.
        Displays a native tooltip showing the exact Risk and Return percentages.
        
        Args:
            point (QPointF): The exact point (x, y) on the chart that is being hovered.
            state (bool): True if the mouse cursor entered the item area, False if it left.
            series_name (str): The name of the series being hovered to display in bold.
        """
        if state:
            risk = point.x()
            expected_return = point.y()
            
            tooltip_text = f"<b>{series_name}</b><br>Risk: {risk:.2f}%<br>Return: {expected_return:.2f}%"
            
            QToolTip.showText(QCursor.pos(), tooltip_text, self)
        else:
            QToolTip.hideText()