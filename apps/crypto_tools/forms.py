"""
Forms for encryption and decryption tools.
"""

from django import forms


class EncryptForm(forms.Form):
    """Form for image encryption."""

    image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/png,image/jpeg,image/bmp",
            "id": "encrypt-file-input",
            "class": "file-input-hidden",
        }),
    )
    mode = forms.ChoiceField(
        choices=[
            ("default", "Default Encryption"),
            ("full", "Full Protection"),
        ],
        initial="default",
        widget=forms.RadioSelect(attrs={
            "id": "encrypt-mode",
        }),
    )


class DecryptForm(forms.Form):
    """Form for file decryption."""

    encrypted_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/png,.enc",
            "id": "decrypt-file-input",
            "class": "file-input-hidden",
        }),
    )
    key = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            "placeholder": "Paste your decryption key here",
            "id": "decrypt-key-input",
            "rows": 3,
            "class": "key-input",
        }),
    )
