"""
File handling utilities for uploads.

Handles:
- Upload validation (type, size, extension)
- Secure filename generation (UUID-based)
- Temporary file saving and cleanup

Note: Output files are no longer saved locally — they go to
Supabase Storage (see supabase_storage.py).
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


# Valid image MIME types
VALID_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/bmp",
}

# Valid encrypted file MIME types (binary)
VALID_ENCRYPTED_MIMES = {
    "application/octet-stream",
    "application/x-binary",
}


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


def validate_image_upload(file: UploadedFile) -> None:
    """
    Validate an uploaded image file.

    Checks:
    - File is not empty
    - File size is within limits
    - File extension is allowed
    """
    if not file:
        raise FileValidationError("No file was uploaded.")

    if file.size == 0:
        raise FileValidationError("Uploaded file is empty.")

    if file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_MB
        raise FileValidationError(
            f"File too large. Maximum size is {max_mb}MB."
        )

    ext = Path(file.name).suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)
        raise FileValidationError(
            f"Invalid file type '{ext}'. Allowed types: {allowed}"
        )


def validate_encrypted_upload(file: UploadedFile) -> None:
    """
    Validate an uploaded encrypted file (.enc or image).
    """
    if not file:
        raise FileValidationError("No file was uploaded.")

    if file.size == 0:
        raise FileValidationError("Uploaded file is empty.")

    if file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_MB
        raise FileValidationError(
            f"File too large. Maximum size is {max_mb}MB."
        )

    ext = Path(file.name).suffix.lower()
    allowed = settings.ALLOWED_IMAGE_EXTENSIONS + settings.ALLOWED_ENCRYPTED_EXTENSIONS
    if ext not in allowed:
        raise FileValidationError(
            f"Invalid file type '{ext}'. Upload an encrypted image (.png) "
            f"or encrypted file (.enc)."
        )


def generate_secure_filename(extension: str) -> str:
    """Generate a UUID-based filename with the given extension."""
    return f"{uuid.uuid4().hex}{extension}"


def get_upload_dir() -> Path:
    """Get (and create if needed) the temporary upload directory."""
    upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_uploaded_file(file: UploadedFile, directory: Path) -> Path:
    """Save an uploaded file to disk with a secure UUID filename."""
    ext = Path(file.name).suffix.lower()
    filename = generate_secure_filename(ext)
    filepath = directory / filename

    with open(filepath, "wb") as dest:
        for chunk in file.chunks():
            dest.write(chunk)

    return filepath


def cleanup_file(filepath: Path) -> None:
    """Safely delete a file if it exists."""
    try:
        if filepath and filepath.exists():
            filepath.unlink()
    except OSError:
        pass  # Best-effort cleanup
