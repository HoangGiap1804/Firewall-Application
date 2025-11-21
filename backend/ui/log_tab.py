from PyQt6 import QtWidgets
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtGui import QColor
import re
from backend.notifications import send_attack_alert, send_notification
from datetime import datetime
import threading
import subprocess

Roles = [
    "in", "out", "mac", "src", "dst", "len", "tos", "prec",
    "ttl", "id", "proto", "spt", "dpt", "len2"
]

def parse_message(msg: str):
    """Phân tích dòng log."""
    result = {k: "" for k in Roles}
    for key, val in re.findall(r"(\b[A-Z]+)=([^\s]+)", msg):
        k = key.lower()
        if k in result:
            result[k] = val
    return result

blocked_ips = set()

def block_ip(ip):
    """
    Chặn IP bằng iptables (Linux). 
    Có thể thay bằng nftables nếu bạn dùng nft.
    """
    try:
        # Kiểm tra IP đã bị chặn chưa
        result = subprocess.run(["iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print(f"⚠️ IP {ip} đã bị chặn trước đó.")
            return

        subprocess.run(["sudo", "iptables", "-I", "INPUT", "1", "-s", ip, "-j", "DROP"], check=True)
        print(f"🚫 Đã chặn IP: {ip}")
    except Exception as e:
        print(f"❌ Lỗi khi chặn IP {ip}: {e}")

class LogTab(QtWidgets.QWidget):
    def __init__(self, tableWidget):
        super().__init__()
        self.tableWidget = tableWidget

        self.tableWidget.setColumnCount(len(Roles))
        self.tableWidget.setHorizontalHeaderLabels([r.upper() for r in Roles])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        # Bắt đầu đọc log kernel
        self.process = QProcess()
        self.process.setProgram("tail")
        self.process.setArguments(["-f", "/var/log/kern.log"])
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.start()

    def read_log(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.strip().splitlines():
            fields = parse_message(line)
            if all(v == "" for v in fields.values()):
                continue

            src_ip = fields.get("src", "")
            if src_ip in blocked_ips:
                # ❌ Bỏ qua log từ IP đã bị chặn
                continue
            
            # Kiểm tra xem có đang ở gần cuối bảng không
            scroll_bar = self.tableWidget.verticalScrollBar()
            is_near_bottom = False
            if scroll_bar:
                max_scroll = scroll_bar.maximum()
                current_scroll = scroll_bar.value()
                # Nếu đang ở trong vòng 10 pixels từ cuối, coi như đang ở cuối
                is_near_bottom = (max_scroll - current_scroll) <= 10
            
            # Thêm dòng vào bảng hiển thị
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)
            bg = QColor("#f0f0f0") if row % 2 == 0 else QColor("white")

            attack_patterns = {
                "PING_FLOOD": ("ICMP Flood", "High"),
                "SYN_FLOOD": ("SYN Flood", "High"),
                "IP Spoofing": ("IP Spoofing", "Critical"),
                "Port Scan": ("Port Scan", "Medium"),
                "Invalid Packet": ("Invalid Packet", "Medium"),
                "Broadcast Control": ("Broadcast Attack", "High"),
                "Outbound Protection": ("Outbound Attack", "Medium"),
                "FIN/XMAS/NULL Scan": ("Stealth Scan", "High"),
            }

            # 🔥 Kiểm tra từng loại tấn công
            for pattern, (attack_type, severity) in attack_patterns.items():
                if pattern in line:
                    print(f"⚠️ {attack_type} detected in log:", line)

                    src_ip = fields.get("src", "Unknown")
                    log_time = fields.get("DATE", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                    title = f"🚨 Phát hiện tấn công {attack_type}"
                    message = f"Từ IP: {src_ip}\nThời gian: {log_time}\nMức độ: {severity}"
                    bg = QColor("#db5858")

                    # 🔒 Chặn IP nếu chưa chặn
                    if src_ip and src_ip not in blocked_ips:
                        blocked_ips.add(src_ip)
                        threading.Thread(target=block_ip, args=(src_ip,), daemon=True).start()

                    # 📢 Gửi thông báo hệ thống
                    send_notification(title, message)

                    # 📧 Gửi email cảnh báo
                    def send_alert_thread():
                        try:
                            send_attack_alert(attack_type, src_ip, severity, log_time)
                        except Exception as e:
                            print("❌ Error sending alert email:", e)

                    threading.Thread(target=send_alert_thread, daemon=True).start()
                    break  # ✅ Dừng lại nếu đã match 1 loại tấn công


            for c, k in enumerate(Roles):
                item = QTableWidgetItem(fields[k])
                item.setBackground(bg)
                self.tableWidget.setItem(row, c, item)
            
            # Chỉ tự động cuộn xuống nếu đang ở gần cuối bảng
            if is_near_bottom:
                self.tableWidget.scrollToBottom()