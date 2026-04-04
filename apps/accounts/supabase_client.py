"""
Supabase client singleton for the application.

Initializes a single Supabase client instance using environment variables.
All auth operations should use this client.
"""

from django.conf import settings
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Return a Supabase client instance.

    Uses SUPABASE_URL and SUPABASE_ANON_KEY from Django settings
    (loaded from environment variables).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError(
            "Supabase credentials not configured. "
            "Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
