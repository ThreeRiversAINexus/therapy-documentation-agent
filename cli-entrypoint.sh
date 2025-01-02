#!/bin/bash

# Only initialize if INIT_DB is true or database doesn't exist
if [ "${INIT_DB:-false}" = "true" ] || [ ! -f "/app/data/therapy.db" ]; then
    # Initialize database
    echo "Initializing database..."
    python3 -c "from init_db import init_db; init_db()"
fi

# Run CLI with the provided arguments
python3 cli.py "$@"
