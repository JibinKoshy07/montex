# Montex - Lightweight Server Monitoring

A production-grade, lightweight server monitoring application that monitors remote servers via SSH and displays CPU, Memory, and Storage metrics. Includes Telegram notifications for threshold alerts.

## Features

- **SSH-based Monitoring**: Connect to remote servers via SSH to collect metrics
- **Real-time Dashboard**: View all servers and their status at a glance
- **Metrics Collection**: CPU, Memory, and Storage usage monitoring
- **Telegram Alerts**: Get notified via Telegram when thresholds are exceeded
- **Server Offline Alerts**: Notifications when servers go offline/come back online
- **Dark Theme UI**: Modern, production-grade interface
- **Responsive Design**: Works on desktop, tablet, and mobile

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python3 app.py
```

The application will be available at `http://localhost:5000`

## Configuration

### Adding a Server

1. Click "Add Server" in the sidebar
2. Enter server details:
   - Server Name (e.g., "Production Web Server")
   - Hostname/IP (e.g., "192.168.1.100")
   - SSH Port (default: 22)
   - SSH Username
   - Authentication Type (Password or SSH Key)
3. Click "Test Connection" to verify
4. Click "Save Server"

### Configuring Telegram Notifications

1. Go to Settings
2. Enter your Telegram Bot Token (get from @BotFather)
3. Enter your Chat ID (get from @userinfobot)
4. Adjust threshold sliders as needed
5. Click "Save Settings"
6. Click "Test" to verify notifications work

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard |
| GET | `/api/servers` | List all servers |
| POST | `/api/servers` | Add new server |
| PUT | `/api/servers/<id>` | Update server |
| DELETE | `/api/servers/<id>` | Delete server |
| GET | `/api/settings` | Get settings |
| POST | `/api/settings` | Update settings |
| POST | `/api/test-connection` | Test SSH connection |
| POST | `/api/test-telegram` | Test Telegram notification |

## Default Thresholds

- CPU: 80%
- Memory: 85%
- Storage: 90%

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **SSH**: Paramiko
- **Scheduling**: APScheduler
- **Notifications**: Telegram Bot API

## Security

- SSH credentials are encrypted at rest
- No plain-text passwords stored
- Secure session management

## ⚠️ Security Setup Before Running

**Before running the application in production, you MUST update these security keys:**

### 1. Set SECRET_KEY Environment Variable

The application uses a default secret key for session management. **Change this before production use:**

```bash
# Generate a random secret key (Python 3.6+)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or set it as an environment variable
export SECRET_KEY="your-unique-secret-key-here"
```

You can also set it in docker-compose.yml or a `.env` file.

### 2. Change Default Admin Password

The application creates a default admin user (`admin`/`admin123`) on first run. **Change this password immediately** after first login via the Settings → Change Password option.

### 3. Recommended Environment Variables

```bash
export SECRET_KEY="your-secure-random-key"      # Required: session security
export ENCRYPTION_KEY="your-encryption-key"  # Optional: auto-generated if not set
```

### 4. Create a Read-Only SSH User for Monitoring

When adding remote servers to monitor, **create a dedicated read-only user** on each remote server instead of using root or privileged users. This follows the **principle of least privilege**.

The monitoring app only needs to run read-only commands like `top`, `free`, `df`, and `uptime` - these don't require root/sudo.

On each remote server, run:

```bash
# Create a read-only user (no root/sudo needed)
useradd -m -s /bin/bash montex

# Set password for the user
passwd montex
```

Then use these read-only credentials when adding servers in Montex.

## License

MIT
