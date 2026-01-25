#!/bin/bash
# Run Django server with HTTPS support
# Usage: ./run_https.sh [port] [host]
# Example: ./run_https.sh 8080 0.0.0.0

PORT=${1:-8080}
HOST=${2:-0.0.0.0}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CERT_FILE="$SCRIPT_DIR/../frontEnd/cert.pem"
KEY_FILE="$SCRIPT_DIR/../frontEnd/key.pem"

# Check if certificates exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Warning: SSL certificates not found at:"
    echo "  Cert: $CERT_FILE"
    echo "  Key: $KEY_FILE"
    echo "Running without HTTPS..."
    cd "$SCRIPT_DIR"
    source ../../venv/bin/activate
    python manage.py runserver $HOST:$PORT
else
    echo "Starting Django server with HTTPS on $HOST:$PORT"
    cd "$SCRIPT_DIR"
    source ../../venv/bin/activate
    python manage.py runserver_plus --cert-file="$CERT_FILE" --key-file="$KEY_FILE" $HOST:$PORT
fi
