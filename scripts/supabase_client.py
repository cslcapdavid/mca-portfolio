import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Get Supabase client using same credentials as other repos"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        raise ValueError("Missing Supabase credentials")
    
    return create_client(url, key)
