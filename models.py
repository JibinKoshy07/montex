import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import config

DATABASE_PATH = config.Config.DATABASE_PATH

@contextmanager
def get_db():
    """Database context manager"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Servers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hostname TEXT NOT NULL,
                port INTEGER DEFAULT 22,
                username TEXT NOT NULL,
                auth_type TEXT NOT NULL,
                password_encrypted TEXT,
                key_encrypted TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Metrics history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_used INTEGER,
                memory_total INTEGER,
                storage_percent REAL,
                storage_used INTEGER,
                storage_total INTEGER,
                is_online INTEGER DEFAULT 1,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_server_time 
            ON metrics_history (server_id, collected_at)
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                metric TEXT NOT NULL,
                threshold REAL NOT NULL,
                actual_value REAL NOT NULL,
                message TEXT,
                is_resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()

def get_all_servers():
    """Get all servers"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servers ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]

def get_server(server_id):
    """Get single server by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_server(name, hostname, port, username, auth_type, password=None, key=None, tags=None):
    """Add new server"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO servers (name, hostname, port, username, auth_type, password_encrypted, key_encrypted, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, hostname, port, username, auth_type, password, key, tags))
        return cursor.lastrowid

def update_server(server_id, name, hostname, port, username, auth_type, password=None, key=None, tags=None):
    """Update server"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE servers 
            SET name=?, hostname=?, port=?, username=?, auth_type=?, 
                password_encrypted=?, key_encrypted=?, tags=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (name, hostname, port, username, auth_type, password, key, tags, server_id))

def delete_server(server_id):
    """Delete server"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM servers WHERE id = ?', (server_id,))

def save_metrics(server_id, cpu_percent, memory_percent, memory_used, memory_total,
                 storage_percent, storage_used, storage_total, is_online):
    """Save metrics to history"""
    from datetime import datetime, timezone
    with get_db() as conn:
        cursor = conn.cursor()
        # Use UTC timestamp to ensure consistency with SQLite
        utc_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO metrics_history 
            (server_id, cpu_percent, memory_percent, memory_used, memory_total,
             storage_percent, storage_used, storage_total, is_online, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (server_id, cpu_percent, memory_percent, memory_used, memory_total,
              storage_percent, storage_used, storage_total, is_online, utc_now))

def get_latest_metrics(server_id):
    """Get latest metrics for a server"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM metrics_history 
            WHERE server_id = ? 
            ORDER BY collected_at DESC 
            LIMIT 1
        ''', (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_metrics_history(server_id, hours=24):
    """Get metrics history for a server"""
    with get_db() as conn:
        cursor = conn.cursor()
        since = datetime.now() - timedelta(hours=hours)
        # Format for SQLite: YYYY-MM-DD HH:MM:SS
        since_str = since.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT * FROM metrics_history 
            WHERE server_id = ? AND collected_at > ?
            ORDER BY collected_at ASC
        ''', (server_id, since_str))
        return [dict(row) for row in cursor.fetchall()]
def get_metrics_in_minutes(server_id, minutes):
    '''Get metrics within the last N minutes'''
    import logging
    logger = logging.getLogger(__name__)
    with get_db() as conn:
        cursor = conn.cursor()
        # Use UTC datetime consistently
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        since = now_utc - timedelta(minutes=minutes)
        since_str = since.strftime('%Y-%m-%d %H:%M:%S')
        current_str = now_utc.strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"get_metrics_in_minutes: server_id={server_id}, minutes={minutes}, since={since_str}, now={current_str}")
        
        cursor.execute('''
            SELECT * FROM metrics_history 
            WHERE server_id = ? AND collected_at > ? AND collected_at <= ?
            ORDER BY collected_at DESC
        ''', (server_id, since_str, current_str))
        results = cursor.fetchall()
        logger.info(f"Found {len(results)} metrics in last {minutes} min")
        return [dict(row) for row in results]

def get_all_latest_metrics():
    """Get latest metrics for all servers"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, s.name as server_name, s.hostname
            FROM metrics_history m
            JOIN servers s ON m.server_id = s.id
            WHERE m.id IN (
                SELECT MAX(id) FROM metrics_history 
                GROUP BY server_id
            )
        ''')
        return [dict(row) for row in cursor.fetchall()]

def cleanup_old_metrics(hours=24):
    """Remove old metrics data"""
    with get_db() as conn:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        # Use same format as get_metrics_history for consistent comparison
        cursor.execute('DELETE FROM metrics_history WHERE collected_at < ?', (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))

def get_setting(key, default=None):
    """Get setting value"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

def set_setting(key, value):
    """Set setting value"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
        ''', (key, value, value))

def get_all_settings():
    """Get all settings"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM settings')
        return {row['key']: row['value'] for row in cursor.fetchall()}

def save_alert(server_id, alert_type, metric, threshold, actual_value, message):
    """Save alert"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (server_id, alert_type, metric, threshold, actual_value, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (server_id, alert_type, metric, threshold, actual_value, message))

def get_unresolved_alerts():
    """Get unresolved alerts"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, s.name as server_name
            FROM alerts a
            JOIN servers s ON a.server_id = s.id
            WHERE a.is_resolved = 0
            ORDER BY a.created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def resolve_alert(alert_id):
    """Resolve alert"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE alerts SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (alert_id,))

def init():
    """Initialize database"""
    init_db()