"""
System Monitor sử dụng API Service
"""

import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import QLabel
from service.api_client import get_client


class MonitoringDataWorker(QThread):
    """Worker thread để lấy monitoring data không block UI"""
    data_loaded = pyqtSignal(dict)
    
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    def run(self):
        """Lấy monitoring data từ API trong thread riêng"""
        try:
            data = self.client.get_monitoring_data()
            self.data_loaded.emit(data)
        except Exception as e:
            print(f"❌ Lỗi khi lấy monitoring data: {e}")
            self.data_loaded.emit({})


class SystemMonitorAPI(QObject):
    """System Monitor sử dụng API Service thay vì truy cập trực tiếp"""
    
    # Signals để cập nhật UI
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, ui, interval=3000):
        super().__init__()
        self.ui = ui
        self.client = get_client()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(interval)  # Tăng từ 2s lên 3s
        
        # Cache widgets để tránh findChild() mỗi lần
        self._label_cpu = None
        self._label_ram = None
        self._label_disk = None
        self._label_netproc = None
        self._label_service = None
        self._cache_widgets()
        
        # Giá trị hiện tại để chart có thể truy cập
        self.current_cpu_percent = 0
        self.current_ram_percent = 0
        self.current_temperature = 0
        self.current_network_rx = 0
        self.current_network_tx = 0
        
        self.worker = None  # Worker thread
        self.is_updating = False  # Flag để tránh update đồng thời
    
    def _cache_widgets(self):
        """Cache các widgets một lần để tránh findChild() mỗi lần"""
        self._label_cpu = self.ui.findChild(QLabel, "label_cpu")
        self._label_ram = self.ui.findChild(QLabel, "label_ram")
        self._label_disk = self.ui.findChild(QLabel, "label_disk")
        self._label_netproc = self.ui.findChild(QLabel, "label_netproc")
        self._label_service = self.ui.findChild(QLabel, "label_service")
    
    def update_stats(self):
        """Cập nhật stats từ API (async)"""
        # Nếu đang update, bỏ qua
        if self.is_updating:
            return
        
        # Nếu worker đang chạy, bỏ qua
        if self.worker and self.worker.isRunning():
            return
        
        self.is_updating = True
        
        # Tạo và chạy worker thread
        self.worker = MonitoringDataWorker(self.client)
        self.worker.data_loaded.connect(self._on_data_loaded)
        self.worker.finished.connect(lambda: setattr(self, 'is_updating', False))
        self.worker.start()
    
    def _on_data_loaded(self, data):
        """Xử lý khi monitoring data đã được load xong"""
        try:
            if not data:
                return
            
            # Cập nhật CPU
            cpu_percent = data.get("cpu_percent", 0)
            self.current_cpu_percent = cpu_percent
            if self._label_cpu:
                self._label_cpu.setText(f"{cpu_percent:.1f}%")
            
            # Cập nhật RAM
            ram_percent = data.get("ram_percent", 0)
            ram_mb = data.get("ram_mb", 0)
            self.current_ram_percent = ram_percent
            if self._label_ram:
                self._label_ram.setText(f"{ram_mb:.1f} MB ({ram_percent:.1f}%)")
            
            # Cập nhật Disk
            disk_read = data.get("disk_read_mb", 0)
            disk_write = data.get("disk_write_mb", 0)
            if self._label_disk:
                self._label_disk.setText(f"↑ {disk_write:.1f} MB  ↓ {disk_read:.1f} MB")
            
            # Cập nhật Network processes
            net_procs = data.get("network_procs", 0)
            if self._label_netproc:
                self._label_netproc.setText(f"Net procs: {net_procs} kết nối")
            
            # Cập nhật Temperature
            temp = data.get("temperature", 0)
            self.current_temperature = temp
            
            # Cập nhật Network traffic
            self.current_network_rx = data.get("network_rx", 0)
            self.current_network_tx = data.get("network_tx", 0)
            
            # Cập nhật Services
            services_count = data.get("services_count", 0)
            if self._label_service:
                self._label_service.setText(f"{services_count} running services")
            
            # Xử lý alerts
            alerts = data.get("alerts", [])
            for alert in alerts[-5:]:  # Chỉ hiển thị 5 alerts gần nhất
                print(f"⚠️ {alert.get('type')}: {alert.get('message')}")
            
            # Emit signal với dữ liệu
            self.stats_updated.emit(data)
            
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật stats: {e}")

