"""Итоги прошедшего дня для рассылок в Битрикс24 — только из TrueStats.

Репозиторий публичный, поэтому цифры никуда не сохраняются и не печатаются в лог —
они попадают только в сообщение в Битрикс24 и в контрольную копию владельцу (control_text).

Источник один: TrueStats, метод «Агрегированный вид по дням» (как вкладка «По дням» в оцифровке):
заказы (ordersCount), сумма заказов (orders), продажи (sales), реализация (realisation) и прибыль (profit) по дням.

Данные ещё не выгрузились: TrueStats заполняет день с задержкой — сначала приходят заказы,
а продажи и реализация остаются нулём. Если хотя бы за один день периода продажи и реализация = 0
(или дня нет в ответе), ready = False — рассылку в чаты не отправляем.

Переменные окружения:
  TRUE_STATS            API-токен TrueStats (обязателен; без него напутствие уходит без цифр)
  TRUESTATS_ACCOUNTS    магазины TrueStats через запятую (названия или ID), например
                        «Дари Радость, Дари сейчас» — итоги только по ним
  TRUESTATS_GROUP       группа артикулов TrueStats (название, например «НГ26-27/Новый год 2027», или ID) — итоги только по ней
  SEASON_START          начало сезона ГГГГ-ММ-ДД — добавляет итоги с начала сезона
  STATS_LABEL           подпись в строке итогов, например «по НГ-коллекции»

Период — всегда один день: вчера, в сравнении с позавчера (в понедельник — воскресенье с субботой). Уровень:
Уровень считается по выручке (сумме заказов), а не по их количеству:
  record  — лучший день по выручке за последние 30 дней (или с начала сезона, если задан SEASON_START)
  up      — выручка больше, чем днём раньше
  steady  — примерно так же (спад выручки не больше 10%)
  support — спад больше 10% или TrueStats недоступен: напутствие без цифр
"""
import datetime as dt
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


def _ts(path, body):
    headers = {"X-Api-Token": os.environ["TRUE_STATS"].strip(), "Content-Type": "application/json", "Accept": "application/json"}
    return json.loads(_get("https://api.truestats.ru" + path, headers, json.dumps(body).encode()))


def truestats_group_id(group):
    """ID группы артикулов по названию (или сам ID, если передано число)."""
    if str(group).isdigit():
        return int(group)
    facets = _ts("/reporting/facets", {"_dimensions": ["groups"]})
    want = " ".join(str(group).lower().split())
    for g in facets.get("groups", []):
        if " ".join(str(g.get("name", "")).lower().split()) == want:
            return int(g["id"])
    raise LookupError(f"группа «{group}» не найдена в TrueStats")


def truestats_account_ids(names):
    """ID магазинов TrueStats по названиям (или сами ID)."""
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    facets = _ts("/reporting/facets", {"_dimensions": ["accounts"]})
    norm = lambda t: " ".join(str(t).lower().replace("ё", "е").split())
    by_name = {norm(a.get("name", "")): int(a["id"]) for a in facets.get("accounts", [])}
    ids = []
    for n in wanted:
        if n.isdigit():
            ids.append(int(n))
        elif norm(n) in by_name:
            ids.append(by_name[norm(n)])
        else:
            raise LookupError(f"магазин «{n}» не найден в TrueStats")
    return ids


def truestats(start, end, accounts=None):
    """Заказы, сумма заказов, прибыль, продажи и реализация по дням из TrueStats
    (с фильтром по магазинам и/или группе артикулов; accounts — список ID вместо TRUESTATS_ACCOUNTS)."""
    key = os.environ.get("TRUE_STATS", "").strip()
    if not key:
        return None, {}, {}
    body = {"dateFrom": start.isoformat(), "dateTo": end.isoformat()}
    group = os.environ.get("TRUESTATS_GROUP", "").strip()
    filters = {}
    if group:
        filters["group"] = [truestats_group_id(group)]
    names = os.environ.get("TRUESTATS_ACCOUNTS", "").strip()
    if accounts or names:
        filters["accounts"] = accounts or truestats_account_ids(names)
    if filters:
        body["filters"] = filters
    res = _ts("/reporting/aggregated-view/day", body)
    days, profit, sold = {}, {}, {}
    for r in res.get("result", []):
        d = _date(r.get("date"))
        if d and start <= d <= end:
            days[d] = (int(_num(r.get("ordersCount"))), _num(r.get("orders")))
            sold[d] = (_num(r.get("sales")), _num(r.get("realisation")))
            if r.get("profit") is not None:
                profit[d] = _num(r.get("profit"))
    return days, profit, sold


def by_account(start, end):
    """Итоги периода по каждому магазину из TRUESTATS_ACCOUNTS — для контрольной копии."""
    names = [n.strip() for n in os.environ.get("TRUESTATS_ACCOUNTS", "").split(",") if n.strip()]
    if len(names) < 2:
        return []
    rows = []
    for name, aid in zip(names, truestats_account_ids(",".join(names))):
        days, profit, sold = truestats(start, end, [aid])
        rows.append([name, sum(o for o, _ in days.values()), round(sum(r for _, r in days.values())),
                     round(sum(s for s, _ in sold.values())), round(sum(r for _, r in sold.values())),
                     round(sum(profit.values()))])
    return rows


def period(today):
    """Всегда вчерашний день — сравнение день ко дню, в том числе в понедельник (воскресенье с субботой)."""
    end = today - dt.timedelta(days=1)
    return end, end


def collect(today):
    start, end = period(today)
    first = end - dt.timedelta(days=HISTORY_DAYS)
    total, sources, errors = {}, [], []
    wins, profit, sold = {}, {}, {}
    season = os.environ.get("SEASON_START", "").strip()
    season_start = dt.date.fromisoformat(season) if season else None
    if season_start and season_start < first:
        first = season_start  # история нужна с начала сезона — для итогов сезона
    try:
        got, profit, sold = truestats(first, end)
    except Exception as e:  # TrueStats недоступен — напутствие уйдёт без цифр, но уйдёт
        errors.append(f"TrueStats: {type(e).__name__}" + (f" {e.code}" if hasattr(e, "code") else ""))
        got = None
    if got is not None:
        sources.append(f"TrueStats ({sum(1 for o, _ in got.values() if o)} дн. с заказами)")
        total = dict(got)

    length = (end - start).days + 1
    window = lambda s: [s + dt.timedelta(days=i) for i in range(length)]
    summ = lambda s: (sum(total.get(d, (0, 0))[0] for d in window(s)), sum(total.get(d, (0, 0.0))[1] for d in window(s)))
    orders, revenue = summ(start)
    period_profit = [profit[d] for d in window(start) if d in profit]
    prev_orders, prev_revenue = summ(start - dt.timedelta(days=length))
    # рекорд: в сезон — за весь сезон, иначе — за последние 30 дней
    hist = season_start if season_start else max(first, end - dt.timedelta(days=HISTORY_DAYS))
    past = [summ(hist + dt.timedelta(days=i))[1] for i in range((start - hist).days - length + 1)]
    past = [p for p in past if p]

    # данные ещё не выгрузились: за день периода нет строки или продажи и реализация = 0
    not_loaded = [d.isoformat() for d in window(start) if got is not None and not any(sold.get(d, (0, 0)))]
    accounts = []
    if sources and not not_loaded:
        try:
            accounts = by_account(start, end)
        except Exception as e:
            errors.append(f"TrueStats по магазинам: {type(e).__name__}")

    if not sources or orders == 0 or not revenue:
        level = "support"
    elif len(past) >= 7 and revenue > max(past):
        level = "record"
    elif prev_revenue and revenue > prev_revenue:
        level = "up"
    elif not prev_revenue or revenue >= prev_revenue * 0.9:
        level = "steady"
    else:
        level = "support"
    season_days = [d for d in total if season_start and season_start <= d <= end]
    return {"level": level, "start": start.isoformat(), "end": end.isoformat(), "days": length,
            "season_orders": sum(total[d][0] for d in season_days) if season_start else None,
            "season_revenue": round(sum(total[d][1] for d in season_days)) if season_start else None,
            "record_label": "лучший результат сезона" if season_start else "лучший результат за месяц",
            "orders": orders, "revenue": round(revenue),
            "profit": round(sum(period_profit)) if period_profit else None, "prev_orders": prev_orders,
            "prev_revenue": round(prev_revenue),
            "wins": [wins[d] for d in sorted(wins) if start <= d <= end],
            "ready": not not_loaded, "not_loaded": not_loaded,
            "per_day": [[d.isoformat(), *total.get(d, (0, 0.0)), *sold.get(d, (0.0, 0.0)), profit.get(d)]
                        for d in window(start)],
            "accounts": accounts, "prev_start": (start - dt.timedelta(days=length)).isoformat(),
            "record_from": hist.isoformat(), "record_best": max(past) if past else None,
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
        label = os.environ.get("STATS_LABEL", "").strip()
        s = f"Итоги {label + ' ' if label else ''}{when}: {num(o)} {_plural(o, 'заказ', 'заказа', 'заказов')}"
        if r["revenue"]:
            s += f" на {num(r['revenue'])} ₽"
        if r.get("profit"):
            s += f", {num(r['profit'])} ₽ прибыли"
        if r["level"] == "record":
            s += f" — {r.get('record_label') or 'лучший результат за месяц'}!"
        elif r["level"] == "up" and r.get("prev_revenue"):
            pct = round((r["revenue"] / r["prev_revenue"] - 1) * 100)
            if pct >= 1:
                s += f" — выручка на {pct}% больше, чем " + ("днём раньше" if r["days"] == 1 else "за такой же период перед этим")
        lines.append(s + ("." if not s.endswith("!") else ""))
        if r.get("season_orders"):
            so = r["season_orders"]
            lines.append(f"С начала сезона: {num(so)} {_plural(so, 'заказ', 'заказа', 'заказов')}"
                         + (f" на {num(r['season_revenue'])} ₽." if r.get("season_revenue") else "."))
    for w in r["wins"]:
        lines.append(f"Победа дня: {w}")
    return "\n".join(lines)


LEVELS = {"record": "рекорд", "up": "рост", "steady": "стабильно", "support": "поддержка, без цифр"}


def control_text(r):
    """Разбивка для сверки с TrueStats — только в личную контрольную копию, не в чат и не в лог."""
    num = lambda n: f"{round(n or 0):,}".replace(",", "\u00a0")
    dm = lambda d: dt.date.fromisoformat(d).strftime("%d.%m")
    flt = [f"магазины «{os.environ['TRUESTATS_ACCOUNTS'].strip()}»"] if os.environ.get("TRUESTATS_ACCOUNTS", "").strip() else []
    if os.environ.get("TRUESTATS_GROUP", "").strip():
        flt.append(f"группа «{os.environ['TRUESTATS_GROUP'].strip()}»")
    lines = [f"Фильтр TrueStats: {', '.join(flt) or 'весь кабинет'}",
             f"Источник: {', '.join(r['sources']) or 'нет'}" + (f"; ошибки: {'; '.join(r['errors'])}" if r["errors"] else ""),
             "", "[B]По дням[/B] (заказы · сумма заказов · продажи · реализация · прибыль):"]
    for d, o, rev, sales, real, prof in r.get("per_day", []):
        lines.append(f"{dm(d)} — {num(o)} · {num(rev)} ₽ · {num(sales)} ₽ · {num(real)} ₽ · "
                     + (f"{num(prof)} ₽" if prof is not None else "нет данных")
                     + (" ⚠️ не выгрузилось" if d in r.get("not_loaded", []) else ""))
    if r.get("accounts"):
        lines += ["", "[B]По магазинам за период[/B]:"]
        lines += [f"{n} — {num(o)} · {num(rev)} ₽ · {num(s)} ₽ · {num(re_)} ₽ · {num(p)} ₽" for n, o, rev, s, re_, p in r["accounts"]]
    orders = lambda n: f"{num(n)} {_plural(n or 0, 'заказ', 'заказа', 'заказов')}"
    lines += ["", f"Сравнение по выручке: {num(r['revenue'])} ₽ ({orders(r['orders'])}) против "
                  f"{num(r.get('prev_revenue'))} ₽ ({orders(r['prev_orders'])}) "
                  f"за {dm(r['prev_start'])} → уровень «{LEVELS.get(r['level'], r['level'])}»"]
    if r.get("record_best") is not None:
        lines.append(f"Лучшая прошлая выручка за день с {dm(r['record_from'])}: {num(r['record_best'])} ₽")
    if r.get("season_orders") is not None:
        lines.append(f"Сезон: {orders(r['season_orders'])} на {num(r['season_revenue'])} ₽")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from zoneinfo import ZoneInfo
    today = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(ZoneInfo("Europe/Samara")).date()
    r = collect(today)
    # в лог — только уровень и источники, без цифр
    print(f"{r['start']}…{r['end']}: уровень {r['level']}, источники: {', '.join(r['sources']) or 'нет'}"
          + (f", ошибки: {'; '.join(r['errors'])}" if r["errors"] else ""))
