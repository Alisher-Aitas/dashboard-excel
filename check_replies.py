import json
import os
import requests
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = "state.json"
OFFSET_FILE = "telegram_offset.json"

ASTANA_OFFSET = timezone(timedelta(hours=5))


def now_astana():
    return datetime.now(timezone.utc).astimezone(ASTANA_OFFSET)


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("offset", 0)
    return 0


def save_offset(offset):
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


def get_updates(offset):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 0}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("ok"):
        return data["result"]
    print("Ошибка получения обновлений:", data)
    return []


def send_message(text, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    requests.post(url, json=payload)


def classify_reply(text):
    text_lower = text.strip().lower()
    done_words = ["выполнено", "готово", "сделано", "✅", "да"]
    not_done_words = ["не выполнено", "не сделано", "❌", "нет"]
    if any(w in text_lower for w in not_done_words):
        return "not_done"
    if any(w in text_lower for w in done_words):
        return "done"
    return None


def advance_stage(item, state, today_str):
    stage_order = state["stage_order"]
    stage_names = state["stage_names"]
    current_index = stage_order.index(item["stage"])
    next_index = current_index + 1

    item["history"].append({
        "stage": item["stage"],
        "completed_on": today_str,
    })

    if next_index >= len(stage_order) - 1:
        item["stage"] = "done"
        send_message(
            f"✅ {item['factory']} — {item['name']}: цикл закупки завершён "
            f"(заказ поставщику оформлен)."
        )
    else:
        item["stage"] = stage_order[next_index]
        item["stage_started"] = today_str
        item["last_reminder_date"] = None
        next_label = stage_names[item["stage"]]
        send_message(
            f"Принято: {item['factory']} — {item['name']} продвинулась дальше по циклу.\n"
            f"Следующий шаг появится по сроку: {next_label}."
        )


def main():
    state = load_state()
    offset = load_offset()
    updates = get_updates(offset)

    if not updates:
        print("Новых обновлений нет.")
        return

    today_str = now_astana().date().isoformat()
    items_by_msg_id = {item.get("last_message_id"): item for item in state["items"] if item.get("last_message_id")}

    max_update_id = offset

    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        message = update.get("message")
        if not message:
            continue

        reply_to = message.get("reply_to_message")
        text = message.get("text", "")
        if not reply_to or not text:
            continue

        replied_msg_id = reply_to.get("message_id")
        item = items_by_msg_id.get(replied_msg_id)
        if not item:
            continue

        result = classify_reply(text)
        if result == "done":
            advance_stage(item, state, today_str)
        elif result == "not_done":
            send_message(
                f"Понял, {item['factory']} — {item['name']} ещё в работе. "
                f"Напомню завтра.",
                reply_to=message["message_id"],
            )
        # last_reminder_date оставляем как есть — завтра напомнит снова, т.к. дата сменится

    save_state(state)
    save_offset(max_update_id + 1)
    print("Обработка ответов завершена.")


if __name__ == "__main__":
    main()
