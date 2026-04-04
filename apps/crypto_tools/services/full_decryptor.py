"""
Full file decryption service (Mode B).

Reverses the Fernet encryption from full_encryptor.py.

Decryption flow:
1. Parse key string → extract Fernet key
2. Read encrypted .enc file
3. Fernet decrypt (validates HMAC — detects wrong key or tampering)
4. Split header to recover original extension
5. Save restored file with original extension
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .key_manager import deserialize_key
from .file_handler import get_output_dir, get_media_url, generate_secure_filename


class FullDecryptionError(Exception):
    """Raised when full decryption fails."""
    pass


def decrypt_file(encrypted_file_path: Path, key_string: str) -> dict:
    """
    Decrypt a Fernet-encrypted .enc file back to the original image.

    Args:
        encrypted_file_path: Path to the .enc file.
        key_string: Base64url key string from encryption.

    Returns:
        Dictionary with:
            - 'decrypted_image_path': Path to restored image file
            - 'decrypted_image_url': Media URL for the restored image
            - 'original_extension': Restored file extension

    Raises:
        FullDecryptionError: If decryption fails (wrong key, tampered data, etc.).
    """
    try:
        # Step 1: Parse key metadata
        try:
            key_data = deserialize_key(key_string)
        except ValueError as e:
            raise FullDecryptionError(f"Invalid key format: {e}")

        if key_data.get("m") != "full":
            raise FullDecryptionError(
                "This key is for default encryption mode, not full encryption. "
                "Please use the correct decryption mode."
            )

        fernet_key = key_data["k"].encode("ascii")

        # Validate Fernet key format
        try:
            f = Fernet(fernet_key)
        except (ValueError, Exception) as e:
            raise FullDecryptionError(f"Invalid Fernet key: {e}")

        # Step 2: Read encrypted file
        try:
            encrypted_data = encrypted_file_path.read_bytes()
        except Exception as e:
            raise FullDecryptionError(f"Cannot read encrypted file: {e}")

        if not encrypted_data:
            raise FullDecryptionError("Encrypted file is empty.")

        # Step 3: Fernet decrypt (HMAC verification catches wrong key + tampering)
        try:
            decrypted_payload = f.decrypt(encrypted_data)
        except InvalidToken:
            raise FullDecryptionError(
                "Decryption failed — incorrect key or the file has been tampered with. "
                "Please verify you are using the correct decryption key."
            )

        # Step 4: Split header to recover original extension
        # Format: ".png|<file_bytes>"
        separator_index = decrypted_payload.find(b"|")
        if separator_index == -1 or separator_index > 10:
            raise FullDecryptionError(
                "Decrypted data has invalid format. The file may be corrupted."
            )

        original_ext = decrypted_payload[:separator_index].decode("utf-8")
        file_bytes = decrypted_payload[separator_index + 1:]

        # Validate extension
        if not original_ext.startswith("."):
            original_ext = ".png"  # Fallback

        # Step 5: Save restored file
        output_dir = get_output_dir()
        output_filename = generate_secure_filename(original_ext)
        output_path = output_dir / output_filename
        output_path.write_bytes(file_bytes)

        return {
            "decrypted_image_path": output_path,
            "decrypted_image_url": get_media_url(output_path),
            "original_extension": original_ext,
        }

    except FullDecryptionError:
        raise
    except Exception as e:
        raise FullDecryptionError(f"Decryption failed: {e}") from e
