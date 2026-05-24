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
    message["Subject"] = "Verify Your Email - PingBee App"
    
    # Plain text version (fallback)
    text_content = f"Hello,\n\nYour verification code for PingBee App is: {otp}\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nPingBee Team"
    message.set_content(text_content)

    # HTML version with highlighting
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #2c3e50; text-align: center;">Verify Your Email</h2>
                <p>Hello,</p>
                <p>Thank you for using PingBee App. Please use the following verification code to complete your request:</p>
                <div style="background-color: #f4f7f6; padding: 20px; text-align: center; margin: 20px 0; border-radius: 6px; border: 1px dashed #2c3e50;">
                    <span style="font-size: 32px; font-weight: bold; color: #2c3e50; letter-spacing: 5px;">{otp}</span>
                </div>
                <p>This code is valid for a limited time. If you did not request this code, you can safely ignore this email.</p>
                <p style="margin-top: 30px; border-top: 1px solid #eeeeee; padding-top: 20px;">
                    Best regards,<br>
                    <strong>PingBee Team</strong>
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


async def send_password_reset_email(email: str, otp: str):
    """
    Sends a password reset email using SMTP and aiosmtplib.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not set. Logging Reset OTP to console instead.")
        logger.info(f"🔑 YOUR PASSWORD RESET CODE FOR {email}: {otp}")
        return True

    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = email
    message["Subject"] = "Reset Your Password - PingBee App"
    
    # Plain text version (fallback)
    text_content = f"Hello,\n\nYour password reset code for PingBee App is: {otp}\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nPingBee Team"
    message.set_content(text_content)

    # HTML version with highlighting
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #c0392b; text-align: center;">Reset Your Password</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password. Please use the following code to reset it:</p>
                <div style="background-color: #f9ebea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 6px; border: 1px dashed #c0392b;">
                    <span style="font-size: 32px; font-weight: bold; color: #c0392b; letter-spacing: 5px;">{otp}</span>
                </div>
                <p>This code is valid for a limited time. If you did not request this code, you can safely ignore this email.</p>
                <p style="margin-top: 30px; border-top: 1px solid #eeeeee; padding-top: 20px;">
                    Best regards,<br>
                    <strong>PingBee Team</strong>
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
        logger.info(f"📧 Password reset email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send reset email to {email}: {str(e)}")
        # Fallback to logging in development
        logger.info(f"🔑 FALLBACK - YOUR PASSWORD RESET CODE: {otp}")
        return False








""" import os
import logging
import resend
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Resend Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")

if RESEND_API_KEY and not RESEND_API_KEY.startswith("re_your"):
    resend.api_key = RESEND_API_KEY

async def send_verification_email(email: str, otp: str):
    ""
    Sends a verification email using Resend API.
    ""
    # If API key is missing or is the placeholder, fallback to console logging
    if not RESEND_API_KEY or RESEND_API_KEY.startswith("re_your"):
        logger.warning("RESEND_API_KEY not set or is placeholder. Logging OTP to console.")
        logger.info(f"🔑 YOUR VERIFICATION CODE FOR {email}: {otp}")
        return True

    # HTML version with highlighting
    html_content = f""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #2c3e50; text-align: center;">Verify Your Email</h2>
                <p>Hello,</p>
                <p>Thank you for using PingBee App. Please use the following verification code to complete your request:</p>
                <div style="background-color: #f4f7f6; padding: 20px; text-align: center; margin: 20px 0; border-radius: 6px; border: 1px dashed #2c3e50;">
                    <span style="font-size: 32px; font-weight: bold; color: #2c3e50; letter-spacing: 5px;">{otp}</span>
                </div>
                <p>This code is valid for a limited time. If you did not request this code, you can safely ignore this email.</p>
                <p style="margin-top: 30px; border-top: 1px solid #eeeeee; padding-top: 20px;">
                    Best regards,<br>
                    <strong>PingBee Team</strong>
                </p>
            </div>
        </body>
    </html>
    ""

    try:
        params = {
            "from": RESEND_FROM,
            "to": email,
            "subject": "Verify Your Email - PingBee App",
            "html": html_content,
        }

        # Send email via Resend
        resend.Emails.send(params)
        
        logger.info(f"📧 Verification email sent successfully to {email} via Resend")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {email} via Resend: {str(e)}")
        # Fallback to logging in development
        logger.info(f"🔑 FALLBACK - YOUR VERIFICATION CODE: {otp}")
        return False
 """
