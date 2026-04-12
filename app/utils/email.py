import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from app.config import Config

logger = logging.getLogger(__name__)

# Configure Brevo API client
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = Config.BREVO_API_KEY
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

async def send_verification_email(email: str, verification_link: str, full_name: str):
    subject = "Verify your CCSConnect student account"
    sender = {"name": "CCSConnect", "email": Config.MAIL_FROM}
    to = [{"email": email, "name": full_name}]
    html_content = f"""
    <h3>Hello {full_name},</h3>
    <p>Please click the link below to verify your email and complete your registration:</p>
    <p><a href="{verification_link}">{verification_link}</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>– CCSConnect Team</p>
    """
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Verification email sent to {email}")
        return api_response
    except ApiException as e:
        logger.error(f"Exception when sending verification email to {email}: {e}")
        raise Exception(f"Email sending failed: {e}")

async def send_temp_password_email(email: str, temp_password: str, full_name: str):
    subject = "Your CCSConnect Account Credentials"
    sender = {"name": "CCSConnect", "email": Config.MAIL_FROM}
    to = [{"email": email, "name": full_name}]
    html_content = f"""
    <h3>Welcome to CCSConnect, {full_name}!</h3>
    <p>Your student account has been created. Use the temporary password below to log in:</p>
    <p><strong>{temp_password}</strong></p>
    <p>After logging in, you can change your password in your profile.</p>
    <p>– CCSConnect Team</p>
    """
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Temporary password email sent to {email}")
        return api_response
    except ApiException as e:
        logger.error(f"Exception when sending temp password email to {email}: {e}")
        raise Exception(f"Email sending failed: {e}")