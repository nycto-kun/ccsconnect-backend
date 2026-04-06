import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config

logger = logging.getLogger(__name__)

async def send_temp_password_email(email: str, temp_password: str):
    """
    Send an email with the temporary password after account verification.
    """
    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_FROM
    msg['To'] = email
    msg['Subject'] = "Your CCSConnect Account Credentials"

    body = f"""
    <h3>Welcome to CCSConnect!</h3>
    <p>Your student account has been created. Use the temporary password below to log in:</p>
    <p><strong>{temp_password}</strong></p>
    <p>After logging in, you can change your password in your profile.</p>
    <p>– CCSConnect Team</p>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Temporary password email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        raise Exception(f"Email sending failed: {str(e)}")

async def send_verification_email(email: str, verification_link: str, full_name: str):
    """
    Send a verification email with a link to complete registration.
    """
    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_FROM
    msg['To'] = email
    msg['Subject'] = "Verify your CCSConnect student account"

    body = f"""
    <h3>Hello {full_name},</h3>
    <p>Please click the link below to verify your email and complete your registration:</p>
    <p><a href="{verification_link}">{verification_link}</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>– CCSConnect Team</p>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        raise Exception(f"Email sending failed: {str(e)}")