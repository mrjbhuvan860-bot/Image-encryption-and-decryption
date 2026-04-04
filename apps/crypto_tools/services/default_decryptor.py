"""
Default image decryption service (Mode A).

Reverses the AES-256-CBC pixel encryption from default_encryptor.py.

Decryption flow:
1. Parse key string → extract AES key, IV, dimensions, overflow
2. Load encrypted PNG with Pillow
3. Extract pixel bytes
4. Reconstruct full ciphertext by appending overflow bytes
5. AES-CBC decrypt
6. PKCS7 unpad
7. Reconstruct original image from decrypted pixel bytes
"""

from pathlib import Path

from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .key_manager import deserialize_key
from .file_handler import get_output_dir, get_media_url, generate_secure_filename


class DefaultDecryptionError(Exception):
    """Raised when default decryption fails."""
    pass


def decrypt_image(encrypted_image_path: Path, key_string: str) -> dict:
    """
    Decrypt an AES-256-CBC encrypted image back to the original.

    Args:
        encrypted_image_path: Path to the encrypted PNG file.
        key_string: Base64url key string from encryption.

    Returns:
        Dictionary with:
            - 'decrypted_image_path': Path to restored image
            - 'decrypted_image_url': Media URL for the restored image

    Raises:
        DefaultDecryptionError: If decryption fails (wrong key, corrupted file, etc.).
    """
    try:
        # Step 1: Parse key metadata
        try:
            key_data = deserialize_key(key_string)
        except ValueError as e:
            raise DefaultDecryptionError(f"Invalid key format: {e}")

        if key_data.get("m") != "default":
            raise DefaultDecryptionError(
                "This key is for full encryption mode, not default mode. "
                "Please use the correct decryption mode."
            )

        aes_key = bytes.fromhex(key_data["k"])
        iv = bytes.fromhex(key_data["iv"])
        original_width = key_data["w"]
        original_height = key_data["h"]
        overflow = bytes.fromhex(key_data["o"])

        # Validate key component sizes
        if len(aes_key) != 32:
            raise DefaultDecryptionError("Invalid AES key length in key data.")
        if len(iv) != 16:
            raise DefaultDecryptionError("Invalid IV length in key data.")

        # Step 2: Load encrypted PNG
        try:
            enc_img = Image.open(encrypted_image_path)
            enc_img = enc_img.convert("RGB")
        except Exception as e:
            raise DefaultDecryptionError(f"Cannot open encrypted image: {e}")

        # Verify dimensions match key metadata
        if enc_img.size != (original_width, original_height):
            raise DefaultDecryptionError(
                f"Image dimensions {enc_img.size} do not match key metadata "
                f"({original_width}x{original_height}). Wrong file or key."
            )

        # Step 3: Extract pixel bytes from encrypted image
        encrypted_pixels = enc_img.tobytes()

        # Step 4: Reconstruct full ciphertext by appending overflow
        full_ciphertext = encrypted_pixels + overflow

        # Verify ciphertext length is multiple of AES block size
        if len(full_ciphertext) % AES.block_size != 0:
            raise DefaultDecryptionError(
                "Reconstructed ciphertext has invalid length. "
                "The file or key may be corrupted."
            )

        # Step 5: AES-CBC decrypt
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(full_ciphertext)

        # Step 6: PKCS7 unpad
        try:
            original_data = unpad(decrypted_padded, AES.block_size)
        except ValueError:
            raise DefaultDecryptionError(
                "Decryption failed — incorrect key or corrupted data. "
                "The padding is invalid, which means the key does not match."
            )

        # Verify data length matches expected dimensions
        expected_length = original_width * original_height * 3  # RGB
        if len(original_data) != expected_length:
            raise DefaultDecryptionError(
                f"Decrypted data length ({len(original_data)}) does not match "
                f"expected ({expected_length}). Data may be corrupted."
            )

        # Step 7: Reconstruct original image
        restored_img = Image.frombytes("RGB", (original_width, original_height), original_data)

        # Save restored image
        output_dir = get_output_dir()
        output_filename = generate_secure_filename(".png")
        output_path = output_dir / output_filename
        restored_img.save(str(output_path), format="PNG")

        return {
            "decrypted_image_path": output_path,
            "decrypted_image_url": get_media_url(output_path),
        }

    except DefaultDecryptionError:
        raise
    except Exception as e:
        raise DefaultDecryptionError(f"Decryption failed: {e}") from e
