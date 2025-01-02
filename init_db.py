#!/usr/bin/env python3
import sqlite3
import os

def init_db():
    """Initialize the database"""
    db_path = os.environ.get('DATABASE', 'therapy.db')
    
    # Check if we should initialize the database
    init_db = os.environ.get('INIT_DB', 'false').lower() == 'true'
    
    # If database exists and INIT_DB is false, skip initialization
    if os.path.exists(db_path) and not init_db:
        print(f"Database {db_path} exists and INIT_DB=false, skipping initialization")
        return
    
    print(f"Initializing database {db_path}...")
    db = sqlite3.connect(db_path)
    
    with open('schema.sql', 'r') as f:
        db.executescript(f.read())
    
    db.close()
    print("Database initialized successfully")

if __name__ == "__main__":
    init_db()
