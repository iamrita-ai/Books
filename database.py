import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE,
                file_unique_id TEXT UNIQUE,
                normalized_name TEXT,
                original_filename TEXT,
                file_size INTEGER,
                message_id INTEGER,
                channel_id INTEGER,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_normalized_name ON files(normalized_name);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_locked', 'false')")
        conn.commit()

def add_file(file_id, file_unique_id, original_filename, file_size, message_id, channel_id):
    from utils import normalize_name
    name, _ = os.path.splitext(original_filename)
    normalized = normalize_name(name)
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO files (file_id, file_unique_id, normalized_name, original_filename,
                                   file_size, message_id, channel_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_id, file_unique_id, normalized, original_filename, file_size, message_id, channel_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def search_files(query):
    from utils import normalize_name
    normalized_query = f"%{normalize_name(query)}%"
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, normalized_name, original_filename, file_size, file_id
            FROM files
            WHERE normalized_name LIKE ?
            ORDER BY upload_time DESC
        """, (normalized_query,)).fetchall()
    return [dict(row) for row in rows]

def get_file_by_id(file_id):
    with get_db() as conn:
        row = conn.execute("SELECT file_id FROM files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None

def update_user(user_id, first_name, username):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, first_name, username, last_interaction)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                last_interaction = CURRENT_TIMESTAMP
        """, (user_id, first_name, username))
        conn.commit()

def is_bot_locked():
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'bot_locked'").fetchone()
    return row and row[0] == 'true'

# Add other functions as needed (log_to_channel, etc.)
