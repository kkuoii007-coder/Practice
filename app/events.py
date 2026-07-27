"""Фиксация событий «заявка принята» (Вариант A — Event Log в файл).

Формат events.log — Markdown-таблица с полями заявки:
| № | Площадка / чат | Ссылка / скрин | Дата | Текст отклика |

Поля таблицы отражают принятую заявку:
- №           — id заявки в БД;
- Площадка    — source (источник заявки);
- Ссылка      — контакт клиента (телефон/email/ник);
- Дата        — created_at (ISO-время UTC);
- Текст отклика — name + comment.
"""

from app.logging_config import get_logger
from app import db

EVENTS_LOG_PATH = "events.log"

# Заголовок Markdown-таблицы, который пишется в начале файла
_TABLE_HEADER = (
    "| № | Площадка / чат | Ссылка / скрин | Дата | Текст отклика |\n"
    "|---|---------------|---------------|------|---------------|\n"
)


def _ensure_header() -> None:
    """Создаёт файл events.log с заголовком таблицы, если его ещё нет или он пуст."""
    try:
        with open(EVENTS_LOG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    # Если заголовка нет — дописываем его
    if _TABLE_HEADER not in content:
        mode = "w" if not content else "a"
        with open(EVENTS_LOG_PATH, mode, encoding="utf-8") as f:
            if mode == "w" or content and not content.endswith("\n"):
                f.write(_TABLE_HEADER)
            else:
                f.write(_TABLE_HEADER)


def _table_row(lead: tuple) -> str:
    """Формирует строку Markdown-таблицы из данных заявки.

    lead: (id, created_at, name, contact, source, comment)
    """
    lead_id, created_at, name, contact, source, comment = lead
    source = source or ""
    contact = contact or ""
    name = name or ""
    comment = comment or ""
    text = f"{name} {comment}".strip()
    return f"| {lead_id} | {source} | {contact} | {created_at} | {text} |\n"


def log_lead_saved(lead_id: int) -> None:
    """Записывает событие о сохранении новой заявки в events.log и в лог приложения."""
    message = f"New lead saved: {lead_id}"
    # Основной лог приложения (app.log + консоль) — обычный текст
    get_logger().info(message)
    # Отдельный файл событий в формате Markdown-таблицы
    _ensure_header()
    lead = db.get_lead(lead_id)
    if lead is None:
        # Если заявка не найдена в БД — пишем упрощённую строку
        row = f"| {lead_id} | | | | |\n"
    else:
        row = _table_row(lead)
    with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(row)
