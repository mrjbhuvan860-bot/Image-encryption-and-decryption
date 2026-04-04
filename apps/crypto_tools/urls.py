"""Crypto tools URL patterns."""

from django.urls import path
from . import views

app_name = "crypto_tools"

urlpatterns = [
    path("encrypt/", views.encrypt_view, name="encrypt"),
    path("decrypt/", views.decrypt_view, name="decrypt"),
    path("download/", views.download_view, name="download"),
]
