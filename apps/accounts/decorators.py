"""
Authentication decorators for protecting views.

Uses Django session to check for Supabase auth state.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def supabase_login_required(view_func):
    """
    Decorator that restricts access to authenticated Supabase users.

    Checks request.session for 'supabase_user' key.
    Redirects to login page if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("supabase_user"):
            messages.warning(request, "Please log in to access this page.")
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)
    return wrapper
