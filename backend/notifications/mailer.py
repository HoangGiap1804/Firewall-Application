import os
import smtplib
import threading
from dotenv import load_dotenv
from email.message import EmailMessage
from datetime import datetime

load_dotenv()


SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
PASSWORD_EMAIL = os.getenv("PASSWORD_EMAIL")


def _send_email_in_thread(email_func, *args, **kwargs):
    """Wrapper function để chạy email function trong thread riêng"""
    try:
        email_func(*args, **kwargs)
    except Exception as e:
        error_msg = f"Lỗi khi gửi email: {str(e)}"
        print(f"❌ {error_msg}")


def _send_attack_alert_sync(attack_type: str, src_ip: str, severity: str, log_time: str | None = None):
    """Hàm gửi email đồng bộ (chạy trong thread)"""
    if log_time is None:
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mức độ màu sắc cảnh báo
    color = {
        "low": "#22c55e",       # xanh lá
        "medium": "#eab308",    # vàng
        "high": "#ef4444",      # đỏ
    }.get(severity.lower(), "#eab308")

    # Nội dung HTML
    html_content = f"""\
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>⚠️ Cảnh báo tấn công hệ thống</title>
    <style>
      body {{
        font-family: Arial, Helvetica, sans-serif;
        background-color: #f6f8fa;
        margin: 0;
        padding: 20px;
      }}
      .card {{
        max-width: 650px;
        background: #ffffff;
        border-radius: 10px;
        margin: 0 auto;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        overflow: hidden;
      }}
      .header {{
        background: linear-gradient(90deg, #991b1b, #7f1d1d);
        color: #fff;
        padding: 20px;
        text-align: center;
      }}
      .header h1 {{
        margin: 0;
        font-size: 22px;
      }}
      .content {{
        padding: 25px;
        line-height: 1.6;
        color: #333;
      }}
      .badge {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 12px;
        font-weight: 600;
        background: {color};
        color: white;
        margin-top: 6px;
      }}
      .footer {{
        background: #f9fafb;
        padding: 12px;
        font-size: 13px;
        text-align: center;
        color: #666;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
      }}
      td {{
        padding: 6px 0;
        border-bottom: 1px solid #eee;
      }}
      strong {{
        color: #111827;
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="header">
        <h1>⚠️ CẢNH BÁO TẤN CÔNG HỆ THỐNG</h1>
        <p style="margin:6px 0 0;">Hệ thống phát hiện hoạt động đáng ngờ</p>
      </div>
      <div class="content">
        <p>Xin chào,</p>
        <p>Hệ thống tường lửa đã phát hiện một cuộc tấn công khả nghi.</p>

        <table>
          <tr><td><strong>Loại tấn công:</strong></td><td>{attack_type}</td></tr>
          <tr><td><strong>Địa chỉ IP nguồn:</strong></td><td>{src_ip}</td></tr>
          <tr><td><strong>Thời gian phát hiện:</strong></td><td>{log_time}</td></tr>
          <tr><td><strong>Mức độ:</strong></td><td><span class="badge">{severity.upper()}</span></td></tr>
        </table>

        <p style="margin-top:18px;">
          Vui lòng kiểm tra nhật ký hệ thống (<code>/var/log/syslog</code> hoặc <code>/var/log/kern.log</code>)
          và thực hiện các biện pháp cần thiết để ngăn chặn hành vi này.
        </p>

        <p style="margin-top:10px;color:#6b7280;font-size:13px;">
          Email này được gửi tự động bởi hệ thống giám sát an ninh mạng.
        </p>
      </div>
      <div class="footer">
        © 2025 Network Security System — Giap Security Monitor
      </div>
    </div>
  </body>
</html>
"""

    # Tạo email
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"[{severity.upper()}] {attack_type} detected from {src_ip}"
    msg.set_content("A new attack was detected. Please view the HTML version for details.")
    msg.add_alternative(html_content, subtype="html")

    # Gửi mail
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, PASSWORD_EMAIL)
        server.send_message(msg)

    print(f"📧 Cảnh báo '{attack_type}' đã được gửi tới {RECEIVER_EMAIL}!")


def send_attack_alert(attack_type: str, src_ip: str, severity: str, log_time: str | None = None):
    """Gửi email cảnh báo tấn công trong thread riêng (không block)"""
    thread = threading.Thread(
        target=_send_email_in_thread,
        args=(_send_attack_alert_sync, attack_type, src_ip, severity, log_time),
        daemon=True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
    )
    thread.start()
    # Thread sẽ tự cleanup khi hoàn thành


def _send_malware_alert_sync(malware_type: str, severity: str, log_time: str | None = None):
    """Hàm gửi email đồng bộ (chạy trong thread)"""
    if log_time is None:
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Màu severity
    color = {
        "low": "#22c55e",
        "medium": "#eab308",
        "high": "#ef4444",
    }.get(severity.lower(), "#eab308")

    html_content = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>⚠️ Cảnh báo mã độc</title>
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      background-color: #f6f8fa;
      margin: 0;
      padding: 20px;
    }}
    .card {{
      max-width: 600px;
      margin: 0 auto;
      background: white;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(90deg, #7f1d1d, #991b1b);
      color: white;
      padding: 20px;
      text-align: center;
    }}
    .content {{
      padding: 20px;
      color: #333;
      line-height: 1.6;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 14px;
      border-radius: 12px;
      font-weight: 600;
      background: {color};
      color: white;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    td {{
      padding: 6px 0;
      border-bottom: 1px solid #eee;
    }}
    .footer {{
      background: #f9fafb;
      padding: 10px;
      text-align: center;
      font-size: 13px;
      color: #666;
    }}
  </style>
</head>

<body>
  <div class="card">
    <div class="header">
      <h2>⚠️ PHÁT HIỆN MÃ ĐỘC</h2>
      <p>Hệ thống phát hiện hoạt động đáng ngờ trong sandbox</p>
    </div>

    <div class="content">

      <table>
        <tr><td><strong>Loại mã độc:</strong></td><td>{malware_type}</td></tr>
        <tr><td><strong>Mức độ nguy hiểm:</strong></td><td><span class="badge">{severity.upper()}</span></td></tr>
        <tr><td><strong>Thời gian:</strong></td><td>{log_time}</td></tr>
      </table>

      <p style="margin-top:15px;">
        Hệ thống sandbox phát hiện dấu hiệu nhiễm mã độc.  
        Vui lòng kiểm tra ngay lập tức để đảm bảo an toàn hệ thống.
      </p>
    </div>

    <div class="footer">© 2025 Giap Security Monitor</div>
  </div>
</body>
</html>
"""

    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"[{severity.upper()}] Malware detected ({malware_type})"
    msg.set_content("A malware threat has been detected. Please check the HTML version.")
    msg.add_alternative(html_content, subtype="html")

    # send mail
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, PASSWORD_EMAIL)
        server.send_message(msg)

    print("📧 Đã gửi email cảnh báo mã độc!")


def send_malware_alert(malware_type: str, severity: str, log_time: str | None = None):
    """Gửi email cảnh báo mã độc trong thread riêng (không block)"""
    thread = threading.Thread(
        target=_send_email_in_thread,
        args=(_send_malware_alert_sync, malware_type, severity, log_time),
        daemon=True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
    )
    thread.start()
    # Thread sẽ tự cleanup khi hoàn thành


def _send_performance_alert_sync(resource_type: str, usage_value: str, severity: str, log_time: str | None = None):
    """Hàm gửi email cảnh báo hiệu năng đồng bộ"""
    if log_time is None:
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    color = {
        "low": "#22c55e",
        "medium": "#eab308",
        "high": "#f97316", # Cam đậm
        "critical": "#ef4444",
    }.get(severity.lower(), "#eab308")

    html_content = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>⚠️ Cảnh báo tài nguyên hệ thống</title>
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      background-color: #f6f8fa;
      margin: 0;
      padding: 20px;
    }}
    .card {{
      max-width: 600px;
      margin: 0 auto;
      background: white;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(90deg, #ea580c, #c2410c);
      color: white;
      padding: 20px;
      text-align: center;
    }}
    .content {{
      padding: 20px;
      color: #333;
      line-height: 1.6;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 14px;
      border-radius: 12px;
      font-weight: 600;
      background: {color};
      color: white;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    td {{
      padding: 6px 0;
      border-bottom: 1px solid #eee;
    }}
    .footer {{
      background: #f9fafb;
      padding: 10px;
      text-align: center;
      font-size: 13px;
      color: #666;
    }}
  </style>
</head>

<body>
  <div class="card">
    <div class="header">
      <h2>⚠️ CẢNH BÁO TÀI NGUYÊN</h2>
      <p>Sử dụng tài nguyên hệ thống vượt ngưỡng</p>
    </div>

    <div class="content">

      <table>
        <tr><td><strong>Tài nguyên:</strong></td><td>{resource_type}</td></tr>
        <tr><td><strong>Mức sử dụng:</strong></td><td>{usage_value}</td></tr>
        <tr><td><strong>Mức độ:</strong></td><td><span class="badge">{severity.upper()}</span></td></tr>
        <tr><td><strong>Thời gian:</strong></td><td>{log_time}</td></tr>
      </table>

      <p style="margin-top:15px;">
        Vui lòng kiểm tra các tiến trình đang chạy để tối ưu hóa hiệu năng.
      </p>
    </div>

    <div class="footer">© 2025 Giap Security Monitor</div>
  </div>
</body>
</html>
"""

    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"[{severity.upper()}] High {resource_type} Usage: {usage_value}"
    msg.set_content("High system resource usage detected. Please check the HTML version.")
    msg.add_alternative(html_content, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, PASSWORD_EMAIL)
        server.send_message(msg)

    print(f"📧 Đã gửi email cảnh báo hiệu năng ({resource_type})!")


def send_performance_alert(resource_type: str, usage_value: str, severity: str, log_time: str | None = None):
    """Gửi email cảnh báo hiệu năng trong thread riêng"""
    thread = threading.Thread(
        target=_send_email_in_thread,
        args=(_send_performance_alert_sync, resource_type, usage_value, severity, log_time),
        daemon=True
    )
    thread.start()
