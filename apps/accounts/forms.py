"""
Authentication forms for login and signup.

These are standard Django forms (not ModelForms since we don't use Django User model).
Validation happens here; Supabase API calls happen in views.
"""

from django import forms


class LoginForm(forms.Form):
    """Login form with email and password."""

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email",
            "autocomplete": "email",
            "id": "login-email",
        }),
    )
    password = forms.CharField(
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
            "id": "login-password",
        }),
    )


class SignupForm(forms.Form):
    """Signup form with email, password, and confirmation."""

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email",
            "autocomplete": "email",
            "id": "signup-email",
        }),
    )
    password = forms.CharField(
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a password (min 8 characters)",
            "autocomplete": "new-password",
            "id": "signup-password",
        }),
    )
    confirm_password = forms.CharField(
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirm your password",
            "autocomplete": "new-password",
            "id": "signup-confirm-password",
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data
