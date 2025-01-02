-- User authentication tables
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Therapy documentation tables
DROP TABLE IF EXISTS category_data;
DROP TABLE IF EXISTS category_notes;
DROP TABLE IF EXISTS category_sections;

CREATE TABLE category_data (
    category_id TEXT PRIMARY KEY,
    next_steps TEXT
);

CREATE TABLE category_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id TEXT NOT NULL,
    section_name TEXT NOT NULL,
    observations TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, section_name, timestamp)
);

CREATE TABLE category_notes (
    category_id TEXT PRIMARY KEY,
    notes TEXT
);

-- Create indexes for better performance
CREATE INDEX idx_category_data ON category_data(category_id);
CREATE INDEX idx_category_notes ON category_notes(category_id);
CREATE INDEX idx_category_sections ON category_sections(category_id);
CREATE INDEX idx_category_sections_timestamp ON category_sections(timestamp);
