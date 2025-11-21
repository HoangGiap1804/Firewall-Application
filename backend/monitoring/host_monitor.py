"""
SystemMonitor cho máy thật (host system), không phải container
"""
import time
import subprocess
from PyQt6.QtCore import QObject, QTimer, pyqtSlot
import psutil


class HostSystemMonitor(QObject):
    """Monitor hệ thống máy thật (host), không phải container"""
    
    def __init__(self, interval=1000):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(interval)  # Cập nhật mỗi 1 giây

        # Biến tạm cho tính toán CPU & Network
        self.prev_cpu_times = psutil.cpu_times()
        self.prev_time = time.time()
        self.prev_net_rx = 0
        self.prev_net_tx = 0

        # Giá trị hiện tại để chart có thể truy cập
        self.current_cpu_percent = 0
        self.current_ram_percent = 0
        self.current_temperature = 0
        self.current_network_rx = 0  # bytes per second
        self.current_network_tx = 0  # bytes per second

    @pyqtSlot()
    def update_stats(self):
        """Cập nhật tất cả thống kê"""
        self.update_cpu()
        self.update_ram()
        self.update_temperature()
        self.update_network_traffic()

    def update_cpu(self):
        """Lấy CPU usage từ psutil"""
        try:
            # Lấy CPU percent (non-blocking)
            cpu_percent = psutil.cpu_percent(interval=None)
            self.current_cpu_percent = cpu_percent
        except Exception as e:
            print("❌ CPU error (host):", e)
            self.current_cpu_percent = 0

    def update_ram(self):
        """Lấy RAM usage từ psutil"""
        try:
            mem = psutil.virtual_memory()
            self.current_ram_percent = mem.percent
        except Exception as e:
            print("❌ RAM error (host):", e)
            self.current_ram_percent = 0

    def update_temperature(self):
        """Lấy nhiệt độ CPU từ /sys/class/thermal hoặc psutil"""
        try:
            temp_celsius = None
            
            # Thử đọc nhiệt độ từ thermal zones
            for i in range(10):  # Thử các thermal zone 0-9
                try:
                    temp_file = f"/sys/class/thermal/thermal_zone{i}/temp"
                    with open(temp_file) as f:
                        temp_millidegrees = int(f.read().strip())
                        temp_celsius = temp_millidegrees / 1000.0
                        break
                except:
                    continue
            
            # Fallback: dùng psutil nếu có
            if temp_celsius is None:
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # Lấy nhiệt độ đầu tiên tìm thấy
                        for name, entries in temps.items():
                            if entries:
                                temp_celsius = entries[0].current
                                break
                except:
                    pass
            
            if temp_celsius is not None:
                self.current_temperature = temp_celsius
            else:
                self.current_temperature = 0
                
        except Exception as e:
            print("❌ Temperature error (host):", e)
            self.current_temperature = 0

    def update_network_traffic(self):
        """Tính toán network traffic (bytes per second) từ lệnh `ip -s link`
        Sử dụng công thức: (dữ liệu mới - dữ liệu cũ) / thời gian
        
        Format output của ip -s link:
        RX:  bytes packets errors dropped  missed   mcast
            11816938   99822      0       0       0       0 
        TX:  bytes packets errors dropped carrier collsns
            11816938   99822      0       0       0       0 
        """
        try:
            # Chạy lệnh ip -s link để lấy thống kê mạng
            result = subprocess.run(
                ["ip", "-s", "link"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise Exception(f"ip -s link failed: {result.stderr}")
            
            # Parse output để lấy tổng RX và TX bytes từ tất cả interfaces
            total_rx_bytes = 0
            total_tx_bytes = 0
            
            lines = result.stdout.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                # Tìm dòng RX: (header line) - có thể có khoảng trắng ở đầu
                if "RX:" in line and "bytes" in line:
                    # Dòng tiếp theo chứa dữ liệu
                    if i + 1 < len(lines):
                        data_line = lines[i + 1].strip()
                        # Loại bỏ tất cả khoảng trắng và tách
                        parts = data_line.split()
                        if len(parts) >= 1:
                            try:
                                rx_bytes = int(parts[0])  # Số đầu tiên là bytes
                                total_rx_bytes += rx_bytes
                            except (ValueError, IndexError) as e:
                                print(f"⚠️ RX parse error: {e}, line: {repr(data_line)}")
                                pass
                # Tìm dòng TX: (header line)
                elif "TX:" in line and "bytes" in line:
                    # Dòng tiếp theo chứa dữ liệu
                    if i + 1 < len(lines):
                        data_line = lines[i + 1].strip()
                        parts = data_line.split()
                        if len(parts) >= 1:
                            try:
                                tx_bytes = int(parts[0])  # Số đầu tiên là bytes
                                total_tx_bytes += tx_bytes
                            except (ValueError, IndexError) as e:
                                print(f"⚠️ TX parse error: {e}, line: {repr(data_line)}")
                                pass
                i += 1
            
            current_rx = total_rx_bytes
            current_tx = total_tx_bytes
            
            now = time.time()
            
            # Kiểm tra nếu đây là lần đầu tiên (chưa có dữ liệu cũ)
            if self.prev_net_rx == 0 and self.prev_net_tx == 0:
                # Lần đầu tiên: chỉ lưu giá trị, chưa tính toán
                if current_rx > 0 or current_tx > 0:
                    self.prev_net_rx = current_rx
                    self.prev_net_tx = current_tx
                    self.prev_time = now
                    self.current_network_rx = 0
                    self.current_network_tx = 0
                return
            
            # Tính delta time (giây)
            delta_time = now - self.prev_time
            
            if delta_time > 0:
                # Tính tốc độ: (dữ liệu mới - dữ liệu cũ) / thời gian
                rx_speed = (current_rx - self.prev_net_rx) / delta_time  # bytes per second
                tx_speed = (current_tx - self.prev_net_tx) / delta_time  # bytes per second
                
                # Đảm bảo giá trị không âm (tránh trường hợp counter reset)
                if rx_speed < 0:
                    rx_speed = 0
                if tx_speed < 0:
                    tx_speed = 0
                
                # Lưu giá trị tốc độ (bytes per second)
                self.current_network_rx = rx_speed
                self.current_network_tx = tx_speed
            
            # Cập nhật giá trị cũ cho lần sau
            self.prev_net_rx = current_rx
            self.prev_net_tx = current_tx
            self.prev_time = now
            
        except Exception as e:
            print(f"❌ Network traffic error (host): {e}")
            import traceback
            traceback.print_exc()
            self.current_network_rx = 0
            self.current_network_tx = 0

