import sys, subprocess, threading
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlContext
from PySide6.QtCore import QObject, Signal


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

email = "hgiap1804@gmail.com"
receiver_email = "hgiap1804@gmail.com"
password = "dvmtvtlvqfbcwelw"

class LogWatcher(QObject):
    pingFloodDetected = Signal(dict)  # emit dict chứa các field

    def __init__(self):
        super().__init__()
        # start watching in background thread
        threading.Thread(target=self.watch_logs, daemon=True).start()

    def watch_logs(self):
        """
        Theo dõi journal kernel realtime.
        Nếu log chứa "PING_FLOOD:" thì parse fields và emit signal.
        """
        try:
            proc = subprocess.Popen(
                ["journalctl", "-k", "-f", "-n", "0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            print("Không thể chạy journalctl:", e)
            return

        for line in proc.stdout:
            if "PING_FLOOD:"in line:
                log_data = self.parse_log(line)
                # Gửi notification từ Python
                self.send_notify("Ping flood",log_data)
                self.send_email(sender_email=email, password=password, receiver_email=receiver_email, title="Ping flood",data=log_data)
                
                # Emit cho QML
                self.pingFloodDetected.emit(log_data)
            elif "SYN_FLOOD" in line:
                log_data = self.parse_log(line)
                # Gửi notification từ Python
                self.send_notify("Syn flood",log_data)
                self.send_email(sender_email=email, password=password, receiver_email=receiver_email, title="Syn flood",data=log_data)
                # Emit cho QML
                self.pingFloodDetected.emit(log_data)
                
    def parse_log(self, line: str) -> dict:
        """
        Parse iptables log line để lấy các field.
        Ví dụ log: IN=eth0 OUT= MAC=aa:bb:cc SRC=1.2.3.4 DST=5.6.7.8 LEN=84 TOS=0x00 PREC=0x00 TTL=64 ID=12345 PROTO=ICMP SPT=0 DPT=0 ...
        Trả về dict phù hợp với model QML.
        """
        def extract(regex):
            m = re.search(regex, line)
            return m.group(1) if m else "-"

        fields = {
            "in": extract(r"IN=(\S+)"),
            "out": extract(r"OUT=(\S+)"),
            "mac": extract(r"MAC=(\S+)"),
            "src": extract(r"SRC=(\S+)"),
            "dst": extract(r"DST=(\S+)"),
            "len": extract(r"LEN=(\S+)"),
            "tos": extract(r"TOS=(\S+)"),
            "prec": extract(r"PREC=(\S+)"),
            "ttl": extract(r"TTL=(\S+)"),
            "id": extract(r"ID=(\S+)"),
            "proto": extract(r"PROTO=(\S+)"),
            "spt": extract(r"SPT=(\S+)"),
            "dpt": extract(r"DPT=(\S+)"),
            "len2": extract(r"LEN=(\S+)")  # duplicate but kept for compatibility
        }
        return fields

    def send_notify(self, title, data: dict):
        """
        Gửi notification bằng notify-send (libnotify).
        Title/Body ngắn gọn để không spam quá nhiều.
        """
        title =  title + " detected"
        body = f"SRC={data.get('src','-')} → DST={data.get('dst','-')}  PROTO={data.get('proto','-')}"
        try:
            subprocess.Popen(["notify-send", title, body])

        except Exception as e:
            # nếu notify-send không tồn tại, in ra log (không raise)
            print("notify-send failed:", e)

    def send_email(self, sender_email, password, receiver_email, title, data: dict):
        """
        Gửi email thông báo tấn công.
        subject: {title} detected
        message: chứa SRC, DST, PROTO
        """
        subject = f"{title} detected"
        message = f"SRC={data.get('src','-')} → DST={data.get('dst','-')}  PROTO={data.get('proto','-')}"

        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.starttls
            server.login(email, password)
            server.sendmail(email, receiver_email, msg.as_string())

        print(f"Email has been sent to {receiver_email}")