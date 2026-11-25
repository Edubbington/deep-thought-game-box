"""The character files on the box: data/characters/<name>.json.

All the arithmetic is in dt_characters.py. This is only the filing: which
sheets are in the party, which are waiting to be checked, and safe loading."""
import json
import os
import sys
import uuid

from ... import paths

if paths.SOFTWARE not in sys.path:
    sys.path.insert(0, paths.SOFTWARE)
import dt_characters as ch  # noqa: E402  (the tested module, kept where its tests expect it)

COIN_NAMES = [("pp", "Platinum"), ("gp", "Gold"), ("ep", "Electrum"), ("sp", "Silver"), ("cp", "Copper")]


def folder():
    return paths.data("characters")


def files():
    return sorted(n for n in os.listdir(folder()) if n.endswith(".json"))


def load(fname):
    """The character in that file, or None if it is missing or not a sheet."""
    if not fname:
        return None
    try:
        c = ch.load(os.path.join(folder(), fname))
    except (OSError, ValueError):
        return None
    if not isinstance(c, dict) or not isinstance(c.get("hp"), dict) or not isinstance(c.get("abilities"), dict):
        return None
    c.setdefault("classes", [])
    c.setdefault("equipment", [])
    c.setdefault("coins", {})
    for k, _ in COIN_NAMES:
        c["coins"].setdefault(k, 0)
    c["hp"].setdefault("temp", 0)
    return c


def save(c, fname=None):
    """Save with the tested module. The file is named after the character, so
    a sheet that arrived under another name is renamed. Returns the file name.
    Only the screen that checks an upload uses this; everything else uses
    write(), which never renames."""
    want = ch.slug(c["name"]) + ".json"
    if fname and fname != want and os.path.isfile(os.path.join(folder(), want)):
        return write(c, fname)                    # that name is another character's file: leave both where they are
    path = ch.save(c, folder())
    new = os.path.basename(path)
    if fname and fname != new and os.path.isfile(os.path.join(folder(), fname)):
        os.remove(os.path.join(folder(), fname))
    return new


def write(c, fname):
    """Save a sheet back to the file it came from. The file keeps its name
    whatever the character is called: a fight in progress, and its undo, point
    at that name. Returns the file name."""
    path = os.path.join(folder(), fname)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)                                 # never leaves a half-written sheet
    return fname


def stamp(c):
    """Give a sheet an id of its own if it has none, so it can be found again
    after it is renamed. True when one was added (the sheet then needs saving)."""
    if c.get("id"):
        return False
    c["id"] = uuid.uuid4().hex[:12]
    return True


def usable(c):
    """Enough numbers to put this character in a fight."""
    return bool(c and c.get("name") and c.get("classes")
                and all(isinstance(c["abilities"].get(a), int) for a in ch.ABILITIES)
                and isinstance(c["hp"].get("max"), int) and isinstance(c["hp"].get("current"), int))


def imported(c):
    return (c.get("ac_note") == "from the uploaded sheet"
            or any("Imported" in str(h.get("what", "")) for h in c.get("history", ())))


def needs_review(c):
    """An uploaded sheet nobody has checked yet. The box never trusts an upload."""
    if c.get("reviewed"):
        return False
    return bool(c.get("needs_review") or imported(c) or not usable(c))


def everyone():
    out = []
    for name in files():
        c = load(name)
        if c:
            out.append((name, c))
    return out


def party():
    """Checked, usable characters who are not sitting this one out."""
    return [(n, c) for n, c in everyone() if usable(c) and not needs_review(c) and not c.get("benched")]


def roster():
    """Everyone the Party screen lists: checked and usable, benched or not."""
    return [(n, c) for n, c in everyone() if usable(c) and not needs_review(c)]


def waiting():
    return [(n, c) for n, c in everyone() if needs_review(c)]


def numbers(c):
    """dt_characters.derived, or None for a sheet too broken to work out."""
    try:
        return ch.derived(c)
    except (TypeError, KeyError, ValueError):
        return None


def class_line(c):
    try:
        return " / ".join("%s %d" % (k["name"], k["level"]) for k in c["classes"])
    except (TypeError, KeyError):
        return ""


def coins_text(c):
    parts = ["%d %s" % (c["coins"].get(k, 0), name.lower()) for k, name in COIN_NAMES if c["coins"].get(k)]
    return ", ".join(parts) or "none"


def signed(n):
    return ("+%d" % n) if n >= 0 else ("−%d" % -n)
