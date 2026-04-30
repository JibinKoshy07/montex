import os
from cryptography.fernet import Fernet
import base64
import config

def get_encryption_key():
    """Get or generate encryption key"""
    key = config.Config.ENCRYPTION_KEY
    if key:
        # Use provided key (must be valid Fernet key)
        return key.encode() if isinstance(key, str) else key
    
    # Try to load existing key from database first
    import models
    saved_key = models.get_setting('encryption_key')
    if saved_key:
        return saved_key.encode()
    
    # Generate a new key and save it for persistence
    machine_id = os.urandom(32)
    new_key = base64.urlsafe_b64encode(machine_id)
    
    # Save the key to database so it persists across restarts
    try:
        models.set_setting('encryption_key', new_key.decode())
    except Exception:
        pass
    
    return new_key

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