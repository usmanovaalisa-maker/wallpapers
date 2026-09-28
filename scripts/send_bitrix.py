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
  CARD=1              нарисовать картинку cards/ДАТА.jpg и выйти (шаг до отправки)
  CARD_URL            публичная ссылка на картинку — прикладывается к сообщению в чат
"""
import base64
import datetime as dt
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def todays_text(date):
    data = json.loads((ROOT / "wishes" / "team.json").read_text(encoding="utf-8"))
    daily = data.get("daily", {}).get(date)
    if isinstance(daily, list):
        daily = daily[0] if daily else None
    return daily or data.get("calendar", {}).get(date)


def normalize_webhook(url):
    # Оставляем только https://портал/rest/ID/КОД/ — без примера метода вроде «profile» на конце
    m = re.match(r"(https?://[^/]+/rest/\d+/[^/]+)", url.strip())
    return m.group(1) + "/" if m else url.strip()


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
        hint = ""
        if body["error"] in ("ERROR_METHOD_NOT_FOUND", "insufficient_scope"):
            scope = "Живая лента (log)" if method.startswith("log.") else "Чат и уведомления (im)"
            hint = f"\nПохоже, у вебхука нет права «{scope}»: отметьте его в настройках вебхука в Битрикс24 и сохраните."
        sys.exit(f"Битрикс24 вернул ошибку на {method}: {body.get('error')}: {body.get('error_description')}{hint}")
    return body


def todays_date():
    tz = ZoneInfo(os.environ.get("WISH_TZ") or "Europe/Samara")
    return os.environ.get("WISH_DATE") or dt.datetime.now(tz).date().isoformat()


def image_attach(url):
    return [{"IMAGE": [{"NAME": "Напутствие дня", "LINK": url, "PREVIEW": url, "WIDTH": 1080, "HEIGHT": 1080}]}]


def main():
    date = todays_date()
    text = todays_text(date)
    if not text:
        print(f"{date}: на сегодня напутствия нет — ничего не отправляем.")
        return

    if os.environ.get("CARD") == "1":
        from make_card import make_card
        card = make_card(date, text)
        print(f"Картинка: {card}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"card=cards/{card.name}\n")
        return

    title = "☕ Напутствие дня от «Дари Сейчас»"
    print(f"{date}: {text}")
    webhook = normalize_webhook(os.environ.get("BITRIX_WEBHOOK_URL", ""))
    if os.environ.get("DRY_RUN") == "1":
        return
    if not webhook:
        print("::warning::Не задан секрет BITRIX_WEBHOOK_URL — сообщение не отправлено.")
        return

    card_url = os.environ.get("CARD_URL", "").strip()
    card_file = ROOT / "cards" / f"{date}.jpg"
    dialog = os.environ.get("BITRIX_DIALOG_ID", "").strip()
    if dialog:
        payload = {"MESSAGE": f"[B]{title}[/B]\n\n{text}"}
        if card_url:
            payload["ATTACH"] = image_attach(card_url)
        body = call(webhook, "im.message.add", {"DIALOG_ID": dialog, **payload}, fail=dialog.startswith("chat"))
        if "error" in body:
            # личное сообщение самому себе (вебхук создан этим же пользователем) Битрикс может не принять —
            # тогда присылаем системное уведомление
            print(f"Личное сообщение не отправилось ({body['error']}), отправляю уведомлением.")
            call(webhook, "im.notify.system.add", {"USER_ID": int(dialog), **payload})
    else:
        post = {"POST_TITLE": title, "POST_MESSAGE": text, "DEST": ["UA"]}
        if card_file.exists():
            post["FILES"] = [[card_file.name, base64.b64encode(card_file.read_bytes()).decode()]]
        body = call(webhook, "log.blogpost.add", post, fail="FILES" not in post)
        if "error" in body:
            print(f"Пост с картинкой не принят ({body['error']}), отправляю без вложения.")
            post.pop("FILES")
            if card_url:
                post["POST_MESSAGE"] += f"\n\n[URL={card_url}]Открыть картинку[/URL]"
            call(webhook, "log.blogpost.add", post)
    print("Отправлено.")


if __name__ == "__main__":
    main()
