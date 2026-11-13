"""Новогодняя рассылка: значения вкладки «Свод по дням» Google Sheets.

Адрес хранится только в NG_SHEETS_URL, не в публичном репозитории.
Данные читаются в памяти; суммы не выводятся в журналы и не записываются в Git.
"""
import csv
import datetime as dt
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class SheetError(ValueError):
    pass


MARKETS = (("wb", "ВБ", 2), ("ozon", "Озон", 3), ("total", "Итого", 1))


def date_value(value):
    for fmt in ("%d.%m.%y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    return None


def number(value, percent=False):
    raw = str(value).strip().replace("−", "-")
    if raw in ("", "—", "–"):
        return None
    raw = re.sub(r"\s", "", raw).replace("₽", "")
    has_percent = raw.endswith("%")
    raw = raw.removesuffix("%").replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", raw):
        raise SheetError("В числовых ячейках есть ошибка или неподдерживаемый формат")
    try:
        result = Decimal(raw)
    except InvalidOperation:
        raise SheetError("Некорректное число") from None
    if has_percent:
        result /= 100
    if percent and not 0 <= result <= 1:
        raise SheetError("Выкуп должен быть от нуля до ста процентов")
    return result


def read_csv():
    source = os.environ.get("NG_SHEETS_URL", "").strip()
    parsed = urllib.parse.urlparse(source)
    match = re.fullmatch(r"/spreadsheets/d/([A-Za-z0-9_-]+)(?:/.*)?", parsed.path)
    if parsed.scheme != "https" or parsed.hostname != "docs.google.com" or not match:
        raise SheetError("Не настроен адрес таблицы NG_SHEETS_URL")
    gid = os.environ.get("NG_SHEETS_GID") or "1887142559"
    if not gid.isdigit():
        raise SheetError("Некорректный номер вкладки")
    base = "https://docs.google.com/spreadsheets/d/" + match[1]
    formatted = fetch(base + "/export?" + urllib.parse.urlencode(
        {"format": "csv", "gid": gid, "range": "A1:P1000"}))
    raw = fetch(base + "/gviz/tq?" + urllib.parse.urlencode(
        {"gid": gid, "headers": "0", "range": "A7:P1000", "tqx": "out:json"}))
    return precise_csv(formatted, raw)


def fetch(url):
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read(2_000_001)
    except urllib.error.HTTPError as error:
        raise SheetError(f"Таблица недоступна (HTTP {error.code})") from None
    except (urllib.error.URLError, OSError):
        raise SheetError("Таблица недоступна: сетевая ошибка") from None
    if len(body) > 2_000_000:
        raise SheetError("Ответ таблицы превышает ожидаемый размер")
    return body.decode("utf-8-sig")


def precise_csv(formatted, raw):
    """Заголовки проверяем в CSV, расчёты ведём по точным значениям ячеек."""
    try:
        body = raw if raw.lstrip().startswith("{") else raw[raw.index("(") + 1:raw.rindex(")")]
        payload = json.loads(body, parse_float=Decimal)
        table = payload["table"]
        if payload["status"] != "ok" or [c["type"] for c in table["cols"]] != ["date"] + ["number"] * 15:
            raise ValueError
        values = {}
        for row in table["rows"]:
            cells = row["c"]
            value = (cells[0] or {}).get("v", "")
            match = re.fullmatch(r"Date\((\d+),(\d+),(\d+)\)", value)
            if not match:
                raise ValueError
            year, month, day = map(int, match.groups())
            date = dt.date(year, month + 1, day)
            if date in values:
                raise ValueError
            values[date] = [str(cell["v"]) if cell and cell.get("v") is not None else "" for cell in cells[1:16]]
        rows = list(csv.reader(io.StringIO(formatted)))
        seen = set()
        for row in rows[6:]:
            date = date_value(row[0]) if row else None
            if date is None:
                continue
            exact = values.get(date)
            if exact is None or len(exact) != 15:
                raise ValueError
            for i, value in enumerate(exact, 1):
                screen = number(row[i], percent=7 <= i <= 9)
                precise = number(value, percent=7 <= i <= 9)
                tolerance = Decimal("0.00051") if 7 <= i <= 9 or 13 <= i <= 15 else Decimal("0.51")
                if (screen is None) != (precise is None) or (screen is not None and abs(screen - precise) > tolerance):
                    raise ValueError
            row[1:16] = exact
            seen.add(date)
        if seen != set(values):
            raise ValueError
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        return output.getvalue()
    except (ValueError, KeyError, IndexError, TypeError):
        raise SheetError("Не удалось сверить точные значения таблицы; чтение будет повторено") from None


def parse(text, today):
    rows = [row + [""] * max(0, 16 - len(row)) for row in csv.reader(io.StringIO(text))]
    if len(rows) < 7 or rows[5][:4] != ["Дата", "Итого", "ВБ", "Озон"]:
        raise SheetError("Не совпала структура вкладки «Свод по дням»")
    expected = {1: "Заказы, ₽", 4: "Продажи, ₽", 7: "Выкуп, %", 13: "Чистая маржа, %"}
    if any(rows[4][column].strip() != name for column, name in expected.items()):
        raise SheetError("Изменились заголовки показателей таблицы")
    profit_labels = {"Прибыль без опер. расх., ₽": "Прибыль без опер. расходов", "Чистая прибыль, ₽": "Чистая прибыль"}
    profit_label = profit_labels.get(rows[4][10].strip())
    if not profit_label:
        raise SheetError("Изменился заголовок прибыли в таблице")
    for column in (4, 7, 10, 13):
        if rows[5][column:column + 3] != ["Итого", "ВБ", "Озон"]:
            raise SheetError("Изменился порядок маркетплейсов в таблице")
    if rows[2][1].strip() != os.environ.get("NG_SHEETS_SEASON", "НГ 2027"):
        raise SheetError("В таблице выбран другой сезон")
    yesterday = today - dt.timedelta(days=1)
    stamp = re.search(r"данные по (\d{2}\.\d{2}\.\d{4})", rows[2][4])
    through = date_value(stamp[1]) if stamp else None
    if not through or through < yesterday:
        raise SheetError("Таблица ещё не обновлена за вчерашний день")
    days = {}
    for row in rows[6:]:
        date = date_value(row[0])
        if date is None or date > yesterday:
            continue
        if date in days:
            raise SheetError("В таблице повторяется дата")
        markets = {}
        for key, label, column in MARKETS:
            values = {"orders_amount": number(row[column]), "sales": number(row[column + 3]),
                      "buyout": number(row[column + 6], percent=True), "profit": number(row[column + 9]),
                      "margin": number(row[column + 12])}
            if any(values[k] is None for k in ("orders_amount", "sales", "profit")):
                raise SheetError("Не заполнены денежные показатели за один из дней")
            markets[key] = values
        # На экране деньги округлены до рублей: сумма округлений может отличаться на один рубль.
        for metric in ("orders_amount", "sales", "profit"):
            difference = markets["total"][metric] - markets["wb"][metric] - markets["ozon"][metric]
            if abs(difference) > 1:
                raise SheetError("Итого не совпадает с суммой ВБ и Озон")
        days[date] = markets
    if yesterday not in days:
        raise SheetError("Нет строки за вчерашний день")
    first = min(days)
    current = days[yesterday]
    previous_date = yesterday - dt.timedelta(days=1)
    previous = days.get(previous_date)
    amount = current["total"]["orders_amount"]
    past = [markets["total"]["orders_amount"] for date, markets in days.items() if date < yesterday]
    complete = all(first + dt.timedelta(days=i) in days for i in range((yesterday - first).days + 1))
    level = "support"
    if amount > 0 and complete and len(past) >= 7 and amount > max(past):
        level = "record"
    elif amount > 0 and previous:
        prev_amount = previous["total"]["orders_amount"]
        level = "up" if amount > prev_amount else ("steady" if amount >= prev_amount * Decimal("0.9") else "support")
    totals = {key: float(sum(day[key]["orders_amount"] for day in days.values())) for key, _, _ in MARKETS}
    return {"source_type": "google_sheet", "source_label": "Google Sheets — «Свод по дням»",
            "sources": ["Google Sheets — «Свод по дням»"], "errors": [], "ready": True, "not_loaded": [],
            "level": level, "start": yesterday.isoformat(), "end": yesterday.isoformat(), "days": 1,
            "orders": None, "revenue": float(amount), "profit": float(current["total"]["profit"]),
            "profit_label": profit_label,
            "prev_revenue": float(previous["total"]["orders_amount"]) if previous else None,
            "prev_start": previous_date.isoformat(),
            "marketplaces": {key: {k: float(v) if v is not None else None for k, v in values.items()}
                             for key, values in current.items()},
            "period_from": first.isoformat(), "period_orders_amount": totals if complete else None,
            "record_best": float(max(past)) if past else None, "record_from": first.isoformat(),
            "record_label": "лучший результат в таблице", "wins": []}


def collect(today, text=None):
    try:
        return parse(read_csv() if text is None else text, today)
    except (SheetError, UnicodeError) as error:
        day = (today - dt.timedelta(days=1)).isoformat()
        return {"source_type": "google_sheet", "source_label": "Google Sheets — «Свод по дням»",
                "sources": ["Google Sheets — «Свод по дням»"], "errors": [str(error)],
                "ready": False, "not_loaded": [day], "level": "support", "start": day, "end": day,
                "days": 1, "orders": None, "revenue": None, "profit": None,
                "marketplaces": {}, "wins": []}


def money(value):
    rounded = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(rounded):,}".replace(",", " ").replace("-", "−") + " ₽"


def percentage(value):
    return "нет данных" if value is None else f"{value * 100:.1f}".replace(".", ",").replace("-", "−") + "%"


def stats_line(result):
    if not result.get("ready"):
        return ""
    day = dt.date.fromisoformat(result["end"]).strftime("%d.%m.%Y")
    profit_label = result.get("profit_label", "Прибыль без опер. расходов").lower()
    lines = [f"Итоги по новогодке за {day}:"]
    for key, label, _ in MARKETS:
        values = result["marketplaces"][key]
        lines += ["", f"[B]{label}[/B]",
                  f"Заказы: {money(values['orders_amount'])}; продажи: {money(values['sales'])}.",
                  f"Выкуп: {percentage(values['buyout'])}; {profit_label}: {money(values['profit'])} (маржинальность: {percentage(values['margin'])})."]
    if result.get("prev_revenue") is not None and result["prev_revenue"] > 0:
        delta = (result["revenue"] / result["prev_revenue"] - 1) * 100
        previous_day = dt.date.fromisoformat(result["prev_start"]).strftime("%d.%m")
        change = f"{delta:+.1f}".replace(".", ",").replace("-", "−")
        lines += ["", f"Сумма заказов к {previous_day}: {change}%."]
    if result.get("period_orders_amount"):
        first = dt.date.fromisoformat(result["period_from"]).strftime("%d.%m.%Y")
        lines += ["", f"Сумма заказов с {first} по {day}:",
                  "; ".join(f"{label}: {money(result['period_orders_amount'][key])}" for key, label, _ in MARKETS) + "."]
    return "\n".join(lines)


def control_text(result):
    lines = ["Источник: Google Sheets, вкладка «Свод по дням», сезон НГ 2027."]
    if not result.get("ready"):
        return "\n".join(lines + ["Отправка отложена: " + "; ".join(result["errors"])])
    lines += ["Показатели взяты из ячеек таблицы; заказы — сумма в рублях.", stats_line(result), "",
              f"Уровень текста: {result['level']} (по общей сумме заказов)."]
    if not result.get("period_orders_amount"):
        lines.append("В истории есть пропуски: накопительная сумма не показана.")
    return "\n".join(lines)
