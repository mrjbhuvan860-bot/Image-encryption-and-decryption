"""
Supabase Storage service for encrypted file management.

Handles:
- Uploading encrypted files to Supabase Storage
- Generating signed download URLs
- Checking file existence (one-time key validation)
- Deleting files after decryption (key invalidation)

The storage bucket acts as a one-time key validity marker:
- File exists → key is valid
- File deleted → key has been used
"""

from django.conf import settings
from supabase import create_client

BUCKET_NAME = "encrypted-files"

_bucket_ensured = False


class StorageError(Exception):
    """Raised when a Supabase Storage operation fails."""
    pass


def get_storage_client():
    """
    Create a Supabase client with the service role key.

    The service role key bypasses RLS and allows server-side
    storage operations on private buckets.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise StorageError(
            "Supabase credentials not configured. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def ensure_bucket_exists():
    """
    Create the storage bucket if it doesn't already exist.

    Called lazily before first upload. Uses module-level flag
    to avoid redundant API calls.
    """
    global _bucket_ensured
    if _bucket_ensured:
        return

    client = get_storage_client()
    try:
        client.storage.get_bucket(BUCKET_NAME)
    except Exception:
        try:
            client.storage.create_bucket(
                BUCKET_NAME,
                options={"public": False}
            )
        except Exception:
            pass  # May already exist (race condition)

    _bucket_ensured = True


def get_storage_path(file_id: str, extension: str) -> str:
    """
    Derive the storage path from file_id and extension.

    Args:
        file_id: UUID hex string identifying the file.
        extension: File extension including dot (e.g., '.png', '.enc').

    Returns:
        Storage path string like 'files/abc123.png'.
    """
    return f"files/{file_id}{extension}"


def upload_file(file_bytes: bytes, storage_path: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload bytes to Supabase Storage.

    Args:
        file_bytes: Raw file bytes to upload.
        storage_path: Path within the bucket.
        content_type: MIME type of the file.

    Returns:
        The storage path (for reference).

    Raises:
        StorageError: If the upload fails.
    """
    ensure_bucket_exists()
    client = get_storage_client()

    try:
        client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )
        return storage_path
    except Exception as e:
        raise StorageError(f"Failed to upload file: {e}") from e


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """
    Generate a temporary signed URL for downloading a file.

    Args:
        storage_path: Path within the bucket.
        expires_in: URL validity in seconds (default: 1 hour).

    Returns:
        Signed URL string.

    Raises:
        StorageError: If URL generation fails.
    """
    client = get_storage_client()

    try:
        result = client.storage.from_(BUCKET_NAME).create_signed_url(
            storage_path, expires_in
        )
        # supabase-py v2 returns dict with "signedURL" key
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signed_url", "")
        return getattr(result, "signed_url", str(result))
    except Exception as e:
        raise StorageError(f"Failed to generate signed URL: {e}") from e


def file_exists(storage_path: str) -> bool:
    """
    Check if a file exists in the storage bucket.

    Used for one-time key validation: if the file exists,
    the key hasn't been used yet.

    Args:
        storage_path: Path within the bucket.

    Returns:
        True if file exists, False otherwise.
    """
    client = get_storage_client()

    try:
        folder = "files"
        filename = storage_path.split("/")[-1]
        files = client.storage.from_(BUCKET_NAME).list(folder)
        return any(f.get("name") == filename for f in files)
    except Exception:
        return False


def delete_file(storage_path: str) -> None:
    """
    Delete a file from storage (invalidates the one-time key).

    Args:
        storage_path: Path within the bucket.
    """
    client = get_storage_client()

    try:
        client.storage.from_(BUCKET_NAME).remove([storage_path])
    except Exception:
        pass  # Best-effort deletion
