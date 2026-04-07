"""
Key management for both encryption modes.

Handles key generation, serialization (to base64url JSON), and deserialization.
Keys are NEVER stored server-side — they are returned to the user for safekeeping.

Each key now includes a 'fid' (file ID) used for:
- Locating the encrypted file in Supabase Storage
- One-time key validation (file exists → key is valid)
"""

import json
import base64
import uuid


def generate_file_id() -> str:
    """
    Generate a unique file ID for storage path tracking.

    Returns:
        UUID hex string (32 characters).
    """
    return uuid.uuid4().hex


def serialize_key(key_data: dict) -> str:
    """
    Serialize key metadata to a URL-safe base64 string.

    The key string encodes everything needed for decryption:
    - For default mode: AES key, IV, dimensions, overflow bytes, file_id
    - For full mode: Fernet key, file_id

    Args:
        key_data: Dictionary with key metadata.

    Returns:
        Base64url-encoded JSON string.
    """
    json_bytes = json.dumps(key_data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("ascii")


def deserialize_key(key_string: str) -> dict:
    """
    Deserialize a key string back to metadata dictionary.

    Args:
        key_string: Base64url-encoded JSON string from serialize_key().

    Returns:
        Dictionary with key metadata.

    Raises:
        ValueError: If key string is invalid or corrupted.
    """
    try:
        json_bytes = base64.urlsafe_b64decode(key_string.encode("ascii"))
        return json.loads(json_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid decryption key: {e}")


def detect_mode(key_string: str) -> str:
    """
    Detect the encryption mode from a key string.

    Returns:
        "default" or "full"

    Raises:
        ValueError: If key format is unrecognized.
    """
    key_data = deserialize_key(key_string)
    mode = key_data.get("m")
    if mode not in ("default", "full"):
        raise ValueError(f"Unrecognized encryption mode in key: {mode}")
    return mode


def get_file_id_from_key(key_string: str) -> str:
    """
    Extract the file ID from a key string.

    Args:
        key_string: Base64url-encoded key string.

    Returns:
        File ID string.

    Raises:
        ValueError: If key has no file ID (legacy key).
    """
    key_data = deserialize_key(key_string)
    fid = key_data.get("fid")
    if not fid:
        raise ValueError(
            "This key does not contain a file ID. "
            "It may be from an older version and cannot be validated."
        )
    return fid


def get_storage_extension(mode: str) -> str:
    """
    Get the storage file extension for a given encryption mode.

    Args:
        mode: 'default' or 'full'.

    Returns:
        File extension string (e.g., '.png' or '.enc').
    """
    return ".png" if mode == "default" else ".enc"
