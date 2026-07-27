"""Работа с SQLite: инициализация схемы и сохранение заявок."""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

DB_PATH = "leads.db"


def init_db() -> None:
    """Создаёт таблицу leads, если её ещё нет."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                contact TEXT NOT NULL,
                source TEXT,
                comment TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Контекстный менеджер соединения с SQLite.

    Используется check_same_thread=False, т.к. FastAPI может обращаться
    к БД из разных потоков (uvicorn). Для MVP этого достаточно.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def save_lead(name: str | None, contact: str, source: str | None, comment: str | None) -> tuple[int, str]:
    """Сохраняет заявку и возвращает кортеж (id, created_at)."""
    from datetime import datetime, timezone

    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO leads (created_at, name, contact, source, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (created_at, name, contact, source, comment),
        )
        conn.commit()
        return int(cursor.lastrowid), created_at


def get_lead(lead_id: int) -> tuple | None:
    """Возвращает строку заявки по id: (id, created_at, name, contact, source, comment)."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, created_at, name, contact, source, comment FROM leads WHERE id = ?",
            (lead_id,),
        )
        return cursor.fetchone()
