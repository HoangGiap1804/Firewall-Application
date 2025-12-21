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
        self.data_values = []      # For single line charts
        self.rx_values = []        # For Network RX
        self.tx_values = []        # For Network TX
        
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
        self.series_rx = None
        self.series_tx = None
        
        if self.chart_type == "CPU":
            self.series.setName("CPU Usage (%)")
            self.series.setColor(Qt.GlobalColor.blue)
            self.series.setColor(Qt.GlobalColor.blue)
            self.chart.addSeries(self.series)
        elif self.chart_type == "RAM":
            self.series.setName("RAM Usage (%)")
            self.series.setColor(Qt.GlobalColor.red)
            self.series.setColor(Qt.GlobalColor.red)
            self.chart.addSeries(self.series)
        elif self.chart_type == "Temperature":
            self.series.setName("Temperature (°C)")
            self.series.setColor(Qt.GlobalColor.magenta)
            self.series.setColor(Qt.GlobalColor.magenta)
            self.chart.addSeries(self.series)
        elif self.chart_type == "Network":
            # Network displays 2 lines
            self.series = None # Not used for Network
            
            self.series_rx = QLineSeries()
            self.series_rx.setName("RX (In)")
            self.series_rx.setColor(Qt.GlobalColor.green)
            self.chart.addSeries(self.series_rx)
            
            self.series_tx = QLineSeries()
            self.series_tx.setName("TX (Out)")
            self.series_tx.setColor(Qt.GlobalColor.red)
            self.chart.addSeries(self.series_tx)
        else:
            self.series.setName(f"{self.chart_type} Usage (%)")
            self.series.setColor(Qt.GlobalColor.blue)
            self.chart.addSeries(self.series)
        
        # Tạo và cấu hình trục X (thời gian)
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time (seconds)")
        self.axis_x.setRange(0, 60)  # Hiển thị 60 giây
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setLabelFormat("%d")
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        
        # Attach series to X axis
        if self.chart_type == "Network":
            self.series_rx.attachAxis(self.axis_x)
            self.series_tx.attachAxis(self.axis_x)
        else:
            self.series.attachAxis(self.axis_x)
        
        # Tạo và cấu hình trục Y
        self.axis_y = QValueAxis()
        if self.chart_type == "CPU" or self.chart_type == "RAM":
            self.axis_y.setTitleText("Usage (%)")
            self.axis_y.setRange(0, 100)
            self.axis_y.setLabelFormat("%.0f")
        elif self.chart_type == "Temperature":
            self.axis_y.setTitleText("Temperature (°C)")
            self.axis_y.setRange(0, 100)
            self.axis_y.setLabelFormat("%.1f")
        elif self.chart_type == "Network":
            self.axis_y.setTitleText("Traffic (B/s)")
            self.axis_y.setRange(0, 1000000)  # Giá trị mặc định, sẽ tự động điều chỉnh
            self.axis_y.setLabelFormat("%.0f")
        else:
            self.axis_y.setTitleText("Value")
            self.axis_y.setRange(0, 100)
            self.axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        
        if self.chart_type == "Network":
            self.series_rx.attachAxis(self.axis_y)
            self.series_tx.attachAxis(self.axis_y)
        else:
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
            self.time_data.clear()
            self.data_values.clear()
            self.rx_values.clear()
            self.tx_values.clear()
            self.start_time = time.time()
            # Reset trục X về 0-60
            self.axis_x.setRange(0, 60)
        
        current_time = time.time() - self.start_time
        
        # Thêm dữ liệu mới
        self.time_data.append(current_time)
        
        if self.chart_type == "Network":
            if isinstance(value, tuple) and len(value) == 2:
                self.rx_values.append(value[0])
                self.tx_values.append(value[1])
            else:
                # Fallback purely for safety
                self.rx_values.append(value)
                self.tx_values.append(0)
        else:
            self.data_values.append(value)
        
        # Giới hạn số điểm dữ liệu
        if len(self.time_data) > self.max_points:
            self.time_data.pop(0)
            if self.chart_type == "Network":
                if self.rx_values: self.rx_values.pop(0)
                if self.tx_values: self.tx_values.pop(0)
            else:
                self.data_values.pop(0)
        
        # Cập nhật series
        if self.chart_type == "Network":
            self.series_rx.clear()
            self.series_tx.clear()
            for i, t in enumerate(self.time_data):
                if i < len(self.rx_values):
                    self.series_rx.append(t, self.rx_values[i])
                    self.series_tx.append(t, self.tx_values[i])
        else:
            self.series.clear()
            for i, t in enumerate(self.time_data):
                self.series.append(t, self.data_values[i])
        
        # Cập nhật phạm vi trục X để cuộn theo thời gian
        if current_time > 60:
            self.axis_x.setRange(current_time - 60, current_time)
        else:
            self.axis_x.setRange(0, 60)
        
        # Tự động điều chỉnh trục Y cho Network chart
        if self.chart_type == "Network" and len(self.rx_values) > 0:
            # check both rx and tx for max
            all_vals = self.rx_values + self.tx_values
            if not all_vals: return
            
            min_val = min(all_vals)
            max_val = max(all_vals)
            
            # Nếu có dữ liệu, điều chỉnh range
            if max_val > 0:
                # Thêm padding 10% ở trên và dưới
                padding = max(max_val * 0.1, 1000)  # Ít nhất 1000 bytes padding
                y_min = max(0, min_val - padding)
                y_max = max_val + padding
                
                # Đảm bảo range tối thiểu
                if y_max - y_min < 10000:
                    y_max = y_min + 10000
                
                self.axis_y.setRange(y_min, y_max)
            else:
                # Nếu chưa có dữ liệu, dùng range mặc định
                self.axis_y.setRange(0, 1000000)
    
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
    """Quản lý cả 4 chart CPU, RAM, Temperature và Network Traffic, nhận dữ liệu từ SystemMonitor"""
    
    def __init__(self, monitor=None, label_services=None, label_free_disk=None):
        """
        monitor: SystemMonitor instance để lấy dữ liệu
        label_services: QLabel để hiển thị số lượng service
        label_free_disk: QLabel để hiển thị free Disk space
        """
        self.monitor = monitor
        self.label_services = label_services
        self.label_free_disk = label_free_disk
        
        self.cpu_chart = SingleChart("CPU")
        self.ram_chart = SingleChart("RAM")
        self.temp_chart = SingleChart("Temperature")
        self.network_chart = SingleChart("Network")
        
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
            temperature = getattr(self.monitor, 'current_temperature', 0)
            network_rx = getattr(self.monitor, 'current_network_rx', 0)  # bytes per second
            network_tx = getattr(self.monitor, 'current_network_tx', 0)  # bytes per second
            
            # New stats
            services_count = getattr(self.monitor, 'current_services_count', 0)
            disk_free = getattr(self.monitor, 'current_disk_free', 0)
            
            self.cpu_chart.add_data_point(cpu_percent)
            self.ram_chart.add_data_point(ram_percent)
            self.temp_chart.add_data_point(temperature)
            # Pass tuple (rx, tx) for Network chart
            self.network_chart.add_data_point((network_rx, network_tx))
            
            # Update Labels
            if self.label_services:
                self.label_services.setText(f"Active Services: {services_count}")
            
            if self.label_free_disk:
                self.label_free_disk.setText(f"Free Disk: {disk_free:.2f} GB")
                
        except Exception as e:
            print(f"Error updating chart data: {e}")
    
    def update_data(self, cpu_percent, ram_percent, temperature=0, network_mbps=0):
        """Cập nhật dữ liệu trực tiếp (nếu không dùng SystemMonitor)"""
        self.cpu_chart.add_data_point(cpu_percent)
        self.ram_chart.add_data_point(ram_percent)
        self.temp_chart.add_data_point(temperature)
        self.network_chart.add_data_point(network_mbps)
    
    def start_monitoring(self, interval=2000):
        """Bắt đầu giám sát"""
        self.cpu_chart.start_monitoring(interval)
        self.ram_chart.start_monitoring(interval)
        self.temp_chart.start_monitoring(interval)
        self.network_chart.start_monitoring(interval)
    
    def stop_monitoring(self):
        """Dừng giám sát"""
        self.cpu_chart.stop_monitoring()
        self.ram_chart.stop_monitoring()
        self.temp_chart.stop_monitoring()
        self.network_chart.stop_monitoring()
    
    def get_cpu_chart_view(self):
        """Trả về CPU chart view"""
        return self.cpu_chart.get_chart_view()
    
    def get_ram_chart_view(self):
        """Trả về RAM chart view"""
        return self.ram_chart.get_chart_view()
    
    def get_temperature_chart_view(self):
        """Trả về Temperature chart view"""
        return self.temp_chart.get_chart_view()
    
    def get_network_chart_view(self):
        """Trả về Network chart view"""
        return self.network_chart.get_chart_view()


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

