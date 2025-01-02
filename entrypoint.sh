#!/bin/bash
set -e

# Initialize the database if it doesn't exist
if [ ! -f "$DATABASE" ]; then
    echo "Initializing database..."
    python3 -c "from app import init_db; init_db()"
fi

# Start the application
echo "Starting application..."
gunicorn --bind 0.0.0.0:5000 app:app
