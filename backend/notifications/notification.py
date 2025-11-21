import subprocess
from PySide6.QtCore import QObject, Slot


def send_notification(title: str, message: str):
     
    try:
        subprocess.Popen([
            "notify-send",
            "--icon=dialog-warning",      # Có thể đổi thành dialog-information / security-high
            "--urgency=critical",         # low | normal | critical
            "--expire-time=60000",         # 60 giây
            title,
            message
        ])
        print(f"📢 Notification sent: {title} - {message}")
    except Exception as e:
        print("❌ Failed to send notification:", e)
