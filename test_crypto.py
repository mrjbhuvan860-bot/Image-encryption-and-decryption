"""
Round-trip validation test for both encryption modes.
Verifies:
1. Default mode: encrypt → decrypt = identical pixels
2. Full mode: encrypt → decrypt = identical file bytes
3. Wrong key produces explicit error
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from pathlib import Path
from PIL import Image
import tempfile

from apps.crypto_tools.services.default_encryptor import encrypt_image
from apps.crypto_tools.services.default_decryptor import decrypt_image, DefaultDecryptionError
from apps.crypto_tools.services.full_encryptor import encrypt_file
from apps.crypto_tools.services.full_decryptor import decrypt_file, FullDecryptionError
from apps.crypto_tools.services.key_manager import serialize_key, deserialize_key, detect_mode


def test_default_mode():
    """Test Mode A: AES-256-CBC pixel encryption round-trip."""
    print("=" * 60)
    print("TEST: Default Encryption Mode (AES-256-CBC)")
    print("=" * 60)

    # Create a test image (100x80 RGB with known pixel data)
    test_img = Image.new("RGB", (100, 80))
    pixels = test_img.load()
    for x in range(100):
        for y in range(80):
            pixels[x, y] = (x * 2 % 256, y * 3 % 256, (x + y) % 256)

    # Save test image
    test_path = Path("media/test_original.png")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_img.save(str(test_path), format="PNG")
    original_bytes = test_img.tobytes()
    print(f"  Original image: {test_img.size}, {len(original_bytes)} bytes")

    # Encrypt
    result = encrypt_image(test_path)
    print(f"  Encrypted to: {result['encrypted_image_path']}")
    print(f"  Key string length: {len(result['key_string'])} chars")

    # Verify encrypted image looks different
    enc_img = Image.open(result["encrypted_image_path"])
    enc_bytes = enc_img.tobytes()
    assert enc_bytes != original_bytes, "FAIL: Encrypted image is identical to original!"
    print(f"  Encrypted image is visually different: OK")

    # Verify key metadata
    key_data = deserialize_key(result["key_string"])
    assert key_data["m"] == "default", "FAIL: Mode should be 'default'"
    assert key_data["w"] == 100, "FAIL: Width mismatch"
    assert key_data["h"] == 80, "FAIL: Height mismatch"
    assert detect_mode(result["key_string"]) == "default"
    print(f"  Key metadata valid: OK")

    # Decrypt
    dec_result = decrypt_image(result["encrypted_image_path"], result["key_string"])
    dec_img = Image.open(dec_result["decrypted_image_path"])
    dec_bytes = dec_img.tobytes()

    # Verify round-trip
    assert dec_bytes == original_bytes, "FAIL: Decrypted image does not match original!"
    assert dec_img.size == test_img.size, "FAIL: Dimensions mismatch!"
    print(f"  Round-trip match: OK ({len(dec_bytes)} bytes)")

    # Test wrong key
    fake_key_data = key_data.copy()
    fake_key_data["k"] = "00" * 32  # wrong key
    fake_key = serialize_key(fake_key_data)
    try:
        decrypt_image(result["encrypted_image_path"], fake_key)
        print("  FAIL: Should have raised error with wrong key!")
    except DefaultDecryptionError as e:
        print(f"  Wrong key error: OK ({str(e)[:60]}...)")

    # Cleanup
    test_path.unlink(missing_ok=True)
    result["encrypted_image_path"].unlink(missing_ok=True)
    dec_result["decrypted_image_path"].unlink(missing_ok=True)

    print("  ✓ DEFAULT MODE: ALL TESTS PASSED")
    print()


def test_full_mode():
    """Test Mode B: Fernet full-file encryption round-trip."""
    print("=" * 60)
    print("TEST: Full Encryption Mode (Fernet)")
    print("=" * 60)

    # Create a test image
    test_img = Image.new("RGB", (50, 50), color=(128, 64, 200))
    test_path = Path("media/test_full_original.png")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_img.save(str(test_path), format="PNG")
    original_file_bytes = test_path.read_bytes()
    print(f"  Original file: {len(original_file_bytes)} bytes")

    # Encrypt
    result = encrypt_file(test_path)
    print(f"  Encrypted to: {result['encrypted_file_path']}")
    print(f"  Key string length: {len(result['key_string'])} chars")

    # Verify key metadata
    assert detect_mode(result["key_string"]) == "full"
    print(f"  Key metadata valid: OK")

    # Verify encrypted file is different
    enc_bytes = result["encrypted_file_path"].read_bytes()
    assert enc_bytes != original_file_bytes, "FAIL: Encrypted file is identical!"
    print(f"  Encrypted content is different: OK")

    # Decrypt
    dec_result = decrypt_file(result["encrypted_file_path"], result["key_string"])
    dec_bytes = dec_result["decrypted_image_path"].read_bytes()

    # Verify round-trip
    assert dec_bytes == original_file_bytes, "FAIL: Decrypted file does not match original!"
    print(f"  Round-trip match: OK ({len(dec_bytes)} bytes)")

    # Test wrong key
    from cryptography.fernet import Fernet
    fake_key_data = {"m": "full", "k": Fernet.generate_key().decode("ascii")}
    fake_key = serialize_key(fake_key_data)
    try:
        decrypt_file(result["encrypted_file_path"], fake_key)
        print("  FAIL: Should have raised error with wrong key!")
    except FullDecryptionError as e:
        print(f"  Wrong key error: OK ({str(e)[:60]}...)")

    # Cleanup
    test_path.unlink(missing_ok=True)
    result["encrypted_file_path"].unlink(missing_ok=True)
    dec_result["decrypted_image_path"].unlink(missing_ok=True)

    print("  ✓ FULL MODE: ALL TESTS PASSED")
    print()


def test_key_manager():
    """Test key serialization/deserialization."""
    print("=" * 60)
    print("TEST: Key Manager")
    print("=" * 60)

    data = {"m": "default", "k": "ab" * 32, "iv": "cd" * 16, "w": 100, "h": 80, "o": "ef" * 8}
    serialized = serialize_key(data)
    deserialized = deserialize_key(serialized)
    assert deserialized == data, "FAIL: Roundtrip mismatch!"
    print(f"  Serialization round-trip: OK")

    # Test invalid key
    try:
        deserialize_key("not-valid-base64!!!")
        print("  FAIL: Should have raised ValueError!")
    except ValueError as e:
        print(f"  Invalid key error: OK")

    print("  ✓ KEY MANAGER: ALL TESTS PASSED")
    print()


if __name__ == "__main__":
    test_key_manager()
    test_default_mode()
    test_full_mode()
    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
