import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'montex-secret-key-change-in-production')
    
    # Database
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'montex.db')
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    
    # Metrics collection
    METRICS_INTERVAL = int(os.environ.get('METRICS_INTERVAL', '60'))
    SSH_TIMEOUT = int(os.environ.get('SSH_TIMEOUT', '10'))
    SSH_RETRY = int(os.environ.get('SSH_RETRY', '3'))
    
    # Default thresholds
    DEFAULT_CPU_THRESHOLD = 80
    DEFAULT_MEMORY_THRESHOLD = 85
    DEFAULT_STORAGE_THRESHOLD = 90
    
    # Metrics history
    METRICS_RETENTION_HOURS = 24