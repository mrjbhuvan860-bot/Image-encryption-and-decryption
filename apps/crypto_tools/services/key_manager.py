"""
Key management for both encryption modes.

Handles key generation, serialization (to base64url JSON), and deserialization.
Keys are NEVER stored server-side — they are returned to the user for safekeeping.
"""

import json
import base64


def serialize_key(key_data: dict) -> str:
    """
    Serialize key metadata to a URL-safe base64 string.

    The key string encodes everything needed for decryption:
    - For default mode: AES key, IV, dimensions, overflow bytes
    - For full mode: Fernet key

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
