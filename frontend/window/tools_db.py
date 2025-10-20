import sqlite3
from pathlib import Path

DB_PATH = Path("data/tools.db")

class ToolsDB:
    """Tool Library DB with auto-migrations."""

    def __init__(self):
        self._ensure_db()
        self._migrate_columns()

    def _ensure_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT,
                    diameter REAL,
                    length REAL,
                    rpm INTEGER,
                    feedrate REAL,
                    image_path TEXT
                )
            """)
            con.commit()

    def _migrate_columns(self):
        """Add missing columns if the DB is old."""
        with sqlite3.connect(DB_PATH) as con:
            cur = con.execute("PRAGMA table_info(tools)")
            cols = {row[1] for row in cur.fetchall()}
            if "feedrate" not in cols:
                con.execute("ALTER TABLE tools ADD COLUMN feedrate REAL DEFAULT 500;")
            if "image_path" not in cols:
                con.execute("ALTER TABLE tools ADD COLUMN image_path TEXT DEFAULT '';")
            con.commit()

    # CRUD
    def add_tool(self, name, type_, diameter, length, rpm, feedrate, image_path=""):
        with sqlite3.connect(DB_PATH) as con:
            cur = con.execute("""
                INSERT INTO tools (name, type, diameter, length, rpm, feedrate, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, type_, diameter, length, rpm, feedrate, image_path))
            con.commit()
            return cur.lastrowid

    def list_tools(self):
        with sqlite3.connect(DB_PATH) as con:
            cur = con.execute("SELECT * FROM tools ORDER BY id ASC")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_tool(self, tool_id):
        if not tool_id:
            return None
        with sqlite3.connect(DB_PATH) as con:
            cur = con.execute("SELECT * FROM tools WHERE id=?", (tool_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def update_tool(self, tool_id, **kw):
        if not tool_id:
            return
        fields, vals = [], []
        for k, v in kw.items():
            fields.append(f"{k}=?")
            vals.append(v)
        if not fields:
            return
        vals.append(tool_id)
        with sqlite3.connect(DB_PATH) as con:
            con.execute(f"UPDATE tools SET {', '.join(fields)} WHERE id=?", tuple(vals))
            con.commit()

    def delete_tool(self, tool_id):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("DELETE FROM tools WHERE id=?", (tool_id,))
            con.commit()
