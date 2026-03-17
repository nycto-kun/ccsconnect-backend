import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config

logger = logging.getLogger(__name__)

async def send_temp_password_email(email: str, temp_password: str):
    """
    Send an email with the temporary password using SMTP.
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