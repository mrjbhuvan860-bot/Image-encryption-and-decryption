"""
Full file decryption service (Mode B).

Reverses the Fernet encryption from full_encryptor.py.
Returns decrypted file bytes in memory — nothing is saved to disk.

Decryption flow:
1. Parse key string → extract Fernet key
2. Read encrypted .enc file
3. Fernet decrypt (validates HMAC — detects wrong key or tampering)
4. Split header to recover original extension
5. Return file bytes and metadata
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .key_manager import deserialize_key


class FullDecryptionError(Exception):
    """Raised when full decryption fails."""
    pass


def decrypt_file(encrypted_file_path: Path, key_string: str) -> dict:
    """
    Decrypt a Fernet-encrypted .enc file back to the original image.

    Returns the decrypted file as bytes in memory. No files are
    saved to disk.

    Args:
        encrypted_file_path: Path to the .enc file.
        key_string: Base64url key string from encryption.

    Returns:
        Dictionary with:
            - 'image_bytes': Raw bytes of the restored file
            - 'mime_type': MIME type string
            - 'extension': Original file extension
            - 'original_extension': Same as extension (for compatibility)

    Raises:
        FullDecryptionError: If decryption fails.
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

        # Step 5: Determine MIME type
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(original_ext, "image/png")

        # Return bytes (no local file saved)
        return {
            "image_bytes": file_bytes,
            "mime_type": mime_type,
            "extension": original_ext,
            "original_extension": original_ext,
        }

    except FullDecryptionError:
        raise
    except Exception as e:
        raise FullDecryptionError(f"Decryption failed: {e}") from e
