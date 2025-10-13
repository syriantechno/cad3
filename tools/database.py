
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "profiles.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT,
    dimensions TEXT,
    notes TEXT,
    dxf_path TEXT NOT NULL,
    brep_path TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name) ON CONFLICT IGNORE
);
"""

class ProfileDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self._ensure_db()

    def _ensure_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as con:
            con.execute(SCHEMA)

    def add_profile(self, *, name: str, code: str, dimensions: str, notes: str,
                    dxf_path: str, brep_path: str, image_path: str) -> int:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO profiles (name, code, dimensions, notes, dxf_path, brep_path, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, code, dimensions, notes, dxf_path, brep_path, image_path))
            con.commit()
            return cur.lastrowid

    def list_profiles(self, limit: int = 200):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("""SELECT id, name, code, dimensions, notes, dxf_path, brep_path, image_path, created_at
                           FROM profiles ORDER BY created_at DESC LIMIT ?""", (limit,))
            return cur.fetchall()
