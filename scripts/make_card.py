"""Рисует картинку с напутствием дня: cards/ГГГГ-ММ-ДД.jpg (1080×1080).

Использование: python scripts/make_card.py ГГГГ-ММ-ДД "текст" ["пожелание"]
Нужен пакет playwright и Chrome/Chromium (на GitHub Actions используется установленный Chrome;
CHROME_PATH — путь к другому браузеру).
"""
import datetime as dt
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def date_label(date):
    d = dt.date.fromisoformat(date)
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"


def make_card(date, text, wish=""):
    out = ROOT / "cards" / f"{date}.jpg"
    out.parent.mkdir(exist_ok=True)
    with sync_playwright() as p:
        path = os.environ.get("CHROME_PATH")
        browser = p.chromium.launch(executable_path=path) if path else p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.goto((ROOT / "scripts" / "card" / "template.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.evaluate("([t, d, w]) => fill(t, d, w)", [text, date_label(date), wish])
        page.wait_for_timeout(200)
        page.screenshot(path=str(out), type="jpeg", quality=90)
        browser.close()
    return out


if __name__ == "__main__":
    print(make_card(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""))
