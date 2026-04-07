"""
Default image encryption service (Mode A).

Uses Pillow + PyCryptodome AES-256-CBC to produce a visually encrypted image
that appears as random noise/static while remaining a valid PNG file.

Encryption flow:
1. Load image with Pillow → convert to RGB
2. Extract raw pixel bytes
3. Generate AES-256 key + CBC IV
4. PKCS7 pad pixel bytes to AES block size
5. AES-CBC encrypt
6. Split ciphertext: image_portion (original length) + overflow bytes
7. Reconstruct encrypted PNG from image_portion
8. Upload encrypted PNG to Supabase Storage
9. Serialize key + IV + dimensions + overflow + file_id into key string
"""

import io
from pathlib import Path

from PIL import Image
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

from .key_manager import serialize_key, generate_file_id
from .supabase_storage import upload_file, get_signed_url, get_storage_path


class DefaultEncryptionError(Exception):
    """Raised when default encryption fails."""
    pass


def encrypt_image(image_path: Path) -> dict:
    """
    Encrypt an image using AES-256-CBC on raw pixel data.

    The output is a valid PNG image containing encrypted pixel data
    that appears as random RGB noise. The encrypted PNG is uploaded
    to Supabase Storage.

    Args:
        image_path: Path to the source image file.

    Returns:
        Dictionary with:
            - 'signed_url': Signed URL for the encrypted PNG download/preview
            - 'key_string': Base64url key string for decryption
            - 'original_filename': Original file basename
            - 'download_name': Suggested download filename

    Raises:
        DefaultEncryptionError: If encryption fails.
    """
    try:
        # Step 1: Load image and convert to RGB
        img = Image.open(image_path)
        img = img.convert("RGB")
        width, height = img.size

        # Step 2: Extract raw pixel bytes
        pixel_data = img.tobytes()
        original_length = len(pixel_data)  # W × H × 3

        # Step 3: Generate AES-256 key and CBC initialization vector
        aes_key = get_random_bytes(32)  # 256-bit key
        iv = get_random_bytes(16)       # 128-bit IV

        # Step 4: PKCS7 pad pixel data to AES block size (16 bytes)
        padded_data = pad(pixel_data, AES.block_size)

        # Step 5: AES-256-CBC encrypt
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(padded_data)

        # Step 6: Split ciphertext
        image_portion = ciphertext[:original_length]
        overflow = ciphertext[original_length:]

        # Step 7: Reconstruct as RGB PNG in memory
        encrypted_img = Image.frombytes("RGB", (width, height), image_portion)
        buf = io.BytesIO()
        encrypted_img.save(buf, format="PNG")
        encrypted_bytes = buf.getvalue()

        # Step 8: Upload to Supabase Storage
        file_id = generate_file_id()
        storage_path = get_storage_path(file_id, ".png")
        upload_file(encrypted_bytes, storage_path, content_type="image/png")

        # Generate signed URL for download/preview
        signed_url = get_signed_url(storage_path)

        # Step 9: Serialize key metadata (includes file_id for one-time tracking)
        key_data = {
            "m": "default",
            "k": aes_key.hex(),
            "iv": iv.hex(),
            "w": width,
            "h": height,
            "o": overflow.hex(),
            "fid": file_id,
        }
        key_string = serialize_key(key_data)

        return {
            "signed_url": signed_url,
            "key_string": key_string,
            "original_filename": image_path.name,
            "download_name": f"encrypted_{image_path.stem}.png",
        }

    except Exception as e:
        raise DefaultEncryptionError(f"Encryption failed: {e}") from e
