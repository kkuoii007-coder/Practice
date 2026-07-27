# Lead Webhook MVP

Минимальный сервис приёма заявок (лидов): **Webhook → SQLite → Event Log**.

Принимает заявку через `POST /lead`, сохраняет в SQLite, фиксирует событие в `events.log`.
Обрабатывает ошибки валидации (HTTP 400) и сбои БД (HTTP 500 + лог).

> Полное объяснение устройства проекта и инструкцию по подключению к клиенту
> см. в [`GUIDE.md`](GUIDE.md).

## Стек

- **Python 3.10+** (проверено на 3.14)
- **FastAPI** — веб-фреймворк
- **SQLite** — встроенная база данных
- **Pydantic** — валидация входных данных
- **pytest** — тесты

## Структура проекта

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI-приложение, endpoint POST /lead
│   ├── db.py             # Работа с SQLite
│   ├── events.py         # Фиксация события «заявка принята»
│   └── logging_config.py # Настройка логирования
├── tests/
│   └── test_lead.py      # 7 тестов (валидация, ошибки, БД)
├── test_payloads.json    # 10 тестовых заявок
├── demo.py               # Демонстрационный скрипт
├── requirements.txt
├── GUIDE.md              # Подробное руководство для неспециалиста
└── README.md
```

## Запуск за 5–10 минут

### 1. Установка

Создать виртуальное окружение и установить зависимости:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Запуск сервера

```powershell
uvicorn app.main:app --reload
```

Сервер поднимется на `http://127.0.0.1:8000`.
Интерактивная документация (Swagger UI, на русском) — на `http://127.0.0.1:8000/docs`.

### 3. Пример запроса к `POST /lead`

**PowerShell** (нативный `Invoke-RestMethod`):

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/lead -Method Post `
  -ContentType "application/json" `
  -Body '{"name":"Ирина","contact":"+79990000000","source":"landing","comment":"Хочу консультацию"}'
```

**Или через curl:**

```powershell
curl -X POST http://127.0.0.1:8000/lead `
  -H "Content-Type: application/json" `
  -d '{\"name\":\"Ирина\",\"contact\":\"+79990000000\",\"source\":\"landing\",\"comment\":\"Хочу консультацию\"}'
```

**Или через Swagger UI:** открыть `http://127.0.0.1:8000/docs` → `POST /lead` → кнопка **Try it out** → **Execute**.

**Успешный ответ (HTTP 200):**

```json
{
  "id": 1,
  "status": "ok",
  "message": "Заявка принята"
}
```

### 4. Где смотреть результаты

После отправки заявки результаты появляются в трёх местах:

#### SQLite (база заявок) — `leads.db`

Файл `leads.db` создаётся автоматически при первом запуске. Это и есть база данных.

**Посмотреть через командную строку:**

```powershell
python -c "import sqlite3; [print(r) for r in sqlite3.connect('leads.db').execute('SELECT id, created_at, name, contact, source, comment FROM leads')]"
```

Пример вывода:
```
(1, '2026-07-24T10:15:30+00:00', 'Ирина', '+79990000000', 'landing', 'Хочу консультацию')
```

**Посмотреть через графическую программу:**

Открыть файл `leads.db` в [DB Browser for SQLite](https://sqlitebrowser.org/) (бесплатная программа).
Вкладка «Обзор данных» → таблица `leads`.

#### Журнал событий — `events.log`

Текстовый файл в корне проекта. Каждая принятая заявка добавляет строку:

```
New lead saved: 1
New lead saved: 2
...
```

Открыть можно в любом текстовом редакторе (Блокнот, VS Code) или вывести в терминал:

```powershell
Get-Content events.log
```

#### Лог приложения — `app.log`

Полный лог сервиса: запуск, ошибки, события. Дублируется в консоль и в файл `app.log`.
Здесь же появляются записи об ошибках (например, если база недоступна — HTTP 500).

```powershell
Get-Content app.log
```

## API

### `POST /lead`

Принимает JSON-заявку и сохраняет её в базу.

**Тело запроса:**

| Поле     | Тип    | Обязательный | Описание                |
|----------|--------|--------------|-------------------------|
| name     | string | нет          | Имя клиента             |
| contact  | string | **да**       | Контакт (телефон/email) |
| source   | string | нет          | Источник заявки         |
| comment  | string | нет          | Комментарий             |

**Пример запроса:**
```json
{
  "name": "Ирина",
  "contact": "+79990000000",
  "source": "landing",
  "comment": "Хочу консультацию по тарифам"
}
```

**Ответы:**

- `200 OK` — заявка принята:
  ```json
  {"id": 1, "status": "ok", "message": "Заявка принята"}
  ```
- `400 Bad Request` — невалидный JSON или отсутствует `contact`:
  ```json
  {"detail": "Невалидные данные заявки", "errors": [...]}
  ```
- `500 Internal Server Error` — ошибка базы данных:
  ```json
  {"detail": "Внутренняя ошибка сервера"}
  ```

### `GET /health`

Health-check. Возвращает `{"status": "ok"}`.

## Надёжность

| Сценарий                          | Поведение                                  |
|-----------------------------------|--------------------------------------------|
| Невалидный JSON                   | HTTP 400 + описание ошибки                 |
| Отсутствует или пустой `contact`  | HTTP 400 + описание ошибки                 |
| База данных недоступна            | HTTP 500 + запись в `app.log`              |
| Ошибка записи в `events.log`      | Заявка остаётся принятой, ошибка логируется |

## Уведомления (Вариант A — Event Log)

Каждая принятая заявка фиксируется в двух местах:

1. **`events.log`** — отдельный файл событий с записью `New lead saved: <id>`
2. **`app.log`** — полный лог приложения (в консоль + файл)

> Про email-уведомления (Вариант B) и другие варианты масштабирования см. `GUIDE.md`.

## Дополнительно

### Демо-скрипт

В отдельном терминале (сервер должен быть запущен):

```powershell
python demo.py
```

Отправляет 5 разных запросов (валидные и ошибочные) и показывает результат с цветной подсветкой и содержимое `events.log`.

### Тестовые payloads

Отправить 10 заявок из `test_payloads.json` одной командой (сервер должен быть запущен):

```powershell
python -c "import json,urllib.request; [urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/lead',data=json.dumps(p).encode('utf-8'),headers={'Content-Type':'application/json'})) for p in json.load(open('test_payloads.json',encoding='utf-8'))]"
```

### Тесты

```powershell
pytest tests/ -v
```

7 тестов покрывают все сценарии: успешное сохранение, ошибки валидации (400), недоступность БД (500), health-check.
#   @0:B8:0 
 