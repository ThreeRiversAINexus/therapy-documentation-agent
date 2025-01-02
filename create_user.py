#!/usr/bin/env python3
import os
import sqlite3

def get_db():
    """Get database connection, initializing only if needed"""
    db_path = os.environ.get('DATABASE', 'therapy.db')
    init_db = os.environ.get('INIT_DB', 'false').lower() == 'true'
    
    # If database doesn't exist or INIT_DB is true, initialize it
    if not os.path.exists(db_path) or init_db:
        print("Initializing database...")
        db = sqlite3.connect(db_path)
        with open('schema.sql', 'r') as f:
            db.executescript(f.read())
        return db
    
    # Otherwise just connect to existing database
    return sqlite3.connect(db_path)

def create_user(username, password):
    """Create a user with the given username and password"""
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, f"pbkdf2:sha256:260000${password}")
        )
        db.commit()
        print(f"User '{username}' created successfully!")
    except sqlite3.IntegrityError:
        print(f"User '{username}' already exists")
    except Exception as e:
        print(f"Error creating user '{username}': {e}")
    finally:
        db.close()

def create_test_user():
    """Create default test user"""
    create_user('test', 'test123')

if __name__ == "__main__":
    create_test_user()
