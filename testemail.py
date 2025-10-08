import os
import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS

SENDER = "hgiap1804@gmail.com"
PASSWORD = os.environ.get("EMAIL_PASSWORD")  # set via env var
TO = "hgiap1804@gmail.com"

msg = EmailMessage()
msg["Subject"] = "Test từ Python"
msg["From"] = SENDER
msg["To"] = TO
msg.set_content("Xin chào,\n\nĐây là email test gửi bằng Python.\n\nThân!")

try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()       # bảo mật
        smtp.ehlo()
        smtp.login(SENDER, PASSWORD)
        smtp.send_message(msg)
    print("Đã gửi thành công!")
except Exception as e:
    print("Lỗi khi gửi:", e)
