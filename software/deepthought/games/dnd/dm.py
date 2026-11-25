"""DM mode: the campaign file, tonight's prep, the recap, people, quests, the
fight loader and book search. Improvise, the calendar, treasure, roll tables
and the monster pages are in dmtools.py. Everything here is behind the DM code and
shows 'DM only' in the strip. Nothing here is ever sent to a phone or the
scoreboard, and none of it is read aloud unless the DM asks."""
import re
import datetime
import json
import os
import shutil

from ... import paths, settings
from ... import theme as T
from ...screens.common import BOTTOM_H, BOTTOM_Y, Choice, Pages, TextEntry
from ...widgets import Button, row
from . import dmdata, party, rules
from .plugin import AddCombatant, DndBase
from .ui import HINT_Y, PER_PAGE, NumberPad, Row, lines, pages_for, row_rect

STATUSES = ["not posted", "posted", "taken", "done"]
ATTITUDES = [None, "friendly", "wary", "hostile"]


# ---------------------------------------------------------------- the campaign file
def folder():
    return paths.data("campaigns")


def files():
    """Campaign files on the box. The ones shipped with the program are copied
    in the first time, so the DM's notes never touch the originals."""
    here = folder()
    found = sorted(n for n in os.listdir(here) if n.endswith(".json"))
    if not found:
        shipped = os.path.join(paths.SOFTWARE, "campaigns")
        if os.path.isdir(shipped):
            for n in sorted(os.listdir(shipped)):
                if n.endswith(".json"):
                    shutil.copyfile(os.path.join(shipped, n), os.path.join(here, n))
        found = sorted(n for n in os.listdir(here) if n.endswith(".json"))
    return found


def current():
    """File name of the campaign in use, or None."""
    found = files()
    name = settings.get("dnd_campaign")
    return name if name in found else (found[0] if found else None)


def load(name):
    try:
        with open(os.path.join(folder(), name), encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError, TypeError, RecursionError):      # RecursionError: brackets nested beyond reading
        return None
    if not isinstance(c, dict):
        return None
    return dmdata.tidy(tidy(c))


def _text(x):
    """Words from the file, as written. Only the type is mended: a number
    becomes its digits, and what is not words at all becomes nothing. Nothing
    is cut or re-flowed here; the screens do that as they draw."""
    if isinstance(x, str):
        return x
    return str(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else ""


def _whole(x, default=None):
    """A whole number from the file; '3' and 3.0 count. The value is never
    changed, only its type: what is not a whole number gives the default."""
    if isinstance(x, bool):
        return default
    if isinstance(x, float):
        try:                                      # 1e999 reads as infinity, and NaN is a number to JSON:
            x = int(x) if x == int(x) else x      # neither is a whole number
        except (OverflowError, ValueError):
            return default
    if isinstance(x, str) and re.fullmatch(r"\s*-?[0-9]{1,9}\s*", x):
        x = int(x)
    return x if isinstance(x, int) else default


def tidy(c):
    """Make every part of the file the screens read the shape they expect. The
    file is edited by hand, and a slip of the hand must never take the desk
    down: a bare name becomes an entry, a number typed as words becomes a
    number, and what cannot be read as anything is left out. A value that can
    be read is never shortened or corrected: the file is the DM's own."""
    for key in ("people", "quests", "sessions", "session_outline", "prep_checklist"):
        if not isinstance(c.get(key), list):
            c[key] = []
    if c.get("campaign") is not None:
        c["campaign"] = _text(c["campaign"])
    for key in ("source_book", "note"):
        if key in c:
            c[key] = _text(c[key])
    people = []
    for p in c["people"]:
        if isinstance(p, str) and p.strip():
            p = {"name": p}
        if not isinstance(p, dict):
            continue
        p["name"] = _text(p.get("name")) if _text(p.get("name")).strip() else "?"
        for key in ("where", "role", "your_note", "note"):
            if key in p or key in ("where", "role"):
                p[key] = _text(p.get(key))
        if isinstance(p.get("met"), (dict, list)):
            p["met"] = False
        p.setdefault("met", False)
        if not isinstance(p.get("attitude"), str):
            p["attitude"] = None
        people.append(p)
    c["people"] = people
    quests = []
    for q in c["quests"]:
        if isinstance(q, str) and q.strip():
            q = {"name": q}
        if not isinstance(q, dict):
            continue
        q["name"] = _text(q.get("name")) if _text(q.get("name")).strip() else "?"
        q["status"] = _text(q.get("status")) or STATUSES[0]
        for key in ("kind", "watch_for", "box_setup", "your_notes"):
            q[key] = _text(q.get(key))
        q["tier"] = _whole(q.get("tier")) if q.get("tier") is not None else None
        quests.append(q)
    c["quests"] = quests
    pos = c.get("position") if isinstance(c.get("position"), dict) else {}
    pos["quest"] = _text(pos.get("quest")) or None
    pos["booklet_page"] = _whole(pos.get("booklet_page"))
    c["position"] = pos
    lev = c.get("levelling") if isinstance(c.get("levelling"), dict) else {}
    lev["party_level"] = _whole(lev.get("party_level"), 1)
    if "method" in lev:
        lev["method"] = _text(lev["method"])
    c["levelling"] = lev
    sessions = []
    for e in c["sessions"]:
        if isinstance(e, dict):
            n = _whole(e.get("n"))
            if n is None:
                e.pop("n", None)
            else:
                e["n"] = n
            if "date" in e:
                e["date"] = _text(e["date"])
            if "started" in e and not isinstance(e["started"], str):
                e.pop("started")
            sessions.append(e)
        elif isinstance(e, str):
            sessions.append(e)
    c["sessions"] = sessions
    outline = []
    for o in c["session_outline"]:
        if isinstance(o, dict):
            prep = o.get("prep")
            prep = prep if isinstance(prep, list) else [prep]
            o["n"], o["title"], o["prep"] = _whole(o.get("n")), _text(o.get("title")), [_text(x) for x in prep if _text(x)]
            outline.append(o)
        elif isinstance(o, str):
            outline.append(o)                     # a bare line: no screen reads it, and it is the DM's to keep
    c["session_outline"] = outline
    c["prep_checklist"] = [_text(x) or "?" for x in c["prep_checklist"]]
    fights = []
    for f in c.get("fights") if isinstance(c.get("fights"), list) else []:
        if not isinstance(f, dict) or not isinstance(f.get("enemies"), list):
            continue
        enemies = []
        for e in f["enemies"]:
            if isinstance(e, str) and e.strip():
                e = {"name": e}
            if not isinstance(e, dict) or not _text(e.get("name")).strip():
                continue
            e["name"], e["count"] = _text(e["name"]), _whole(e.get("count"), 1)
            e["hp"] = _whole(e.get("hp"))
            for key in ("ac", "init_bonus"):
                if key in e:
                    e[key] = _whole(e[key])
                    if e[key] is None:
                        del e[key]
            enemies.append(e)
        if enemies:
            f["name"], f["enemies"] = _text(f.get("name")) or "unnamed", enemies
            fights.append(f)
    if "fights" in c or fights:
        c["fights"] = fights
    return c


def save(c, name):
    path = os.path.join(folder(), name)
    tmp = path + ".tmp"
    text = paths.json_text(c, indent=1, ensure_ascii=False)       # before the file is opened: a value that
    with open(tmp, "w", encoding="utf-8") as f:                   # cannot be written must not leave half a file
        f.write(text)
    os.replace(tmp, path)


def entry_lines(entry):
    """A session log entry as a list of lines, whatever shape the DM gave it."""
    if isinstance(entry, str):
        return [entry] if entry.strip() else []
    if not isinstance(entry, dict):
        return []
    got = entry.get("lines")
    if isinstance(got, dict):                     # lines typed as {"1": "...", "2": "..."}
        got = list(got.values())
    if isinstance(got, str) and got.strip():      # lines typed as one string
        return [x.strip() for x in got.split("\n") if x.strip()]
    if isinstance(got, list):
        return [str(x) for x in got if str(x).strip()]
    for key in ("summary", "log", "notes", "text"):
        if entry.get(key):
            return [x.strip() for x in str(entry[key]).split("\n") if x.strip()]
    return []


def tonight_index(c, started):
    """Tonight's log entry. First the one this game made tonight: same game,
    dated today or yesterday (a night that runs past midnight is still one
    night), or not dated at all. Failing that, the one with today's date: there
    is one entry to a calendar date, however many games are started that day.
    The same game picked up again on a later date gets a new entry."""
    today = datetime.date.today()
    near = (today.isoformat(), (today - datetime.timedelta(days=1)).isoformat())
    mine = [i for i, e in enumerate(c["sessions"])
            if isinstance(e, dict) and started and e.get("started") == started and (not e.get("date") or e.get("date") in near)]
    if mine:
        return mine[-1]
    for i, e in enumerate(c["sessions"]):
        if isinstance(e, dict) and e.get("date") == near[0]:
            return i
    return None


def last_index(c, started):
    """The newest log entry that is not tonight's, or None. One with something
    written in it if there is one: an empty entry is no use as 'last time'."""
    t = tonight_index(c, started)
    older = [i for i in range(len(c["sessions"])) if i != t]
    written = [i for i in older if entry_lines(c["sessions"][i])]
    return (written or older)[-1] if older else None


def _blank(e):
    """An entry the box made and nothing was ever written in: its lines are an
    empty list (or missing) and it holds nothing else. An entry whose lines
    are some other shape is the DM's own typing, and is never thrown away."""
    return (isinstance(e, dict) and e.get("lines") in (None, []) and not entry_lines(e)
            and set(e) <= {"n", "date", "started", "lines"})


def tonight_entry(c, started):
    """Tonight's log entry as a dict with 'lines', made if there is none yet.
    Only called when something is about to be written: a night with nothing
    logged leaves no entry and is not counted as a session."""
    i = tonight_index(c, started)
    if i is None:
        c["sessions"][:] = [e for e in c["sessions"] if not _blank(e)]      # empty ones left by earlier nights
        e = {"n": session_number(c, started), "date": datetime.date.today().isoformat(), "started": started, "lines": []}
        c["sessions"].append(e)
        return e
    e = c["sessions"][i]
    e["lines"] = entry_lines(e)
    if not e["lines"]:
        e["n"] = session_number(c, started)       # an empty entry was never a session: it takes tonight's number
    return e


def log_line(c, started, text):
    """Add a line to tonight's log entry, making the entry if there is none yet."""
    e = tonight_entry(c, started)
    e["lines"].append(text)
    return e


def session_number(c, started):
    """Tonight's session number: one more than the sessions with something
    logged. Entries with no lines do not count."""
    t = tonight_index(c, started)
    if t is not None and entry_lines(c["sessions"][t]) and isinstance(c["sessions"][t].get("n"), int) and c["sessions"][t]["n"]:
        return c["sessions"][t]["n"]
    written = [e for i, e in enumerate(c["sessions"]) if i != t and entry_lines(e)]
    if not written:
        return 1
    return max((e.get("n") if isinstance(e, dict) and isinstance(e.get("n"), int) else k + 1)
               for k, e in enumerate(written)) + 1


# A roll on a DM table (where the dragon is) is kept in the log for the DM, but
# the recap is read to the whole table, so it leaves those lines out.
SECRET_LINE = re.compile(r"^Day \d+\. .+ table, rolled \d+:")


def recap(c, started):
    """(heading, text) built from the last log entry."""
    last = last_index(c, started)
    if last is None:
        return "No log yet", "Nothing has been logged for this campaign. Add a few lines under Log tonight, and next time there will be a recap here."
    e = c["sessions"][last]
    n = e.get("n") if isinstance(e, dict) and e.get("n") else last + 1
    when = " (%s)" % e["date"] if isinstance(e, dict) and e.get("date") else ""
    got = [line for line in entry_lines(e) if not SECRET_LINE.match(line)]
    return "Last time: session %s%s" % (n, when), "\n".join(got) if got else "That session's entry is empty."


def level_due(c):
    """Characters in the party below the level the campaign file says they should be."""
    want = c["levelling"].get("party_level") or 1
    return [(n, sheet) for n, sheet in party.party() if (party.numbers(sheet) or {}).get("level", 99) < want]


def open_desk(app, session):
    """Open the DM desk, asking for the code first if DM mode is locked."""
    if app.dm:
        app.push(Desk(app, session))
        return

    def done(text):
        if text.replace(" ", "") == str(settings.get("dm_code")):
            app.dm = True
            app.say("DM mode unlocked. Players, look away.")
            app.push(Desk(app, session))
        else:
            app.say("That is not the code.")
            app.screen.refresh()
    app.push(TextEntry(app, "DM code", "", done, "Unlock", max_len=8))


# ---------------------------------------------------------------- screens
class DmBase(DndBase):
    """A DM-only screen. If DM mode is locked it shows nothing but a way out."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self.name = current()
        self.camp = load(self.name) if self.name else None

    def ok(self):
        return bool(self.app.dm and self.camp)

    def reload(self):
        self.name = current()
        self.camp = load(self.name) if self.name else None

    def store(self):
        save(self.camp, self.name)

    def tell(self, words, **_):
        """A line for the DM: on the box only. Never read to the table, never on the scoreboard page."""
        self.app.say(words, private=True)

    def back_only(self):
        return row([("Back", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def locked(self, surf):
        if self.app.dm and self.name:                 # a file is there, and it will not read: say which, and where
            from .dmtools import file_words, hard_wrap
            T.draw_text(surf, "I cannot read the campaign file.", "head5", 28, T.TEXT, (20, 76), max_w=760)
            y = lines(surf, "It is not the file it should be: a comma or a bracket lost in a hand edit will do that. "
                      "Mend it on a computer. I have changed nothing in it, and shall not until it reads.",
                      20, 124, 760, 4, T.DIM, size=24, pitch=30)
            for line in hard_wrap(file_words(self.name), "text", 22, 760)[:3]:
                T.draw_text(surf, line, "text", 22, T.TEXT, (20, y + 10))
                y += 28
            return
        words = "This is the DM's desk, and it is locked." if not self.app.dm else "There is no campaign file on the box."
        T.draw_text(surf, words, "head5", 28, T.TEXT, (T.W // 2, 200), "center", max_w=760)

    @property
    def started(self):
        return self.session.d.get("started")


class Desk(DmBase):
    """The campaign at a glance. Two pages of tiles: the session, then the tools."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self.tools = False

    @property
    def heading(self):
        return "Session %d" % session_number(self.camp, self.started) if self.ok() else "DM desk"

    def enter(self):
        self.reload()                             # reading only: opening the desk never writes the campaign file
        super().enter()

    def draw_body(self, surf):
        if not self.ok():
            self.locked(surf)

    def build(self):
        if not self.ok():
            return self.back_only()
        c, s = self.camp, self.state
        page = c["position"].get("booklet_page")
        out = [Button((20, 68, 500, 64), c.get("campaign") or self.name, self.campaign, size=22),
               Button((530, 68, 250, 64), "Page %s" % (page if page else "–"), self.set_page, size=22)]
        met = sum(1 for p in c["people"] if p.get("met"))
        t = tonight_index(c, self.started)
        logged = len(entry_lines(c["sessions"][t])) if t is not None else 0
        n_prep = len(rules.PREP) + len(c["prep_checklist"][len(rules.PREP):len(rules.PREP) + 1])
        tiles = [("Recap", "Last session", self.recap),
                 ("Prep", "%d of %d done" % (sum(1 for x in s["prep"][:n_prep] if x), n_prep), self.prep),
                 ("Fights", "Load enemies", self.fights),
                 ("People", "%d known, %d met" % (len(c["people"]), met), self.people),
                 ("Quests", "Now: %s" % (c["position"].get("quest") or "not set"), self.quests),
                 ("Log", "%d line%s tonight" % (logged, "" if logged == 1 else "s"), self.log)]
        if self.tools:
            tabs = dmdata.tables(c)
            if not tabs:
                tab_sub = "None in the file"
            elif len(tabs) == 1:
                tab_sub = "%s: %s" % (tabs[0]["name"], "d%d" % tabs[0]["die"] if tabs[0]["rows"] else "not copied in")
            else:
                tab_sub = "%d to roll on" % len(tabs)
            n_items = len(c["treasure"])
            tiles = [("Improvise", "Make one up", self.improvise),
                     ("Calendar", "Day %d" % c["calendar"]["day"], self.calendar),
                     ("Treasure", "%d item%s" % (n_items, "" if n_items == 1 else "s"), self.treasure),
                     ("Tables", tab_sub, self.tables)]
        for i, (name, sub, act) in enumerate(tiles):
            out.append(Button((20 + (i % 3) * 257, 142 + (i // 3) * 124, 247, 118), name, act, "tile", sub))
        spec = [("Back to the fight", self.app.pop, 1.9, "primary"),
                ("More %d/2" % (2 if self.tools else 1), self.flip, 1, "plain"), ("Book search", self.search, 1.3, "plain")]
        if level_due(c):
            spec.append(("Level up", self.level_up, 1, "plain"))
        spec.append(("Lock", self.lock, 0.8, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def flip(self):
        self.tools = not self.tools
        self.refresh()

    def improvise(self):
        from .dmtools import Improvise
        self.app.push(Improvise(self.app, self.session))

    def calendar(self):
        from .dmtools import Calendar
        self.app.push(Calendar(self.app, self.session))

    def treasure(self):
        from .dmtools import Treasure
        self.app.push(Treasure(self.app, self.session))

    def tables(self):
        from .dmtools import RollTable, Tables
        tabs = dmdata.tables(self.camp)
        if len(tabs) == 1:                        # one table: straight to it
            return self.app.push(RollTable(self.app, self.session, tabs[0]["name"]))
        self.app.push(Tables(self.app, self.session))

    def campaign(self):
        found = files()
        if len(found) > 1:
            settings.put("dnd_campaign", found[(found.index(self.name) + 1) % len(found)])
            self.reload()
            return self.refresh()
        c = self.camp
        lev = c["levelling"]
        steps = [(c.get("campaign") or self.name, "%s\n\n%s" % (c.get("source_book", ""), c.get("note", ""))),
                 ("Levelling", "Party level in this file: %s.\n\n%s" % (lev.get("party_level", 1), lev.get("method", "")))]
        self.app.push(Pages(self.app, "D&D · DM only", "Campaign", steps, note="DM only", speak=False))

    def set_page(self):
        def then(n):
            self.reload()
            self.camp["position"]["booklet_page"] = n
            self.store()
            self.refresh()
        self.app.push(NumberPad(self.app, "Page", then, "The page of your book you stopped on. Only the number is kept.",
                                low=1, high=999, left=self.left))

    def recap(self):
        c = self.camp
        head, text = recap(c, self.started)
        steps = [(head, text)]
        n = session_number(c, self.started)
        outline = next((o for o in c["session_outline"] if isinstance(o, dict) and o.get("n") == n), None)
        if outline:
            steps.append(("Tonight, by the outline: %s" % outline.get("title", ""),
                          "\n".join(str(x) for x in outline.get("prep", []))))
        # Read aloud is a button on the page: nothing here is spoken unless the DM presses it.
        self.app.push(Pages(self.app, "D&D · DM only", "Recap", steps, note="DM only. Correct it under Log first."))

    def prep(self):
        self.app.push(Prep(self.app, self.session))

    def fights(self):
        self.app.push(FightLoader(self.app, self.session))

    def people(self):
        self.app.push(People(self.app, self.session))

    def quests(self):
        self.app.push(Quests(self.app, self.session))

    def log(self):
        self.app.push(Log(self.app, self.session))

    def search(self):
        from ...screens.lookup import Lookup
        self.app.push(Lookup(self.app, "dnd"))      # Lookup searches with dm=app.dm, so campaign pages show

    def level_up(self):
        due = level_due(self.camp)
        if due:
            from .sheets import LevelUp
            self.app.push(LevelUp(self.app, self.session, due[0][0]))

    def lock(self):
        self.app.dm = False
        self.app.pop()
        self.app.say("DM mode locked.")


class Prep(DmBase):
    """Seven steps before the session, the same every time. Ticks last one session."""
    heading = "Prep"

    def steps(self):
        return rules.PREP + [str(x) for x in self.camp["prep_checklist"][len(rules.PREP):len(rules.PREP) + 1]]

    def build(self):
        if not self.ok():
            return self.back_only()
        out = []
        for i, step in enumerate(self.steps()):
            rect = (20 + (i // 4) * 385, 68 + (i % 4) * 74, 375, 68)
            out.append(Row(rect, step, lambda i=i: self.do(ev="prep", i=i), tick=bool(self.state["prep"][i])))
        return out + self.back_only()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        T.draw_text(surf, "Ticks last for tonight only. A new session starts with none.", "text", 22, T.DIM,
                    (20, HINT_Y), "midleft", max_w=760)


class People(DmBase):
    """Everyone the party might meet. One line each."""
    heading = "People"

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = 0

    def enter(self):
        self.reload()
        super().enter()

    def build(self):
        if not self.ok():
            return self.back_only()
        folk, out = self.camp["people"], []
        n_pages = pages_for(len(folk))
        self.page = min(self.page, n_pages - 1)
        for i, p in enumerate(folk[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            k = self.page * PER_PAGE + i
            tags = (["Met"] if p.get("met") else []) + ([p["attitude"].capitalize()] if p.get("attitude") else [])
            tags += ["Invented"] if p.get("invented") else []
            out.append(Row(row_rect(i), str(p.get("name", "?")), lambda k=k: self.open(k), right=str(p.get("where", "")),
                           tags=tags))
        spec = [("Back", self.app.pop, 1, "primary")]
        if n_pages > 1:
            spec.append(("List %d/%d" % (self.page + 1, n_pages), self.more_rows, 1, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(self.camp["people"]))
        self.refresh()

    def open(self, k):
        self.app.push(Person(self.app, self.session, k))

    def primary(self):
        if self.ok() and pages_for(len(self.camp["people"])) > 1:
            self.more_rows()
        else:
            self.app.pop()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not self.camp["people"]:
            T.draw_text(surf, "Nobody in the file yet.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")
        T.draw_text(surf, "Tap a name for your note on them.", "text", 22, T.DIM, (20, HINT_Y), "midleft")


class Person(DmBase):
    def __init__(self, app, session, k):
        super().__init__(app, session)
        self.k = k

    heading = "Person"

    def p(self):
        return self.camp["people"][self.k] if self.ok() and self.k < len(self.camp["people"]) else None

    def build(self):
        p = self.p()
        if not p:
            return self.back_only()
        out = [Button((20, 276, 375, 64), "Met: %s" % ("yes" if p.get("met") else "not yet"), self.met, size=22),
               Button((405, 276, 375, 64), "Attitude: %s" % (p.get("attitude") or "unknown"), self.attitude, size=22)]
        return out + row([("Back", self.app.pop, 1, "primary"), ("Change note", self.note, 1, "plain")], BOTTOM_Y, BOTTOM_H)

    def change(self, **kw):
        self.reload()
        p = self.p()
        if p:
            p.update(kw)
            self.store()
        self.refresh()

    def met(self):
        self.change(met=not self.p().get("met"))

    def attitude(self):
        now = self.p().get("attitude")
        i = ATTITUDES.index(now) if now in ATTITUDES else 0
        self.change(attitude=ATTITUDES[(i + 1) % len(ATTITUDES)])

    def note(self):
        self.app.push(TextEntry(self.app, "Your note", "", lambda t: self.change(your_note=t.capitalize()), "Done", max_len=60))

    def draw_body(self, surf):
        p = self.p()
        if not p:
            return self.locked(surf)
        T.draw_text(surf, str(p.get("name", "?")), "head", 36, T.TEXT, (20, 72), max_w=760)
        T.draw_text(surf, str(p.get("where", "")), "text", 22, T.DIM, (20, 120), max_w=760)
        y = lines(surf, str(p.get("role", "")), 20, 152, 760, 2, size=24, pitch=30)
        note = p.get("your_note") or p.get("note") or ""
        lines(surf, "Your note: %s" % (note or "none yet. One line is enough."), 20, y + 6, 760, 2, T.DIM)


class Quests(DmBase):
    heading = "Quests"

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = 0

    def enter(self):
        self.reload()
        super().enter()

    def build(self):
        if not self.ok():
            return self.back_only()
        quests, out = self.camp["quests"], []
        n_pages = pages_for(len(quests))
        self.page = min(self.page, n_pages - 1)
        now = self.camp["position"].get("quest")
        for i, q in enumerate(quests[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            k = self.page * PER_PAGE + i
            tags = (["Tonight"] if q.get("name") == now else []) + (["Tier %s" % q["tier"]] if q.get("tier") else [])
            out.append(Row(row_rect(i), str(q.get("name", "?")), lambda k=k: self.open(k), right=str(q.get("status", "")),
                           tags=tags, selected=q.get("name") == now))
        spec = [("Back", self.app.pop, 1, "primary"),
                ("Party level %s" % (self.camp["levelling"].get("party_level") or 1), self.level, 1.4, "plain")]
        if n_pages > 1:
            spec.append(("List %d/%d" % (self.page + 1, n_pages), self.more_rows, 1, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(self.camp["quests"]))
        self.refresh()

    def open(self, k):
        self.app.push(Quest(self.app, self.session, k))

    def level(self):
        now = self.camp["levelling"].get("party_level") or 1
        if now >= 20:
            return self.tell("Level 20 is as far as it goes.")

        def up():
            self.reload()
            self.camp["levelling"]["party_level"] = now + 1
            self.store()
            self.tell("The file says level %d. The desk now offers Level up for each character in turn." % (now + 1))
            self.refresh()
        self.app.push(Choice(self.app, "Level the party?", "Has the party earned level %d?\nYour book's own table decides; "
                             "I only keep the number." % (now + 1), [("Not yet", None), ("Level %d" % (now + 1), up)],
                             left="D&D · DM only"))

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not self.camp["quests"]:
            T.draw_text(surf, "No quests in the file yet.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")
        T.draw_text(surf, "Tap a quest for your notes on it, and to make it tonight's.", "text", 22, T.DIM,
                    (20, HINT_Y), "midleft", max_w=760)


class Quest(DmBase):
    heading = "Quest"

    def __init__(self, app, session, k):
        super().__init__(app, session)
        self.k = k

    def q(self):
        return self.camp["quests"][self.k] if self.ok() and self.k < len(self.camp["quests"]) else None

    def build(self):
        q = self.q()
        if not q:
            return self.back_only()
        tonight = self.camp["position"].get("quest") == q.get("name")
        out = [Button((20, 316, 375, 64), "Status: %s" % q.get("status", "?"), self.status, size=22),
               Button((405, 316, 375, 64), "Tonight's quest: yes" if tonight else "Make it tonight's quest", self.tonight, size=22)]
        return out + self.back_only()

    def status(self):
        self.reload()
        q = self.q()
        order = STATUSES if q.get("status") in STATUSES else [q.get("status")] + STATUSES
        q["status"] = order[(order.index(q.get("status")) + 1) % len(order)]
        self.store()
        self.refresh()

    def tonight(self):
        self.reload()
        q = self.q()
        same = self.camp["position"].get("quest") == q.get("name")
        self.camp["position"]["quest"] = None if same else q.get("name")
        self.store()
        self.refresh()

    def draw_body(self, surf):
        q = self.q()
        if not q:
            return self.locked(surf)
        T.draw_text(surf, str(q.get("name", "?")), "head", 36, T.TEXT, (20, 70), max_w=760)
        sub = "  ·  ".join(x for x in (str(q.get("kind", "")), "Tier %s" % q["tier"] if q.get("tier") else "") if x)
        T.draw_text(surf, sub, "text", 22, T.DIM, (20, 116), max_w=760)
        y = lines(surf, "Watch for: %s" % (q.get("watch_for") or "nothing noted."), 20, 150, 760, 3)
        y = lines(surf, "On the box: %s" % (q.get("box_setup") or "nothing to set up."), 20, y + 6, 760, 2, T.DIM)
        if q.get("your_notes") and y < 286:
            lines(surf, "Your notes: %s" % q["your_notes"], 20, y + 6, 760, 1, T.DIM)


class FightLoader(DmBase):
    """Line up named enemies before the players reach them. They go into the
    tracker with no initiative yet, hidden unless the DM says otherwise.
    When the loaded books have a page for the name, the DM is shown it and
    takes the numbers from there; with no such page it is done by hand."""
    heading = "Load a fight"
    LIMIT = 4

    def __init__(self, app, session):
        super().__init__(app, session)
        self.draft, self.hidden, self.saved_i = [], True, -1

    def saved(self):
        got = self.camp.get("fights") if self.camp else None
        return [f for f in got if isinstance(f, dict) and f.get("enemies")] if isinstance(got, list) else []

    def total(self):
        return sum(e["count"] for e in self.draft)

    def build(self):
        if not self.ok():
            return self.back_only()
        out = []
        for i, e in enumerate(self.draft[:self.LIMIT]):
            right = "%d hit points each" % e["hp"] if e.get("hp") else "no hit points set"
            if e.get("ac") is not None or e.get("init_bonus") is not None:        # numbers taken from the DM's book
                right = " · ".join(x for x in ("HP %d" % e["hp"] if e.get("hp") else "",
                                                 "AC %d" % e["ac"] if e.get("ac") is not None else "",
                                                 "init %s" % party.signed(e["init_bonus"])
                                                 if e.get("init_bonus") is not None else "") if x)
            out.append(Row(row_rect(i), e["name"], lambda i=i: self.drop(i), num="%d×" % e["count"], right=right))
        spec = [("Load %d" % self.total() if self.draft else "Load", self.load_fight, 1.2, "primary"),
                ("Add enemy", self.add, 1.3, "plain"),
                ("Hidden: %s" % ("yes" if self.hidden else "no"), self.toggle, 1.3, "plain")]
        if self.saved():
            spec.append(("Saved %d" % len(self.saved()), self.next_saved, 1.1, "plain"))
        spec.append(("Back", self.app.pop, 0.8, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def drop(self, i):
        del self.draft[i]
        self.refresh()

    def toggle(self):
        self.hidden = not self.hidden
        self.refresh()

    def next_saved(self):
        saved = self.saved()
        self.saved_i = (self.saved_i + 1) % len(saved)
        self.draft = []
        for e in saved[self.saved_i]["enemies"][:self.LIMIT]:
            if isinstance(e, dict) and e.get("name"):
                hp = e.get("hp")
                self.draft.append({"name": str(e["name"])[:18], "count": max(1, min(rules.MAX_GROUP, int(e.get("count", 1)))),
                                   "hp": int(hp) if isinstance(hp, int) and hp > 0 else None})
                for key in ("ac", "init_bonus"):                   # the DM's own numbers, if he wrote them in
                    if isinstance(e.get(key), int) and not isinstance(e.get(key), bool):
                        self.draft[-1][key] = e[key]
        self.tell("Loaded your saved fight: %s." % saved[self.saved_i].get("name", "unnamed"))
        self.refresh()

    def add(self):
        if len(self.draft) >= self.LIMIT:
            return self.tell("Four kinds at a time. Load these, then come back for more.")
        self.app.push(AddCombatant(self.app, self.session, collect=self.collected))

    def collected(self, base, count, numbered):
        from .dmtools import MonsterBook, book_pages

        def put(hp, ac=None, bonus=None):
            e = {"name": base, "count": count, "hp": hp}
            if ac is not None:
                e["ac"] = ac
            if bonus is not None:
                e["init_bonus"] = bonus
            self.draft.append(e)
            self.refresh()
        found = book_pages(self.app, base)
        if found:                                 # the DM's own book has a page: show it, take the numbers from there
            return self.app.push(MonsterBook(self.app, self.session, base, count, found, put))
        if self.app.library.counts()[0]:
            self.tell("Nothing in your loaded books under %s. By hand, then." % base, speak=False)
        else:
            self.tell("No books are loaded, so %s is entered by hand." % base, speak=False)
        self.app.push(NumberPad(self.app, "Hit points each", put,
                                "DM only. The hit point maximum for %s, from your own book. I count down from it "
                                "and show it to nobody else." % base, low=1, high=9999,
                                skip=("No number", lambda: put(None)), left=self.left))

    def load_fight(self):
        if not self.draft:
            return self.tell("Add an enemy first. I cannot load an absence.")
        n = self.total()
        if self.do(ev="load", enemies=self.draft, hidden=self.hidden):
            self.app.pop()
            self.tell("%d loaded%s. Enter initiative when the fight begins."
                         % (n, ", hidden from the players" if self.hidden else ""))

    def primary(self):
        self.load_fight()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not self.draft:
            T.draw_text(surf, "Nobody lined up.", "head", 36, T.TEXT, (T.W // 2, 140), "center")
            lines(surf, "Add the enemies you expect tonight. Names and numbers only: their statistics stay in "
                  "your book, which Book search will open.", 60, 190, 680, 3, T.DIM, size=24, pitch=32)
        words = "Hidden enemies never reach the scoreboard or a phone."
        if self.draft:
            words = "Tap a line to take it out. Hidden ones reach no scoreboard or phone."
        T.draw_text(surf, words, "text", 22, T.DIM, (20, HINT_Y), "midleft", max_w=760)


class Log(DmBase):
    """A few lines about tonight, for next session's recap. Last time's can be corrected."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self.last = False                         # False: tonight's entry. True: the one before.

    @property
    def heading(self):
        return "Log: last time" if self.last else "Log: tonight"

    def index(self):
        return last_index(self.camp, self.started) if self.last else tonight_index(self.camp, self.started)

    def lines_now(self):
        i = self.index()
        return entry_lines(self.camp["sessions"][i]) if i is not None else []

    def build(self):
        if not self.ok():
            return self.back_only()
        out = []
        got = self.lines_now()
        for i, text in enumerate(got[-PER_PAGE:]):
            k = len(got) - len(got[-PER_PAGE:]) + i
            out.append(Row(row_rect(i), text, lambda k=k: self.remove(k)))
        spec = [("Back", self.app.pop, 0.8, "plain"), ("Add a line", self.add, 1.2, "primary")]
        if last_index(self.camp, self.started) is not None:
            spec.append(("Show tonight" if self.last else "Show last time", self.flip, 1.4, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def flip(self):
        self.last = not self.last
        self.refresh()

    def entry(self, make=False):
        """The entry being edited, as a dict with 'lines'."""
        i = self.index()
        if i is None:
            if not make or self.last:
                return None
            return tonight_entry(self.camp, self.started)
        if make and not self.last:
            return tonight_entry(self.camp, self.started)
        e = self.camp["sessions"][i]
        if not isinstance(e, dict):
            e = {"n": i + 1}
        e["lines"] = entry_lines(self.camp["sessions"][i])
        self.camp["sessions"][i] = e
        return e

    def add(self):
        def done(text):
            if text:
                self.reload()
                e = self.entry(make=True)
                if e is not None:
                    e["lines"].append(text[0].upper() + text[1:])
                    self.store()
            self.refresh()
        self.app.push(TextEntry(self.app, "What happened", "", done, "Add", max_len=60))

    def remove(self, k):
        """Ask first: there is no undo for the log."""
        got = self.lines_now()
        if not k < len(got):
            return
        text = got[k]

        def rm():
            self.reload()
            e = self.entry() if self.ok() else None
            if e and k < len(e["lines"]) and e["lines"][k] == text:
                del e["lines"][k]
                self.store()
            self.refresh()
        self.app.push(Choice(self.app, "Remove this line?", text, [("Keep it", None), ("Remove", rm)], left="D&D · DM only"))

    def primary(self):
        self.add()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not self.lines_now():
            T.draw_text(surf, "Nothing logged.", "head", 36, T.TEXT, (T.W // 2, 140), "center")
            lines(surf, "Three or four short lines are enough. Longer notes are easier from a phone or a keyboard.",
                  60, 190, 680, 3, T.DIM, size=24, pitch=32)
        T.draw_text(surf, "Tap a line to remove it. Next session's recap is built from these.", "text", 22, T.DIM,
                    (20, HINT_Y), "midleft", max_w=760)
