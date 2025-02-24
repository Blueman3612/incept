from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

def get_supabase() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: Supabase client instance
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY
    ) 