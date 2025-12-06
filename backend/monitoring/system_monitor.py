import os
import time
import subprocess
from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from PyQt6.QtWidgets import QLabel
from backend.notifications import send_malware_alert, send_performance_alert
import re
import psutil

CONTAINER_NAME = "ubuntu"
CGROUP_BASE = f"/sys/fs/cgroup/machine.slice/machine-{CONTAINER_NAME}.scope"


class SystemMonitor(QObject):
    def __init__(self, ui, interval=2000):
        super().__init__()
        self.ui = ui
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(interval)

        # Biến tạm cho tính toán CPU & Network
        self.prev_cpu_usage = 0
        self.prev_time = time.time()
        self.prev_net_rx = 0
        self.prev_net_tx = 0

        # Tìm interface veth tương ứng
        self.veth_iface = self.find_veth()

         # --- THÊM ---
        self.prev_cpu_percent = 0
        
        # Giá trị hiện tại để chart có thể truy cập
        self.current_cpu_percent = 0
        self.current_ram_percent = 0
        self.current_temperature = 0
        self.current_network_rx = 0  # bytes per second
        self.current_network_tx = 0  # bytes per second


        self.CPU_MAX_PERCENT = 85      # CPU vượt ngưỡng nguy hiểm
        
        self.last_ram_alert_time = 0
        self.RAM_ALERT_COOLDOWN = 60


    # =======================
    # === Update toàn bộ ===
    # =======================
    @pyqtSlot()
    def update_stats(self):
        self.update_cpu()
        self.update_ram()
        self.update_disk()
        self.update_network()
        self.update_temperature()
        self.update_network_traffic()
        self.update_services()

    # =======================
    # === RAM ===
    # =======================
    def update_ram(self):
        try:
            mem_file = os.path.join(CGROUP_BASE, "memory.current")
            if not os.path.exists(mem_file):
                return

            with open(mem_file) as f:
                used_bytes = int(f.read().strip())

            # Tổng RAM host (để tính %)
            with open("/proc/meminfo") as f:
                total_kb = int([l.split()[1] for l in f if l.startswith("MemTotal:")][0])
            total_bytes = total_kb * 1024

            used_mb = used_bytes / (1024 ** 2)
            percent = used_bytes / total_bytes * 100
            
            # Lưu giá trị để chart có thể truy cập
            self.current_ram_percent = percent
            
            # Check RAM > 90%
            if percent > 90:
                now = time.time()
                now = time.time()
                if now - self.last_ram_alert_time >= self.RAM_ALERT_COOLDOWN:
                    send_performance_alert(
                        resource_type="RAM",
                        usage_value=f"{percent:.1f}% (>90%)",
                        severity="high"
                    )
                    self.last_ram_alert_time = now
                    # Optional: Add local visual warning if needed, e.g. update label color
                    self.show_alert(f"RAM Alert: {percent:.1f}%")






            label = self.ui.findChild(QLabel, "label_ram")
            if label:
                label.setText(f"{used_mb:.1f} MB ({percent:.1f}%)")

        except Exception as e:
            print("❌ RAM error:", e)

    # =======================
    # === CPU ===
    # =======================
    def update_cpu(self):
        try:
            cpu_file = os.path.join(CGROUP_BASE, "cpu.stat")
            if not os.path.exists(cpu_file):
                return

            with open(cpu_file) as f:
                data = dict(line.strip().split() for line in f.readlines())

            usage_usec = int(data.get("usage_usec", 0))
            now = time.time()
            delta_time = now - self.prev_time
            delta_usage = usage_usec - self.prev_cpu_usage

            cpu_percent = (delta_usage / 1e6) / delta_time * 100 / os.cpu_count()
            
            # Lưu giá trị để chart có thể truy cập
            self.current_cpu_percent = cpu_percent

            self.prev_cpu_usage = usage_usec
            self.prev_time = now

            label = self.ui.findChild(QLabel, "label_cpu")
            if label:
                label.setText(f"{cpu_percent:.1f}%")

        except Exception as e:
            print("❌ CPU error:", e)

    # =======================
    # === Disk ===
    # =======================
    def update_disk(self):
        try:
            io_file = os.path.join(CGROUP_BASE, "io.stat")
            if not os.path.exists(io_file):
                return

            read_bytes = 0
            write_bytes = 0

            with open(io_file) as f:
                for line in f:
                    parts = line.strip().split()
                    for p in parts:
                        if p.startswith("rbytes="):
                            read_bytes += int(p.split("=")[1])
                        elif p.startswith("wbytes="):
                            write_bytes += int(p.split("=")[1])

            label = self.ui.findChild(QLabel, "label_disk")
            if label:
                label.setText(f"↑ {write_bytes / 1e6:.1f} MB  ↓ {read_bytes / 1e6:.1f} MB")

        except Exception as e:
            print("❌ Disk error:", e)

    # =======================
    # === Network ===
    # =======================
    def find_veth(self):
        """
        Tự tìm interface veth tương ứng với container trong `ip link`
        (nspawn đặt tên theo pattern veth<container>-xxxx)
        """
        try:
            out = subprocess.check_output(["ip", "link"], text=True)
            for line in out.splitlines():
                if f"veth{CONTAINER_NAME}" in line:
                    return line.split(":")[1].strip()
        except:
            pass
        return None

    def update_network(self):
        """
        Đếm số tiến trình có kết nối mạng (ESTABLISHED).
        Thử: 1) chạy ss trong container bằng machinectl; 2) fallback: psutil trên host.
        Cập nhật QLabel 'label_netproc' (hoặc gộp vào 'label_net' nếu label_netproc không tồn tại).
        """
        count = 0

        # ---- 1) Thử chạy ss trong container (nếu máy đã cấu hình sudo machinectl không hỏi mật khẩu) ----
        # ---- 1) Thử chạy ss trong container (nếu máy đã cấu hình sudo machinectl không hỏi mật khẩu) ----
        try:
            cmd = ["machinectl", "shell", f"root@{CONTAINER_NAME}", "/bin/ss", "-tunp", "state", "established"]
            if os.geteuid() != 0:
                cmd.insert(0, "sudo")
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            out = proc.stdout or ""
            if out:
                # ss output contains pid=NNN,parse all pid numbers and dedupe
                pids = set(re.findall(r"pid=(\d+),", out))
                # sometimes ss prints "users:(("... with pid; also handle "pid=1234,fd=6"
                count = len(pids)
        except Exception:
            # im lặng nếu lỗi — chuyển sang fallback
            count = 0

        # ---- 2) Fallback: dùng psutil trên host để đếm tiến trình có connection ESTABLISHED ----
        if count == 0:
            try:
                conns = psutil.net_connections(kind='inet')  # requires psutil
                pids = set()
                for c in conns:
                    # filter ESTABLISHED only and valid pid
                    # c.status may be 'ESTABLISHED' or other states
                    if getattr(c, "status", "").upper() == "ESTABLISHED" and c.pid:
                        pids.add(c.pid)
                count = len(pids)
            except Exception as e:
                print("❌ Network-process fallback error:", e)
                count = 0

        # ---- Cập nhật QLabel ----
        label_proc = self.ui.findChild(QLabel, "label_netproc")
        if label_proc:
            label_proc.setText(f"Net procs: {count} kết nối")
        else:
            # nếu không có label_netproc thì gộp vào label_net (nếu có)
            label_net = self.ui.findChild(QLabel, "label_net")
            if label_net:
                # Lưu text gốc nếu cần (không overwrite throughput info)
                base = label_net.text().split("|")[0].strip() if "|" in label_net.text() else label_net.text().strip()
                label_net.setText(f"{base} | Procs: {count}")

    # =======================
    # === Temperature ===
    # =======================
    def update_temperature(self):
        """Lấy nhiệt độ CPU từ /sys/class/thermal"""
        try:
            # Thử đọc nhiệt độ từ thermal zones
            temp_celsius = None
            for i in range(10):  # Thử các thermal zone 0-9
                try:
                    temp_file = f"/sys/class/thermal/thermal_zone{i}/temp"
                    if os.path.exists(temp_file):
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
            print("❌ Temperature error:", e)
            self.current_temperature = 0

    # =======================
    # === Network Traffic ===
    # =======================
    def update_network_traffic(self):
        """Tính toán network traffic (bytes per second)"""
        try:
            # Lấy thống kê mạng từ psutil
            net_io = psutil.net_io_counters()
            current_rx = net_io.bytes_recv
            current_tx = net_io.bytes_sent
            
            now = time.time()
            delta_time = now - self.prev_time
            
            if delta_time > 0 and self.prev_net_rx > 0:
                # Tính bytes per second
                rx_speed = (current_rx - self.prev_net_rx) / delta_time
                tx_speed = (current_tx - self.prev_net_tx) / delta_time
                
                self.current_network_rx = rx_speed
                self.current_network_tx = tx_speed
            else:
                self.current_network_rx = 0
                self.current_network_tx = 0
            
            self.prev_net_rx = current_rx
            self.prev_net_tx = current_tx
            
        except Exception as e:
            print("❌ Network traffic error:", e)
            self.current_network_rx = 0
            self.current_network_tx = 0

    # =======================
    # === Services ===
    # =======================
    last_service_alert_time = 0
    SERVICE_ALERT_COOLDOWN = 60
    def update_services(self):
        try:
            # Liệt kê dịch vụ đang chạy trong container
            cmd = ["machinectl", "shell", f"root@{CONTAINER_NAME}", "/bin/systemctl", "list-units", "--type=service", "--state=running", "--no-pager"]
            if os.geteuid() != 0:
                cmd.insert(0, "sudo")

            result = subprocess.run(
                cmd,
                capture_output=True, text=True
            )
            running = len([l for l in result.stdout.splitlines() if ".service" in l])

            label = self.ui.findChild(QLabel, "label_service")
            now = time.time()
            if running > 10:
                if now - self.last_service_alert_time >= self.SERVICE_ALERT_COOLDOWN:
                    self.last_service_alert_time = now  # cập nhật lại thời điểm gửi cảnh báo
                    send_malware_alert(
                        malware_type="Service",
                        severity="high"
                    )

            if label:
                label.setText(f"{running} running services")

        except Exception as e:
            print("❌ Service error:", e)

    def show_alert(self, message):
        print("CẢNH BÁO BẢO MẬT")
        print(message)
