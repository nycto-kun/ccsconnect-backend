import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Find the .env file (go up until we find it)
env_path = Path(__file__).parent.parent / ".env"  # app/../.env
load_dotenv(dotenv_path=env_path)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    raise ValueError(f"Missing SUPABASE_URL or SUPABASE_SERVICE_KEY. Looking for .env at {env_path}")

supabase: Client = create_client(url, key)