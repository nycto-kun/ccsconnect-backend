import logging
import requests
from app.config import Config

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

def _send_brevo_email(to_email: str, to_name: str, subject: str, html_content: str):
    api_key = Config.BREVO_API_KEY
    if not api_key:
        raise Exception("BREVO_API_KEY not set in environment variables")

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    data = {
        "sender": {"name": "CCSConnect", "email": Config.MAIL_FROM},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    try:
        response = requests.post(BREVO_API_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Email sent to {to_email}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise Exception(f"Email sending failed: {e}")

async def send_verification_email(email: str, verification_link: str, full_name: str):
    subject = "Verify your CCSConnect student account"
    html_content = f"""
    <h3>Hello {full_name},</h3>
    <p>Please click the link below to verify your email and complete your registration:</p>
    <p><a href="{verification_link}">{verification_link}</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>– CCSConnect Team</p>
    """
    return _send_brevo_email(email, full_name, subject, html_content)

async def send_temp_password_email(email: str, temp_password: str, full_name: str):
    subject = "Your CCSConnect Account Credentials"
    html_content = f"""
    <h3>Welcome to CCSConnect, {full_name}!</h3>
    <p>Your student account has been created. Use the temporary password below to log in:</p>
    <p><strong>{temp_password}</strong></p>
    <p>After logging in, you can change your password in your profile.</p>
    <p>– CCSConnect Team</p>
    """
    return _send_brevo_email(email, full_name, subject, html_content)