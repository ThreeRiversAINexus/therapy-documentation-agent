from typing import Dict, List, Optional

class TherapyDocTools:
    """Tools for documenting therapy sessions"""
    
    def __init__(self):
        """Initialize therapy documentation tools"""
        import sqlite3
        import os
        
        self.current_category = None
        self.current_data = {}
        self.notes = {}
        self.db_path = os.environ.get('DATABASE', '/app/data/therapy.db')
        
        # Create tables if they don't exist
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS category_data (
                    category_id TEXT PRIMARY KEY,
                    next_steps TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS category_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id TEXT NOT NULL,
                    section_name TEXT NOT NULL,
                    observations TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS category_notes (
                    category_id TEXT PRIMARY KEY,
                    notes TEXT
                )
            """)
            
            # Initialize categories and their sections
            categories = self.get_categories()
            for category in categories:
                db.execute("""
                    INSERT OR IGNORE INTO category_data (category_id, next_steps)
                    VALUES (?, '')
                """, (category['id'],))
                db.execute("""
                    INSERT OR IGNORE INTO category_notes (category_id, notes)
                    VALUES (?, '')
                """, (category['id'],))
                
                # No need to initialize empty sections anymore
                pass
    
    def set_category_section_observations(self, *, category_id: str, section_name: str, observations: str):
        """Set observations for a specific section of a therapy category"""
        # Validate category exists
        categories = {cat['id']: cat for cat in self.get_categories()}
        if category_id not in categories:
            raise ValueError(f"Invalid category: {category_id}")
        
        # Validate section exists
        if section_name not in categories[category_id].get('sections', []):
            raise ValueError(f"Invalid section: {section_name}")
        
        import sqlite3
        self.current_category = category_id
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO category_sections (category_id, section_name, observations)
                VALUES (?, ?, ?)
            """, (category_id, section_name, observations))
            db.commit()
        return f"Observations set for {category_id} - {section_name}"
    
    def set_category_next_steps(self, *, category_id: str, next_steps: str):
        """Set next steps for a therapy category"""
        # Validate category exists
        categories = {cat['id'] for cat in self.get_categories()}
        if category_id not in categories:
            raise ValueError(f"Invalid category: {category_id}")
        
        import sqlite3
        self.current_category = category_id
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT OR REPLACE INTO category_data (category_id, next_steps)
                VALUES (?, ?)
            """, (category_id, next_steps))
            db.commit()
        return f"Next steps set for {category_id}"
    
    def add_category_notes(self, *, category_id: str, notes: str):
        """Add notes to a therapy category"""
        # Validate category exists
        categories = {cat['id'] for cat in self.get_categories()}
        if category_id not in categories:
            raise ValueError(f"Invalid category: {category_id}")
        
        import sqlite3
        self.current_category = category_id
        with sqlite3.connect(self.db_path) as db:
            # Get existing notes
            cur = db.execute("SELECT notes FROM category_notes WHERE category_id = ?", (category_id,))
            row = cur.fetchone()
            existing_notes = row[0] if row else ''
            
            # Append new notes
            new_notes = notes if not existing_notes else f"{existing_notes}\n{notes}"
            
            # Update notes
            db.execute("""
                INSERT OR REPLACE INTO category_notes (category_id, notes)
                VALUES (?, ?)
            """, (category_id, new_notes))
            db.commit()
        return f"Notes added to {category_id}"
    
    def get_category_summary(self, *, category_id: str) -> Dict[str, str]:
        """Get summary of documentation for a category"""
        # Validate category exists
        categories = {cat['id']: cat for cat in self.get_categories()}
        if category_id not in categories:
            raise ValueError(f"Invalid category: {category_id}")
        
        import sqlite3
        with sqlite3.connect(self.db_path) as db:
            # Get main data
            cur = db.execute("""
                SELECT d.next_steps, n.notes
                FROM category_data d
                LEFT JOIN category_notes n ON d.category_id = n.category_id
                WHERE d.category_id = ?
            """, (category_id,))
            row = cur.fetchone()
            
            # Get section observations from the last 2 weeks, excluding empty observations
            sections_cur = db.execute("""
                SELECT id, section_name, observations, timestamp
                FROM category_sections
                WHERE category_id = ? 
                AND timestamp >= datetime('now', '-14 days')
                AND observations != ''
                ORDER BY timestamp DESC
            """, (category_id,))
            
            sections_data = {}
            for section_row in sections_cur:
                section_name = section_row[1]
                if section_name not in sections_data:
                    sections_data[section_name] = []
                sections_data[section_name].append({
                    'id': section_row[0],
                    'observation': section_row[2],
                    'timestamp': section_row[3]
                })
            
            return {
                'sections': sections_data,
                'next_steps': row[0] if row else '',
                'notes': row[1] if row else ''
            }
    
    def clear_category(self, *, category_id: str):
        """Clear documentation for a category"""
        # Validate category exists
        categories = {cat['id'] for cat in self.get_categories()}
        if category_id not in categories:
            raise ValueError(f"Invalid category: {category_id}")
        
        import sqlite3
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                UPDATE category_data
                SET next_steps = ''
                WHERE category_id = ?
            """, (category_id,))
            db.execute("""
                UPDATE category_sections
                SET observations = ''
                WHERE category_id = ?
            """, (category_id,))
            db.execute("""
                UPDATE category_notes
                SET notes = ''
                WHERE category_id = ?
            """, (category_id,))
            db.commit()
        return f"Documentation cleared for {category_id}"
    
    def get_categories(self) -> List[Dict[str, str]]:
        """Get list of available therapy categories"""
        return [
            {
                'id': 'journaling',
                'name': 'Journaling',
                'sections': ['General notes', 'Counting entries', 'Cognitive therapy']
            },
            {
                'id': 'sleep',
                'name': 'Sleep',
                'sections': ['General notes', 'Length of sleep', 'Schedule', 'Dreams']
            },
            {
                'id': 'physical',
                'name': 'Physical Activity',
                'sections': ['General notes', 'Fitbit heart rate zones', 'Strength training']
            },
            {
                'id': 'social',
                'name': 'Social Engagement',
                'sections': ['General notes', 'In-person', 'Text', 'VC']
            },
            {
                'id': 'productivity',
                'name': 'Productivity & Work',
                'sections': ['General notes', 'Cold Turkey', 'iOS Screen Time']
            },
            {
                'id': 'spiritual',
                'name': 'Spiritual Practice',
                'sections': ['General notes', 'Solo', 'Group']
            },
            {
                'id': 'self_care',
                'name': 'Basic Self-Care',
                'sections': ['General notes', 'Meals hygiene meds', 'budget checklist medical appts']
            }
        ]
    
    def get_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        return [
            {
                'name': 'set_category_section_observations',
                'description': 'Set observations for a specific section of a therapy category. Required parameters: {"category_id": "category name", "section_name": "section name", "observations": "observation text"}',
                'func': self.set_category_section_observations
            },
            {
                'name': 'set_category_next_steps',
                'description': 'Set next steps for a therapy category. Required parameters: {"category_id": "category name", "next_steps": "next steps text"}',
                'func': self.set_category_next_steps
            },
            {
                'name': 'add_category_notes',
                'description': 'Add notes to a therapy category. Required parameters: {"category_id": "category name", "notes": "notes text"}',
                'func': self.add_category_notes
            },
            {
                'name': 'get_category_summary',
                'description': 'Get summary of documentation for a category',
                'func': self.get_category_summary
            },
            {
                'name': 'clear_category',
                'description': 'Clear documentation for a category',
                'func': self.clear_category
            },
            {
                'name': 'get_categories',
                'description': 'Get list of available therapy categories',
                'func': self.get_categories
            }
        ]
