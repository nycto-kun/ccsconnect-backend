import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@ccsconnect.edu")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    # Other config values (Supabase URL, etc.) are already in database.py