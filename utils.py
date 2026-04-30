import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def format_bytes(bytes_value):
    """Format bytes to human readable format"""
    if not bytes_value or bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    value = float(bytes_value)
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    return f"{value:.1f} {units[unit_index]}"

def format_uptime(seconds):
    """Format uptime seconds to human readable"""
    if not seconds:
        return "Unknown"
    
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def is_valid_hostname(hostname):
    """Check if hostname is valid"""
    if not hostname:
        return False
    
    # Simple validation - check for empty string and basic characters
    return len(hostname) > 0 and ' ' not in hostname

def is_valid_port(port):
    """Check if port is valid"""
    try:
        port = int(port)
        return 1 <= port <= 65535
    except (ValueError, TypeError):
        return False