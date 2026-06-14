import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
service_key: str = os.getenv("SUPABASE_SERVICE_KEY")
anon_key: str = os.getenv("SUPABASE_ANON_KEY")

if not url or not service_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

# For operations that need to bypass RLS (admin functions)
supabase_admin: Client = create_client(url, service_key)

# For regular operations (respects RLS)
supabase: Client = create_client(url, anon_key) if anon_key else supabase_admin