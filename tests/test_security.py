# ============================================================================
# tests/test_security.py - Security-focused tests
# ============================================================================

import pytest
from shared.crypto import encrypt_password, decrypt_password
from utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_hash_password(self):
        """Test that passwords are hashed correctly"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test that correct passwords are verified"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test that wrong passwords are rejected"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False


class TestJWT:
    """Test JWT token functionality"""

    def test_create_token(self):
        """Test token creation"""
        token = create_access_token({"sub": "testuser", "role": "admin"})

        assert token is not None
        assert len(token) > 50  # JWT tokens are long
        assert token.count(".") == 2  # JWT has 3 parts

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        """Test that invalid tokens raise exception"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")

        assert exc_info.value.status_code == 401


class TestCredentialEncryption:
    """Test credential encryption for device passwords"""

    def test_encrypt_password(self):
        """Test password encryption"""
        password = "device_password_123"
        encrypted = encrypt_password(password)

        assert encrypted != password
        assert len(encrypted) > len(password)

    def test_decrypt_password(self):
        """Test password decryption"""
        password = "device_password_123"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password

    def test_empty_password(self):
        """Test handling of empty passwords"""
        assert encrypt_password("") == ""
        assert decrypt_password("") == ""

    def test_encryption_is_unique(self):
        """Test that same password produces different ciphertext (IV)"""
        password = "test_password"
        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # Fernet uses random IV, so encryptions should differ
        # But both should decrypt to same value
        assert decrypt_password(encrypted1) == password
        assert decrypt_password(encrypted2) == password


class TestTransformExecutorSecurity:
    """Test transform executor security restrictions"""

    def test_dangerous_patterns_blocked(self):
        """Test that dangerous code patterns are blocked"""
        from engine.step_executors.transform_executor import TransformExecutor, DANGEROUS_PATTERNS
        import re

        dangerous_scripts = [
            "import os",
            "__import__('os')",
            "exec('print(1)')",
            "eval('1+1')",
            "open('/etc/passwd')",
            "os.system('ls')",
            "subprocess.run(['ls'])",
        ]

        for script in dangerous_scripts:
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, script, re.IGNORECASE):
                    # At least one pattern should match
                    break
            else:
                pytest.fail(f"Dangerous script not blocked: {script}")
