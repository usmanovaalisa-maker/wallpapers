"""Накопленная прибыль двух WB-артикулов для новогоднего корпоратива.

Только чтение TrueStats. Суммы не попадают в Git, картинки или публичные логи.
Поле profitWithoutExpense — прибыль без операционных расходов; в рассылке
она называется валовой прибылью по решению владельца от 24.11.2026.
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ARTICLES = (261657089, 44713360)
PAGE_SIZE = 1000
PROFIT_FIELD = "profitWithoutExpense"
URL = "https://api.truestats.ru/reporting/main/products"


class CorporateProfitError(ValueError):
    pass


def season_start(today):
    return dt.date(today.year if today.month >= 9 else today.year - 1, 9, 1)


def request(body, token):
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers={
        "X-Api-Token": token, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise CorporateProfitError("Ответ TrueStats превышает ожидаемый размер")
        return json.loads(raw, parse_float=Decimal)
    except urllib.error.HTTPError as error:
        raise CorporateProfitError(f"TrueStats недоступен (HTTP {error.code})") from None
    except (urllib.error.URLError, OSError):
        raise CorporateProfitError("TrueStats недоступен: сетевая ошибка") from None
    except (ValueError, UnicodeError):
        raise CorporateProfitError("Некорректный ответ TrueStats") from None


def collect(today, token=None):
    token = token or os.environ.get("TRUE_STATS") or os.environ.get("TRUESTATS_API_KEY")
    if not token or not token.strip():
        raise CorporateProfitError("Не настроен ключ TrueStats для итога на корпоратив")
    first = season_start(today)
    totals = {article: Decimal(0) for article in ARTICLES}
    found, seen = set(), set()
    for page in range(1, 21):
        payload = request({"dateFrom": first.isoformat(), "dateTo": today.isoformat(),
                           "groupBy": "nm_id", "tableArticles": list(ARTICLES),
                           "filters": {"accountTypes": [0], "article": [str(a) for a in ARTICLES]},
                           "page": page, "limit": PAGE_SIZE}, token.strip())
        rows = payload.get("byProduct") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise CorporateProfitError("Нет детализации по артикулам в ответе TrueStats")
        for row in rows:
            if not isinstance(row, dict):
                raise CorporateProfitError("Некорректная строка артикула TrueStats")
            # Общие stats/total могут включать весь кабинет: складываем только byProduct.
            article = str(row.get("article", ""))
            if not article.isdigit() or int(article) not in totals:
                raise CorporateProfitError("TrueStats вернул посторонние артикулы")
            types = row.get("accountType")
            if types is not None and types != [0]:
                raise CorporateProfitError("TrueStats вернул данные другого маркетплейса")
            identity = json.dumps(row, sort_keys=True, default=str)
            if identity in seen:
                raise CorporateProfitError("TrueStats повторил строку артикула")
            seen.add(identity)
            value = row.get(PROFIT_FIELD)
            if value is None or isinstance(value, bool):
                raise CorporateProfitError("Не заполнена прибыль по одному из артикулов")
            try:
                amount = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise CorporateProfitError("Некорректная прибыль по артикулу") from None
            if not amount.is_finite():
                raise CorporateProfitError("Некорректная прибыль по артикулу")
            article = int(article)
            totals[article] += amount
            found.add(article)
        if len(rows) < PAGE_SIZE:
            break
    else:
        raise CorporateProfitError("Не удалось прочитать все страницы TrueStats")
    if found != set(ARTICLES):
        raise CorporateProfitError("В TrueStats нет данных по одному из артикулов")
    return {"start": first.isoformat(), "end": today.isoformat(),
            "amount": str(sum(totals.values())), "by_article": {str(k): str(v) for k, v in totals.items()},
            "profit_field": PROFIT_FIELD, "source": "TrueStats"}


def footer(result):
    value = result.get("corporate_profit")
    if not value:
        return ""
    rounded = Decimal(value["amount"]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    rubles = f"{int(rounded):,}".replace(",", " ").replace("-", "−")
    return f"На новогодний корпоратив заработано {rubles} рублей."
