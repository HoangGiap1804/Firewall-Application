"""
System Monitor sử dụng API Service
"""

import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel
from service.api_client import get_client


class SystemMonitorAPI(QObject):
    """System Monitor sử dụng API Service thay vì truy cập trực tiếp"""
    
    # Signals để cập nhật UI
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, ui, interval=2000):
        super().__init__()
        self.ui = ui
        self.client = get_client()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(interval)
        
        # Giá trị hiện tại để chart có thể truy cập
        self.current_cpu_percent = 0
        self.current_ram_percent = 0
        self.current_temperature = 0
        self.current_network_rx = 0
        self.current_network_tx = 0
    
    def update_stats(self):
        """Cập nhật stats từ API"""
        try:
            data = self.client.get_monitoring_data()
            
            # Cập nhật CPU
            cpu_percent = data.get("cpu_percent", 0)
            self.current_cpu_percent = cpu_percent
            label = self.ui.findChild(QLabel, "label_cpu")
            if label:
                label.setText(f"{cpu_percent:.1f}%")
            
            # Cập nhật RAM
            ram_percent = data.get("ram_percent", 0)
            ram_mb = data.get("ram_mb", 0)
            self.current_ram_percent = ram_percent
            label = self.ui.findChild(QLabel, "label_ram")
            if label:
                label.setText(f"{ram_mb:.1f} MB ({ram_percent:.1f}%)")
            
            # Cập nhật Disk
            disk_read = data.get("disk_read_mb", 0)
            disk_write = data.get("disk_write_mb", 0)
            label = self.ui.findChild(QLabel, "label_disk")
            if label:
                label.setText(f"↑ {disk_write:.1f} MB  ↓ {disk_read:.1f} MB")
            
            # Cập nhật Network processes
            net_procs = data.get("network_procs", 0)
            label_proc = self.ui.findChild(QLabel, "label_netproc")
            if label_proc:
                label_proc.setText(f"Net procs: {net_procs} kết nối")
            
            # Cập nhật Temperature
            temp = data.get("temperature", 0)
            self.current_temperature = temp
            
            # Cập nhật Network traffic
            self.current_network_rx = data.get("network_rx", 0)
            self.current_network_tx = data.get("network_tx", 0)
            
            # Cập nhật Services
            services_count = data.get("services_count", 0)
            label = self.ui.findChild(QLabel, "label_service")
            if label:
                label.setText(f"{services_count} running services")
            
            # Xử lý alerts
            alerts = data.get("alerts", [])
            for alert in alerts[-5:]:  # Chỉ hiển thị 5 alerts gần nhất
                print(f"⚠️ {alert.get('type')}: {alert.get('message')}")
            
            # Emit signal với dữ liệu
            self.stats_updated.emit(data)
            
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật stats từ API: {e}")

