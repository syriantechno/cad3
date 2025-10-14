from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "tools.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            diameter REAL,
            length REAL,
            type TEXT,
            rpm INTEGER,
            steps INTEGER,
            image_path TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_tool(name, diameter, length, type_, rpm, steps, image_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tools (name, diameter, length, type, rpm, steps, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, diameter, length, type_, rpm, steps, image_path))
    conn.commit()
    conn.close()

def get_all_tools():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools")
    tools = cursor.fetchall()
    conn.close()
    return tools