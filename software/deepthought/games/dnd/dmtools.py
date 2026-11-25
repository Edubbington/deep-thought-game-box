"""More of the DM's desk: Improvise, the calendar, the party's treasure, roll
tables, and finding a monster in the DM's own loaded books.

All of it is behind the DM code, like the rest of dm.py. None of it is spoken
aloud: the lines she shows here are shown only."""
import copy
import os
import random
import threading

import pygame

from ... import paths
from ... import theme as T
from ...screens.common import BOTTOM_H, BOTTOM_Y, Choice, Pages, TextEntry
from ...widgets import Button, row
from . import dmdata, improv, party
from .dm import DmBase, folder, log_line
from .plugin import short
from .ui import HINT_Y, PER_PAGE, NumberPad, Row, lines, pages_for, panel, row_rect

DM_LEFT = "D&D · DM only"


def background(fn):
    """Run something that waits on the network off the screen's loop. The
    result must come back through app.later(). The tests swap this out."""
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t


def first_upper(text):
    return text[:1].upper() + text[1:]


def file_words(name):
    """The campaign file in use, as a path the owner can find: from the
    software folder when it is inside it."""
    path = os.path.join(folder(), name)
    try:
        rel = os.path.relpath(path, paths.SOFTWARE)
    except ValueError:                                # another drive
        return path
    return path if rel.startswith("..") else os.path.join("software", rel)


def hard_wrap(text, kind, size, max_w):
    """Wrap something with no spaces in it, such as a file path."""
    f, out, cur = T.font(kind, size), [], ""
    for ch in text:
        if cur and f.size(cur + ch)[0] > max_w:
            out.append(cur)
            cur = ""
        cur += ch
    return out + ([cur] if cur else [])


class ToolBase(DmBase):
    """A DM screen that changes the campaign file and can take its last
    change back. Double press = undo, as on the tracker: the button sends a
    press and then a double (see gestures.py), and the shell gives the double
    to the screen its press went to. So the double first takes back whatever
    that press did here, and then undoes the change before it. On a screen
    whose press is Back, the press has closed it and there is no double."""
    KEYS = ()                                         # the parts of the file this screen changes

    def __init__(self, app, session):
        super().__init__(app, session)
        self.undos = []
        self.n_changes = 0                            # counts every change made here (undos is capped)
        self._press_changed = False                   # the last press of the button changed the file

    def enter(self):
        self.reload()
        super().enter()

    def change(self, fn):
        """Read the file again, change it with fn(campaign), save, and remember
        how it was. fn may raise ValueError to refuse; then nothing is saved."""
        self.reload()
        if not self.ok():
            return False
        before = {k: copy.deepcopy(self.camp.get(k)) for k in self.KEYS}
        try:
            fn(self.camp)
        except ValueError as e:
            self.reload()
            self.tell(str(e))
            self.refresh()
            return False
        self.store()
        self.undos.append(before)
        self.n_changes += 1
        del self.undos[:-20]
        self.refresh()
        return True

    def undo_last(self):
        if not self.undos:
            self.tell("Nothing to undo here.")
            return False
        self.reload()
        if self.ok():
            self.camp.update(self.undos.pop())
            self.store()
            self.reload()
            self.tell("Undone.")
        self.refresh()
        return True

    def unpress(self):
        """Put back anything a press changed on the screen that is not in the file."""

    def on_button(self, gesture):
        if not self.ok():
            if gesture == "press":
                self.app.pop()                        # locked: the only thing the button does is leave
        elif gesture == "press":
            n = self.n_changes
            self.primary()
            self._press_changed = self.n_changes > n
        elif gesture == "double":
            if self._press_changed and self.undos:    # the press that came with this double: take it back first
                self.reload()
                if self.ok():
                    self.camp.update(self.undos.pop())
                    self.store()
            self._press_changed = False
            self.unpress()
            self.undo_last()                          # and then the undo that was asked for


# ---------------------------------------------------------------- improvise
class Improvise(ToolBase):
    """A name, a shop or a rumour, on the spot. Always marked as invented."""
    heading = "Improvise"
    KEYS = ("people", "calendar")

    def __init__(self, app, session, rng=None):
        super().__init__(app, session)
        self.rng = rng or random
        self.kind, self.kept, self.waiting, self.ticket = "name", False, False, 0
        self.item = improv.invent(self.kind, self.rng)

    def cloud(self):
        """The existing cloud path, or None when it is off, capped or has no key."""
        fn = getattr(getattr(self.app, "voice", None), "_llm", None)
        try:
            return fn() if fn else None
        except Exception:
            return None

    def build(self):
        if not self.ok():
            return self.back_only()
        out = [Button((20 + k * 190, 68, 180, 64), word, lambda kind=kind: self.set_kind(kind),
                      selected=kind == self.kind, size=22) for k, (kind, word) in enumerate(improv.KINDS)]
        spec = [("Back", self.app.pop, 0.8, "plain"), ("Kept" if self.kept else "Keep", self.keep, 0.9, "plain")]
        if self.cloud():
            spec.append(("Ask the cloud", self.ask_cloud, 1.4, "plain"))
        spec.append(("Another", self.another, 1.3, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def set_kind(self, kind):
        self.kind = kind
        self.another()

    def another(self):
        self.ticket += 1                              # an answer still on its way is no longer wanted
        self.waiting, self.kept = False, False
        self.item = improv.invent(self.kind, self.rng)
        self.refresh()

    def ask_cloud(self):
        llm = self.cloud()
        if not llm:
            return self.tell("The cloud is off. My own lists will have to do.")
        self.ticket += 1
        ticket, kind, self.waiting = self.ticket, self.kind, True
        self.refresh()

        def job():
            try:
                reply, err = llm(improv.SYSTEM, improv.request(kind)), ""
            except Exception as e:                    # network, key, cap: never a crash
                reply, err = "", str(e)
            self.app.later(lambda: self.arrived(ticket, kind, reply, err))
        background(job)

    def arrived(self, ticket, kind, reply, err=""):
        if ticket != self.ticket:
            return
        self.waiting, self.kept = False, False
        item = improv.from_cloud(kind, reply)
        if item is None:
            item = improv.invent(kind, self.rng)
            self.tell("%s This one is from my own lists." % (err or "The cloud sent nothing I could use."))
        self.item = item
        if self.app.screen is self:
            self.refresh()

    def keep(self):
        if self.waiting:
            return
        if self.kept:
            return self.tell("Already kept.")
        said = []
        if self.change(lambda c: said.append(improv.keep(c, self.item))):
            self.kept = True
            self.tell(said[0])
            self.refresh()

    def undo_last(self):
        if super().undo_last():
            self.kept = False
            self.refresh()

    def primary(self):
        self._shown = (self.item, self.kept)
        self.another()

    def unpress(self):
        if getattr(self, "_shown", None):
            self.ticket += 1
            (self.item, self.kept), self.waiting, self._shown = self._shown, False, None

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        box = panel(surf, (20, 142, 760, 216))
        tag = pygame.Rect(box.x + 16, box.y + 14, T.font("bold", 22).size("INVENTED")[0] + 24, 36)
        pygame.draw.rect(surf, T.TEXT, tag, 2, border_radius=8)       # a boxed word, not a colour
        T.draw_text(surf, "INVENTED", "bold", 22, T.TEXT, tag.center, "center")
        if self.waiting:
            T.draw_text(surf, "by the cloud model, when it answers", "text", 22, T.DIM, (tag.right + 14, tag.centery),
                        "midleft", max_w=box.right - tag.right - 30)
            T.draw_text(surf, "Asking the cloud.", "head", 34, T.TEXT, (box.x + 18, box.y + 62), max_w=724)
            lines(surf, "The network is not quick. Another gives you one from my own lists at once.", box.x + 18,
                  box.y + 116, 724, 2, T.DIM, size=24, pitch=30)
        else:
            T.draw_text(surf, improv.source_words(self.item), "text", 22, T.DIM, (tag.right + 14, tag.centery),
                        "midleft", max_w=box.right - tag.right - 30)
            T.draw_text(surf, self.item["title"], "head", 34, T.TEXT, (box.x + 18, box.y + 62), max_w=724)
            lines(surf, self.item["text"], box.x + 18, box.y + 116, 724, 3, size=24, pitch=30)
        where = "People" if self.kind == "name" else "the calendar's notes"
        words = "Kept, marked Invented. Double press takes it back." if self.kept else \
            "Not from any book. Keep saves it to %s." % where
        T.draw_text(surf, words, "text", 22, T.DIM, (20, HINT_Y), "midleft", max_w=760)


# ---------------------------------------------------------------- calendar
class Calendar(ToolBase):
    """The in-world day, and notes against days. The button is 'next day'."""
    heading = "Calendar"
    KEYS = ("calendar",)
    PER = 2

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = 0

    def build(self):
        if not self.ok():
            return self.back_only()
        notes = dmdata.notes_newest(self.camp)
        n_pages = pages_for(len(notes), self.PER)
        self.page = min(self.page, n_pages - 1)
        out = [Button((590, 68, 190, 64), "Name the date", self.name_date, size=22)]
        for k, (label, act) in enumerate([("Long rest", self.long_rest), ("+1 week", lambda: self.advance(7)),
                                          ("Add a note", self.add_note), ("Undo", self.undo_last)]):
            out.append(Button((20 + k * 192, 140, 184, 64), label, act, size=22))
        for i, (k, n) in enumerate(notes[self.page * self.PER:(self.page + 1) * self.PER]):
            out.append(Row(row_rect(i + 2), n["text"], lambda k=k: self.open(k), right="Day %d" % n["day"],
                           tags=["Invented"] if n.get("invented") else []))
        spec = [("Back", self.app.pop, 1, "plain")]
        if n_pages > 1:
            spec.append(("Notes %d/%d" % (self.page + 1, n_pages), self.more_rows, 1, "plain"))
        spec.append(("Next day", lambda: self.advance(1), 1.6, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(self.camp["calendar"]["notes"]), self.PER)
        self.refresh()

    def advance(self, days):
        if self.change(lambda c: dmdata.advance(c, days)):
            self.tell("%s. Double press takes it back." % dmdata.day_words(self.camp))

    def long_rest(self):
        def rest(c):
            dmdata.advance(c, 1)
            dmdata.add_note(c, "Long rest.")
        if self.change(rest):
            self.page = 0
            self.tell("Day %d, after a long rest. The tracker's Long rest button is what restores the party."
                      % self.camp["calendar"]["day"])
            self.refresh()

    def name_date(self):
        def done(text):
            self.change(lambda c: c["calendar"].update(date=first_upper(text)))
        self.app.push(TextEntry(self.app, "Named date", self.camp["calendar"]["date"].lower(), done, "Done", max_len=28))

    def add_note(self):
        def done(text):
            if text:
                self.page = 0
                self.change(lambda c: dmdata.add_note(c, first_upper(text)))
            else:
                self.refresh()
        self.app.push(TextEntry(self.app, "Note for day %d" % self.camp["calendar"]["day"], "", done, "Add", max_len=60))

    def open(self, k):
        notes = self.camp["calendar"]["notes"]
        if not k < len(notes):
            return
        note = notes[k]

        def remove():
            def rm(c):
                if k < len(c["calendar"]["notes"]) and c["calendar"]["notes"][k] == note:
                    del c["calendar"]["notes"][k]
            self.change(rm)
        self.app.push(Choice(self.app, "Note, day %d" % note["day"], note["text"],
                             [("Keep it", None), ("Remove", remove)], left=DM_LEFT))

    def primary(self):
        self.advance(1)

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        cal = self.camp["calendar"]
        r = T.draw_text(surf, "Day %d" % cal["day"], "head", 48, T.TEXT, (20, 100), "midleft", max_w=260)
        T.draw_text(surf, cal["date"] or "No named date", "text", 24, T.DIM, (r.right + 18, 104), "midleft",
                    max_w=570 - r.right - 18)
        if not cal["notes"]:
            T.draw_text(surf, "No notes yet.", "head5", 28, T.TEXT, (T.W // 2, 270), "center")
            words = "Press: next day. Double press: undo."
        else:
            words = "Tap a note to read or remove it. Press: next day. Double: undo."
        T.draw_text(surf, words, "text", 22, T.DIM, (20, HINT_Y), "midleft", max_w=760)


# ---------------------------------------------------------------- treasure
class Treasure(ToolBase):
    """What the party has found, and who is carrying it."""
    heading = "Treasure"
    KEYS = ("treasure",)

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = 0

    def build(self):
        if not self.ok():
            return self.back_only()
        items, out = self.camp["treasure"], []
        n_pages = pages_for(len(items))
        self.page = min(self.page, n_pages - 1)
        for i, it in enumerate(items[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            k = self.page * PER_PAGE + i
            out.append(Row(row_rect(i), it["name"], lambda k=k: self.open(k), right=dmdata.holder_words(it)))
        spec = [("Back", self.app.pop, 0.9, "plain"), ("Coins", self.coins, 1, "plain")]
        if n_pages > 1:
            spec.append(("List %d/%d" % (self.page + 1, n_pages), self.more_rows, 1, "plain"))
        spec.append(("Add item", self.add, 1.4, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(self.camp["treasure"]))
        self.refresh()

    def open(self, k):
        self.app.push(TreasureItem(self.app, self.session, k))

    def coins(self):
        self.app.push(PartyCoins(self.app, self.session))

    def add(self):
        def done(text):
            if text and self.change(lambda c: dmdata.add_item(c, first_upper(text))):
                self.page = pages_for(len(self.camp["treasure"])) - 1
            self.refresh()
        self.app.push(TextEntry(self.app, "Item found", "", done, "Add", max_len=30))

    def primary(self):
        self.add()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not self.camp["treasure"]:
            T.draw_text(surf, "No treasure yet.", "head", 36, T.TEXT, (T.W // 2, 140), "center")
            lines(surf, "Add what the party finds, by name. What an item does stays in your book.", 60, 190, 680, 3,
                  T.DIM, size=24, pitch=32)
        T.draw_text(surf, "Party coins: %s. Tap an item for who holds it." % dmdata.coins_words(self.camp), "text", 22,
                    T.DIM, (20, HINT_Y), "midleft", max_w=760)


class TreasureItem(ToolBase):
    heading = "Treasure item"
    KEYS = ("treasure",)

    def __init__(self, app, session, k):
        super().__init__(app, session)
        self.k = k

    def it(self):
        return self.camp["treasure"][self.k] if self.ok() and self.k < len(self.camp["treasure"]) else None

    def build(self):
        it = self.it()
        if not it:
            return self.back_only()
        out = [Button((20, 276, 470, 64), "Held by: %s" % (it.get("holder") or "the party"), self.pass_on, size=22),
               Button((500, 276, 280, 64), "Remove", self.remove, size=22)]
        return out + self.back_only()

    def pass_on(self):
        names = [sheet["name"] for _, sheet in party.roster()]

        def give(c):
            if self.k < len(c["treasure"]):
                c["treasure"][self.k]["holder"] = dmdata.next_holder(c["treasure"][self.k].get("holder"), names)
        if not names:
            return self.tell("There are no characters to hold it. It stays with the party.")
        self.change(give)

    def remove(self):
        it = self.it()

        def rm():
            self.reload()
            if self.ok() and self.k < len(self.camp["treasure"]) and self.camp["treasure"][self.k]["name"] == it["name"]:
                del self.camp["treasure"][self.k]
                self.store()
            self.app.pop()
            self.tell("%s is off the list." % it["name"])
        self.app.push(Choice(self.app, "Remove it?", "Take %s off the treasure list?\nThis cannot be undone." % it["name"],
                             [("Keep it", None), ("Remove", rm)], left=DM_LEFT))

    def draw_body(self, surf):
        it = self.it()
        if not it:
            return self.locked(surf) if not self.ok() else T.draw_text(
                surf, "That item is no longer on the list.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")
        T.draw_text(surf, it["name"], "head", 36, T.TEXT, (20, 72), max_w=760)
        T.draw_text(surf, "Found on day %d" % it["day"] if it.get("day") else "No day noted", "text", 22, T.DIM, (20, 120))
        lines(surf, "Tap Held by to pass it round the party. This is only the DM's list: it changes no character "
              "sheet.", 20, 160, 760, 3, T.DIM, size=24, pitch=32)


class PartyCoins(ToolBase):
    """The party's shared purse, one kind of coin at a time."""
    heading = "Party coins"
    KEYS = ("party_coins",)
    STEPS = (-100, -10, -1, 1, 10, 100)

    def __init__(self, app, session):
        super().__init__(app, session)
        self.coin = "gp"

    def build(self):
        if not self.ok():
            return self.back_only()
        out = [Button((20 + k * 154, 68, 144, 64), name, lambda coin=coin: self.pick(coin), selected=coin == self.coin,
                      size=22) for k, (coin, name) in enumerate(party.COIN_NAMES)]
        for k, n in enumerate(self.STEPS):
            out.append(Button((20 + k * 128, 250, 120, 64), party.signed(n), lambda n=n: self.step(n), size=26))
        return out + row([("Back", self.app.pop, 1.4, "primary"), ("Undo", self.undo_last, 1, "plain")], BOTTOM_Y, BOTTOM_H)

    def pick(self, coin):
        self.coin = coin
        self.refresh()

    def step(self, n):
        self.change(lambda c: dmdata.step_coin(c, self.coin, n))

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        coins = self.camp["party_coins"]
        for k, (coin, _) in enumerate(party.COIN_NAMES):
            T.draw_text(surf, str(coins[coin]), "head", 34, T.TEXT if coin == self.coin else T.DIM,
                        (20 + k * 154 + 72, 160), "center", max_w=140)
        T.draw_text(surf, "Changing %s: the party has %d." % (dmdata.coin_name(self.coin), coins[self.coin]), "mid", 24,
                    T.TEXT, (20, 218), "midleft", max_w=760)
        T.draw_text(surf, "The party's shared purse. Each character's own coins are on their sheet.", "text", 22, T.DIM,
                    (20, HINT_Y - 28), "midleft", max_w=760)
        T.draw_text(surf, "Undo takes the last step back. The button is Back.", "text", 22, T.DIM, (20, HINT_Y), "midleft",
                    max_w=760)


# ---------------------------------------------------------------- roll tables
def table_words(t):
    if not t["rows"]:
        return "not copied in yet"
    return "d%d, %d row%s" % (t["die"], len(t["rows"]), "" if len(t["rows"]) == 1 else "s")


class Tables(DmBase):
    """Every roll table the campaign file defines."""
    heading = "Tables"

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = 0

    def enter(self):
        self.reload()
        super().enter()

    def build(self):
        if not self.ok():
            return self.back_only()
        got, out = dmdata.tables(self.camp), []
        n_pages = pages_for(len(got))
        self.page = min(self.page, n_pages - 1)
        for i, t in enumerate(got[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            out.append(Row(row_rect(i), t["name"], lambda t=t: self.open(t["name"]), right=table_words(t)))
        spec = [("Back", self.app.pop, 1, "primary")]
        if n_pages > 1:
            spec.append(("List %d/%d" % (self.page + 1, n_pages), self.more_rows, 1, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(dmdata.tables(self.camp)))
        self.refresh()

    def open(self, name):
        self.app.push(RollTable(self.app, self.session, name))

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        if not dmdata.tables(self.camp):
            T.draw_text(surf, "No tables in this campaign file.", "head5", 28, T.TEXT, (T.W // 2, 130), "center")
            y = lines(surf, "Copy a table from your own book into the file yourself, under the field \"tables\". "
                      "I roll it; I do not write it.", 40, 170, 720, 3, T.DIM, size=24, pitch=32)
            for line in hard_wrap(file_words(self.name), "text", 22, 720)[:3]:
                T.draw_text(surf, line, "text", 22, T.TEXT, (40, y + 8))
                y += 28
        T.draw_text(surf, "Tap a table to roll on it.", "text", 22, T.DIM, (20, HINT_Y), "midleft")


class RollTable(ToolBase):
    """Roll on one table. The result is shown large and goes in tonight's
    log with the in-world day. The button rolls; double press takes it back."""
    KEYS = ("sessions", "dragon")

    def __init__(self, app, session, table_name, rng=None):
        super().__init__(app, session)
        self.table_name, self.rng, self.last = table_name, rng or random, None

    @property
    def heading(self):
        return "%s table" % short(self.table_name, 16) if self.ok() else "DM desk"

    def table(self):
        return dmdata.table(self.camp, self.table_name) if self.ok() else None

    def ready(self):
        t = self.table()
        return bool(t and t["rows"])

    def build(self):
        if not self.ready():
            return self.back_only()
        spec = [("Back", self.app.pop, 1, "plain")]
        if self.undos:
            spec.append(("Undo roll", self.undo_last, 1.1, "plain"))
        spec.append(("Roll d%d" % self.table()["die"], self.roll, 1.6, "primary"))
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def roll(self):
        self.reload()
        t = self.table()
        if not (t and t["rows"]):
            return self.refresh()
        n, text = dmdata.roll(t, self.rng)

        def write(c):
            log_line(c, self.started, dmdata.roll_line(c, t, n, text))
            dmdata.record_roll(c, t, n, text)
        if self.change(write):
            self.last = (n, text, self.camp["calendar"]["day"])
            self.refresh()

    def undo_last(self):
        if super().undo_last():
            self.last = None
            self.tell("Roll undone, and out of tonight's log.")
            self.refresh()

    def primary(self):
        if self.ready():
            self.roll()
        else:
            self.app.pop()

    def unpress(self):
        self.last = None                              # the roll that press made has been taken back

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        t = self.table()
        if not t:
            return T.draw_text(surf, "That table is not in the file.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")
        if not t["rows"]:
            T.draw_text(surf, "Not copied in yet.", "head", 36, T.TEXT, (20, 70))
            y = lines(surf, "The %s table has no rows. Copy them from your own book into the campaign file, one "
                      "line for each result. I roll it; I do not write it for you." % t["name"], 20, 122, 760, 3,
                      size=24, pitch=31)
            T.draw_text(surf, "File:", "bold", 22, T.DIM, (20, y + 8))
            for line in hard_wrap(file_words(self.name), "text", 22, 690)[:3]:
                T.draw_text(surf, line, "text", 22, T.TEXT, (90, y + 8))
                y += 28
            T.draw_text(surf, "Field:", "bold", 22, T.DIM, (20, y + 12))
            T.draw_text(surf, t["where"], "text", 22, T.TEXT, (90, y + 12), max_w=690)
            return
        box = panel(surf, (20, 68, 220, 290), "d%d" % t["die"])
        if self.last:
            n, text, day = self.last
            T.draw_text(surf, str(n), "head", 120, T.TEXT, box.center, "center", max_w=200)
            lines(surf, text or "That row is empty in the file. Fill it in, or roll again.", 262, 78, 518, 7,
                  kind="mid", size=28, pitch=38)
            words = "Day %d. In tonight's log. Double press, or Undo roll, takes it back." % day
        else:
            T.draw_text(surf, "?", "head", 120, T.DIM, box.center, "center")
            y = lines(surf, "%d row%s in the file. Press the button to roll." % (len(t["rows"]), "" if len(t["rows"]) == 1
                      else "s"), 262, 78, 518, 2, size=28, pitch=38)
            was = self.camp.get("dragon") if t.get("dragon") and isinstance(self.camp.get("dragon"), dict) else None
            if was and was.get("last_roll"):
                lines(surf, "Last roll %s: %s" % (was["last_roll"], was.get("current_location") or "no words for that row."),
                      262, y + 14, 518, 4, T.DIM, size=24, pitch=32)
            words = "Each roll goes in tonight's log with the day. DM only."
        T.draw_text(surf, words, "text", 22, T.DIM, (20, HINT_Y), "midleft", max_w=760)


# ---------------------------------------------------------------- monsters from the DM's own books
def book_pages(app, name, limit=5):
    """Pages of the loaded library that mention this monster, best first, as
    library.doc() gives them. DM-only pages are included only in DM mode."""
    lib, out = app.library, []
    for r in lib.search(name, "dnd", dm=app.dm, limit=limit + 3):
        d = lib.doc(r["id"]) if r["kind"] == "doc" else None
        if d:
            out.append(d)
    return out[:limit]


class MonsterBook(DmBase):
    """The loaded book's own page for a monster, and three numbers to take
    from it. They are read off the page when it states them the usual way;
    the DM checks them and types the rest. Nothing is kept but the numbers."""
    FIELDS = [("hp", "Hit points", 1, 9999), ("ac", "Armour Class", 1, 40), ("bonus", "Initiative", -5, 20)]

    def __init__(self, app, session, monster, count, pages, then):
        super().__init__(app, session)
        self.mon, self.count, self.found, self.then = monster, count, pages, then
        self.i, self.vals, self.typed, self.read, self.excerpt = 0, {"hp": None, "ac": None, "bonus": None}, set(), [], ""
        self.guess()

    @property
    def heading(self):
        return "%s: your books" % short(self.mon, 14) if self.ok() else "DM desk"

    def guess(self):
        self.excerpt = dmdata.stat_excerpt(self.found[self.i]["body"], self.mon)
        got = dmdata.stat_guess(self.excerpt)
        self.read = []
        for key, word, low, high in self.FIELDS:
            if key not in self.typed:
                v = got[key]
                if v is not None and not low <= v <= high:
                    v = None                          # outside what could be typed here: a misreading, so not offered
                self.vals[key] = v
                if v is not None:
                    self.read.append(word)

    def shown(self, key):
        v = self.vals[key]
        return "–" if v is None else (party.signed(v) if key == "bonus" else str(v))

    def build(self):
        if not self.ok():
            return self.back_only()
        out = [Button((20 + k * 257, 240, 247, 64), "%s %s" % (word, self.shown(key)), lambda key=key: self.set(key),
                      size=22) for k, (key, word, _, _) in enumerate(self.FIELDS)]
        spec = [("Back", self.app.pop, 0.8, "plain"), ("Read page", self.read_page, 1.1, "plain")]
        if len(self.found) > 1:
            spec.append(("Next %d/%d" % (self.i + 1, len(self.found)), self.next_page, 1, "plain"))
        spec.append(("Add %s" % (self.mon if self.count == 1 else "%d × %s" % (self.count, self.mon)), self.add, 1.7,
                     "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def set(self, key):
        _, word, low, high = next(f for f in self.FIELDS if f[0] == key)

        def then(n):
            self.vals[key] = n
            self.typed.add(key)
            self.refresh()
        hint = "DM only. %s for %s, from your own book. I show it to nobody else." % (word, self.mon)
        if key == "bonus":
            hint = "DM only. The number %s adds to the d20 for initiative: the Dexterity modifier, as a rule." % self.mon
        v = self.vals[key]
        self.app.push(NumberPad(self.app, word, then, hint, low=low, high=high, negative=key == "bonus", left=self.left,
                                start="" if v is None or v < 0 else v))

    def read_page(self):
        d = self.found[self.i]
        self.app.push(Pages(self.app, d["title"], "", [(d["heading"], d["body"])],
                            note="DM only" if d["dm_only"] else None, speak=False))

    def next_page(self):
        self.i = (self.i + 1) % len(self.found)
        self.guess()
        self.refresh()

    def add(self):
        self.app.pop()
        self.then(self.vals["hp"], self.vals["ac"], self.vals["bonus"])

    def primary(self):
        if self.ok():
            self.add()
        else:
            self.app.pop()

    def draw_body(self, surf):
        if not self.ok():
            return self.locked(surf)
        d = self.found[self.i]
        T.draw_text(surf, d["title"] + (" · DM only" if d["dm_only"] else ""), "bold", 22, T.TEXT, (20, 66), max_w=760)
        lines(surf, self.excerpt or "This page is empty.", 20, 98, 760, 5, T.DIM, pitch=27)
        if self.read:
            words = "Found on this page: %s. Check them." % ", ".join(self.read).lower()
        else:
            words = "I could not read the numbers off this page. Tap a box to type one."
        T.draw_text(surf, words, "text", 22, T.TEXT, (20, 328), "midleft", max_w=760)
        T.draw_text(surf, "From your own loaded book. Only the three numbers go into the fight.", "text", 22, T.DIM,
                    (20, HINT_Y - 6), "midleft", max_w=760)
