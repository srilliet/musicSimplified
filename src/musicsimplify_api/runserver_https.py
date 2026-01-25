#!/usr/bin/env python
"""
Run Django development server with HTTPS support.
Usage: python runserver_https.py [port] [host]
Example: python runserver_https.py 8080 0.0.0.0
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import settings
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'musicsimplify_api.settings')

import django
from django.core.management import execute_from_command_line
from django.conf import settings

if __name__ == '__main__':
    django.setup()
    
    # Get port and host from command line arguments
    port = sys.argv[1] if len(sys.argv) > 1 else '8080'
    host = sys.argv[2] if len(sys.argv) > 2 else '0.0.0.0'
    
    # Check if SSL certificates exist
    cert_path = getattr(settings, 'SSL_CERTIFICATE', None)
    key_path = getattr(settings, 'SSL_PRIVATE_KEY', None)
    
    if cert_path and key_path and cert_path.exists() and key_path.exists():
        # Use runserver_plus with SSL
        execute_from_command_line([
            'manage.py',
            'runserver_plus',
            f'--cert-file={cert_path}',
            f'--key-file={key_path}',
            f'{host}:{port}'
        ])
    else:
        # Fall back to regular runserver if certificates don't exist
        print("Warning: SSL certificates not found. Running without HTTPS.")
        print(f"Expected cert: {cert_path}")
        print(f"Expected key: {key_path}")
        execute_from_command_line([
            'manage.py',
            'runserver',
            f'{host}:{port}'
        ])
