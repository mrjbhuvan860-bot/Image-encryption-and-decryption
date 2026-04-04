"""
Core views: landing page and authenticated dashboard.
"""

from django.shortcuts import render, redirect
from apps.accounts.decorators import supabase_login_required


def landing_view(request):
    """Public landing page. Redirect to dashboard if already logged in."""
    if request.session.get("supabase_user"):
        return redirect("core:dashboard")
    return render(request, "core/landing.html")


@supabase_login_required
def dashboard_view(request):
    """Authenticated user dashboard."""
    user_data = request.session.get("supabase_user", {})
    return render(request, "core/dashboard.html", {
        "user_email": user_data.get("email", ""),
    })
