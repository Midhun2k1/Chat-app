import os
import smtplib
from email.mime.text import MIMEText
import traceback

def send_debug_email_sync(to_email: str, subject: str, body: str):

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        # Missing credentials, silently ignore sending email.
        return

    msg = MIMEText(body)
    msg["Subject"] = f"[DEBUG] {subject}"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_port == 587:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())
    except Exception as e:
        # Print error for debugging purposes; could be logged instead.
        print("Failed to send debug email:", e)
        traceback.print_exc()
