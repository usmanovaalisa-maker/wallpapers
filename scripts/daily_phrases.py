"""Ежедневная задача Claude «Рассылки и фразы — Дари Сейчас»: всё механическое одной командой.

Задача запускается по расписанию без человека рядом, поэтому любая команда, которой нет
в «Всегда разрешено», вешает запуск до ручного подтверждения. Здесь собраны все шаги,
кроме сочинения текстов, — задаче нужны только три команды:

  python3 scripts/daily_phrases.py start
      обновляет main из origin, пишет отметку .github/last-local-run (время по Самаре),
      печатает ЗАВТРАШНЮЮ дату, что уже заполнено и тексты последних дней для разнообразия.
  python3 scripts/daily_phrases.py add [черновик.json]
      проверяет черновик (длины, поля, похожесть на все фразы в трёх файлах — difflib > 0.8)
      и вставляет его; затем json.load всех файлов и DRY_RUN обеих рассылок.
      Без пути берёт свежий phrases.json из папки scratchpad задачи.
      При любой ошибке ничего не записывает (или откатывает wishes/) и выходит с кодом 1.
  python3 scripts/daily_phrases.py publish
      коммит «Свежие фразы на ДАТА» (или «Запуск рассылок») и push в main с повторами.
      Этот push запускает сегодняшние рассылки в GitHub Actions.

С 29.10.2026 пишем только ng (новогодняя рассылка); fans и team отключены и пропускаются.
Черновик — JSON с любыми из ключей fans / team / ng:
  {"date": "ГГГГ-ММ-ДД",
   "fans": ["12 фраз подписчикам"],
   "team": {"record", "up", "steady", "support",
            "reaction_record", "reaction_up", "reaction_steady", "reaction_support"},
   "ng":   {те же восемь полей}}
"""
import datetime as dt
import difflib
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Samara")
FILES = {"fans": "wishes/fans.json", "team": "wishes/team.json", "ng": "wishes/ng.json"}
# С 29.10.2026 пишем только новогоднюю рассылку: «Доброплан» (team) и подписчики (fans) отключены.
# Их файлы остаются для проверки похожести и календаря рабочих дней (calendar в team.json).
ACTIVE = ["ng"]
MAIN_KEYS = ["record", "up", "steady", "support"]
REACTION_KEYS = ["reaction_" + k for k in MAIN_KEYS]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
# Папки scratchpad сессий Claude, запущенных в этом репозитории
SCRATCH_GLOB = "/private/tmp/claude-*/-Users-alisatitova-Documents-wallpapers/*/scratchpad/phrases.json"
SIMILAR = 0.8


def now():
    return dt.datetime.now(TZ)


def tomorrow():
    return (now().date() + dt.timedelta(days=1)).isoformat()


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} — ошибка:\n{r.stdout}{r.stderr}")
    return r


def load(key):
    return json.loads((ROOT / FILES[key]).read_text(encoding="utf-8"))


def is_last_workday_of_month(day):
    nxt = day + dt.timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += dt.timedelta(days=1)
    return day.weekday() < 5 and nxt.month != day.month


def cmd_start():
    git("fetch", "-q", "origin", "main")
    git("checkout", "-q", "main")
    git("reset", "-q", "--hard", "origin/main")
    stamp = now().strftime("%Y-%m-%d %H:%M:%S")
    (ROOT / ".github/last-local-run").write_text(stamp + "\n", encoding="utf-8")

    date = tomorrow()
    day = dt.date.fromisoformat(date)
    print(f"Отметка запуска: {stamp} (Самара)")
    print(f"ДАТА = {date}, {WEEKDAYS[day.weekday()]}"
          + (" — последний рабочий день месяца" if is_last_workday_of_month(day) else ""))
    data = {k: load(k) for k in FILES}
    cal = data["team"].get("calendar", {}).get(date)
    if not cal:
        print(f"{date} — не рабочий день (нет в calendar team.json): тексты не нужны — сразу publish.")
        return
    todo = [k for k in ACTIVE if date not in data[k].get("daily", {})]
    for k in ACTIVE:
        print(f"  {FILES[k]}: " + ("нужно написать" if k in todo else "уже есть — пропустить"))
    if cal:
        print(f"calendar[{date}] в team.json (сохрани этот повод в основных текстах): {cal}")
    if not todo:
        print("\nВсё уже заполнено — сразу publish.")
        return

    print(f"\nЧерновик сохрани инструментом Write в свою папку scratchpad как phrases.json, "
          f'с "date": "{date}" и ключами: {", ".join(todo)}. Затем: python3 scripts/daily_phrases.py add')

    for k in ("team", "ng"):
        if k not in todo:
            continue
        print(f"\n== {FILES[k]}: последние 7 дней daily (образы и начала не повторять)")
        for d in sorted(data[k]["daily"])[-7:]:
            v = data[k]["daily"][d]
            print(f"-- {d}")
            if isinstance(v, dict):
                for f in MAIN_KEYS + REACTION_KEYS:
                    if f in v:
                        print(f"  {f}: {v[f]}")
            else:
                print(f"  {v}")
    if "fans" in todo:
        print(f"\n== {FILES['fans']}: последние 2 дня (для тона, не повторять)")
        for d in sorted(data["fans"]["daily"])[-2:]:
            print(f"-- {d}")
            for s in data["fans"]["daily"][d]:
                print(f"  {s}")


def norm(s):
    return re.sub(r"[^\w ]", "", s.lower().replace("ё", "е")).strip()


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def find_draft(arg):
    if arg:
        return pathlib.Path(arg)
    found = sorted(glob.glob(SCRATCH_GLOB), key=os.path.getmtime)
    fresh = [p for p in found if time.time() - os.path.getmtime(p) < 6 * 3600]
    if not fresh:
        sys.exit("Черновик не найден: сохрани phrases.json инструментом Write в свою папку scratchpad "
                 "или передай путь: python3 scripts/daily_phrases.py add ПУТЬ")
    return pathlib.Path(fresh[-1])


def check_obj(key, obj, errors):
    if not isinstance(obj, dict):
        errors.append(f"{key}: нужен объект с восемью полями")
        return
    missing = [f for f in MAIN_KEYS + REACTION_KEYS if not str(obj.get(f, "")).strip()]
    extra = [f for f in obj if f not in MAIN_KEYS + REACTION_KEYS]
    if missing:
        errors.append(f"{key}: нет полей {missing}")
    if extra:
        errors.append(f"{key}: лишние поля {extra}")
    for f in MAIN_KEYS:
        s = str(obj.get(f, ""))
        if len(s) > 200:
            errors.append(f"{key}.{f}: {len(s)} символов, нужно до 200")
        if re.search(r"\d", s):
            errors.append(f"{key}.{f}: в основном тексте не должно быть цифр")
    for f in REACTION_KEYS:
        s = str(obj.get(f, ""))
        if len(s) > 150:
            errors.append(f"{key}.{f}: {len(s)} символов, нужно до 150")


def cmd_add(arg):
    path = find_draft(arg)
    print(f"Черновик: {path}")
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"Черновик не читается как JSON: {e}")
    date = draft.get("date")
    if date != tomorrow():
        sys.exit(f'В черновике "date": {date!r}, а завтра {tomorrow()} — исправь дату')

    data = {k: load(k) for k in FILES}
    errors, warnings, new = [], [], {}
    for k in FILES:
        if k not in draft:
            continue
        if k not in ACTIVE:
            warnings.append(f"{FILES[k]}: эта рассылка отключена — пропускаю")
            continue
        if date in data[k].get("daily", {}):
            warnings.append(f"{FILES[k]}: daily[{date}] уже есть — пропускаю")
            continue
        new[k] = draft[k]
    if not new:
        print("\n".join(warnings) or "В черновике нет ни fans, ни team, ни ng")
        print("Нечего добавлять.")
        return

    if "fans" in new:
        fans = new["fans"]
        if not (isinstance(fans, list) and all(isinstance(s, str) and s.strip() for s in fans)):
            errors.append("fans: нужен массив строк")
        else:
            if len(fans) != 12:
                errors.append(f"fans: {len(fans)} фраз, нужно 12")
            for s in fans:
                if len(s) > 110:
                    errors.append(f"fans: {len(s)} символов, нужно до 110: {s}")
                if "#" in s or re.search("[\U0001F000-\U0001FAFF☀-➿]", s):
                    errors.append(f"fans: без эмодзи и хэштегов: {s}")
    for k in ("team", "ng"):
        if k in new:
            check_obj(k, new[k], errors)

    # Похожесть: со всеми фразами трёх файлов и внутри черновика
    old = [(norm(s), s) for k in FILES for s in strings(data[k]) if len(s) > 15]
    seen = []
    for s in (x for k in new for x in strings(new[k])):
        n = norm(s)
        for on, o in old + seen:
            sm = difflib.SequenceMatcher(None, n, on)
            if sm.real_quick_ratio() <= SIMILAR or sm.quick_ratio() <= SIMILAR:
                continue
            r = sm.ratio()
            if r > SIMILAR:
                errors.append(f"похоже ({r:.2f}): «{s}» ~ «{o}»")
                break
        seen.append((n, s))

    for w in warnings:
        print(w)
    if errors:
        print("\nОШИБКИ — ничего не записано, исправь черновик и запусти add снова:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)

    if "fans" in new:
        # fans.json не пересериализуем: вставляем блок текстом в конец daily (последний ключ файла)
        p = ROOT / FILES["fans"]
        txt = p.read_text(encoding="utf-8")
        idx = txt.rstrip().rfind("]")
        block = (f',\n    "{date}": [\n'
                 + ",\n".join("      " + json.dumps(s, ensure_ascii=False) for s in new["fans"])
                 + "\n    ]")
        p.write_text(txt[:idx + 1] + block + txt[idx + 1:], encoding="utf-8")
    for k in ("team", "ng"):
        if k in new:
            data[k]["daily"][date] = {f: new[k][f] for f in MAIN_KEYS + REACTION_KEYS}
            (ROOT / FILES[k]).write_text(json.dumps(data[k], ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8")

    def rollback(msg):
        git("checkout", "--", *FILES.values())
        sys.exit(msg + "\nИзменения в wishes/ откатил.")

    for k in FILES:
        try:
            d = load(k)
        except Exception as e:
            rollback(f"{FILES[k]} после вставки не читается: {e}")
        if k in new and d["daily"].get(date) is None:
            rollback(f"{FILES[k]}: daily[{date}] не появился")
        if k == "fans" and "fans" in new:
            rest = {kk: vv for kk, vv in d.items() if kk != "daily"}
            if rest != {kk: vv for kk, vv in data["fans"].items() if kk != "daily"}:
                rollback("fans.json: вставка задела что-то кроме daily")

    for extra in ({"WISHES_FILE": "wishes/ng.json"},):
        env = {**os.environ, "WISH_DATE": date, "DRY_RUN": "1", **extra}
        r = subprocess.run([sys.executable, "scripts/send_bitrix.py"], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        name = extra.get("WISHES_FILE", "wishes/team.json")
        if r.returncode:
            rollback(f"DRY_RUN для {name} упал:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
        print(f"DRY_RUN {name}: ok")

    print(f"\nДобавлено на {date}: " + ", ".join(FILES[k] for k in new))
    print("Дальше: python3 scripts/daily_phrases.py publish")


def cmd_publish():
    date = tomorrow()
    git("add", ".github/last-local-run", "wishes")
    changed = git("diff", "--cached", "--name-only").stdout.split()
    if not changed:
        sys.exit("Нечего коммитить: сначала python3 scripts/daily_phrases.py start")
    msg = f"Новогодние тексты на {date}" if any(c.startswith("wishes/") for c in changed) else "Запуск рассылки"
    git("commit", "-q", "-m", msg)
    for attempt in range(1, 5):
        r = git("push", "-q", "origin", "HEAD:main", check=False)
        if not r.returncode:
            print(f"Push ok: {git('rev-parse', '--short', 'HEAD').stdout.strip()} «{msg}» — "
                  "GitHub Actions запустит сегодняшние рассылки.")
            return
        print(f"Push отклонён (попытка {attempt}): {r.stderr.strip()[-300:]}")
        git("pull", "-q", "--rebase", "origin", "main", check=False)
    sys.exit("Push не прошёл за 4 попытки")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "start":
        cmd_start()
    elif cmd == "add":
        cmd_add(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "publish":
        cmd_publish()
    else:
        sys.exit(__doc__)
