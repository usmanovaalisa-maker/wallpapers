"""Отправляет напутствие дня сотрудникам в Битрикс24.

Текст берётся из wishes/team.json: daily[дата] (свежий) или calendar[дата].
Если на сегодня текста нет (выходной, праздник) — ничего не отправляет.

Переменные окружения:
  BITRIX_WEBHOOK_URL  входящий вебхук, например https://company.bitrix24.ru/rest/1/abc123/
  BITRIX_DIALOG_ID    куда писать: chat123 (групповой чат) или ID пользователя (личное сообщение,
                      например для проверки — свой ID).
                      Если не задан — пост в Живую ленту для всех сотрудников.
  WISH_TZ             часовой пояс компании (по умолчанию Europe/Samara, GMT+4)
  WISH_DATE           дата ГГГГ-ММ-ДД вместо сегодняшней (для проверки)
  DRY_RUN=1           только показать текст, не отправлять
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent


def todays_text(date):
    data = json.loads((ROOT / "wishes" / "team.json").read_text(encoding="utf-8"))
    daily = data.get("daily", {}).get(date)
    if isinstance(daily, list):
        daily = daily[0] if daily else None
    return daily or data.get("calendar", {}).get(date)


def call(webhook, method, payload, fail=True):
    req = urllib.request.Request(
        webhook.rstrip("/") + f"/{method}.json",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8") or "{}")
        body.setdefault("error", f"HTTP {e.code}")
    if "error" in body and fail:
        sys.exit(f"Битрикс24 вернул ошибку: {body.get('error')}: {body.get('error_description')}")
    return body


def main():
    tz = ZoneInfo(os.environ.get("WISH_TZ") or "Europe/Samara")
    date = os.environ.get("WISH_DATE") or dt.datetime.now(tz).date().isoformat()
    text = todays_text(date)
    if not text:
        print(f"{date}: на сегодня напутствия нет — ничего не отправляем.")
        return

    title = "☕ Напутствие дня от «Дари Сейчас»"
    print(f"{date}: {text}")
    webhook = os.environ.get("BITRIX_WEBHOOK_URL", "").strip()
    if os.environ.get("DRY_RUN") == "1":
        return
    if not webhook:
        print("::warning::Не задан секрет BITRIX_WEBHOOK_URL — сообщение не отправлено.")
        return

    dialog = os.environ.get("BITRIX_DIALOG_ID", "").strip()
    if dialog:
        message = f"[B]{title}[/B]\n\n{text}"
        body = call(webhook, "im.message.add", {"DIALOG_ID": dialog, "MESSAGE": message}, fail=dialog.startswith("chat"))
        if "error" in body:
            # личное сообщение самому себе (вебхук создан этим же пользователем) Битрикс может не принять —
            # тогда присылаем системное уведомление
            print(f"Личное сообщение не отправилось ({body['error']}), отправляю уведомлением.")
            call(webhook, "im.notify.system.add", {"USER_ID": int(dialog), "MESSAGE": message})
    else:
        call(webhook, "log.blogpost.add", {"POST_TITLE": title, "POST_MESSAGE": text, "DEST": ["UA"]})
    print("Отправлено.")


if __name__ == "__main__":
    main()
