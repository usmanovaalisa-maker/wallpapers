"""Отправляет напутствие дня сотрудникам в Битрикс24.

Текст берётся из wishes/team.json: daily[дата] (свежий) или calendar[дата].
daily[дата] может быть объектом с вариантами под итоги прошедшего дня
({"record", "up", "steady", "support"}) — вариант выбирается по scripts/day_results.py,
а строка с цифрами добавляется только в сообщение (не в картинку и не в лог:
репозиторий публичный). Если на сегодня текста нет (выходной, праздник) — ничего не отправляет.

Переменные окружения:
  BITRIX_WEBHOOK_URL  входящий вебхук, например https://company.bitrix24.ru/rest/1/abc123/
  BITRIX_CHAT_NAME    название группового чата (например «Доброплан 2026 _ Чат руководителей») — скрипт сам найдёт его ID;
                      важнее BITRIX_DIALOG_ID. Владелец вебхука должен состоять в этом чате.
  SEND_TO_ME=1        тестовая отправка в BITRIX_DIALOG_ID, чат по названию не ищется
  BITRIX_DIALOG_ID    куда писать: chat123 (групповой чат) или ID пользователя (личное сообщение,
                      например для проверки — свой ID).
                      Если не задан — пост в Живую ленту для всех сотрудников.
  WISH_TZ             часовой пояс компании (по умолчанию Europe/Samara, GMT+4)
  WISH_DATE           дата ГГГГ-ММ-ДД вместо сегодняшней (для проверки)
  DRY_RUN=1           только показать текст, не отправлять
  CARD=1              нарисовать картинку cards/ДАТА.jpg и выйти (шаг до отправки)
  CARD_URL            публичная ссылка на картинку — прикладывается к сообщению в чат
  WISHES_FILE, CARD_TEMPLATE, CARD_PREFIX, MESSAGE_TITLE — для отдельной рассылки (например, новогодней):
                      файл текстов, шаблон картинки, префикс имени картинки и заголовок сообщения
  TRUE_STATS, TRUESTATS_ACCOUNTS, TRUESTATS_GROUP — итоги дня только из TrueStats
                      (см. scripts/day_results.py); без них напутствие уходит без цифр
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


def team_data():
    # WISHES_FILE — файл с текстами рассылки (по умолчанию напутствие команде wishes/team.json)
    return json.loads((ROOT / (os.environ.get("WISHES_FILE") or "wishes/team.json")).read_text(encoding="utf-8"))


def work_calendar():
    """Рабочие дни всегда по календарю напутствия команде (wishes/team.json)."""
    return json.loads((ROOT / "wishes" / "team.json").read_text(encoding="utf-8")).get("calendar", {})


def todays_text(date, level="support", data=None):
    data = data or team_data()
    daily = data.get("daily", {}).get(date)
    if isinstance(daily, list):
        daily = daily[0] if daily else None
    if isinstance(daily, dict):
        daily = next((daily[k] for k in (level, "support", "steady", "up") if daily.get(k)), None)
    if daily or data.get("calendar", {}).get(date):
        return daily or data["calendar"][date]
    # запасные тексты рассылки без календаря (например, новогодней) — только в рабочие дни
    options = (data.get("fallback") or {}).get(level) or (data.get("fallback") or {}).get("support") or []
    if options and date in work_calendar():
        return options[dt.date.fromisoformat(date).toordinal() % len(options)]
    return None


def results_reaction(date, level, data):
    """Поддерживающая фраза с пожеланием после цифр: свежая из daily[дата]["reaction_<уровень>"],
    а если её нет — из запасного набора results_reactions, каждый день следующая по кругу."""
    daily = data.get("daily", {}).get(date)
    if isinstance(daily, dict) and daily.get(f"reaction_{level}"):
        return daily[f"reaction_{level}"]
    options = data.get("results_reactions", {}).get(level) or []
    return options[dt.date.fromisoformat(date).toordinal() % len(options)] if options else ""


def day_results(date, data):
    """Итоги прошедшего дня: считаем один раз за запуск (у WB лимит — 1 запрос в минуту)
    и держим во временной папке раннера, вне репозитория."""
    import day_results as dr
    cache = pathlib.Path(os.environ.get("RUNNER_TEMP") or "/tmp") / f"day_results_{os.environ.get('CARD_PREFIX', '')}{date}.json"
    if cache.exists():
        r = json.loads(cache.read_text(encoding="utf-8"))
    else:
        r = dr.collect(dt.date.fromisoformat(date), work_calendar())
        cache.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        print(f"Итоги {r['start']}…{r['end']}: уровень {r['level']}, источники: {', '.join(r['sources']) or 'нет'}"
              + (f", ошибки: {'; '.join(r['errors'])}" if r["errors"] else ""))
    return r, dr.stats_line(r)


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


def find_chat(webhook, name):
    """ID группового чата по названию (без учёта регистра и лишних пробелов) → "chat123" или None."""
    norm = lambda t: " ".join(str(t or "").lower().replace("ё", "е").split())
    want = norm(name)
    candidates = []
    for method, payload in (("im.search.chat.list", {"FIND": name}), ("im.search.chat.list", {"FIND": name.split()[0]}),
                            ("im.recent.list", {"SKIP_OPENLINES": "Y"}), ("im.recent.get", {})):
        body = call(webhook, method, payload, fail=False)
        if "error" in body:
            print(f"  {method}: {body.get('error')} {body.get('error_description', '')}")
            continue
        res = body.get("result") or []
        items = res.get("items", []) if isinstance(res, dict) else res
        for i in items:
            c = i.get("chat") if isinstance(i.get("chat"), dict) else i
            title = c.get("name") or c.get("title") or i.get("title")
            cid = c.get("id") or (str(i.get("id", "")).removeprefix("chat") if str(i.get("id", "")).startswith("chat") else None)
            if title and cid:
                candidates.append((title, cid))
                if norm(title) == want:
                    return f"chat{cid}"
    similar = sorted({t for t, _ in candidates if norm(name.split()[0])[:5] in norm(t)})
    print(f"  чатов в выдаче: {len(candidates)}; похожие названия: {similar or 'нет'}")
    return None


def todays_date():
    tz = ZoneInfo(os.environ.get("WISH_TZ") or "Europe/Samara")
    return os.environ.get("WISH_DATE") or dt.datetime.now(tz).date().isoformat()


def image_attach(url):
    return [{"IMAGE": [{"NAME": "Напутствие дня", "LINK": url, "PREVIEW": url, "WIDTH": 1080, "HEIGHT": 1080}]}]


def main():
    date = todays_date()
    data = team_data()
    if not todays_text(date, data=data):
        print(f"{date}: на сегодня напутствия нет — ничего не отправляем.")
        return
    results, stats = day_results(date, data)
    text = todays_text(date, results["level"], data)
    # пожелание идёт в сообщение (после цифр) и одно — на картинку; без итогов на картинке основной текст
    reaction = results_reaction(date, results["level"], data) if stats else ""

    if os.environ.get("CARD") == "1":
        from make_card import make_card
        card = make_card(date, reaction or text, os.environ.get("CARD_TEMPLATE") or "template.html",
                         os.environ.get("CARD_PREFIX", ""))
        print(f"Картинка: {card}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"card=cards/{card.name}\n")
        return

    title = os.environ.get("MESSAGE_TITLE") or "☕ Напутствие дня от «Дари Сейчас»"
    print(f"{date}: {text}" + ("\n(+ строка с итогами дня — в лог не выводится)" if stats else ""))
    if stats:
        text = f"{text}\n\n{stats}"
        if reaction:
            text += f"\n\n{reaction}"
    webhook = normalize_webhook(os.environ.get("BITRIX_WEBHOOK_URL", ""))
    if not webhook:
        print("::warning::Не задан секрет BITRIX_WEBHOOK_URL — сообщение не отправлено.")
        return
    dialog = os.environ.get("BITRIX_DIALOG_ID", "").strip()
    chat_name = os.environ.get("BITRIX_CHAT_NAME", "").strip()
    if os.environ.get("SEND_TO_ME") == "1":
        if not dialog:
            sys.exit("Тест «мне»: не задан BITRIX_DIALOG_ID — не отправляю, чтобы сообщение не ушло в общий чат.")
        print(f"Тест: отправляю в {dialog}, а не в чат «{chat_name}».")
        chat_name = ""
    if chat_name:
        chat = find_chat(webhook, chat_name)
        if chat:
            print(f"Чат «{chat_name}»: {chat}")
            dialog = chat
        else:
            print(f"::warning::Чат «{chat_name}» не найден (владелец вебхука в нём состоит?) — пишу в {dialog or 'Живую ленту'}.")
    if os.environ.get("DRY_RUN") == "1":
        return

    card_url = os.environ.get("CARD_URL", "").strip()
    card_file = ROOT / "cards" / f"{os.environ.get('CARD_PREFIX', '')}{date}.jpg"
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
