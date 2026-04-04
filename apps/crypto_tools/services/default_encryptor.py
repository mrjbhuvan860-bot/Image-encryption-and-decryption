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
8. Serialize key + IV + dimensions + overflow into key string

The encrypted image looks like vivid RGB noise. Decryption with the correct
key perfectly restores the original image.
"""

from pathlib import Path

from PIL import Image
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

from .key_manager import serialize_key
from .file_handler import get_output_dir, save_bytes_to_file, get_media_url


class DefaultEncryptionError(Exception):
    """Raised when default encryption fails."""
    pass


def encrypt_image(image_path: Path) -> dict:
    """
    Encrypt an image using AES-256-CBC on raw pixel data.

    The output is a valid PNG image containing encrypted pixel data
    that appears as random RGB noise.

    Args:
        image_path: Path to the source image file.

    Returns:
        Dictionary with:
            - 'encrypted_image_path': Path to encrypted PNG
            - 'encrypted_image_url': Media URL for the encrypted PNG
            - 'key_string': Base64url key string for decryption
            - 'original_filename': Original file basename

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
        # image_portion: first 'original_length' bytes → becomes the visible encrypted image
        # overflow: remaining bytes (1-16) → stored in key metadata for perfect reversal
        image_portion = ciphertext[:original_length]
        overflow = ciphertext[original_length:]

        # Step 7: Reconstruct as RGB PNG
        encrypted_img = Image.frombytes("RGB", (width, height), image_portion)
        output_dir = get_output_dir()

        # Save as PNG (MUST be lossless — JPEG would destroy ciphertext)
        from .file_handler import generate_secure_filename
        output_filename = generate_secure_filename(".png")
        output_path = output_dir / output_filename
        encrypted_img.save(str(output_path), format="PNG")

        # Step 8: Serialize key metadata
        key_data = {
            "m": "default",             # mode identifier
            "k": aes_key.hex(),          # AES-256 key (64 hex chars)
            "iv": iv.hex(),              # CBC IV (32 hex chars)
            "w": width,                  # original width
            "h": height,                 # original height
            "o": overflow.hex(),         # overflow bytes (2-32 hex chars)
        }
        key_string = serialize_key(key_data)

        return {
            "encrypted_image_path": output_path,
            "encrypted_image_url": get_media_url(output_path),
            "key_string": key_string,
            "original_filename": image_path.name,
        }

    except Exception as e:
        raise DefaultEncryptionError(f"Encryption failed: {e}") from e
