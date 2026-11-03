"""Рисует картинку с напутствием дня: cards/ГГГГ-ММ-ДД.jpg (1080×1080).

Использование: python scripts/make_card.py ГГГГ-ММ-ДД "текст"
Нужен пакет playwright и Chrome/Chromium (на GitHub Actions используется установленный Chrome;
CHROME_PATH — путь к другому браузеру).
"""
import datetime as dt
import os
import pathlib
import json
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def date_label(date):
    d = dt.date.fromisoformat(date)
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"


def make_card(date, text, template="template.html", prefix="", occasion=None, output=None):
    """occasion — {"title": "День доброты", "icon": "heart"} для наклейки «Сегодня» (есть в новогоднем шаблоне)."""
    out = pathlib.Path(output) if output else ROOT / "cards" / f"{prefix}{date}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    seed = dt.date.fromisoformat(date).toordinal() % 233280
    args = [text, date_label(date), seed, occasion]
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        node = os.environ.get("CARD_NODE_RUNTIME")
        if not node:
            raise RuntimeError("Нужен Python playwright или CARD_NODE_RUNTIME с Node Playwright")
        subprocess.run([node, str(ROOT / "scripts/card/render.cjs")],
                       input=json.dumps({"template": str(ROOT / "scripts/card" / template),
                                         "output": str(out), "args": args}), text=True, check=True)
        return out
    with sync_playwright() as p:
        path = os.environ.get("CHROME_PATH")
        browser = p.chromium.launch(executable_path=path) if path else p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.goto((ROOT / "scripts" / "card" / template).as_uri())
        page.evaluate("document.fonts.ready")
        page.evaluate("([t, d, s, o]) => fill(t, d, s, o)", args)
        page.wait_for_timeout(200)
        page.screenshot(path=str(out), type="jpeg", quality=90)
        browser.close()
    return out


if __name__ == "__main__":
    print(make_card(sys.argv[1], sys.argv[2]))
