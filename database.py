import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE
import logging

logger = logging.getLogger(__name__)

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
        # Files table with all metadata
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
                author TEXT,
                category TEXT,
                language TEXT,
                year INTEGER,
                pages INTEGER,
                download_count INTEGER DEFAULT 0,
                preview_file_id TEXT,
                avg_rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_normalized_name ON files(normalized_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_author ON files(author);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON files(category);")

        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP
            )
        """)

        # Settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_locked', 'false')")

        # Feedback table (reviews)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER,
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(book_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)

        # Downloads table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(book_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)

        # User warnings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                warned_by INTEGER,
                reason TEXT,
                warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bookmarks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                user_id INTEGER,
                book_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY(book_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)

        conn.commit()

def add_file(file_id, file_unique_id, original_filename, file_size, message_id, channel_id,
             author=None, category=None, language=None, year=None, pages=None):
    from utils import normalize_name
    name, _ = os.path.splitext(original_filename)
    normalized = normalize_name(name)
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO files (file_id, file_unique_id, normalized_name, original_filename,
                                   file_size, message_id, channel_id, author, category, language, year, pages)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_id, file_unique_id, normalized, original_filename, file_size,
                  message_id, channel_id, author, category, language, year, pages))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def search_files(query):
    from utils import normalize_name
    normalized_query = f"%{normalize_name(query)}%"
    logger.info(f"🔍 search_files: query='{query}', normalized='{normalized_query}'")
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, original_filename, file_size, file_id, download_count,
                   author, category, language, year, pages, avg_rating, review_count
            FROM files
            WHERE normalized_name LIKE ?
            ORDER BY upload_time DESC
        """, (normalized_query,)).fetchall()
        logger.info(f"📊 search_files: found {len(rows)} rows")
        return [dict(row) for row in rows]

def get_file_by_id(file_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None

def get_total_files():
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

def get_total_users():
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def get_db_size():
    return os.path.getsize(DATABASE) if os.path.exists(DATABASE) else 0

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

def get_all_users():
    with get_db() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    return [row[0] for row in rows]

def is_bot_locked():
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'bot_locked'").fetchone()
    return row and row[0] == 'true'

def set_bot_locked(locked: bool):
    with get_db() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'bot_locked'", ('true' if locked else 'false',))
        conn.commit()

def increment_download(book_id, user_id):
    with get_db() as conn:
        conn.execute("UPDATE files SET download_count = download_count + 1 WHERE id = ?", (book_id,))
        conn.execute("INSERT INTO downloads (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        conn.commit()

def get_top_books(limit=10):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, original_filename, file_size, download_count
            FROM files
            ORDER BY download_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in rows]

def get_random_book():
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, original_filename, file_size, file_id
            FROM files
            ORDER BY RANDOM()
            LIMIT 1
        """).fetchone()
    return dict(row) if row else None

def add_feedback(user_id, book_id, rating, comment=None):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO feedback (user_id, book_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, book_id, rating, comment))
        # Update avg_rating
        conn.execute("""
            UPDATE files SET
                avg_rating = (SELECT AVG(rating) FROM feedback WHERE book_id = ?),
                review_count = (SELECT COUNT(*) FROM feedback WHERE book_id = ?)
            WHERE id = ?
        """, (book_id, book_id, book_id))
        conn.commit()

def warn_user(user_id, warned_by, reason):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO user_warnings (user_id, warned_by, reason)
            VALUES (?, ?, ?)
        """, (user_id, warned_by, reason))
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM user_warnings WHERE user_id = ?", (user_id,)).fetchone()[0]
        return count

def is_user_banned(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (f"banned_{user_id}",)).fetchone()
        return row is not None and row['value'] == 'true'

def ban_user(user_id):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                     (f"banned_{user_id}", "true"))
        conn.commit()

def bookmark(user_id, book_id):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO bookmarks (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        conn.commit()

def get_user_bookmarks(user_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT f.id, f.original_filename, f.file_size
            FROM bookmarks b
            JOIN files f ON b.book_id = f.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """, (user_id,)).fetchall()
    return [dict(row) for row in rows]

def vacuum_db():
    with get_db() as conn:
        conn.execute("VACUUM")
    logger.info("✅ Database vacuumed.")

def backup_db(bot, chat_id):
    try:
        with open(DATABASE, 'rb') as f:
            bot.send_document(chat_id=chat_id, document=f, filename='bot_data_backup.db')
        return True
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False
