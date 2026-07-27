"""Тесты для эндпоинта POST /lead.

Проверяют:
- успешное сохранение заявки
- ошибку 400 при отсутствии contact
- ошибку 400 при невалидном JSON
- ошибку 500 при недоступности БД
- наличие записи в events.log
"""

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Каждый тест работает с временной БД и events.log."""
    db_path = tmp_path / "test_leads.db"
    events_path = tmp_path / "events.log"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    # Подменяем путь к events.log
    import app.events as events
    monkeypatch.setattr(events, "EVENTS_LOG_PATH", str(events_path))
    # Пересоздаём схему во временной БД
    db.init_db()
    yield db_path, events_path


def test_lead_saved_successfully(isolated_db):
    """Валидная заявка сохраняется, возвращается id, в events.log есть запись."""
    db_path, events_path = isolated_db
    payload = {
        "name": "Ирина",
        "contact": "+79990000000",
        "source": "landing",
        "comment": "Хочу консультацию по тарифам",
    }
    response = client.post("/lead", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    lead_id = body["id"]
    assert isinstance(lead_id, int) and lead_id > 0

    # Проверяем запись в БД
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT name, contact, source, comment FROM leads WHERE id = ?",
            (lead_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "Ирина"
    assert row[1] == "+79990000000"
    assert row[2] == "landing"
    assert row[3] == "Хочу консультацию по тарифам"

    # Проверяем запись в events.log (формат Markdown-таблицы)
    events_content = Path(events_path).read_text(encoding="utf-8")
    # Должен быть заголовок таблицы
    assert "| № | Площадка / чат |" in events_content
    # Должна быть строка с id заявки
    assert f"| {lead_id} |" in events_content


def test_lead_missing_contact_returns_400(isolated_db):
    """Отсутствие обязательного поля contact → HTTP 400."""
    payload = {"name": "Иван", "source": "instagram"}
    response = client.post("/lead", json=payload)
    assert response.status_code == 400


def test_lead_empty_contact_returns_400(isolated_db):
    """Пустой contact → HTTP 400."""
    payload = {"contact": ""}
    response = client.post("/lead", json=payload)
    assert response.status_code == 400


def test_lead_invalid_json_returns_400(isolated_db):
    """Невалидный JSON → HTTP 400."""
    response = client.post(
        "/lead",
        data="not a json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_lead_minimal_payload_ok(isolated_db):
    """Минимально допустимый payload — только contact."""
    response = client.post("/lead", json={"contact": "user@example.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_lead_db_unavailable_returns_500(isolated_db, monkeypatch):
    """Если БД недоступна при сохранении — HTTP 500."""
    def raise_error(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "save_lead", raise_error)
    payload = {"contact": "+79991112233"}
    response = client.post("/lead", json=payload)
    assert response.status_code == 500

def test_health_endpoint():
    """Health-check работает."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
