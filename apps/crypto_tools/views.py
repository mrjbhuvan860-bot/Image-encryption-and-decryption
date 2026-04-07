"""
Views for encryption and decryption tools.

Each view delegates all business logic to service modules.
Views handle: request parsing, form validation, service calls,
template context building, and error display.

Key changes from local storage:
- Encrypted files are stored in Supabase Storage (signed URLs for download)
- Decrypted files are served as base64 data URLs (never saved)
- Keys are one-time use (validated via Supabase Storage file existence)
"""

import base64

from django.shortcuts import render
from django.contrib import messages

from apps.accounts.decorators import supabase_login_required

from .forms import EncryptForm, DecryptForm
from .services.file_handler import (
    validate_image_upload,
    validate_encrypted_upload,
    save_uploaded_file,
    get_upload_dir,
    cleanup_file,
    FileValidationError,
)
from .services.default_encryptor import encrypt_image, DefaultEncryptionError
from .services.default_decryptor import decrypt_image, DefaultDecryptionError
from .services.full_encryptor import encrypt_file, FullEncryptionError
from .services.full_decryptor import decrypt_file, FullDecryptionError
from .services.key_manager import (
    detect_mode,
    get_file_id_from_key,
    get_storage_extension,
)
from .services.supabase_storage import (
    file_exists,
    delete_file,
    get_storage_path,
    StorageError,
)


class KeyAlreadyUsedError(Exception):
    """Raised when a one-time key has already been consumed."""
    pass


@supabase_login_required
def encrypt_view(request):
    """Handle image encryption (both default and full modes)."""
    context = {
        "form": EncryptForm(),
        "result": None,
    }

    if request.method == "POST":
        form = EncryptForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES.get("image")
            mode = form.cleaned_data["mode"]
            saved_path = None

            try:
                # Validate upload
                validate_image_upload(uploaded_file)

                # Save uploaded file to temp disk for processing
                upload_dir = get_upload_dir()
                saved_path = save_uploaded_file(uploaded_file, upload_dir)

                # Encrypt based on selected mode
                if mode == "default":
                    result = encrypt_image(saved_path)
                    context["result"] = {
                        "mode": "default",
                        "signed_url": result["signed_url"],
                        "key_string": result["key_string"],
                        "original_filename": result["original_filename"],
                        "download_name": result["download_name"],
                    }
                    messages.success(
                        request,
                        "Image encrypted successfully! "
                        "Save your key — it is ONE-TIME USE and cannot be recovered."
                    )

                elif mode == "full":
                    result = encrypt_file(saved_path)
                    context["result"] = {
                        "mode": "full",
                        "signed_url": result["signed_url"],
                        "key_string": result["key_string"],
                        "original_filename": result["original_filename"],
                        "download_name": result["download_name"],
                    }
                    messages.success(
                        request,
                        "File encrypted with full protection! "
                        "Save your key — it is ONE-TIME USE and cannot be recovered."
                    )

            except FileValidationError as e:
                messages.error(request, str(e))
            except (DefaultEncryptionError, FullEncryptionError) as e:
                messages.error(request, str(e))
            except StorageError as e:
                messages.error(request, f"Storage error: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
            finally:
                # Clean up uploaded original (temp file)
                if saved_path:
                    cleanup_file(saved_path)

        context["form"] = form

    return render(request, "crypto_tools/encrypt.html", context)


@supabase_login_required
def decrypt_view(request):
    """Handle file decryption (both default and full modes)."""
    context = {
        "form": DecryptForm(),
        "result": None,
    }

    if request.method == "POST":
        form = DecryptForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES.get("encrypted_file")
            key_string = form.cleaned_data["key"].strip()
            saved_path = None

            try:
                # Validate upload
                validate_encrypted_upload(uploaded_file)

                # --- One-Time Key Validation ---
                # Extract file_id from key and check if file still exists in storage
                try:
                    file_id = get_file_id_from_key(key_string)
                    mode = detect_mode(key_string)
                except ValueError as e:
                    messages.error(request, str(e))
                    context["form"] = form
                    return render(request, "crypto_tools/decrypt.html", context)

                ext = get_storage_extension(mode)
                storage_path = get_storage_path(file_id, ext)

                if not file_exists(storage_path):
                    raise KeyAlreadyUsedError(
                        "This key has already been used. "
                        "Each decryption key is ONE-TIME USE only."
                    )

                # Save uploaded file to temp disk for processing
                upload_dir = get_upload_dir()
                saved_path = save_uploaded_file(uploaded_file, upload_dir)

                # Decrypt based on detected mode
                if mode == "default":
                    result = decrypt_image(saved_path, key_string)
                elif mode == "full":
                    result = decrypt_file(saved_path, key_string)

                # --- Invalidate Key ---
                # Delete the marker file from Supabase Storage
                delete_file(storage_path)

                # Encode decrypted image as base64 for inline display
                image_b64 = base64.b64encode(result["image_bytes"]).decode("ascii")
                mime_type = result["mime_type"]
                extension = result.get("extension", ".png")

                context["result"] = {
                    "mode": mode,
                    "image_base64": image_b64,
                    "mime_type": mime_type,
                    "extension": extension,
                    "download_name": f"decrypted_image{extension}",
                }
                messages.success(
                    request,
                    "Image decrypted successfully! "
                    "The key has been invalidated and cannot be used again."
                )

            except KeyAlreadyUsedError as e:
                messages.error(request, str(e))
            except FileValidationError as e:
                messages.error(request, str(e))
            except (DefaultDecryptionError, FullDecryptionError) as e:
                messages.error(request, str(e))
            except StorageError as e:
                messages.error(request, f"Storage error: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
            finally:
                # Clean up uploaded encrypted file (temp file)
                if saved_path:
                    cleanup_file(saved_path)

        context["form"] = form

    return render(request, "crypto_tools/decrypt.html", context)
