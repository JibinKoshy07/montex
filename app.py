from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import models
import ssh_client
import encryptor
import telegram_bot
import metrics_collector
import config
import json
import logging
import logging.handlers
import hashlib

# Setup logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('montex.log', maxBytes=5*1024*1024, backupCount=3),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.config['SECRET_KEY'] = config.Config.SECRET_KEY
app.secret_key = config.Config.SECRET_KEY

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """API login"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'})
    
    if models.verify_user(username, password):
        session['user_id'] = username
        session.permanent = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    """Change password"""
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return jsonify({'success': False, 'message': 'Old and new password required'})
    
    username = session.get('user_id')
    if models.change_password(username, old_password, new_password):
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid old password'})

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """API logout"""
    session.clear()
    return jsonify({'success': True})

@app.route('/')
@login_required
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/servers', methods=['GET'])
@login_required
def get_servers():
    """Get all servers"""
    servers = models.get_all_servers()
    
    # Get latest metrics for each server
    for server in servers:
        metrics = models.get_latest_metrics(server['id'])
        server['metrics'] = metrics
    
    return jsonify(servers)

@app.route('/api/servers', methods=['POST'])
@login_required
def add_server():
    """Add new server"""
    data = request.json
    
    name = data.get('name')
    hostname = data.get('hostname')
    port = int(data.get('port', 22))
    username = data.get('username')
    auth_type = data.get('auth_type')
    password = data.get('password')
    key = data.get('key')
    tags = data.get('tags')
    
    if not all([name, hostname, username, auth_type]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Encrypt credentials
    password_encrypted = encryptor.encrypt(password) if password else None
    key_encrypted = encryptor.encrypt(key) if key else None
    
    server_id = models.add_server(
        name=name,
        hostname=hostname,
        port=port,
        username=username,
        auth_type=auth_type,
        password=password_encrypted,
        key=key_encrypted,
        tags=tags
    )
    
    return jsonify({'success': True, 'server_id': server_id})

@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    """Update server"""
    data = request.json
    
    name = data.get('name')
    hostname = data.get('hostname')
    port = int(data.get('port', 22))
    username = data.get('username')
    auth_type = data.get('auth_type')
    password = data.get('password')
    key = data.get('key')
    tags = data.get('tags')
    
    if not all([name, hostname, username, auth_type]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Encrypt credentials
    password_encrypted = encryptor.encrypt(password) if password else None
    key_encrypted = encryptor.encrypt(key) if key else None
    
    models.update_server(
        server_id=server_id,
        name=name,
        hostname=hostname,
        port=port,
        username=username,
        auth_type=auth_type,
        password=password_encrypted,
        key=key_encrypted,
        tags=tags
    )
    
    return jsonify({'success': True})

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    """Delete server"""
    models.delete_server(server_id)
    return jsonify({'success': True})

@app.route('/api/servers/<int:server_id>/metrics', methods=['GET'])
def get_server_metrics(server_id):
    """Get server metrics"""
    server = models.get_server(server_id)
    if not server:
        return jsonify({'success': False, 'message': 'Server not found'}), 404
    
    hours = int(request.args.get('hours', 24))
    history = models.get_metrics_history(server_id, hours)
    latest = models.get_latest_metrics(server_id)
    
    return jsonify({
        'success': True,
        'server': server,
        'latest': latest,
        'history': history
    })

@app.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test SSH connection"""
    data = request.json
    
    hostname = data.get('hostname')
    port = int(data.get('port', 22))
    username = data.get('username')
    auth_type = data.get('auth_type')
    password = data.get('password')
    key = data.get('key')
    
    result = ssh_client.test_connection(
        hostname=hostname,
        port=port,
        username=username,
        auth_type=auth_type,
        password=password,
        key=key
    )
    
    return jsonify(result)

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get all settings"""
    settings = models.get_all_settings()
    
    # Mask sensitive values
    if settings.get('telegram_token'):
        settings['telegram_token'] = '***' if settings['telegram_token'] != '' else ''
    
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    """Update settings"""
    data = request.json
    
    # Telegram settings
    if 'telegram_token' in data:
        token = data['telegram_token']
        if token and not token.startswith('***'):
            models.set_setting('telegram_token', token)
    
    if 'telegram_chat_id' in data:
        models.set_setting('telegram_chat_id', data['telegram_chat_id'])
    
    # Thresholds
    if 'cpu_threshold' in data:
        models.set_setting('cpu_threshold', str(data['cpu_threshold']))
    
    if 'memory_threshold' in data:
        models.set_setting('memory_threshold', str(data['memory_threshold']))
    
    if 'storage_threshold' in data:
        models.set_setting('storage_threshold', str(data['storage_threshold']))
    
    
    # Per-metric datapoint evaluation settings (like CloudWatch)
    # CPU
    if 'cpu_datapoints' in data:
        models.set_setting('cpu_datapoints', str(data['cpu_datapoints']))
    if 'cpu_evaluation_minutes' in data:
        models.set_setting('cpu_evaluation_minutes', str(data['cpu_evaluation_minutes']))
    
    # Memory
    if 'memory_datapoints' in data:
        models.set_setting('memory_datapoints', str(data['memory_datapoints']))
    if 'memory_evaluation_minutes' in data:
        models.set_setting('memory_evaluation_minutes', str(data['memory_evaluation_minutes']))
    
    # Storage
    if 'storage_datapoints' in data:
        models.set_setting('storage_datapoints', str(data['storage_datapoints']))
    if 'storage_evaluation_minutes' in data:
        models.set_setting('storage_evaluation_minutes', str(data['storage_evaluation_minutes']))
    
    return jsonify({'success': True})
    
    return jsonify({'success': True})

@app.route('/api/test-telegram', methods=['POST'])
@login_required
def test_telegram():
    """Test Telegram notification"""
    data = request.json
    
    token = data.get('token')
    chat_id = data.get('chat_id')
    
    if not token or not chat_id:
        return jsonify({'success': False, 'message': 'Token and chat ID required'}), 400
    
    notifier = telegram_bot.TelegramNotifier(token, chat_id)
    result = notifier.test_notification()
    
    return jsonify(result)

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get unresolved alerts"""
    alerts = models.get_unresolved_alerts()
    return jsonify(alerts)

@app.route('/api/alarms', methods=['GET'])
@login_required
def get_alarms():
    """Get all alarm states for UI sidebar"""
    alarms = models.get_all_alarm_states()
    return jsonify({
        'count': len(alarms),
        'alarms': alarms
    })

def init_app():
    """Initialize the application"""
    # Initialize database
    models.init()
    
    # Create default admin user if none exists
    import logging
    logger = logging.getLogger(__name__)
    with models.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        if count == 0:
            # Create default admin user
            models.create_user('admin', 'admin123')
            logger.info('Created default admin user')

    # Start metrics collector
    metrics_collector.collector.start()

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=False)