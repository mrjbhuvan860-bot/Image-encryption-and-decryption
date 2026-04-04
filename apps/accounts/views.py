"""
Account views: signup, login, logout, profile.

All auth operations delegate to Supabase via supabase_client.
Session data is stored in Django's session framework.
"""

from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import LoginForm, SignupForm
from .supabase_client import get_supabase_client
from .decorators import supabase_login_required


def signup_view(request):
    """Handle user registration via Supabase."""
    # Redirect if already logged in
    if request.session.get("supabase_user"):
        return redirect("core:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            try:
                client = get_supabase_client()
                response = client.auth.sign_up({
                    "email": email,
                    "password": password,
                })

                if response.user:
                    messages.success(
                        request,
                        "Account created successfully! Please log in."
                    )
                    return redirect("accounts:login")
                else:
                    messages.error(
                        request,
                        "Signup failed. Please try again."
                    )
            except Exception as e:
                error_msg = str(e)
                if "already registered" in error_msg.lower():
                    messages.error(request, "An account with this email already exists.")
                else:
                    messages.error(request, f"Signup error: {error_msg}")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    """Handle user login via Supabase."""
    # Redirect if already logged in
    if request.session.get("supabase_user"):
        return redirect("core:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            try:
                client = get_supabase_client()
                response = client.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })

                if response.user and response.session:
                    # Store user info in Django session
                    request.session["supabase_user"] = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "access_token": response.session.access_token,
                    }
                    messages.success(request, f"Welcome back!")
                    return redirect("core:dashboard")
                else:
                    messages.error(request, "Login failed. Please check your credentials.")
            except Exception as e:
                error_msg = str(e)
                if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                    messages.error(request, "Invalid email or password.")
                else:
                    messages.error(request, f"Login error: {error_msg}")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Log out user by clearing session."""
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect("core:landing")


@supabase_login_required
def profile_view(request):
    """Display user profile information."""
    user_data = request.session.get("supabase_user", {})
    return render(request, "accounts/profile.html", {
        "user_email": user_data.get("email", ""),
        "user_id": user_data.get("id", ""),
    })
