"""
Full file encryption service (Mode B).

Uses cryptography.fernet.Fernet for authenticated encryption of the
entire image file bytes. The output is an opaque .enc binary file
that cannot be viewed as an image. Uploaded to Supabase Storage.

Encryption flow:
1. Read entire file as binary
2. Prepend original extension as header (for restoration)
3. Generate Fernet key
4. Encrypt payload (Fernet = AES-128-CBC + HMAC-SHA256)
5. Upload .enc to Supabase Storage
"""

from pathlib import Path

from cryptography.fernet import Fernet

from .key_manager import serialize_key, generate_file_id
from .supabase_storage import upload_file, get_signed_url, get_storage_path


class FullEncryptionError(Exception):
    """Raised when full encryption fails."""
    pass


def encrypt_file(file_path: Path) -> dict:
    """
    Fully encrypt an image file using Fernet authenticated encryption.

    The output is a binary .enc file uploaded to Supabase Storage.
    The original file extension is embedded in the encrypted payload for
    restoration during decryption.

    Args:
        file_path: Path to the source image file.

    Returns:
        Dictionary with:
            - 'signed_url': Signed URL for the .enc download
            - 'key_string': Base64url key string for decryption
            - 'original_filename': Original file basename
            - 'download_name': Suggested download filename

    Raises:
        FullEncryptionError: If encryption fails.
    """
    try:
        # Step 1: Read entire file as binary
        file_bytes = file_path.read_bytes()
        if not file_bytes:
            raise FullEncryptionError("File is empty.")

        # Step 2: Prepend original extension as header
        # Format: ".png|<file_bytes>"
        original_ext = file_path.suffix.lower()
        header = original_ext.encode("utf-8") + b"|"
        payload = header + file_bytes

        # Step 3: Generate Fernet key
        fernet_key = Fernet.generate_key()  # 44-char URL-safe base64

        # Step 4: Encrypt with Fernet (AES-128-CBC + HMAC-SHA256)
        f = Fernet(fernet_key)
        encrypted_data = f.encrypt(payload)

        # Step 5: Upload to Supabase Storage
        file_id = generate_file_id()
        storage_path = get_storage_path(file_id, ".enc")
        upload_file(encrypted_data, storage_path, content_type="application/octet-stream")

        # Generate signed URL for download
        signed_url = get_signed_url(storage_path)

        # Serialize key metadata (includes file_id for one-time tracking)
        key_data = {
            "m": "full",
            "k": fernet_key.decode("ascii"),
            "fid": file_id,
        }
        key_string = serialize_key(key_data)

        return {
            "signed_url": signed_url,
            "key_string": key_string,
            "original_filename": file_path.name,
            "download_name": f"encrypted_{file_path.stem}.enc",
        }

    except FullEncryptionError:
        raise
    except Exception as e:
        raise FullEncryptionError(f"Full encryption failed: {e}") from e
