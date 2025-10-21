
import smtplib
from dotenv import load_dotenv
import os

load_dotenv()

email = os.getenv("SENDER_EMAIL")
receiver_email = os.getenv("RECEIVER_EMAIL")

print(email)
print(receiver_email)

print(os.getenv("PASSWORD_EMAIL"))
subject = "Hello"
message = "Xin chao"

text = f"Subject: {subject}\n\n{message}";

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.starttls
    server.login(email, os.getenv("PASSWORD_EMAIL"))
    server.sendmail(email, receiver_email, text)

print("Email has been sent to email " + receiver_email);