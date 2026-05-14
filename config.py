import os
import logging

logger = logging.getLogger(__name__)

class Config:
    # Flask - SECRET_KEY must be set via environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        logger.error("SECRET_KEY environment variable is required")
        raise ValueError("SECRET_KEY environment variable must be set")
    
    # Database
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'montex.db')
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    
    # Metrics collection
    METRICS_INTERVAL = int(os.environ.get('METRICS_INTERVAL', '5'))
    SSH_TIMEOUT = int(os.environ.get('SSH_TIMEOUT', '10'))
    SSH_RETRY = int(os.environ.get('SSH_RETRY', '3'))
    
    # Default thresholds
    DEFAULT_CPU_THRESHOLD = 80
    DEFAULT_MEMORY_THRESHOLD = 85
    DEFAULT_STORAGE_THRESHOLD = 90
    
    # Default alarm evaluation (like CloudWatch) - per metric
    # Only trigger notification if N datapoints exceed threshold within M minutes
    DEFAULT_CPU_DATAPOINTS = 5
    DEFAULT_CPU_EVALUATION_MINUTES = 5
    
    DEFAULT_MEMORY_DATAPOINTS = 5
    DEFAULT_MEMORY_EVALUATION_MINUTES = 5
    
    DEFAULT_STORAGE_DATAPOINTS = 5
    DEFAULT_STORAGE_EVALUATION_MINUTES = 5
    
    # Metrics history
    METRICS_RETENTION_HOURS = 24 * 7  # 7 days