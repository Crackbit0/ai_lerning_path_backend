#!/bin/bash
set -e

echo "=== Starting AI Learning Path Generator ==="

# Set Flask app for migrations
export FLASK_APP=web_app:create_app

# Debug: Check if SECRET_KEY is set
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY is not set! Sessions/CSRF will not work properly."
else
    echo "SECRET_KEY is configured (length: ${#SECRET_KEY})"
fi

# Initialize database if it doesn't exist
echo "Initializing database..."
python -c "
from web_app import create_app
from web_app.models import db

app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Database initialized')
"

echo "Starting gunicorn server..."
# Use 1 worker to avoid CSRF token mismatch between workers
# Use threads instead for concurrency
exec gunicorn run:app --bind 0.0.0.0:7860 --workers 1 --threads 4 --timeout 120
