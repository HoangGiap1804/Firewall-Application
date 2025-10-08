
import smtplib
email = "hgiap1804@gmail.com"
receiver_email = "hgiap1804@gmail.com"

subject = "Hello"
message = "Xin chao"

text = f"Subject: {subject}\n\n{message}";

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.starttls
    server.login(email, "dvmtvtlvqfbcwelw")
    server.sendmail(email, receiver_email, text)

print("Email has been sent to email " + receiver_email);