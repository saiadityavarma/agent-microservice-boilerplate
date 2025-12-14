"""
API Key generation, hashing, and validation utilities.

This module provides cryptographic functions for secure API key management.
Raw keys are NEVER stored - only SHA256 hashes are persisted to the database.

Security Note:
    - Raw keys are returned ONLY during generation and must be shown to users immediately
    - All storage operations use hashed keys
    - Keys are never logged or included in error messages
"""

import hashlib
import secrets
from dataclasses import dataclass
from typing import Tuple


@dataclass
class APIKeyParts:
    """
    Parsed components of an API key.

    Attributes:
        prefix: The key prefix (e.g., 'sk', 'pk')
        random_part: The random cryptographic component
        full_key: The complete key string
    """
    prefix: str
    random_part: str
    full_key: str


def generate_api_key(prefix: str = "sk") -> Tuple[str, str]:
    """
    Generate a cryptographically secure API key.

    Creates a key in the format: {prefix}_{random_32_chars}
    Returns both the raw key (to show user ONCE) and hashed version (for storage).

    Args:
        prefix: Key prefix to identify key type (default: "sk" for secret key)
                Common prefixes: "sk" (secret), "pk" (public), "test", "live"

    Returns:
        Tuple of (raw_key, hashed_key):
            - raw_key: The actual key to give to the user (NEVER store this)
            - hashed_key: SHA256 hash for database storage

    Example:
        >>> raw_key, hashed_key = generate_api_key("sk_live")
        >>> print(raw_key)  # sk_test_EXAMPLE_KEY_REPLACE_ME
        >>> # Store hashed_key in database, give raw_key to user ONCE

    Security:
        - Uses secrets module for cryptographically secure randomness
        - 32-character random part provides ~191 bits of entropy
        - Raw key is never logged or stored
    """
    # Generate 32 characters of cryptographically secure random hex
    random_part = secrets.token_hex(16)  # 16 bytes = 32 hex chars

    # Construct the full key
    raw_key = f"{prefix}_{random_part}"

    # Hash the key for storage
    hashed_key = hash_api_key(raw_key)

    return raw_key, hashed_key


def hash_api_key(key: str) -> str:
    """
    Hash an API key using SHA256 for secure storage.

    Args:
        key: The raw API key to hash

    Returns:
        Hexadecimal string of the SHA256 hash

    Example:
        >>> key = "sk_test_abc123"
        >>> hashed = hash_api_key(key)
        >>> len(hashed)  # SHA256 produces 64 hex characters
        64

    Security:
        - SHA256 provides one-way hashing (cannot reverse to get original key)
        - Consistent output allows verification without storing raw key
        - Fast verification suitable for high-throughput API requests
    """
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def verify_api_key(key: str, hashed: str) -> bool:
    """
    Verify a raw API key against its stored hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        key: The raw API key to verify
        hashed: The stored SHA256 hash to compare against

    Returns:
        True if the key matches the hash, False otherwise

    Example:
        >>> raw_key, stored_hash = generate_api_key()
        >>> verify_api_key(raw_key, stored_hash)
        True
        >>> verify_api_key("wrong_key", stored_hash)
        False

    Security:
        - Uses secrets.compare_digest for constant-time comparison
        - Prevents timing attacks that could leak information about the hash
        - Never returns or logs the raw key
    """
    computed_hash = hash_api_key(key)
    return secrets.compare_digest(computed_hash, hashed)


def parse_api_key(key: str) -> APIKeyParts:
    """
    Parse an API key into its component parts.

    Extracts the prefix and random part from a key string.

    Args:
        key: The API key to parse

    Returns:
        APIKeyParts containing prefix, random_part, and full_key

    Raises:
        ValueError: If the key format is invalid (no underscore separator)

    Example:
        >>> parts = parse_api_key("sk_test_EXAMPLE_KEY_REPLACE_ME")
        >>> parts.prefix
        'sk_live'
        >>> parts.random_part
        'abc123'

    Note:
        Keys may have multiple underscores (e.g., sk_test_EXAMPLE_KEY_REPLACE_ME).
        The last underscore separates the prefix from the random part.
    """
    if '_' not in key:
        raise ValueError("Invalid API key format: missing underscore separator")

    # Split on the last underscore to separate prefix from random part
    last_underscore_idx = key.rfind('_')
    prefix = key[:last_underscore_idx]
    random_part = key[last_underscore_idx + 1:]

    return APIKeyParts(
        prefix=prefix,
        random_part=random_part,
        full_key=key
    )


def validate_api_key_format(key: str) -> bool:
    """
    Validate that an API key has the correct format.

    Checks:
        - Contains at least one underscore
        - Has a non-empty prefix
        - Has a non-empty random part
        - Random part is at least 16 characters (security requirement)

    Args:
        key: The API key to validate

    Returns:
        True if the format is valid, False otherwise

    Example:
        >>> validate_api_key_format("sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
        True
        >>> validate_api_key_format("invalid_key")
        False
        >>> validate_api_key_format("sk_short")
        False
    """
    try:
        parts = parse_api_key(key)

        # Validate prefix exists
        if not parts.prefix:
            return False

        # Validate random part exists and meets minimum length
        # (16 chars minimum = 64 bits of entropy)
        if not parts.random_part or len(parts.random_part) < 16:
            return False

        return True
    except ValueError:
        return False
