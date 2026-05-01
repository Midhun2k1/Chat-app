import os
import logging
from email.message import EmailMessage
import aiosmtplib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

async def send_verification_email(email: str, otp: str):
    """
    Sends a verification email using SMTP and aiosmtplib.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not set. Logging OTP to console instead.")
        logger.info(f"🔑 YOUR VERIFICATION CODE FOR {email}: {otp}")
        return True

    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = email
    message["Subject"] = "Verify Your Email - Messenger App"
    
    # Plain text version (fallback)
    text_content = f"Hello,\n\nYour verification code for Messenger App is: {otp}\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nMessenger Team"
    message.set_content(text_content)

    # HTML version with highlighting
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #2c3e50; text-align: center;">Verify Your Email</h2>
                <p>Hello,</p>
                <p>Thank you for using Messenger App. Please use the following verification code to complete your request:</p>
                <div style="background-color: #f4f7f6; padding: 20px; text-align: center; margin: 20px 0; border-radius: 6px; border: 1px dashed #2c3e50;">
                    <span style="font-size: 32px; font-weight: bold; color: #2c3e50; letter-spacing: 5px;">{otp}</span>
                </div>
                <p>This code is valid for a limited time. If you did not request this code, you can safely ignore this email.</p>
                <p style="margin-top: 30px; border-top: 1px solid #eeeeee; padding-top: 20px;">
                    Best regards,<br>
                    <strong>Messenger Team</strong>
                </p>
            </div>
        </body>
    </html>
    """
    message.add_alternative(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=(SMTP_PORT == 465),
            start_tls=(SMTP_PORT == 587),
        )
        logger.info(f"📧 Verification email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {email}: {str(e)}")
        # Fallback to logging in development
        logger.info(f"🔑 FALLBACK - YOUR VERIFICATION CODE: {otp}")
        return False
