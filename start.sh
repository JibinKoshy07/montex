#!/bin/bash

# Montex - Server Monitoring Application
# Startup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already running
if pgrep -f "python3 app.py" > /dev/null; then
    echo "Montex is already running"
    exit 0
fi

# Install dependencies if needed
if [ ! -d "venv" ] && [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
echo "Starting Montex..."
python3 app.py > app.log 2>&1 &

# Wait a moment and check if started
sleep 2
if pgrep -f "python3 app.py" > /dev/null; then
    echo "Montex is running on http://localhost:5000"
    echo "To stop: pkill -f 'python3 app.py'"
else
    echo "Failed to start Montex"
    cat app.log
    exit 1
fi