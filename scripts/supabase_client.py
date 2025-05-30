"""
Supabase client for CSL Capital MCA scraper
Uses service_role key for RLS bypass
"""

import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Get Supabase client using service_role key for RLS bypass"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')  # Using service_role key
    
    if not url or not key:
        raise ValueError("Missing Supabase credentials: SUPABASE_URL and SUPABASE_KEY required")
    
    return create_client(url, key)
