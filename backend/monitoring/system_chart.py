"""
Widget hiển thị biểu đồ line chart cho CPU và RAM usage
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
import time

# Thử import QtCharts, nếu không có thì dùng fallback
try:
    from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
    from PyQt6.QtGui import QPainter
    CHARTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PyQt6-Charts không khả dụng: {e}")
    print("📦 Vui lòng cài đặt: pip install PyQt6-Charts")
    print("📦 Hoặc cài đặt Qt6 system libraries:")
    print("   Ubuntu/Debian: sudo apt-get install qt6-base-dev libqt6charts6")
    print("   Fedora: sudo dnf install qt6-qtbase-devel qt6-qtcharts")
    CHARTS_AVAILABLE = False


class SingleChart(QWidget):
    """Widget hiển thị biểu đồ đơn lẻ cho CPU hoặc RAM"""
    
    def __init__(self, chart_type="CPU", parent=None):
        """
        chart_type: "CPU" hoặc "RAM"
        """
        super().__init__(parent)
        self.chart_type = chart_type
        
        # Dữ liệu lịch sử (lưu tối đa 60 điểm)
        self.max_points = 60
        self.time_data = []
        self.data_values = []
        
        # Timer để cập nhật dữ liệu
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.start_time = time.time()
        
        if CHARTS_AVAILABLE:
            self.setup_ui()
        else:
            self.setup_fallback_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện với Qt Charts"""
        # Tạo chart
        self.chart = QChart()
        title = f"{self.chart_type} Usage"
        self.chart.setTitle(title)
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        # Tạo series
        self.series = QLineSeries()
        self.series.setName(f"{self.chart_type} Usage (%)")
        if self.chart_type == "CPU":
            self.series.setColor(Qt.GlobalColor.blue)
        else:
            self.series.setColor(Qt.GlobalColor.red)
        
        # Thêm series vào chart
        self.chart.addSeries(self.series)
        
        # Tạo và cấu hình trục X (thời gian)
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time (seconds)")
        self.axis_x.setRange(0, 60)  # Hiển thị 60 giây
        self.axis_x.setLabelFormat("%d")
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.series.attachAxis(self.axis_x)
        
        # Tạo và cấu hình trục Y (phần trăm)
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Usage (%)")
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.axis_y)
        
        # Tạo chart view
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Đặt kích thước tối thiểu để chart hiển thị đúng
        self.chart_view.setMinimumSize(400, 250)
    
    def setup_fallback_ui(self):
        """Thiết lập giao diện fallback khi không có Qt Charts"""
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setText(
            f"⚠️ Qt Charts không khả dụng\n\n"
            "Vui lòng cài đặt:\n"
            "1. pip install PyQt6-Charts\n"
            "2. Cài đặt Qt6 system libraries:\n"
            "   Ubuntu/Debian: sudo apt-get install qt6-base-dev libqt6charts6\n"
            "   Fedora: sudo dnf install qt6-qtbase-devel qt6-qtcharts\n"
            "   Arch: sudo pacman -S qt6-base qt6-charts"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.chart_view = self  # Fallback: trả về chính widget này
    
    def add_data_point(self, value):
        """Thêm điểm dữ liệu mới vào biểu đồ"""
        if not CHARTS_AVAILABLE:
            return
        
        # Nếu đây là dữ liệu thật đầu tiên và có dữ liệu mẫu, reset lại
        if len(self.time_data) > 0 and self.time_data[0] < 0:
            # Xóa dữ liệu mẫu và reset start_time
            self.time_data.clear()
            self.data_values.clear()
            self.start_time = time.time()
            # Reset trục X về 0-60
            self.axis_x.setRange(0, 60)
        
        current_time = time.time() - self.start_time
        
        # Thêm dữ liệu mới
        self.time_data.append(current_time)
        self.data_values.append(value)
        
        # Giới hạn số điểm dữ liệu
        if len(self.time_data) > self.max_points:
            self.time_data.pop(0)
            self.data_values.pop(0)
        
        # Cập nhật series
        self.series.clear()
        
        for i, t in enumerate(self.time_data):
            self.series.append(t, self.data_values[i])
        
        # Cập nhật phạm vi trục X để cuộn theo thời gian
        if current_time > 60:
            self.axis_x.setRange(current_time - 60, current_time)
        else:
            self.axis_x.setRange(0, 60)
    
    def update_chart(self):
        """Cập nhật biểu đồ"""
        pass
    
    def start_monitoring(self, interval=1000):
        """Bắt đầu giám sát với interval (ms)"""
        self.timer.start(interval)
    
    def stop_monitoring(self):
        """Dừng giám sát"""
        self.timer.stop()
    
    def get_chart_view(self):
        """Trả về QChartView để có thể thêm vào layout"""
        return self.chart_view


class SystemChartsManager:
    """Quản lý cả 2 chart CPU và RAM, nhận dữ liệu từ SystemMonitor"""
    
    def __init__(self, monitor=None):
        """
        monitor: SystemMonitor instance để lấy dữ liệu
        """
        self.monitor = monitor
        self.cpu_chart = SingleChart("CPU")
        self.ram_chart = SingleChart("RAM")
        
        # Kết nối với monitor nếu có
        if monitor:
            monitor.timer.timeout.connect(self.update_from_monitor)
    
    def update_from_monitor(self):
        """Cập nhật dữ liệu từ SystemMonitor"""
        if not self.monitor:
            return
        
        try:
            cpu_percent = getattr(self.monitor, 'current_cpu_percent', 0)
            ram_percent = getattr(self.monitor, 'current_ram_percent', 0)
            
            self.cpu_chart.add_data_point(cpu_percent)
            self.ram_chart.add_data_point(ram_percent)
        except Exception as e:
            print(f"Error updating chart data: {e}")
    
    def update_data(self, cpu_percent, ram_percent):
        """Cập nhật dữ liệu trực tiếp (nếu không dùng SystemMonitor)"""
        self.cpu_chart.add_data_point(cpu_percent)
        self.ram_chart.add_data_point(ram_percent)
    
    def start_monitoring(self, interval=2000):
        """Bắt đầu giám sát"""
        self.cpu_chart.start_monitoring(interval)
        self.ram_chart.start_monitoring(interval)
    
    def stop_monitoring(self):
        """Dừng giám sát"""
        self.cpu_chart.stop_monitoring()
        self.ram_chart.stop_monitoring()
    
    def get_cpu_chart_view(self):
        """Trả về CPU chart view"""
        return self.cpu_chart.get_chart_view()
    
    def get_ram_chart_view(self):
        """Trả về RAM chart view"""
        return self.ram_chart.get_chart_view()


class SystemChart(QWidget):
    """Widget hiển thị biểu đồ CPU và RAM usage theo thời gian (giữ lại để tương thích)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Dữ liệu lịch sử (lưu tối đa 60 điểm)
        self.max_points = 60
        self.time_data = []
        self.cpu_data = []
        self.ram_data = []
        
        # Timer để cập nhật dữ liệu
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.start_time = time.time()
        
        if CHARTS_AVAILABLE:
            self.setup_ui()
        else:
            self.setup_fallback_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện với Qt Charts"""
        # Tạo chart
        self.chart = QChart()
        self.chart.setTitle("System Resource Usage")
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        # Tạo series cho CPU và RAM
        self.cpu_series = QLineSeries()
        self.cpu_series.setName("CPU Usage (%)")
        self.cpu_series.setColor(Qt.GlobalColor.blue)
        
        self.ram_series = QLineSeries()
        self.ram_series.setName("RAM Usage (%)")
        self.ram_series.setColor(Qt.GlobalColor.red)
        
        # Thêm series vào chart
        self.chart.addSeries(self.cpu_series)
        self.chart.addSeries(self.ram_series)
        
        # Tạo và cấu hình trục X (thời gian)
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time (seconds)")
        self.axis_x.setRange(0, 60)  # Hiển thị 60 giây
        self.axis_x.setLabelFormat("%d")
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.cpu_series.attachAxis(self.axis_x)
        self.ram_series.attachAxis(self.axis_x)
        
        # Tạo và cấu hình trục Y (phần trăm)
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Usage (%)")
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.cpu_series.attachAxis(self.axis_y)
        self.ram_series.attachAxis(self.axis_y)
        
        # Tạo chart view
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Đặt kích thước tối thiểu để chart hiển thị đúng
        self.chart_view.setMinimumSize(400, 300)
    
    def setup_fallback_ui(self):
        """Thiết lập giao diện fallback khi không có Qt Charts"""
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setText(
            "⚠️ Qt Charts không khả dụng\n\n"
            "Vui lòng cài đặt:\n"
            "1. pip install PyQt6-Charts\n"
            "2. Cài đặt Qt6 system libraries:\n"
            "   Ubuntu/Debian: sudo apt-get install qt6-base-dev libqt6charts6\n"
            "   Fedora: sudo dnf install qt6-qtbase-devel qt6-qtcharts\n"
            "   Arch: sudo pacman -S qt6-base qt6-charts"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.chart_view = self  # Fallback: trả về chính widget này
    
    def add_data_point(self, cpu_percent, ram_percent):
        """Thêm điểm dữ liệu mới vào biểu đồ"""
        if not CHARTS_AVAILABLE:
            return  # Không làm gì nếu không có charts
        
        # Nếu đây là dữ liệu thật đầu tiên và có dữ liệu mẫu, reset lại
        if len(self.time_data) > 0 and self.time_data[0] < 0:
            # Xóa dữ liệu mẫu và reset start_time
            self.time_data.clear()
            self.cpu_data.clear()
            self.ram_data.clear()
            self.start_time = time.time()
            # Reset trục X về 0-60
            self.axis_x.setRange(0, 60)
        
        current_time = time.time() - self.start_time
        
        # Thêm dữ liệu mới
        self.time_data.append(current_time)
        self.cpu_data.append(cpu_percent)
        self.ram_data.append(ram_percent)
        
        # Giới hạn số điểm dữ liệu
        if len(self.time_data) > self.max_points:
            self.time_data.pop(0)
            self.cpu_data.pop(0)
            self.ram_data.pop(0)
        
        # Cập nhật series
        self.cpu_series.clear()
        self.ram_series.clear()
        
        for i, t in enumerate(self.time_data):
            self.cpu_series.append(t, self.cpu_data[i])
            self.ram_series.append(t, self.ram_data[i])
        
        # Cập nhật phạm vi trục X để cuộn theo thời gian
        if current_time > 60:
            self.axis_x.setRange(current_time - 60, current_time)
        else:
            self.axis_x.setRange(0, 60)
    
    def update_chart(self):
        """Cập nhật biểu đồ (có thể override để lấy dữ liệu từ SystemMonitor)"""
        pass
    
    def start_monitoring(self, interval=1000):
        """Bắt đầu giám sát với interval (ms)"""
        self.timer.start(interval)
    
    def stop_monitoring(self):
        """Dừng giám sát"""
        self.timer.stop()
    
    def get_chart_view(self):
        """Trả về QChartView để có thể thêm vào layout"""
        return self.chart_view

