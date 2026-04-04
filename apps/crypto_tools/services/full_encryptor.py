"""
Full file encryption service (Mode B).

Uses cryptography.fernet.Fernet for authenticated encryption of the
entire image file bytes. The output is an opaque .enc binary file
that cannot be viewed as an image.

Encryption flow:
1. Read entire file as binary
2. Prepend original extension as header (for restoration)
3. Generate Fernet key
4. Encrypt payload (Fernet = AES-128-CBC + HMAC-SHA256)
5. Save as .enc file
"""

from pathlib import Path

from cryptography.fernet import Fernet

from .key_manager import serialize_key
from .file_handler import get_output_dir, get_media_url, generate_secure_filename


class FullEncryptionError(Exception):
    """Raised when full encryption fails."""
    pass


def encrypt_file(file_path: Path) -> dict:
    """
    Fully encrypt an image file using Fernet authenticated encryption.

    The output is a binary .enc file. The original file extension is
    embedded in the encrypted payload for restoration during decryption.

    Args:
        file_path: Path to the source image file.

    Returns:
        Dictionary with:
            - 'encrypted_file_path': Path to .enc output
            - 'encrypted_file_url': Media URL for download
            - 'key_string': Base64url key string for decryption
            - 'original_filename': Original file basename

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

        # Step 5: Save as .enc file
        output_dir = get_output_dir()
        output_filename = generate_secure_filename(".enc")
        output_path = output_dir / output_filename
        output_path.write_bytes(encrypted_data)

        # Serialize key metadata
        key_data = {
            "m": "full",
            "k": fernet_key.decode("ascii"),  # Fernet key is already base64
        }
        key_string = serialize_key(key_data)

        return {
            "encrypted_file_path": output_path,
            "encrypted_file_url": get_media_url(output_path),
            "key_string": key_string,
            "original_filename": file_path.name,
        }

    except FullEncryptionError:
        raise
    except Exception as e:
        raise FullEncryptionError(f"Full encryption failed: {e}") from e
