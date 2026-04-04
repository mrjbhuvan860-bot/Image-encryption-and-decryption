"""
Views for encryption and decryption tools.

Each view delegates all business logic to service modules.
Views only handle: request parsing, form validation, service calls,
template context building, and error display.
"""

import os
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.contrib import messages

from apps.accounts.decorators import supabase_login_required

from .forms import EncryptForm, DecryptForm
from .services.file_handler import (
    validate_image_upload,
    validate_encrypted_upload,
    save_uploaded_file,
    get_upload_dir,
    get_output_dir,
    cleanup_file,
    FileValidationError,
)
from .services.default_encryptor import encrypt_image, DefaultEncryptionError
from .services.default_decryptor import decrypt_image, DefaultDecryptionError
from .services.full_encryptor import encrypt_file, FullEncryptionError
from .services.full_decryptor import decrypt_file, FullDecryptionError
from .services.key_manager import detect_mode


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

                # Save uploaded file to disk
                upload_dir = get_upload_dir()
                saved_path = save_uploaded_file(uploaded_file, upload_dir)

                # Encrypt based on selected mode
                if mode == "default":
                    result = encrypt_image(saved_path)
                    context["result"] = {
                        "mode": "default",
                        "encrypted_url": result["encrypted_image_url"],
                        "key_string": result["key_string"],
                        "original_filename": result["original_filename"],
                        "download_path": str(result["encrypted_image_path"]),
                        "download_name": f"encrypted_{result['original_filename']}",
                    }
                    messages.success(request, "Image encrypted successfully! Save your key — it cannot be recovered.")

                elif mode == "full":
                    result = encrypt_file(saved_path)
                    context["result"] = {
                        "mode": "full",
                        "key_string": result["key_string"],
                        "original_filename": result["original_filename"],
                        "download_path": str(result["encrypted_file_path"]),
                        "download_name": f"encrypted_{os.path.splitext(result['original_filename'])[0]}.enc",
                    }
                    messages.success(request, "File encrypted with full protection! Save your key — it cannot be recovered.")

            except FileValidationError as e:
                messages.error(request, str(e))
            except (DefaultEncryptionError, FullEncryptionError) as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
            finally:
                # Clean up uploaded original (keep output)
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

                # Save uploaded file to disk
                upload_dir = get_upload_dir()
                saved_path = save_uploaded_file(uploaded_file, upload_dir)

                # Auto-detect mode from key
                try:
                    mode = detect_mode(key_string)
                except ValueError as e:
                    messages.error(request, str(e))
                    context["form"] = form
                    return render(request, "crypto_tools/decrypt.html", context)

                # Decrypt based on detected mode
                if mode == "default":
                    result = decrypt_image(saved_path, key_string)
                    context["result"] = {
                        "mode": "default",
                        "decrypted_url": result["decrypted_image_url"],
                        "download_path": str(result["decrypted_image_path"]),
                        "download_name": "decrypted_image.png",
                    }
                    messages.success(request, "Image decrypted successfully!")

                elif mode == "full":
                    result = decrypt_file(saved_path, key_string)
                    ext = result.get("original_extension", ".png")
                    context["result"] = {
                        "mode": "full",
                        "decrypted_url": result["decrypted_image_url"],
                        "download_path": str(result["decrypted_image_path"]),
                        "download_name": f"decrypted_image{ext}",
                        "original_extension": ext,
                    }
                    messages.success(request, "File decrypted successfully!")

            except FileValidationError as e:
                messages.error(request, str(e))
            except (DefaultDecryptionError, FullDecryptionError) as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
            finally:
                # Clean up uploaded encrypted file (keep output)
                if saved_path:
                    cleanup_file(saved_path)

        context["form"] = form

    return render(request, "crypto_tools/decrypt.html", context)


@supabase_login_required
def download_view(request):
    """
    Serve a file for download.

    Expects 'path' query parameter with the file path.
    Expects 'name' query parameter for the download filename.
    """
    file_path = request.GET.get("path", "")
    download_name = request.GET.get("name", "download")

    if not file_path or not os.path.isfile(file_path):
        raise Http404("File not found.")

    # Security: ensure file is within our output directory
    output_dir = str(get_output_dir())
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(output_dir)):
        raise Http404("Access denied.")

    response = FileResponse(
        open(real_path, "rb"),
        as_attachment=True,
        filename=download_name,
    )
    return response
