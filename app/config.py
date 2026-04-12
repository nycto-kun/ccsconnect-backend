import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@ccsconnect.edu")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    # Keep other variables if needed (e.g., for local SMTP fallback)