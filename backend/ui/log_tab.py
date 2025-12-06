from PyQt6 import QtWidgets
from PyQt6.QtCore import QProcess, QDate
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QColor
import re
from backend.notifications import send_attack_alert, send_notification
from datetime import datetime
import threading
import subprocess
import os
from pathlib import Path

Roles = [
    "time", "in", "out", "mac", "src", "dst", "len", "tos", "prec",
    "ttl", "id", "proto", "spt", "dpt", "len2"
]

def is_iptables_log(line: str) -> bool:
    """
    Kiểm tra xem dòng log có phải là log iptables không
    
    Log iptables có thể từ tất cả các chains:
    - INPUT, OUTPUT, FORWARD (built-in chains)
    - Các custom chains (ICMP_FLOOD, SYN_FLOOD, PORT_SCAN, etc.)
    
    Log iptables thường có:
    - Chứa "IPTables-" (IPTables-OUTPUT, IPTables-INPUT, IPTables-FORWARD, etc.)
    - Hoặc có các field đặc trưng như IN=, OUT=, SRC=, DST=, PROTO=
    - Hoặc có log prefix từ các custom chains (PING_FLOOD, SYN_FLOOD, PORT_SCAN, etc.)
    """
    if not line or not isinstance(line, str):
        return False
    
    # Kiểm tra prefix IPTables- (hỗ trợ tất cả chains: INPUT, OUTPUT, FORWARD, và custom chains)
    if "IPTables-" in line:
        return True
    
    # Kiểm tra log prefix từ các custom chains (không chỉ INPUT)
    custom_chain_prefixes = [
        "PING_FLOOD", "SYN_FLOOD", "PORT_SCAN", "IP_SPOOFING", 
        "INVALID_PKT", "BROADCAST_CTRL", "OUTBOUND_PROTECT",
        "FIN_XMAS_NULL_SCAN", "SSH_FTP_BRUTE", "FIN_SCAN", 
        "XMAS_SCAN", "NULL_SCAN", "BROADCAST_PKT"
    ]
    for prefix in custom_chain_prefixes:
        if f"{prefix}:" in line:
            return True
    
    # Kiểm tra các field đặc trưng của iptables log
    # Log iptables thường có ít nhất 2 trong các field sau: IN=, OUT=, SRC=, DST=, PROTO=
    iptables_fields = ["IN=", "OUT=", "SRC=", "DST=", "PROTO="]
    field_count = sum(1 for field in iptables_fields if field in line)
    
    # Nếu có ít nhất 2 field đặc trưng, coi như là log iptables (từ bất kỳ chain nào)
    if field_count >= 2:
        return True
    
    return False

def parse_message(msg: str, timestamp: str = ""):
    """Phân tích dòng log."""
    result = {k: "" for k in Roles}
    
    # Lưu timestamp nếu có
    if timestamp:
        result["time"] = timestamp
    else:
        # Thử parse timestamp từ đầu dòng log nếu có format [YYYY-MM-DD HH:MM:SS]
        timestamp_match = re.match(r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]', msg)
        if timestamp_match:
            result["time"] = timestamp_match.group(1)
    
    # Parse các field khác
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

        cmd = ["iptables", "-I", "INPUT", "1", "-s", ip, "-j", "DROP"]
        if os.geteuid() != 0:
            cmd.insert(0, "sudo")
        
        subprocess.run(cmd, check=True)
        print(f"🚫 Đã chặn IP: {ip}")
    except Exception as e:
        print(f"❌ Lỗi khi chặn IP {ip}: {e}")

class LogTab(QtWidgets.QWidget):
    def __init__(self, tableWidget, date_edit=None, load_button=None, realtime_button=None):
        super().__init__()
        self.tableWidget = tableWidget

        self.tableWidget.setColumnCount(len(Roles))
        self.tableWidget.setHorizontalHeaderLabels([r.upper() for r in Roles])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        # Tạo thư mục logs nếu chưa có
        self.logs_dir = Path(__file__).parent.parent.parent / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # File log hiện tại (mỗi ngày một file)
        self.current_log_file = None
        self.current_log_date = None
        self._update_log_file()
        
        # Trạng thái: True = real-time mode, False = history mode
        self.is_realtime_mode = True

        # Lưu các widget
        self.dateEdit = date_edit
        self.loadLogButton = load_button
        self.realtimeLogButton = realtime_button
        
        # Nếu không có widget, thử tìm từ parent
        if not self.dateEdit or not self.loadLogButton or not self.realtimeLogButton:
            self._find_widgets()
        
        # Thiết lập UI cho date picker
        self._setup_date_picker()

        # Bắt đầu đọc log kernel
        self.process = QProcess()
        self.process.setProgram("tail")
        self.process.setArguments(["-f", "/var/log/kern.log"])
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.start()
    
    def _find_widgets(self):
        """Tìm các widget cần thiết từ parent nếu chưa được truyền vào"""
        if not self.dateEdit:
            parent = self.tableWidget.parent()
            while parent:
                date_edit = parent.findChild(QtWidgets.QDateEdit, "logDateEdit")
                if date_edit:
                    self.dateEdit = date_edit
                    break
                parent = parent.parent()
        
        if not self.loadLogButton or not self.realtimeLogButton:
            parent = self.tableWidget.parent()
            while parent:
                load_button = parent.findChild(QtWidgets.QPushButton, "loadLogButton")
                realtime_button = parent.findChild(QtWidgets.QPushButton, "realtimeLogButton")
                if load_button:
                    self.loadLogButton = load_button
                if realtime_button:
                    self.realtimeLogButton = realtime_button
                if self.loadLogButton and self.realtimeLogButton:
                    break
                parent = parent.parent()
    
    def _setup_date_picker(self):
        """Thiết lập date picker và kết nối signals"""
        try:
            if self.dateEdit:
                # Đặt ngày hiện tại
                today = QDate.currentDate()
                self.dateEdit.setDate(today)
                self.dateEdit.setMaximumDate(today)  # Không cho chọn ngày tương lai
                
                # Kết nối signal cho nút "Xem Log"
                if self.loadLogButton:
                    self.loadLogButton.clicked.connect(self.on_load_log_clicked)
                
                # Kết nối signal cho nút "Log Real-time"
                if self.realtimeLogButton:
                    self.realtimeLogButton.clicked.connect(self.on_realtime_log_clicked)
            else:
                print("⚠️ Không tìm thấy date picker widget")
        except Exception as e:
            print(f"⚠️ Lỗi khi thiết lập date picker: {e}")
            import traceback
            traceback.print_exc()
    
    def on_load_log_clicked(self):
        """Xử lý khi nhấn nút 'Xem Log'"""
        try:
            if not self.dateEdit:
                QMessageBox.warning(None, "Lỗi", "Không tìm thấy date picker")
                return
            
            selected_date = self.dateEdit.date()
            date_str = selected_date.toString("yyyy-MM-dd")
            
            # Tạo đường dẫn file log
            log_file_path = self.logs_dir / f"firewall_log_{date_str}.log"
            
            if not log_file_path.exists():
                QMessageBox.information(
                    None,
                    "Không tìm thấy log",
                    f"Không tìm thấy file log cho ngày {date_str}.\n\n"
                    f"Đường dẫn: {log_file_path}"
                )
                return
            
            # Dừng real-time mode
            self.is_realtime_mode = False
            if self.process.state() == QProcess.ProcessState.Running:
                self.process.kill()
                self.process.waitForFinished()
            
            # Xóa dữ liệu cũ
            self.tableWidget.setRowCount(0)
            
            # Load log từ file
            self.display_log_history(str(log_file_path), max_lines=5000)
            
            QMessageBox.information(
                None,
                "Thành công",
                f"Đã tải log cho ngày {date_str}"
            )
        except Exception as e:
            print(f"❌ Lỗi khi load log: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Lỗi khi tải log: {str(e)}")
    
    def on_realtime_log_clicked(self):
        """Xử lý khi nhấn nút 'Log Real-time'"""
        try:
            # Xóa dữ liệu cũ
            self.tableWidget.setRowCount(0)
            
            # Bật lại real-time mode
            self.is_realtime_mode = True
            
            # Khởi động lại process nếu chưa chạy
            if self.process.state() != QProcess.ProcessState.Running:
                self.process.setProgram("tail")
                self.process.setArguments(["-f", "/var/log/kern.log"])
                self.process.readyReadStandardOutput.connect(self.read_log)
                self.process.start()
            
            QMessageBox.information(
                None,
                "Real-time Mode",
                "Đã chuyển sang chế độ xem log real-time"
            )
        except Exception as e:
            print(f"❌ Lỗi khi chuyển sang real-time mode: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Lỗi khi chuyển sang real-time mode: {str(e)}")
    
    def _update_log_file(self):
        """Cập nhật file log theo ngày hiện tại"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.current_log_date != today:
            self.current_log_date = today
            log_filename = f"firewall_log_{today}.log"
            self.current_log_file = self.logs_dir / log_filename
    
    def _save_log_to_file(self, line: str):
        """Lưu dòng log vào file với timestamp (chỉ lưu log iptables)"""
        try:
            # Chỉ lưu log iptables
            if not is_iptables_log(line):
                return
            
            self._update_log_file()
            if self.current_log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {line}\n")
        except Exception as e:
            print(f"❌ Lỗi khi lưu log vào file: {e}")
    
    def load_log_history(self, log_file_path: str = None, max_lines: int = 1000):
        """
        Đọc lịch sử log từ file
        
        Args:
            log_file_path: Đường dẫn đến file log. Nếu None, đọc file log của ngày hiện tại
            max_lines: Số dòng tối đa để đọc (mặc định 1000)
        
        Returns:
            List các dòng log đã parse
        """
        try:
            if log_file_path is None:
                self._update_log_file()
                log_file_path = str(self.current_log_file)
            
            if not os.path.exists(log_file_path):
                print(f"⚠️ File log không tồn tại: {log_file_path}")
                return []
            
            logs = []
            with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                # Đọc từ cuối file lên (log mới nhất)
                for line in reversed(lines[-max_lines:]):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse timestamp và log content
                    # Format: [YYYY-MM-DD HH:MM:SS] log content
                    if line.startswith("[") and "]" in line:
                        timestamp_end = line.index("]")
                        timestamp = line[1:timestamp_end]
                        log_content = line[timestamp_end + 1:].strip()
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_content = line
                    
                    # Chỉ xử lý log iptables
                    if not is_iptables_log(log_content):
                        continue
                    
                    fields = parse_message(log_content, timestamp)
                    # Đảm bảo timestamp được lưu vào field "time"
                    if not fields.get("time"):
                        fields["time"] = timestamp
                    
                    if any(v != "" for v in fields.values()):
                        logs.append({
                            "timestamp": timestamp,
                            "content": log_content,
                            "fields": fields
                        })
            
            return logs
        except Exception as e:
            print(f"❌ Lỗi khi đọc lịch sử log: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_available_log_files(self):
        """
        Lấy danh sách các file log có sẵn
        
        Returns:
            List các tuple (file_path, file_name, date)
        """
        try:
            if not self.logs_dir.exists():
                return []
            
            log_files = []
            for file_path in sorted(self.logs_dir.glob("firewall_log_*.log"), reverse=True):
                file_name = file_path.name
                # Extract date from filename: firewall_log_YYYY-MM-DD.log
                try:
                    date_str = file_name.replace("firewall_log_", "").replace(".log", "")
                    file_size = file_path.stat().st_size
                    log_files.append((str(file_path), file_name, date_str, file_size))
                except Exception:
                    continue
            
            return log_files
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách file log: {e}")
            return []
    
    def display_log_history(self, log_file_path: str = None, max_lines: int = 5000):
        """
        Hiển thị lịch sử log vào bảng
        
        Args:
            log_file_path: Đường dẫn đến file log. Nếu None, đọc file log của ngày hiện tại
            max_lines: Số dòng tối đa để hiển thị (mặc định 5000)
        """
        try:
            # Xóa dữ liệu cũ
            self.tableWidget.setRowCount(0)
            
            # Hiển thị thông báo đang tải
            if hasattr(self, 'tableWidget'):
                self.tableWidget.setSortingEnabled(False)  # Tắt sorting để tăng tốc độ
            
            logs = self.load_log_history(log_file_path, max_lines)
            
            if not logs:
                print("⚠️ Không có log nào để hiển thị")
                return
            
            # Lọc các log hợp lệ (có dữ liệu và không bị chặn)
            valid_logs = []
            for log_data in logs:
                fields = log_data["fields"]
                # Bỏ qua nếu không có dữ liệu
                if all(v == "" for v in fields.values()):
                    continue
                
                src_ip = fields.get("src", "")
                if src_ip in blocked_ips:
                    continue
                
                valid_logs.append(log_data)
            
            if not valid_logs:
                print("⚠️ Không có log hợp lệ để hiển thị")
                return
            
            # Chuẩn bị dữ liệu trước khi thêm vào bảng
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
            
            # Thêm tất cả rows cùng lúc để tăng hiệu năng
            self.tableWidget.setRowCount(len(valid_logs))
            
            for row_idx, log_data in enumerate(valid_logs):
                fields = log_data["fields"]
                log_content = log_data["content"]
                
                # Xác định màu nền
                bg = QColor("#f0f0f0") if row_idx % 2 == 0 else QColor("white")
                
                # Kiểm tra attack patterns
                for pattern, (attack_type, severity) in attack_patterns.items():
                    if pattern in log_content:
                        bg = QColor("#db5858")
                        break
                
                # Thêm các cột dữ liệu
                for c, k in enumerate(Roles):
                    item = QTableWidgetItem(fields[k])
                    item.setBackground(bg)
                    self.tableWidget.setItem(row_idx, c, item)
            
            # Cuộn xuống cuối
            self.tableWidget.scrollToBottom()
            print(f"✅ Đã tải {len(valid_logs)} dòng log từ lịch sử")
        except Exception as e:
            print(f"❌ Lỗi khi hiển thị lịch sử log: {e}")
            import traceback
            traceback.print_exc()

    def read_log(self):
        # Chỉ xử lý log nếu đang ở real-time mode
        if not self.is_realtime_mode:
            return
        
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        for line in data.strip().splitlines():
            # Chỉ xử lý log iptables
            if not is_iptables_log(line):
                continue
            
            # Lưu log vào file với timestamp (chỉ log iptables)
            self._save_log_to_file(line)
            
            # Lấy timestamp hiện tại
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fields = parse_message(line, current_timestamp)
            
            # Đảm bảo timestamp được lưu vào field "time"
            if not fields.get("time"):
                fields["time"] = current_timestamp
            
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
                    log_time = fields.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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