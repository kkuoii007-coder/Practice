"""Демонстрационный скрипт: отправляет 30 заявок к POST /lead и показывает результат.

После отправки выводит:
- содержимое базы данных leads.db (таблица leads);
- содержимое журнала событий events.log (Markdown-таблица).
"""

import io
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Принудительно переводим stdout в UTF-8, чтобы кириллица и псевдографика
# корректно отображались в консоли Windows (cp1251 по умолчанию).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:  # Python < 3.7 fallback
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8000"

# Палитра для цветного вывода в терминале (ANSI-коды)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# 30 тестовых заявок — валидные, чтобы каждая сохранилась в БД
LEADS = [
    {"name": "Ирина", "contact": "+79990000001", "source": "landing", "comment": "Хочу консультацию по тарифам"},
    {"name": "Алексей", "contact": "alex@example.com", "source": "instagram", "comment": "Интересует курс по Python"},
    {"name": "Мария", "contact": "+79991234567", "source": "telegram", "comment": "Перезвоните пожалуйста"},
    {"name": "Олег", "contact": "+78001112233", "source": "referral", "comment": "Пришёл по рекомендации"},
    {"name": "Елена", "contact": "helen@yandex.ru", "source": "landing", "comment": "Нужен счёт на оплату"},
    {"name": "Дмитрий", "contact": "@dmitry_tg", "source": "telegram", "comment": "Удобно общаться здесь"},
    {"name": "Светлана", "contact": "+79995554433", "source": "facebook", "comment": "Вопрос по возврату"},
    {"name": "Павел", "contact": "pavel@gmail.com", "source": "google_ads", "comment": "Запись на консультацию"},
    {"name": "Анна", "contact": "+79990001122", "source": "landing", "comment": "Оптовая поставка"},
    {"name": "Сергей", "contact": "sergey@mail.ru", "source": "vk", "comment": "Прайс-лист"},
    {"name": "Наталья", "contact": "+79998887766", "source": "instagram", "comment": "Хочу записаться"},
    {"name": "Игорь", "contact": "igor@list.ru", "source": "referral", "comment": "Повторный заказ"},
    {"name": "Виктор", "contact": "+79997776655", "source": "telegram", "comment": "Уточнить детали"},
    {"name": "Ольга", "contact": "olga@yandex.ru", "source": "landing", "comment": "Консультация по продукту"},
    {"name": "Роман", "contact": "@roman_bot", "source": "telegram", "comment": "Перезвоните после 18:00"},
    {"name": "Екатерина", "contact": "+79996665544", "source": "facebook", "comment": "Вопрос по доставке"},
    {"name": "Андрей", "contact": "andrey@gmail.com", "source": "google_ads", "comment": "Хочу demo"},
    {"name": "Татьяна", "contact": "+79995554477", "source": "landing", "comment": "Подбор тарифа"},
    {"name": "Максим", "contact": "maxim@mail.ru", "source": "vk", "comment": "Сотрудничество"},
    {"name": "Юлия", "contact": "+79994443322", "source": "instagram", "comment": "Промокод"},
    {"name": "Артём", "contact": "artem@list.ru", "source": "referral", "comment": "Рекомендация друга"},
    {"name": "Вера", "contact": "+79993332211", "source": "telegram", "comment": "Поменять время звонка"},
    {"name": "Глеб", "contact": "gleb@yandex.ru", "source": "landing", "comment": "Технический вопрос"},
    {"name": "Дарья", "contact": "+79992221100", "source": "facebook", "comment": "Возврат товара"},
    {"name": "Захар", "contact": "zahar@gmail.com", "source": "google_ads", "comment": "Условия акции"},
    {"name": "Кирилл", "contact": "+79991110099", "source": "landing", "comment": "Хочу оформить заказ"},
    {"name": "Лариса", "contact": "larisa@mail.ru", "source": "vk", "comment": "Прайс на услуги"},
    {"name": "Михаил", "contact": "+79990009988", "source": "instagram", "comment": "Запись на завтра"},
    {"name": "Надежда", "contact": "nadezhda@list.ru", "source": "referral", "comment": "По совету коллеги"},
    {"name": "Пётр", "contact": "+79998880077", "source": "telegram", "comment": "Уточнить стоимость"},
]


def send(payload) -> tuple:
    """Отправляет POST /lead и возвращает (status_code, body_dict)."""
    url = f"{BASE}/lead"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def status_label(code: int) -> str:
    """Цветная метка HTTP-статуса."""
    if code == 200:
        return f"{GREEN}HTTP {code} OK{RESET}"
    if code == 400:
        return f"{YELLOW}HTTP {code} Bad Request{RESET}"
    if code == 500:
        return f"{RED}HTTP {code} Internal Server Error{RESET}"
    return f"HTTP {code}"


def print_section(title: str) -> None:
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")


def main():
    print_section("ДЕМО: Сервис приёма заявок (POST /lead) — 30 заявок")

    # Отправляем 30 заявок
    success = 0
    failed = 0
    for i, payload in enumerate(LEADS, start=1):
        code, body = send(payload)
        if code == 200:
            success += 1
            print(f"  {GREEN}●{RESET} [{i:>2}/30] {payload['name']:<10} → "
                  f"id={body.get('id')}, {status_label(code)}")
        else:
            failed += 1
            print(f"  {RED}●{RESET} [{i:>2}/30] {payload.get('name', '—'):<10} → "
                  f"{status_label(code)}: {body}")

    print(f"\n{BOLD}Итого:{RESET} {GREEN}принято {success}{RESET}, "
          f"{RED}отклонено {failed}{RESET}")

    # Показываем содержимое базы данных leads.db
    print_section("БАЗА ДАННЫХ (leads.db, таблица leads)")
    db_path = Path("leads.db")
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute(
                    "SELECT id, created_at, name, contact, source, comment FROM leads ORDER BY id"
                ).fetchall()
            print(f"{DIM}Всего записей в БД: {len(rows)}{RESET}\n")
            # Заголовок таблицы
            print(f"{BOLD}{'ID':<4} {'Дата (UTC)':<28} {'Имя':<12} {'Контакт':<22} {'Источник':<12} Комментарий{RESET}")
            print("-" * 110)
            for row in rows:
                lead_id, created_at, name, contact, source, comment = row
                print(f"{lead_id:<4} {created_at:<28} {(name or ''):<12} {(contact or ''):<22} "
                      f"{(source or ''):<12} {comment or ''}")
        except sqlite3.Error as e:
            print(f"{RED}Ошибка чтения БД: {e}{RESET}")
    else:
        print(f"{YELLOW}Файл leads.db не найден{RESET}")

    # Показываем журнал событий events.log
    print_section("ЖУРНАЛ СОБЫТИЙ (events.log)")
    events = Path("events.log")
    if events.exists():
        content = events.read_text(encoding="utf-8")
        lines = content.splitlines()
        print(f"{DIM}Всего строк: {len(lines)}{RESET}\n")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"{YELLOW}Файл events.log не найден{RESET}")

    print()


if __name__ == "__main__":
    main()

