import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "posts.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            date TEXT PRIMARY KEY,
            content TEXT,
            generated_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_post(date: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO posts (date, content, generated_at)
        VALUES (?, ?, ?)
    ''', (date, content, datetime.now()))
    conn.commit()
    conn.close()

def get_post(date: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT content FROM posts WHERE date = ?', (date,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None