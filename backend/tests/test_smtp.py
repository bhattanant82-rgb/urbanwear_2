
import smtplib
import os
from dotenv import load_dotenv

load_dotenv("urbanwear-fastapi/.env")
email_user = os.getenv("EMAIL_USER")
email_pass = os.getenv("EMAIL_PASS")
smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
smtp_port = int(os.getenv("SMTP_PORT", 587))

print(f"Testing SMTP for {email_user}...")
try:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(email_user, email_pass)
    print("Success! SMTP Login successful.")
except Exception as e:
    print(f"Error SMTP: {e}")
