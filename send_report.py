import openpyxl
import requests
import os
from datetime import datetime

# Настройки из переменных окружения GitHub Secrets
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
EXCEL_FILE = "Дашборд_Ексл.xlsx"

def excel_date_to_str(value):
    """Конвертирует числовую дату Excel или строку в читаемый формат."""
    if isinstance(value, (int, float)):
        try:
            from datetime import date
            delta = datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(value))
            return delta.strftime("%d.%m.%Y")
        except:
            return str(value)
    elif isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    elif value is None:
        return "—"
    return str(value)

def read_tasks():
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    tasks = []
    for row in rows[1:]:  # пропускаем заголовок
        if not any(row):  # пропускаем пустые строки
            continue
        date_exec, task, date_due, status, comment = (list(row) + [None]*5)[:5]
        tasks.append({
            "date_exec": excel_date_to_str(date_exec),
            "task": task or "—",
            "date_due": excel_date_to_str(date_due),
            "status": status or "—",
            "comment": comment or "—",
        })
    return tasks

def build_message(tasks):
    today = datetime.now().strftime("%d.%m.%Y")
    lines = [
        f"☀️ *Доброе утро, Алишер!*",
        f"📅 Сегодня: {today}",
        f"",
        f"📋 *Твои задачи на сегодня:*",
        f"",
    ]

    if not tasks:
        lines.append("✅ Задач нет. Хорошего дня!")
    else:
        for i, t in enumerate(tasks, 1):
            status_icon = "✅" if t["status"].lower() in ["закрыт", "выполнено", "готово"] else "🔴"
            lines.append(f"{status_icon} *{i}. {t['task']}*")
            lines.append(f"   📆 Срок: {t['date_due']}")
            lines.append(f"   📌 Статус: {t['status']}")
            if t["comment"] and t["comment"] != "—":
                lines.append(f"   💬 {t['comment']}")
            lines.append("")

    return "\n".join(lines)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print(f"Статус отправки: {response.status_code}")
    print(response.json())

if __name__ == "__main__":
    tasks = read_tasks()
    message = build_message(tasks)
    send_telegram(message)
