"""
System Monitor sử dụng API Service
"""

import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import QLabel
from service.api_client import get_client
from backend.monitoring.ssh_monitor import SSHMonitor
from backend.sandbox.vmware_manager import VMWareManager
from dotenv import load_dotenv
import os


class LocalStatsWorker(QThread):
    """Worker thread để lấy local stats (SSH/VMWare)"""
    data_loaded = pyqtSignal(tuple) # (used, total, cpu)
    
    def __init__(self, monitor_type, config):
        super().__init__()
        self.monitor_type = monitor_type
        self.config = config
        
    def run(self):
        try:
            if self.monitor_type == 'ssh':
                monitor = SSHMonitor(self.config['user'], self.config['host'])
                stats = monitor.get_stats() # (used, total, cpu)
                self.data_loaded.emit(stats)
            elif self.monitor_type == 'vmware':
                # Note: creating manager every time might be slow? 
                # Better to pass instance, but QThread safety?
                # VMWareManager is just subprocess calls, so it's stateless mostly.
                manager = VMWareManager(self.config['vmx'], self.config['user'], self.config['pass'])
                stats = manager.get_guest_stats()
                self.data_loaded.emit(stats)
        except Exception as e:
            print(f"Local Stats Error: {e}")
            self.data_loaded.emit((0,0,0))

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
            # print(f"❌ Lỗi khi lấy monitoring data: {e}") 
            # Silent fail is better for repetitive poll
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
        
        # Local Monitor Config
        self.local_monitor_type = None
        self.local_config = {}
        self._load_local_config()

        # Giá trị hiện tại để chart có thể truy cập
        self.current_cpu_percent = 0
        self.current_ram_percent = 0
        self.current_temperature = 0
        self.current_network_rx = 0
        self.current_network_tx = 0
        
        self.worker = None  # Worker thread
        self.local_worker = None
        self.is_updating = False  # Flag để tránh update đồng thời

    def _load_local_config(self):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(env_path)
        
        ssh_host = os.getenv("SSH_MONITOR_HOST")
        ssh_user = os.getenv("SSH_MONITOR_USER")
        
        if ssh_host and ssh_user:
            self.local_monitor_type = 'ssh'
            self.local_config = {'host': ssh_host, 'user': ssh_user}
            return

        vmx = os.getenv("VMWARE_VMX_PATH")
        if vmx:
            self.local_monitor_type = 'vmware'
            self.local_config = {
                'vmx': vmx, 
                'user': os.getenv("VMWARE_USER"), 
                'pass': os.getenv("VMWARE_PASSWORD")
            }
    
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
        
        # Update from API (Always needed for Disk/Net/etc)
        self.worker = MonitoringDataWorker(self.client)
        self.worker.data_loaded.connect(self._on_data_loaded)
        self.worker.finished.connect(lambda: setattr(self, 'is_updating', False))
        self.worker.start()
        
        # Update from Local (SSH/VMWare) for CPU/RAM overwrite
        # Make sure to reload config? Maybe occasionally.
        if self.local_monitor_type:
            self.local_worker = LocalStatsWorker(self.local_monitor_type, self.local_config)
            self.local_worker.data_loaded.connect(self._on_local_data_loaded)
            self.local_worker.start()

    def _on_local_data_loaded(self, stats):
        used, total, cpu = stats
        
        # Overwrite CPU
        self.current_cpu_percent = cpu
        if self._label_cpu:
            self._label_cpu.setText(f"{cpu:.1f}%")
            
        # Overwrite RAM
        if total > 0:
            percent = (used / total) * 100
            self.current_ram_percent = percent
            if self._label_ram:
                self._label_ram.setText(f"{used:.1f} MB ({percent:.1f}%)")
    
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

