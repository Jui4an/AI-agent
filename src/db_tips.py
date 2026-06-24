# src/db_tips.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Путь к базе данных советов
DB_PATH = Path(__file__).parent.parent / "data" / "tips.db"

def init_tips_db():
    """Создаёт таблицу tips, если её нет."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_line TEXT NOT NULL,
            advice TEXT NOT NULL,
            dialog_summary TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_tip(gate_line: str, advice: str, dialog_summary: str = "", date: str = None) -> int:
    """Сохраняет совет в БД и возвращает его ID."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tips (gate_line, advice, dialog_summary, date) VALUES (?, ?, ?, ?)",
        (gate_line, advice, dialog_summary, date)
    )
    tip_id = c.lastrowid
    conn.commit()
    conn.close()
    return tip_id

def get_tips(gate_line: str = None, date: str = None) -> List[Dict]:
    """Возвращает список советов по фильтрам."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM tips WHERE 1=1"
    params = []
    if gate_line:
        query += " AND gate_line = ?"
        params.append(gate_line)
    if date:
        query += " AND date = ?"
        params.append(date)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Инициализация БД при импорте модуля
init_tips_db()