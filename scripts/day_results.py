"""Итоги прошедшего дня для напутствия команде: Wildberries, Ozon и Google-таблица.

Репозиторий публичный, поэтому цифры никуда не сохраняются и не печатаются в лог —
они попадают только в сообщение в Битрикс24.

Переменные окружения (любой источник можно не задавать):
  WB_API_TOKEN          токен API Wildberries (категория «Статистика», только чтение)
  OZON_CLIENT_ID        Client-Id продавца Ozon
  OZON_API_KEY          API-ключ Ozon (роль с доступом к аналитике)
  RESULTS_SHEET_CSV_URL ссылка на Google-таблицу, опубликованную как CSV.
                        Колонки: Дата | Заказы | Выручка | Прибыль | Победа дня (любые, кроме даты,
                        можно не заполнять). Прибыль берётся только отсюда — например, из TrueStats

Период — с прошлого рабочего дня по calendar до вчера включительно
(в понедельник это пятница–воскресенье). Уровень:
  record  — лучший результат по заказам за последние 30 дней
  up      — больше, чем за такой же период перед ним
  steady  — примерно так же (спад не больше 10%)
  support — спад больше 10% или данных нет: напутствие без цифр
"""
import csv
import datetime as dt
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

HISTORY_DAYS = 30


def _get(url, headers=None, data=None, retry=True):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8-sig")
    except urllib.error.HTTPError as e:
        if e.code == 429 and retry:  # лимит запросов у WB и Ozon — ждём минуту и пробуем ещё раз
            time.sleep(61)
            return _get(url, headers, data, retry=False)
        raise


def _num(s):
    s = re.sub(r"[^\d,.\-]", "", str(s or "")).replace(",", ".")
    try:
        return float(s) if s not in ("", ".", "-") else 0.0
    except ValueError:
        return 0.0


def _date(s):
    s = str(s or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def wildberries(start, end):
    token = os.environ.get("WB_API_TOKEN", "").strip()
    if not token:
        return None
    # flag=0 — все заказы, изменённые с dateFrom; группируем по дате заказа
    rows = json.loads(_get(
        f"https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom={start}&flag=0",
        {"Authorization": token},
    ))
    days = {}
    for r in rows:
        d = _date(r.get("date"))
        if d and start <= d <= end:
            o, v = days.get(d, (0, 0.0))
            days[d] = (o + 1, v + _num(r.get("priceWithDisc")))
    return days


def ozon(start, end):
    cid, key = os.environ.get("OZON_CLIENT_ID", "").strip(), os.environ.get("OZON_API_KEY", "").strip()
    if not (cid and key):
        return None
    body = {"date_from": start.isoformat(), "date_to": end.isoformat(),
            "metrics": ["ordered_units", "revenue"], "dimension": ["day"], "limit": 1000, "offset": 0}
    res = json.loads(_get("https://api-seller.ozon.ru/v1/analytics/data",
                          {"Client-Id": cid, "Api-Key": key, "Content-Type": "application/json"},
                          json.dumps(body).encode()))
    days = {}
    for r in res.get("result", {}).get("data", []):
        d = _date(r["dimensions"][0]["id"])
        if d:
            days[d] = (int(r["metrics"][0]), float(r["metrics"][1]))
    return days


def sheet(start, end):
    url = os.environ.get("RESULTS_SHEET_CSV_URL", "").strip()
    if not url:
        return None, {}, {}
    rows = list(csv.reader(io.StringIO(_get(url))))
    if not rows:
        return {}, {}, {}
    head = [h.strip().lower() for h in rows[0]]
    col = lambda *names: next((i for i, h in enumerate(head) if any(n in h for n in names)), None)
    ci, co, cv, cw = col("дата"), col("заказ"), col("выручк", "сумм"), col("побед", "комментар")
    cp = col("прибыл")
    days, wins, profit = {}, {}, {}
    for r in rows[1:]:
        d = _date(r[ci]) if ci is not None and ci < len(r) else None
        if not d or not (start <= d <= end):
            continue
        cell = lambda i: r[i] if i is not None and i < len(r) else ""
        o, v = days.get(d, (0, 0.0))
        days[d] = (o + int(_num(cell(co))), v + _num(cell(cv)))
        if cp is not None and cell(cp).strip():
            profit[d] = profit.get(d, 0.0) + _num(cell(cp))
        if cell(cw).strip():
            wins[d] = cell(cw).strip()
    return days, wins, profit


def period(today, calendar):
    """С прошлого рабочего дня (по calendar) до вчера: во вторник — понедельник, в понедельник — пт–вс."""
    end = start = today - dt.timedelta(days=1)
    while start.isoformat() not in calendar and (end - start).days < 6:
        start -= dt.timedelta(days=1)
    return start, end


def collect(today, calendar):
    start, end = period(today, calendar)
    first = end - dt.timedelta(days=HISTORY_DAYS)
    total, sources, errors = {}, [], []
    wins, profit = {}, {}
    for name, fn in (("Wildberries", wildberries), ("Ozon", ozon), ("таблица", sheet)):
        try:
            got = fn(first, end)
            if name == "таблица":
                got, wins, profit = got
        except Exception as e:  # один сломанный источник не должен ломать напутствие
            errors.append(f"{name}: {type(e).__name__}" + (f" {e.code}" if hasattr(e, "code") else ""))
            continue
        if got is None:
            continue
        sources.append(f"{name} ({sum(1 for o, _ in got.values() if o)} дн. с заказами)")
        for d, (o, v) in got.items():
            to, tv = total.get(d, (0, 0.0))
            total[d] = (to + o, tv + v)

    length = (end - start).days + 1
    window = lambda s: [s + dt.timedelta(days=i) for i in range(length)]
    summ = lambda s: (sum(total.get(d, (0, 0))[0] for d in window(s)), sum(total.get(d, (0, 0.0))[1] for d in window(s)))
    orders, revenue = summ(start)
    period_profit = [profit[d] for d in window(start) if d in profit]
    prev_orders, _ = summ(start - dt.timedelta(days=length))
    past = [summ(first + dt.timedelta(days=i))[0] for i in range((start - first).days - length + 1)]
    past = [p for p in past if p]

    if not sources or orders == 0:
        level = "support"
    elif len(past) >= 7 and orders > max(past):
        level = "record"
    elif prev_orders and orders > prev_orders:
        level = "up"
    elif not prev_orders or orders >= prev_orders * 0.9:
        level = "steady"
    else:
        level = "support"
    return {"level": level, "start": start.isoformat(), "end": end.isoformat(), "days": length,
            "orders": orders, "revenue": round(revenue),
            "profit": round(sum(period_profit)) if period_profit else None, "prev_orders": prev_orders,
            "wins": [wins[d] for d in sorted(wins) if start <= d <= end],
            "sources": sources, "errors": errors}


def _plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def stats_line(r):
    """Строка с цифрами для сообщения в чат (не для картинки и не для лога)."""
    lines = []
    if r["level"] != "support":
        dm = lambda d: dt.date.fromisoformat(d).strftime("%d.%m")
        when = "вчера" if r["days"] == 1 else f"с {dm(r['start'])} по {dm(r['end'])}"
        o = r["orders"]
        num = lambda n: f"{n:,}".replace(",", "\u00a0")
        s = f"Итоги {when}: {num(o)} {_plural(o, 'заказ', 'заказа', 'заказов')}"
        if r["revenue"]:
            s += f", {num(r['revenue'])} ₽ выручки"
        if r.get("profit"):
            s += f", {num(r['profit'])} ₽ прибыли"
        if r["level"] == "record":
            s += " — лучший результат за месяц!"
        elif r["level"] == "up" and r["prev_orders"]:
            pct = round((o / r["prev_orders"] - 1) * 100)
            if pct >= 1:
                s += f" — на {pct}% больше, чем " + ("днём раньше" if r["days"] == 1 else "за такой же период перед этим")
        lines.append(s + ("." if not s.endswith("!") else ""))
    for w in r["wins"]:
        lines.append(f"Победа дня: {w}")
    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    import sys
    from zoneinfo import ZoneInfo
    root = pathlib.Path(__file__).resolve().parent.parent
    cal = json.loads((root / "wishes" / "team.json").read_text(encoding="utf-8"))["calendar"]
    today = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(ZoneInfo("Europe/Samara")).date()
    r = collect(today, cal)
    # в лог — только уровень и источники, без цифр
    print(f"{r['start']}…{r['end']}: уровень {r['level']}, источники: {', '.join(r['sources']) or 'нет'}"
          + (f", ошибки: {'; '.join(r['errors'])}" if r["errors"] else ""))
