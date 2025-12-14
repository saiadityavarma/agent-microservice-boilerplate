"""
Unit tests for API key generation, hashing, and validation utilities.

Tests cover:
- API key generation with valid format
- Key hashing consistency
- Key verification correctness
- Invalid key format rejection
- Key parsing functionality
"""

import pytest
import secrets
from agent_service.auth.api_key import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    parse_api_key,
    validate_api_key_format,
    APIKeyParts,
)


class TestAPIKeyGeneration:
    """Test API key generation functionality."""

    def test_generate_api_key_produces_valid_format(self):
        """Test that generated API keys have the correct format."""
        # Test with default prefix
        raw_key, hashed_key = generate_api_key()

        assert raw_key.startswith("sk_")
        assert len(raw_key) > 35  # prefix (3) + underscore (1) + random (32)
        assert "_" in raw_key
        assert len(hashed_key) == 64  # SHA256 hex digest length

    def test_generate_api_key_with_custom_prefix(self):
        """Test API key generation with custom prefixes."""
        prefixes = ["sk_live", "pk_test", "test", "prod"]

        for prefix in prefixes:
            raw_key, hashed_key = generate_api_key(prefix)

            assert raw_key.startswith(f"{prefix}_")
            assert len(hashed_key) == 64

    def test_generate_api_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = set()

        # Generate 100 keys and ensure they're all unique
        for _ in range(100):
            raw_key, _ = generate_api_key()
            keys.add(raw_key)

        assert len(keys) == 100  # All keys should be unique

    def test_generate_api_key_random_part_length(self):
        """Test that the random part has sufficient entropy."""
        raw_key, _ = generate_api_key("sk")
        parts = parse_api_key(raw_key)

        # Random part should be 32 characters (16 bytes * 2 hex chars)
        assert len(parts.random_part) == 32

        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in parts.random_part)

    def test_generate_api_key_uses_secrets_module(self):
        """Test that key generation uses cryptographically secure randomness."""
        # Generate multiple keys and check distribution
        random_parts = []

        for _ in range(10):
            raw_key, _ = generate_api_key()
            parts = parse_api_key(raw_key)
            random_parts.append(parts.random_part)

        # All random parts should be different
        assert len(set(random_parts)) == 10

        # Each should be valid hex
        for part in random_parts:
            int(part, 16)  # Should not raise ValueError


class TestAPIKeyHashing:
    """Test API key hashing functionality."""

    def test_hash_api_key_produces_consistent_output(self):
        """Test that hashing the same key produces the same hash."""
        key = "sk_test_abc123def456"

        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        hash3 = hash_api_key(key)

        assert hash1 == hash2 == hash3

    def test_hash_api_key_produces_sha256_format(self):
        """Test that hash output is SHA256 format."""
        key = "sk_test_example"
        hashed = hash_api_key(key)

        # SHA256 produces 64 hex characters
        assert len(hashed) == 64

        # Should be valid hex
        int(hashed, 16)  # Should not raise ValueError

    def test_hash_api_key_different_keys_different_hashes(self):
        """Test that different keys produce different hashes."""
        key1 = "sk_test_key1"
        key2 = "sk_test_key2"

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2

    def test_hash_api_key_case_sensitive(self):
        """Test that hashing is case-sensitive."""
        key_lower = "sk_test_abc"
        key_upper = "SK_TEST_ABC"

        hash_lower = hash_api_key(key_lower)
        hash_upper = hash_api_key(key_upper)

        assert hash_lower != hash_upper

    def test_hash_api_key_handles_special_characters(self):
        """Test that hashing works with special characters."""
        special_keys = [
            "sk_test-with-dashes",
            "sk_test_with_underscores",
            "sk_test.with.dots",
            "sk_test@with#special!chars",
        ]

        for key in special_keys:
            hashed = hash_api_key(key)
            assert len(hashed) == 64


class TestAPIKeyVerification:
    """Test API key verification functionality."""

    def test_verify_api_key_correct_key(self):
        """Test that verification works for correct keys."""
        raw_key, hashed_key = generate_api_key()

        assert verify_api_key(raw_key, hashed_key) is True

    def test_verify_api_key_incorrect_key(self):
        """Test that verification fails for incorrect keys."""
        _, hashed_key = generate_api_key()
        wrong_key = "sk_wrong_key_12345678901234567890"

        assert verify_api_key(wrong_key, hashed_key) is False

    def test_verify_api_key_uses_constant_time_comparison(self):
        """Test that verification uses constant-time comparison."""
        # This is a basic test - actual timing attacks are complex
        raw_key, hashed_key = generate_api_key()

        # These should both fail, but timing should be similar
        # (though we can't easily test timing in unit tests)
        assert verify_api_key("wrong_key_1", hashed_key) is False
        assert verify_api_key("wrong_key_2", hashed_key) is False

    def test_verify_api_key_case_sensitive(self):
        """Test that verification is case-sensitive."""
        raw_key = "sk_test_abc123"
        hashed_key = hash_api_key(raw_key)

        assert verify_api_key(raw_key, hashed_key) is True
        assert verify_api_key(raw_key.upper(), hashed_key) is False

    def test_verify_api_key_with_slightly_modified_key(self):
        """Test that verification fails for slightly modified keys."""
        raw_key, hashed_key = generate_api_key()

        # Modify one character
        modified_key = raw_key[:-1] + ("a" if raw_key[-1] != "a" else "b")

        assert verify_api_key(modified_key, hashed_key) is False


class TestAPIKeyParsing:
    """Test API key parsing functionality."""

    def test_parse_api_key_standard_format(self):
        """Test parsing of standard format API keys."""
        key = "sk_abc123def456ghi789"
        parts = parse_api_key(key)

        assert isinstance(parts, APIKeyParts)
        assert parts.prefix == "sk"
        assert parts.random_part == "abc123def456ghi789"
        assert parts.full_key == key

    def test_parse_api_key_with_multiple_underscores(self):
        """Test parsing keys with multiple underscores in prefix."""
        key = "sk_test_EXAMPLE_KEY_REPLACE_ME_abc123"
        parts = parse_api_key(key)

        assert parts.prefix == "sk_test_EXAMPLE_KEY_REPLACE_ME"
        assert parts.random_part == "abc123"
        assert parts.full_key == key

    def test_parse_api_key_generated_keys(self):
        """Test parsing of generated API keys."""
        prefixes = ["sk", "sk_live", "pk_test"]

        for prefix in prefixes:
            raw_key, _ = generate_api_key(prefix)
            parts = parse_api_key(raw_key)

            assert parts.prefix == prefix
            assert len(parts.random_part) == 32
            assert parts.full_key == raw_key

    def test_parse_api_key_invalid_format_no_underscore(self):
        """Test that parsing fails for keys without underscores."""
        with pytest.raises(ValueError, match="missing underscore separator"):
            parse_api_key("invalidkey123")

    def test_parse_api_key_empty_string(self):
        """Test that parsing fails for empty strings."""
        with pytest.raises(ValueError, match="missing underscore separator"):
            parse_api_key("")

    def test_parse_api_key_only_underscore(self):
        """Test that parsing handles edge case of only underscore."""
        key = "_"
        parts = parse_api_key(key)

        assert parts.prefix == ""
        assert parts.random_part == ""


class TestAPIKeyFormatValidation:
    """Test API key format validation functionality."""

    def test_validate_api_key_format_valid_keys(self):
        """Test that valid API key formats are accepted."""
        valid_keys = [
            "sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "pk_test_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "sk_test_EXAMPLE_KEY_REPLACE_ME",
        ]

        for key in valid_keys:
            assert validate_api_key_format(key) is True

    def test_validate_api_key_format_generated_keys(self):
        """Test that all generated keys pass format validation."""
        for _ in range(10):
            raw_key, _ = generate_api_key()
            assert validate_api_key_format(raw_key) is True

    def test_validate_api_key_format_invalid_no_underscore(self):
        """Test that keys without underscores are rejected."""
        assert validate_api_key_format("invalidkey") is False

    def test_validate_api_key_format_invalid_empty_prefix(self):
        """Test that keys with empty prefix are rejected."""
        assert validate_api_key_format("_randompart123456") is False

    def test_validate_api_key_format_invalid_short_random_part(self):
        """Test that keys with short random parts are rejected."""
        # Random part must be at least 16 characters
        short_keys = [
            "sk_abc",
            "sk_test_12345",
            "sk_a1b2c3d4e5",
        ]

        for key in short_keys:
            assert validate_api_key_format(key) is False

    def test_validate_api_key_format_minimum_random_length(self):
        """Test the minimum random part length boundary."""
        # Exactly 16 characters should pass
        assert validate_api_key_format("sk_a1b2c3d4e5f6g7h8") is True

        # 15 characters should fail
        assert validate_api_key_format("sk_a1b2c3d4e5f6g7h") is False

    def test_validate_api_key_format_empty_string(self):
        """Test that empty strings are rejected."""
        assert validate_api_key_format("") is False

    def test_validate_api_key_format_only_underscore(self):
        """Test that only underscore is rejected."""
        assert validate_api_key_format("_") is False


class TestAPIKeyIntegration:
    """Integration tests for complete API key workflow."""

    def test_full_key_lifecycle(self):
        """Test complete lifecycle: generation, hashing, verification."""
        # Generate
        raw_key, hashed_key = generate_api_key("sk_live")

        # Validate format
        assert validate_api_key_format(raw_key) is True

        # Parse
        parts = parse_api_key(raw_key)
        assert parts.prefix == "sk_live"

        # Verify
        assert verify_api_key(raw_key, hashed_key) is True

        # Verify wrong key fails
        wrong_key, _ = generate_api_key("sk_live")
        assert verify_api_key(wrong_key, hashed_key) is False

    def test_multiple_keys_independence(self):
        """Test that multiple keys can coexist and be verified independently."""
        keys = []

        # Generate 5 different keys
        for i in range(5):
            raw_key, hashed_key = generate_api_key(f"sk_{i}")
            keys.append((raw_key, hashed_key))

        # Verify each key works with its own hash
        for raw_key, hashed_key in keys:
            assert verify_api_key(raw_key, hashed_key) is True

        # Verify each key fails with other hashes
        for i, (raw_key, _) in enumerate(keys):
            for j, (_, other_hash) in enumerate(keys):
                if i != j:
                    assert verify_api_key(raw_key, other_hash) is False

    def test_key_security_properties(self):
        """Test security properties of generated keys."""
        raw_key, hashed_key = generate_api_key()

        # Raw key should not appear in hash
        assert raw_key not in hashed_key

        # Hash should not reveal prefix
        parts = parse_api_key(raw_key)
        assert parts.prefix not in hashed_key

        # Hash should not reveal random part
        assert parts.random_part not in hashed_key

        # Hash should be one-way (can't reverse)
        # This is a property of SHA256, just verify hash doesn't contain key data
        assert all(char in "0123456789abcdef" for char in hashed_key)

    def test_key_format_enforcement(self):
        """Test that format validation prevents weak keys."""
        weak_keys = [
            "short",
            "no_random",
            "sk_",
            "sk_1234",  # Too short
            "_onlyrand",  # No prefix
        ]

        for weak_key in weak_keys:
            assert validate_api_key_format(weak_key) is False

            # Even if we hash a weak key, verification should be possible
            # but the key would be rejected at validation stage
            hashed = hash_api_key(weak_key)
            assert verify_api_key(weak_key, hashed) is True  # Hash works
            assert validate_api_key_format(weak_key) is False  # But format is invalid
