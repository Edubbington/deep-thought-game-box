"""The parts of the campaign file the DM's tools keep: the calendar, the
party's treasure, roll tables, and reading three numbers out of a page of the
DM's own loaded book. No screen code, no files.

Nothing here holds a word from any book. A roll table's rows are copied in by
the owner, from his own copy, into his own campaign file."""
import random
import re

from ... import dice
from .party import COIN_NAMES

MAX_DAY = 99999
MAX_COINS = 99999
DRAGON = "Dragon"                       # the name the old dragon_table slot goes by
DRAGON_FIELD = "fixed_results.dragon_table.value"


def _int(x, default=None):
    return x if isinstance(x, int) and not isinstance(x, bool) else default


# ---------------------------------------------------------------- tidy on load
def tidy(c):
    """Make sure the calendar, treasure, coins and tables are there and are the
    shape the screens expect, whatever an older or hand-edited file holds."""
    cal = c.get("calendar") if isinstance(c.get("calendar"), dict) else {}
    day = max(1, min(MAX_DAY, _int(cal.get("day"), 1)))
    notes = []
    for n in cal.get("notes") if isinstance(cal.get("notes"), list) else []:
        if isinstance(n, str) and n.strip():
            notes.append({"day": day, "text": n.strip()})
        elif isinstance(n, dict) and str(n.get("text", "")).strip():
            n["day"], n["text"] = max(1, _int(n.get("day"), day)), str(n["text"]).strip()
            notes.append(n)
    cal["day"], cal["date"], cal["notes"] = day, str(cal.get("date") or ""), notes
    c["calendar"] = cal
    items = []
    for t in c.get("treasure") if isinstance(c.get("treasure"), list) else []:
        if isinstance(t, str) and t.strip():
            items.append({"name": t.strip(), "holder": None, "day": None})
        elif isinstance(t, dict) and str(t.get("name", "")).strip():
            t["name"], t["holder"], t["day"] = str(t["name"]).strip(), t.get("holder") or None, _int(t.get("day"))
            items.append(t)
    c["treasure"] = items
    coins = c.get("party_coins") if isinstance(c.get("party_coins"), dict) else {}
    c["party_coins"] = {k: max(0, min(MAX_COINS, _int(coins.get(k), 0))) for k, _ in COIN_NAMES}
    if not isinstance(c.get("tables"), dict):
        c["tables"] = {}
    return c


# ---------------------------------------------------------------- calendar
def day_words(c):
    cal = c["calendar"]
    return "Day %d" % cal["day"] + (", %s" % cal["date"] if cal["date"] else "")


def advance(c, days):
    cal = c["calendar"]
    cal["day"] = max(1, min(MAX_DAY, cal["day"] + int(days)))
    return cal["day"]


def add_note(c, text, **extra):
    """A note against today's in-world day. Returns the note."""
    note = dict({"day": c["calendar"]["day"], "text": " ".join(str(text).split())}, **extra)
    if not note["text"]:
        raise ValueError("An empty note is no note.")
    c["calendar"]["notes"].append(note)
    return note


def notes_newest(c):
    """[(index in the file, note)], latest day first; on one day, last written first."""
    got = list(enumerate(c["calendar"]["notes"]))
    return sorted(got, key=lambda kn: (-kn[1]["day"], -kn[0]))


# ---------------------------------------------------------------- treasure
def add_item(c, name, holder=None):
    name = " ".join(str(name).split())
    if not name:
        raise ValueError("It needs a name.")
    item = {"name": name, "holder": holder or None, "day": c["calendar"]["day"]}
    c["treasure"].append(item)
    return item


def next_holder(now, names):
    """Whoever holds it after 'now': the party as a whole, then each character."""
    order = [None] + [n for n in names if n]
    return order[(order.index(now) + 1) % len(order)] if now in order else None


def holder_words(item):
    return "Held by %s" % item["holder"] if item.get("holder") else "With the party"


def coin_name(coin):
    return dict(COIN_NAMES)[coin].lower()


def step_coin(c, coin, amount):
    """Add to (or take from) one kind of coin. Never below nothing."""
    if coin not in dict(COIN_NAMES):
        raise ValueError("That is not a coin I know.")
    new = c["party_coins"][coin] + int(amount)
    if new < 0:
        raise ValueError("Not enough %s: the party has %d." % (coin_name(coin), c["party_coins"][coin]))
    if new > MAX_COINS:
        raise ValueError("%d is as many as I will count." % MAX_COINS)
    c["party_coins"][coin] = new
    return new


def coins_words(c):
    parts = ["%d %s" % (c["party_coins"][k], name.lower()) for k, name in COIN_NAMES if c["party_coins"][k]]
    return ", ".join(parts) or "none"


# ---------------------------------------------------------------- roll tables
def _rows(raw):
    out = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict) or not str(r.get("text") or "").strip():
            continue
        lo = _int(r.get("lo"), _int(r.get("roll")))
        hi = _int(r.get("hi"), lo)
        if lo is not None and 1 <= lo <= hi:
            out.append({"lo": lo, "hi": hi, "text": str(r["text"]).strip()})
    return sorted(out, key=lambda r: r["lo"])


def _legacy_rows(value):
    """The dragon slot's own shape: {"1": "...", "2": null, "3-4": "..."}."""
    out = []
    for key, text in value.items() if isinstance(value, dict) else []:
        m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", str(key))
        if m and isinstance(text, str) and text.strip():
            lo = int(m.group(1))
            out.append({"lo": lo, "hi": int(m.group(2) or lo), "text": text.strip()})
    return _rows(out)


def tables(c):
    """Every roll table the campaign file defines, as
    {"name", "die", "rows": [{"lo", "hi", "text"}], "where", "dragon"}.
    'where' is the field to fill in. Rows with no words in them do not count."""
    out = []
    got = c.get("tables") if isinstance(c.get("tables"), dict) else {}
    for name, t in got.items():
        if not isinstance(t, dict):
            continue
        rows = _rows(t.get("rows"))
        die = _int(t.get("die"))
        if die is None or not 2 <= die <= 1000:
            die = max([r["hi"] for r in rows] + [20])
        out.append({"name": str(name), "die": die, "rows": rows, "where": "tables.%s.rows" % name,
                    "dragon": str(name).lower() == DRAGON.lower()})
    slot = (c.get("fixed_results") or {}).get("dragon_table") if isinstance(c.get("fixed_results"), dict) else None
    if isinstance(slot, dict) and not any(t["dragon"] for t in out):
        value = slot.get("value")
        keys = [int(k) for k in value if re.fullmatch(r"[0-9]{1,4}", str(k))] if isinstance(value, dict) else []
        out.insert(0, {"name": DRAGON, "die": max(keys + [20]), "rows": _legacy_rows(value),
                       "where": DRAGON_FIELD, "dragon": True})
    return out


def table(c, name):
    return next((t for t in tables(c) if t["name"] == name), None)


def roll(t, rng=random):
    """Roll the table's die. Returns (number, the row's words or None).
    The shared dice module rolls the dice it knows; any other size is rolled here."""
    sides = t["die"]
    n = dice.roll(1, sides, rng)[0] if sides in dice.SIDES else rng.randint(1, sides)
    hit = next((r for r in t["rows"] if r["lo"] <= n <= r["hi"]), None)
    return n, (hit["text"] if hit else None)


def roll_line(c, t, n, text):
    """The session log's line for a roll, with the in-world day."""
    return "Day %d. %s table, rolled %d: %s" % (c["calendar"]["day"], t["name"], n,
                                                 text or "that row is empty in the file.")


def record_roll(c, t, n, text):
    """The dragon's table also keeps where it is now, in the file's own slot."""
    if t.get("dragon") and isinstance(c.get("dragon"), dict):
        c["dragon"]["last_roll"], c["dragon"]["current_location"] = n, text


# ---------------------------------------------------------------- three numbers from a page
SIGN = r"[+\-−–]"
AC_RES = [re.compile(r"\bArmou?r\s+Class\b\s*:?\s*(\d{1,2})\b", re.I), re.compile(r"\bAC\b\s*:?\s*(\d{1,2})\b")]
HP_RES = [re.compile(r"\bHit\s+Points\b\s*:?\s*(\d{1,4})\b", re.I), re.compile(r"\bHP\b\s*:?\s*(\d{1,4})\b")]
DEX_RES = [re.compile(r"\bSTR\s+DEX\s+CON\s+INT\s+WIS\s+CHA\s+\d{1,2}\s*\(\s*%s?\s*\d+\s*\)\s*(\d{1,2})\b" % SIGN),
           re.compile(r"\bDEX(?:TERITY)?\b\s*:?\s*(\d{1,2})\b", re.I)]
INIT_RE = re.compile(r"\bInitiative\b\s*:?\s*(%s)\s*(\d{1,2})\b" % SIGN, re.I)


def _first(patterns, text, low, high):
    for p in patterns:
        m = p.search(text)
        if m and low <= int(m.group(1)) <= high:
            return int(m.group(1))
    return None


def stat_guess(text):
    """Armour Class, hit points and the initiative bonus, if the excerpt states
    them in the usual way. Anything not found is None: the DM types it."""
    text = text or ""
    dex = _first(DEX_RES, text, 1, 30)
    bonus = None if dex is None else (dex - 10) // 2
    m = INIT_RE.search(text)
    if m:
        bonus = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
    return {"ac": _first(AC_RES, text, 1, 40), "hp": _first(HP_RES, text, 1, 9999), "dex": dex, "bonus": bonus}


def stat_excerpt(body, name, span=1500):
    """The stretch of a page that starts at the monster's name: the mention
    that an Armour Class or hit points follows most closely (a page may hold
    several creatures), else the first mention, else the top of the page.
    White space is squeezed."""
    body = body or ""
    starts = [m.start() for m in re.finditer(re.escape(name.strip()), body, re.I)] if name.strip() else []

    def gap(i):
        found = [m.start() for m in (p.search(body, i, i + span) for p in AC_RES + HP_RES) if m]
        return min(found) - i if found else span + 1
    best = min(starts, key=lambda i: (gap(i), i)) if starts else 0
    return " ".join(body[best:best + span].split())
