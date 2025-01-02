#!/bin/bash

# Initialize database
echo "Initializing database..."
python3 init_db.py

# Create default test user
echo "Creating default test user..."
python3 create_user.py

# Run the CLI
python3 cli.py "$@"
