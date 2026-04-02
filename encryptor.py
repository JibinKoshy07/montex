import os
from cryptography.fernet import Fernet
import base64
import hashlib
import config

def get_encryption_key():
    """Get or generate encryption key"""
    key = config.Config.ENCRYPTION_KEY
    if key:
        # Use provided key (must be valid Fernet key)
        return key.encode() if isinstance(key, str) else key
    
    # Generate key from machine-specific data
    machine_id = os.urandom(32)
    key = base64.urlsafe_b64encode(machine_id)
    return key

def encrypt(data):
    """Encrypt data"""
    if not data:
        return None
    f = Fernet(get_encryption_key())
    return f.encrypt(data.encode()).decode()

def decrypt(data):
    """Decrypt data"""
    if not data:
        return None
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(data.encode()).decode()
    except Exception:
        return None