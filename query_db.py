#!/usr/bin/env python3
import sqlite3
import os

def query_db():
    """Query the database tables and show their contents"""
    db_path = '/app/data/therapy.db'
    
    print(f"Querying database at {db_path}")
    
    with sqlite3.connect(db_path) as db:
        # Query category_data table
        print("\nExecuting: SELECT * FROM category_data")
        cur = db.execute("SELECT * FROM category_data")
        rows = cur.fetchall()
        print("\nCategory Data:")
        for row in rows:
            print(f"category_id: {row[0]}")
            print(f"observations: {row[1]}")
            print(f"next_steps: {row[2]}")
            print("---")
            
        # Query category_notes table
        print("\nExecuting: SELECT * FROM category_notes")
        cur = db.execute("SELECT * FROM category_notes")
        rows = cur.fetchall()
        print("\nCategory Notes:")
        for row in rows:
            print(f"category_id: {row[0]}")
            print(f"notes: {row[1]}")
            print("---")

if __name__ == "__main__":
    query_db()
