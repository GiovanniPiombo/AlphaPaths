from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QPainter, QCursor
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtWidgets import QToolTip
from core.logger import app_logger
from core.utils import read_json
from core.path_manager import PathManager

class MonteCarloChartView(QChartView):
    """
    A custom PySide6 QChartView specialized for rendering Monte Carlo simulations.

    This view handles the visualization of thousands of background simulation paths 
    alongside highlighted percentile paths (Worst, Median, Best). It implements 
    a custom dark theme, anti-aliased rendering, and advanced interaction logic 
    (zoom clamping, rubber-band selection, and wheel zoom) while preventing the 
    user from scrolling outside the calculated data boundaries.

    Attributes:
        chart (QChart): The underlying chart object being rendered.
        axis_x (QValueAxis): The dynamic X-axis representing trading days.
        axis_y (QValueAxis): The dynamic Y-axis representing portfolio value.
        orig_x_min, orig_x_max (float): Hard boundaries for the X-axis to constrain zooming.
        orig_y_min, orig_y_max (float): Hard boundaries for the Y-axis to constrain zooming.
    """
    def __init__(self, parent=None):
        """
        Initializes the custom chart view, applies styling, and enables interactions.

        Args:
            parent (QWidget, optional): The parent widget in the Qt hierarchy. 
                Defaults to None.
        """
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
        self.setRubberBand(QChartView.RectangleRubberBand)
        
        self.axis_x = None
        self.axis_y = None
        self.orig_x_min = 0.0
        self.orig_x_max = 0.0
        self.orig_y_min = 0.0
        self.orig_y_max = 0.0

    def update_graph(self, time_steps, worst, median, best, background_lines):
        """
        Clears the existing chart and redraws all simulation data.

        This method dynamically recalculates the chart boundaries based on the 
        new data, draws a sample of semi-transparent background lines, and overlays 
        the main percentile paths with distinct colors. It automatically updates 
        the chart title to reflect the simulated time horizon.

        Args:
            time_steps (list or np.ndarray): X-axis values (usually 0 to Total Days).
            worst (list or np.ndarray): Y-values for the 5th percentile path.
            median (list or np.ndarray): Y-values for the 50th percentile path.
            best (list or np.ndarray): Y-values for the 95th percentile path.
            background_lines (np.ndarray): A 2D array containing the raw, individual 
                simulation paths to be drawn faintly in the background.
        """
        target_currency = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "AUTO").split()[0]
        self.current_currency = target_currency if target_currency != "AUTO" else "€"
        app_logger.debug(f"Redrawing MonteCarloChartView with {len(time_steps)} steps and {background_lines.shape[0]} background paths.")
        self.chart.removeAllSeries()
        
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        self.orig_x_min = 0.0
        self.orig_x_max = float(time_steps[-1])
        
        min_val = float(background_lines.min()) * 0.95
        max_val = float(background_lines.max()) * 1.05
        
        self.orig_y_min = 0.0 if min_val < 0 else min_val 
        self.orig_y_max = max_val

        num_bg_lines = min(100, background_lines.shape[0] if len(background_lines.shape) > 1 else 0)
        
        bg_pen = QPen(QColor(128, 128, 128, 20))
        bg_pen.setWidth(1)

        for i in range(num_bg_lines):
            series = QLineSeries()
            series.setPen(bg_pen)
            points = [QPointF(float(x), float(y)) for x, y in zip(time_steps, background_lines[i])]
            series.append(points)
            self.chart.addSeries(series)

        self._add_main_series(time_steps, worst, "Worst (5%)", "#E05252")
        self._add_main_series(time_steps, median, "Median (50%)", "#4A90E2")
        self._add_main_series(time_steps, best, "Best (95%)", "#2ECC8A")

        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Trading Days")
        self.axis_x.setLabelFormat("%i")
        self.axis_x.setRange(self.orig_x_min, self.orig_x_max)
        self.axis_x.setLabelsColor(QColor('#C8D0DC'))
        self.axis_x.setTitleBrush(QColor('#C8D0DC'))
        self.axis_x.setGridLineColor(QColor(200, 208, 220, 25))

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText(f"Portfolio Value ({self.current_currency})") 
        self.axis_y.setLabelFormat("%.0f")
        self.axis_y.setRange(self.orig_y_min, self.orig_y_max)
        self.axis_y.setLabelsColor(QColor('#C8D0DC'))
        self.axis_y.setTitleBrush(QColor('#C8D0DC'))
        self.axis_y.setGridLineColor(QColor(200, 208, 220, 25))

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        for series in self.chart.series():
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)

        simulated_years = int(self.orig_x_max // 252)
        self.chart.setTitle(f"Portfolio Value Projection ({simulated_years} Years)")

    def _add_main_series(self, x_data, y_data, name, hex_color):
        """
        Helper method to create and style a main percentile line series.

        Args:
            x_data (list or np.ndarray): The X-axis coordinates.
            y_data (list or np.ndarray): The Y-axis coordinates.
            name (str): The label for the series (displays in the legend).
            hex_color (str): The hex code for the line's color (e.g., "#E05252").
        """
        series = QLineSeries()
        series.setName(name)
        
        pen = QPen(QColor(hex_color))
        pen.setWidth(2)
        series.setPen(pen)
        
        points = [QPointF(float(x), float(y)) for x, y in zip(x_data, y_data)]
        series.append(points)
        self.chart.addSeries(series)

        series.hovered.connect(lambda point, state, n=name: self._handle_series_hover(point, state, n))

    def _clamp_axes(self):
        """
        Forces the chart's current viewport to remain within the original data boundaries.

        This prevents the user from zooming out infinitely or panning into 
        empty/negative space where no simulation data exists.
        """
        if not self.axis_x or not self.axis_y:
            return

        # Force X-Axis Limits
        if self.axis_x.min() < self.orig_x_min:
            self.axis_x.setMin(self.orig_x_min)
        if self.axis_x.max() > self.orig_x_max:
            self.axis_x.setMax(self.orig_x_max)

        # Force Y-Axis Limits
        if self.axis_y.min() < self.orig_y_min:
            self.axis_y.setMin(self.orig_y_min)
        if self.axis_y.max() > self.orig_y_max:
            self.axis_y.setMax(self.orig_y_max)

    def wheelEvent(self, event):
        """
        Overrides the default wheel event to implement boundary-constrained zooming.

        Uses the mouse wheel delta to trigger `zoomIn` or `zoomOut`. A QTimer 
        is utilized to defer the execution of `_clamp_axes`, ensuring Qt's 
        internal zooming logic completes before boundaries are enforced.

        Args:
            event (QWheelEvent): The Qt mouse wheel event payload.
        """
        if event.angleDelta().y() > 0:
            self.chart.zoomIn()
        else:
            self.chart.zoomOut()
            
        QTimer.singleShot(10, self._clamp_axes)
        event.accept() 

    def mousePressEvent(self, event):
        """
        Overrides the default press event to track initial click coordinates.

        Records the click position to differentiate between a simple click (reset zoom) 
        and a drag action (rubber-band zoom). Suppresses default right-click behaviors.

        Args:
            event (QMouseEvent): The Qt mouse press event payload.
        """
        self._click_pos = event.pos()
        
        if event.button() == Qt.RightButton:
            event.accept() 
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Overrides the default release event to trigger custom interaction logic.

        Determines if the action was a simple click (Manhattan length < 5 pixels) 
        or a drag. If it was a click, the zoom is reset. If it was a left-drag, 
        it allows the rubber-band zoom to finish and schedules a boundary clamp.

        Args:
            event (QMouseEvent): The Qt mouse release event payload.
        """
        if event.button() == Qt.LeftButton:
            super().mouseReleaseEvent(event)

        is_click = False
        if hasattr(self, '_click_pos') and self._click_pos is not None:
            delta = event.pos() - self._click_pos
            if delta.manhattanLength() < 5:
                is_click = True

        if is_click:
            self.reset_zoom()
            event.accept()
        else:
            if event.button() == Qt.LeftButton:
                QTimer.singleShot(10, self._clamp_axes)
            elif event.button() == Qt.RightButton:
                event.accept()
    
    def reset_zoom(self):
        """
        Programmatically restores the chart axes to their original, maximum boundaries.
        """
        if self.axis_x and self.axis_y:
            self.axis_x.setRange(self.orig_x_min, self.orig_x_max)
            self.axis_y.setRange(self.orig_y_min, self.orig_y_max)

    def _handle_series_hover(self, point: QPointF, state: bool, series_name: str):
        """
        Handles the hover event over the main percentile lines.
        Displays a native tooltip showing the specific day and portfolio value.
        
        Args:
            point (QPointF): The exact point (x, y) on the chart that is being hovered.
            state (bool): True if the mouse cursor entered the line area, False if it left.
            series_name (str): The name of the series being hovered (e.g., 'Median (50%)').
        """
        if state:
            day = int(point.x())
            value = point.y()
            
            cur = getattr(self, 'current_currency', '€')
            
            tooltip_text = f"<b>{series_name}</b><br>Day: {day}<br>Value: {value:,.0f} {cur}"
            
            QToolTip.showText(QCursor.pos(), tooltip_text, self)
        else:
            QToolTip.hideText()