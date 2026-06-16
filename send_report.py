импорт json
импорт os
импорт запросов
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = "state.json"

ASTANA_OFFSET = timezone(timedelta(hours=5))
TARGET_HOUR = 8
TARGET_MINUTE = 30
WINDOW_MINUTES = 20


def now_astana():
    return datetime.now(timezone.utc).astimezone(ASTANA_OFFSET)


def in_send_window(dt):
    if dt.weekday() >= 5: # 5=суббота, 6=воскресенье
        вернуть False
    target = dt.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    delta = abs((dt - target).total_seconds()) / 60
    return delta <= WINDOW_MINUTES


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_message(text, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    если reply_to:
        payload["reply_to_message_id"] = reply_to
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get("ok"):
        return data["result"]["message_id"]
    print("Ошибка отправки:", data)
    вернуть None


def already_sent_today(item, today_str):
    return item.get("last_reminder_date") == today_str


def is_due(item, today):
    этап = элемент["этап"]
    если этап == "выполнено":
        вернуть False

    stage_started = item.get("stage_started")
    если stage_started равно None:
        вернуть True

    started_date = datetime.strptime(stage_started, "%Y-%m-%d").date()
    days_passed = (today - started_date).days
    wait = item.get("_wait_for_this_stage", 0)
    return days_passed >= wait


def main():
    dt = now_astana()
    if not in_send_window(dt):
        print(f"Сейчас {dt.strftime('%Y-%m-%d %H:%M')} по Астане — не входит в окно сообщения. Выход.")
        возвращаться

    состояние = load_state()
    сегодня = dt.date()
    today_str = today.isoformat()
    stage_names = state["stage_names"]
    wait_days = state["wait_days_after_stage"]
    stage_order = state["stage_order"]

    due_items = []

    for item in state["items"]:
        если item["stage"] == "done":
            продолжать
        if already_sent_today(item, today_str):
            продолжать

        prev_stage_index = stage_order.index(item["stage"]) - 1
        prev_stage = stage_order[prev_stage_index] if prev_stage_index >= 0 else None
        wait = wait_days.get(prev_stage, 0) if prev_stage else 0
        item["_wait_for_this_stage"] = wait

        if is_due(item, today):
            due_items.append(item)

    if not due_items:
        print("Нет задач для отправки сегодня.")
        return

    count = len(due_items)
    intro_text = (
        f"Доброе утро, Алишер! ☀️\n"
        f"Сегодня {today.strftime('%d.%m.%Y')}, у тебя {count} "
        f"{'задача' if count == 1 else 'задачи' if count < 5 else 'задач'} по закупу гофротары."
    )
    send_message(intro_text)

    for item in due_items:
        stage_label = stage_names[item["stage"]]
        text = (
            f"📦 {item['factory']} — {item['name']}\n"
            f"Задача: {stage_label}\n"
            f"Поставщик: {item['supplier']}\n\n"
            f"Ответь на это сообщение (Reply) словом «выполнено» или «не выполнено»."
        )
        msg_id = send_message(text)
        item["last_message_id"] = msg_id
        item["last_reminder_date"] = today_str

    save_state(state)
    print(f"Отправлено задач: {count}")


if __name__ == "__main__":
    main()
