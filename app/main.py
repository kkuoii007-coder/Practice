"""FastAPI-сервис приёма заявок (лидов).

Endpoint POST /lead принимает JSON, сохраняет заявку в SQLite,
фиксирует событие в events.log.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import db
from app.events import log_lead_saved
from app.logging_config import get_logger, setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Инициализируем БД при запуске."""
    db.init_db()
    logger.info("База данных инициализирована")
    yield


class LeadIn(BaseModel):
    """Схема входной заявки.

    name — необязательное поле (контакт важнее),
    contact — обязательное,
    source, comment — необязательные.
    """

    name: str | None = Field(default=None, description="Имя клиента")
    contact: str = Field(min_length=1, description="Контакт для связи (телефон, email или ник) — обязательное поле")
    source: str | None = Field(default=None, description="Источник заявки (например: landing, instagram, telegram)")
    comment: str | None = Field(default=None, description="Комментарий клиента")


class LeadOut(BaseModel):
    """Ответ при успешном приёме заявки."""

    id: int = Field(description="Идентификатор сохранённой заявки")
    status: str = Field(default="ok", description="Статус операции")
    message: str = Field(default="Заявка принята", description="Человекочитаемое сообщение")


tags_metadata = [
    {
        "name": "Заявки",
        "description": "Операции с заявками (лидами): приём и сохранение в базу данных.",
    },
    {
        "name": "Служебные",
        "description": "Технические эндпоинты для проверки работоспособности сервиса.",
    },
]


app = FastAPI(
    title="Сервис приёма заявок (Lead Webhook MVP)",
    summary="Минимальный сервис приёма лидов: Webhook → SQLite → Event Log.",
    description=(
        "## Назначение\n"
        "Принимает заявку через веб-перехватчик `POST /lead`, сохраняет её в SQLite "
        "и фиксирует событие «заявка принята» в `events.log`.\n\n"
        "## Возможные ответы\n"
        "- **200** — заявка успешно принята и сохранена.\n"
        "- **400** — невалидный JSON или отсутствует обязательное поле `contact`.\n"
        "- **500** — внутренняя ошибка сервера (например, база данных недоступна)."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Преобразуем 422 (валидация по умолчанию) в 400 с понятным описанием."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Невалидные данные заявки", "errors": exc.errors()},
    )


@app.get(
    "/health",
    tags=["Служебные"],
    summary="Проверка работоспособности",
    description="Возвращает статус сервиса. Используется для health-check.",
)
def health() -> dict:
    """Простой health-check."""
    return {"status": "ok"}


@app.post(
    "/lead",
    tags=["Заявки"],
    response_model=LeadOut,
    summary="Принять заявку",
    description=(
        "Принимает заявку в формате JSON, сохраняет её в SQLite "
        "и фиксирует событие в `events.log`.\n\n"
        "Обязательное поле — `contact`. Остальные поля необязательны."
    ),
    responses={
        400: {"description": "Невалидные данные: отсутствует contact или невалидный JSON"},
        500: {"description": "Внутренняя ошибка сервера (база данных недоступна)"},
    },
)
async def create_lead(lead: LeadIn) -> LeadOut:
    """Принимает заявку, сохраняет в SQLite, фиксирует событие."""
    try:
        lead_id, _created_at = db.save_lead(
            name=lead.name,
            contact=lead.contact,
            source=lead.source,
            comment=lead.comment,
        )
    except Exception as exc:
        # БД недоступна или другая ошибка сохранения
        logger.exception("Ошибка при сохранении заявки в БД")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера") from exc

    # Фиксируем событие «заявка принята»
    try:
        log_lead_saved(lead_id)
    except Exception:
        # Ошибка логирования не должна «ронять» уже принятую заявку
        logger.exception("Не удалось записать событие в events.log")

    return LeadOut(id=lead_id)
