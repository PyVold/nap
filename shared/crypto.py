# ============================================================================
# utils/crypto.py
# ============================================================================

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# In production, this should come from environment variable
# For now, we'll use a derived key from a salt
SECRET_KEY = os.getenv("ENCRYPTION_KEY", "network-audit-platform-secret-key-change-in-production")


def get_encryption_key() -> bytes:
    """Derive an encryption key from the secret"""
    salt = b'network_audit_salt_v1'  # In production, store this securely
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))
    return key


# Initialize Fernet cipher
cipher = Fernet(get_encryption_key())


def encrypt_password(password: str) -> str:
    """Encrypt a password"""
    if not password:
        return ""
    encrypted = cipher.encrypt(password.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password"""
    if not encrypted_password:
        return ""
    try:
        decoded = base64.urlsafe_b64decode(encrypted_password.encode())
        decrypted = cipher.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        return ""  # Return empty string if decryption fails
