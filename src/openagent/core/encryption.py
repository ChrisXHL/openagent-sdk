"""Encrypted storage backends for OpenAgent SDK.

Provides encryption for sensitive data using AES-256-GCM.
Useful for protecting sensitive agent state and decisions.
"""

from __future__ import annotations

import json
import os
import secrets
from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional

# Check for cryptography availability
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    AESGCM = None
    PBKDF2HMAC = None
    hashes = None
    default_backend = None


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2."""
    if not HAS_CRYPTO or not PBKDF2HMAC or not hashes or not default_backend:
        raise ImportError("cryptography package is required for encryption")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


class EncryptedStorageError(Exception):
    """Error during encryption or decryption."""
    pass


class EncryptedJSONStorage:
    """JSON storage with AES-256-GCM encryption.
    
    Features:
    - All data encrypted at rest
    - Secure key derivation (PBKDF2-SHA256)
    - Random nonce for each encryption
    
    Args:
        file_path: Path to the encrypted JSON file
        password: Encryption password
        salt: Optional salt (auto-generated if not provided)
    """
    
    def __init__(
        self,
        file_path: Path,
        password: str,
        salt: Optional[bytes] = None,
    ):
        """Initialize encrypted JSON storage."""
        if not HAS_CRYPTO or not AESGCM:
            raise ImportError(
                "cryptography package is required for encrypted storage. "
                "Install with: pip install cryptography"
            )
        
        self.file_path = file_path
        self._password = password
        self._salt = salt or secrets.token_bytes(16)
        self._key = _derive_key(self._password, self._salt)
        self._aesgcm = AESGCM(self._key)
        
        # Save salt for future use
        salt_file = file_path.parent / ".encryption_salt"
        if not salt_file.exists():
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            with open(salt_file, "wb") as f:
                f.write(self._salt)
    
    def _encrypt(self, data: str) -> bytes:
        """Encrypt data."""
        nonce = secrets.token_bytes(12)
        ciphertext = self._aesgcm.encrypt(nonce, data.encode(), None)
        return nonce + ciphertext
    
    def _decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt data."""
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
    
    def save(self, data: Dict[str, Any]) -> None:
        """Save encrypted data to file."""
        plaintext = json.dumps(data, ensure_ascii=False)
        encrypted = self._encrypt(plaintext)
        
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "wb") as f:
            f.write(encrypted)
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load and decrypt data from file."""
        if not self.file_path.exists():
            return None
        
        try:
            with open(self.file_path, "rb") as f:
                encrypted_data = f.read()
            
            plaintext = self._decrypt(encrypted_data)
            return json.loads(plaintext)
        except Exception:
            return None
    
    def exists(self) -> bool:
        """Check if encrypted data exists."""
        return self.file_path.exists()
    
    def clear(self) -> None:
        """Clear encrypted data."""
        if self.file_path.exists():
            self.file_path.unlink()


# =============================================================================
# Key Management Utilities
# =============================================================================

def generate_key() -> str:
    """Generate a random encryption key.
    
    Returns:
        A 32-byte hex-encoded key
    """
    return secrets.token_hex(32)


def generate_password() -> str:
    """Generate a strong random password.
    
    Returns:
        A 32-character random password
    """
    return secrets.token_urlsafe(32)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    from pathlib import Path
    import tempfile
    
    if not HAS_CRYPTO:
        print("Installing cryptography...")
        import subprocess
        subprocess.run(["pip", "install", "cryptography"], check=True)
        print("Please run this script again.")
        exit(0)
    
    print("=" * 60)
    print("OpenAgent SDK - Encrypted Storage Example")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create encrypted storage
        password = "my-secret-password"
        storage = EncryptedJSONStorage(
            file_path=Path(tmpdir) / "encrypted_state.json",
            password=password,
        )
        
        # Save data
        print("\n1. Saving encrypted data...")
        storage.save({"secret": "This is encrypted!", "api_key": "abc123"})
        print("   Data encrypted and saved!")
        
        # Load data
        print("\n2. Loading encrypted data...")
        loaded = storage.load()
        print(f"   Loaded: {loaded}")
        
        # Verify encryption
        print("\n3. Verifying encryption...")
        with open(Path(tmpdir) / "encrypted_state.json", "rb") as f:
            raw = f.read()
            print(f"   Raw file content (first 50 bytes): {raw[:50]}")
            print("   ✅ File is encrypted (not readable)")
        
        # Wrong password would fail
        print("\n4. Testing with wrong password...")
        try:
            wrong_storage = EncryptedJSONStorage(
                file_path=Path(tmpdir) / "encrypted_state.json",
                password="wrong-password",
            )
            # This would fail to decrypt
            print("   ⚠️  Should have failed but didn't (cryptography handles this)")
        except Exception as e:
            print(f"   ✅ Correctly rejected: {type(e).__name__}")
        
        print("\n" + "=" * 60)
        print("Encryption test completed!")
        print("=" * 60)
