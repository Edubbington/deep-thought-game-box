"""Characters on the box: the party list, a sheet, gear and coins, level-up,
and the check every uploaded sheet goes through. Typing is done on a phone;
here it is taps and a number pad. The sums are dt_characters'."""
import copy
import pygame
from ... import theme as T
from ...screens.common import BOTTOM_H, BOTTOM_Y, Pages, TextEntry
from ...widgets import Button, Tile, row
from . import party
from .party import ch
from .plugin import DndBase
from .ui import HINT_Y, PER_PAGE, NumberPad, Row, lines, pages_for, panel, row_rect

ABBR = {"str": "STR", "dex": "DEX", "con": "CON", "int": "INT", "wis": "WIS", "cha": "CHA"}


class Party(DndBase):
    """Every checked character. Tap one to open the sheet."""
    heading = "Characters"

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page, self.review_i, self.folk, self.waiting = 0, 0, 0, 0

    def build(self):
        folk, out = party.roster(), []
        self.folk, self.waiting = len(folk), len(party.waiting())      # read the folder once per build, not per frame
        n_pages = pages_for(len(folk))
        self.page = min(self.page, n_pages - 1)
        table = self.state["edition"]
        for i, (fname, c) in enumerate(folk[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            tags = [party.class_line(c)]
            if c.get("benched"):
                tags.append("Benched")
            if str(c.get("edition", "2014"))[:4] != table:
                tags.append("%s rules" % str(c.get("edition", "2014"))[:4])
            right = "HP %d/%d   AC %s" % (c["hp"]["current"], c["hp"]["max"], c["ac"] if c.get("ac") is not None else "?")
            out.append(Row(row_rect(i), c["name"], lambda fname=fname: self.open(fname), right=right, tags=tags))
        waiting = self.waiting
        spec = [("Back", self.app.pop, 0.8, "primary"), ("New / upload", self.phone, 1.3, "plain")]
        if waiting:
            spec.append(("Check %d" % waiting, self.check, 1, "plain"))
        spec.append(("Long rest", lambda: self.do(ev="rest"), 1.1, "plain"))
        if n_pages > 1:
            spec.append(("List %d/%d" % (self.page + 1, n_pages), self.more_rows, 0.9, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page += 1
        if self.page >= pages_for(len(party.roster())):
            self.page = 0
        self.refresh()

    def open(self, fname):
        self.app.push(Sheet(self.app, self.session, fname))

    def phone(self):
        self.app.push(PhoneHandoff(self.app, self.session))

    def check(self):
        waiting = party.waiting()
        if waiting:
            self.review_i %= len(waiting)
            self.app.push(Review(self.app, self.session, waiting[self.review_i][0]))
            self.review_i += 1

    def draw_body(self, surf):
        folk, waiting = self.folk, self.waiting
        if not folk:
            T.draw_text(surf, "No characters yet.", "head", 36, T.TEXT, (T.W // 2, 150), "center")
            T.draw_text(surf, "Make one, or upload a sheet, from a phone.", "text", 24, T.DIM, (T.W // 2, 200), "center")
        words = "Tap a character to open the sheet."
        if waiting:
            words = "%d uploaded sheet%s to check before %s can play." % (
                waiting, "" if waiting == 1 else "s", "it" if waiting == 1 else "they")
        T.draw_text(surf, words, "text", 22, T.WARN if waiting else T.DIM, (20, HINT_Y), "midleft", max_w=760)


class PhoneHandoff(DndBase):
    """Making or uploading a character needs typing, and typing needs a phone."""
    heading = "Add a character"

    def build(self):
        return row([("Back", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        web, x = getattr(self.app, "web", None), 40
        url = (web.url.rstrip("/") + "/characters") if web else None
        matrix = None
        if url:
            try:
                from ...screens.web_link import qr_matrix
                matrix = qr_matrix(url)
            except ImportError:
                matrix = None
        if matrix:
            n = len(matrix)
            cell = max(1, 230 // n)
            side = cell * n
            pygame.draw.rect(surf, (255, 255, 255), (30, 84, side, side))
            for r, line in enumerate(matrix):
                for c, on in enumerate(line):
                    if on:
                        pygame.draw.rect(surf, (0, 0, 0), (30 + c * cell, 84 + r * cell, cell, cell))
            x = 30 + side + 28
        room = T.W - x - 20
        T.draw_text(surf, "Use a phone for this part.", "head", 32, T.TEXT, (x, 84), max_w=room)
        steps = ["1. Join the same Wi-Fi as the box.",
                 "2. %s %s." % ("Scan the code, or open" if matrix else "Open", url.replace("http://", "")) if url
                 else "2. The web pages are not running. Start them, then come back.",
                 "3. Make a character, or upload a fillable PDF sheet."]
        y = 140
        for step in steps:
            y = lines(surf, step, x, y, room, 2, pitch=30) + 8
        T.draw_text(surf, "New sheets appear under Party, to be checked.", "text", 22, T.DIM, (20, HINT_Y), "midleft",
                    max_w=760)


class SheetBase(DndBase):
    """A screen about one character file."""

    def __init__(self, app, session, fname):
        super().__init__(app, session)
        self.fname = fname
        self.sheet = party.load(fname)

    def reload(self):
        self.sheet = party.load(self.fname)

    def store(self):
        party.write(self.sheet, self.fname)        # the file keeps its name: a fight in progress points at it

    def enter(self):
        self.reload()
        super().enter()

    def gone(self, surf):
        T.draw_text(surf, "That sheet has gone missing.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")

    def back_only(self):
        return row([("Back", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)


class Sheet(SheetBase):
    """One character: the six abilities, hit points, and the numbers worked out."""

    @property
    def heading(self):
        c = self.sheet
        return "%s, %s" % (c["name"], party.class_line(c)) if c else "Sheet"

    def build(self):
        c = self.sheet
        if not c or not party.usable(c):
            return self.back_only()
        here = self.game.combatant_for(self.state, self.fname)
        out = [Button((20, 178, 68, 68), "−", lambda: self.hp(-1), size=30),
               Button((240, 178, 68, 68), "+", lambda: self.hp(1), size=30),
               Button((322, 178, 150, 68), "AC %s" % (c["ac"] if c.get("ac") is not None else "?"), self.set_ac, size=26),
               Button((20, 256, 240, 64), "In the party: %s" % ("no" if c.get("benched") else "yes"), self.bench,
                      size=22)]
        if not here:
            out.append(Button((270, 256, 240, 64), "Join the fight", self.join, size=22))
        spec = [("Gear", self.gear, 1, "plain"), ("Level up", self.level_up, 1.2, "plain"),
                ("Numbers", self.numbers, 1.2, "plain"), ("History", self.history, 1.1, "plain"),
                ("Back", self.app.pop, 1, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def hp(self, delta):
        here = self.game.combatant_for(self.state, self.fname)
        if here:                                   # in the fight: the tracker's rules apply
            self.do(ev="damage" if delta < 0 else "heal", who=here["id"], amount=1)
        else:
            c = party.load(self.fname)
            if c:
                ch.damage(c, 1) if delta < 0 else ch.heal(c, 1)
                party.write(c, self.fname)
        self.reload()
        self.refresh()

    def set_ac(self):
        def then(n):
            self.reload()
            self.sheet["ac"], self.sheet["ac_note"] = n, "entered on the box"
            ch.log(self.sheet, "Armour Class set to %d" % n)
            self.store()
            self.refresh()
        self.app.push(NumberPad(self.app, "Armour Class", then,
                                "Armour Class is entered by hand: too many things change it for me to guess. "
                                "Take it from the sheet.", low=5, high=30, left=self.left))

    def bench(self):
        self.reload()
        self.sheet["benched"] = not self.sheet.get("benched")
        self.store()
        self.refresh()

    def join(self):
        def then(init):
            self.do(ev="add_char", file=self.fname, init=init)
        if self.state["fight"]:
            self.app.push(NumberPad(self.app, "Initiative", then, "Initiative for %s: the d20 plus the Dexterity "
                                    "modifier." % self.sheet["name"], low=-10, high=50, negative=True, left=self.left))
        else:
            then(None)

    def gear(self):
        self.app.push(Gear(self.app, self.session, self.fname))

    def level_up(self):
        self.app.push(LevelUp(self.app, self.session, self.fname))

    def numbers(self):
        c, d = self.sheet, party.numbers(self.sheet)
        if not d:
            return
        saves = ", ".join("%s %s" % (ch.ABILITY_NAMES[a], party.signed(d["saves"][a])) for a in ch.ABILITIES)
        skills = ", ".join("%s %s" % (s.capitalize(), party.signed(v)) for s, v in sorted(d["skills"].items()))
        slots = ch.slots_text(d["spell_slots"])
        pact = "%d of level %d" % d["pact_slots"] if d["pact_slots"][0] else "none"
        steps = [("Worked out for %s" % c["name"],
                  "Level %d. Proficiency bonus %s.\nInitiative %s. Passive Perception %d.\nHit dice %s, %d spent.\n"
                  "Carries up to %d lb.\nRules: %s." % (d["level"], party.signed(d["proficiency_bonus"]),
                                                       party.signed(d["initiative"]), d["passive_perception"],
                                                       d["hit_dice"], c.get("hit_dice_spent", 0),
                                                       d["carry_capacity_lb"], c.get("edition", "2014"))),
                 ("Saving throws", saves + "."), ("Skills", skills + "."),
                 ("Spell slots", "Slots: %s.\nPact slots: %s.\n\nWhich spells, and what they do, are in your book."
                  % (slots, pact))]
        self.app.push(Pages(self.app, c["name"], "Numbers", steps, speak=False))

    def history(self):
        c = self.sheet
        body = "\n".join("%s, level %s: %s" % (h.get("date", ""), h.get("level", "?"), h.get("what", ""))
                         for h in reversed(c.get("history", []))) or "Nothing has happened to this character yet."
        self.app.push(Pages(self.app, c["name"], "History", [("Newest first", body)], speak=False))

    def draw_body(self, surf):
        c = self.sheet
        d = party.numbers(c) if c and party.usable(c) else None
        if not d:
            return self.gone(surf)
        for i, a in enumerate(ch.ABILITIES):
            r = panel(surf, (20 + i * 128, 68, 120, 100))
            T.draw_text(surf, ABBR[a], "text", 22, T.DIM, (r.centerx, r.y + 6), "midtop")
            T.draw_text(surf, party.signed(d["mods"][a]), "head", 38, T.TEXT, (r.centerx, r.y + 50), "center")
            T.draw_text(surf, str(c["abilities"][a]), "text", 22, T.TEXT, (r.centerx, r.bottom - 5), "midbottom")
        T.draw_text(surf, "%d/%d" % (c["hp"]["current"], c["hp"]["max"]), "head", 38, T.TEXT, (164, 200), "center", max_w=140)
        T.draw_text(surf, "hit points", "text", 22, T.DIM, (164, 232), "center")
        for x, label, value in ((482, "Prof.", party.signed(d["proficiency_bonus"])), (636, "Speed", str(c.get("speed", 30)))):
            r = panel(surf, (x, 178, 144, 68))
            T.draw_text(surf, label, "text", 22, T.DIM, (r.x + 14, r.centery), "midleft")
            T.draw_text(surf, value, "head", 32, T.TEXT, (r.right - 14, r.centery), "midright")
        first = "Initiative %s  ·  Passive Perception %d  ·  Hit dice %s" % (
            party.signed(d["initiative"]), d["passive_perception"], d["hit_dice"])
        second = []
        if c["hp"].get("temp"):
            second.append("%d temporary hit points" % c["hp"]["temp"])
        if d["spell_slots"]:
            second.append("Slots " + ch.slots_text(d["spell_slots"]))
        second.append("%s rules" % str(c.get("edition", "2014"))[:4])
        T.draw_text(surf, first, "text", 22, T.TEXT, (20, 328), max_w=760)
        T.draw_text(surf, "  ·  ".join(second), "text", 22, T.DIM, (20, 358), max_w=760)
        if c.get("player"):
            T.draw_text(surf, "Played by %s" % c["player"], "text", 22, T.DIM, (780, 288), "midright", max_w=250)


class Gear(SheetBase):
    """What the character carries. Tap an item to wear it or pack it away."""
    heading = "Gear"

    def __init__(self, app, session, fname):
        super().__init__(app, session, fname)
        self.page = 0

    def build(self):
        c = self.sheet
        if not c:
            return self.back_only()
        items, out = c["equipment"], []
        n_pages = pages_for(len(items))
        self.page = min(self.page, n_pages - 1)
        for i, item in enumerate(items[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            name = item["name"]
            out.append(Row(row_rect(i, w=606), name, lambda name=name: self.wear(name), num=item.get("qty", 1),
                           right="Worn" if item.get("equipped") else "Packed", selected=bool(item.get("equipped"))))
            out.append(Button(row_rect(i, x=636, w=144), "Attuned" if item.get("attuned") else "Attune",
                              lambda name=name: self.attune(name), selected=bool(item.get("attuned")), size=22))
        spec = [("Back", self.app.pop, 0.9, "primary"), ("Coins", self.coins, 1, "plain")]
        if n_pages > 1:
            spec.append(("More gear %d/%d" % (self.page + 1, n_pages), self.more_gear, 1.5, "plain"))
        spec.append(("Add by phone", self.phone, 1.3, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def more_gear(self):
        self.page = (self.page + 1) % pages_for(len(self.sheet["equipment"]))
        self.refresh()

    def wear(self, name):
        self.reload()
        item = ch.find_item(self.sheet, name)
        if item:
            ch.equip(self.sheet, name, not item.get("equipped"))
            self.store()
        self.refresh()

    def attune(self, name):
        self.reload()
        item = ch.find_item(self.sheet, name)
        if not item:
            return self.refresh()
        try:
            ch.attune(self.sheet, name, not item.get("attuned"))
            self.store()
        except ValueError:
            self.reload()
            self.app.say("%s is already attuned to %d items, and %d is the limit. End one first."
                         % (self.sheet["name"], ch.MAX_ATTUNED, ch.MAX_ATTUNED))
        self.refresh()

    def coins(self):
        self.app.push(Coins(self.app, self.session, self.fname))

    def phone(self):
        self.app.push(PhoneHandoff(self.app, self.session))

    def draw_body(self, surf):
        c = self.sheet
        if not c:
            return self.gone(surf)
        if not c["equipment"]:
            T.draw_text(surf, "Nothing carried.", "head", 36, T.TEXT, (T.W // 2, 150), "center")
            T.draw_text(surf, "Type the gear in from a phone. I shall keep count.", "text", 24, T.DIM, (T.W // 2, 200), "center")
        n = sum(1 for i in c["equipment"] if i.get("attuned"))
        T.draw_text(surf, "Coins: %s" % party.coins_text(c), "text", 22, T.TEXT, (20, HINT_Y), "midleft", max_w=520)
        T.draw_text(surf, "Attuned to %d of %d" % (n, ch.MAX_ATTUNED), "text", 22, T.DIM, (780, HINT_Y), "midright")


class Coins(SheetBase):
    """Spend or gain coins. A purse cannot go below nothing."""
    heading = "Coins"

    def __init__(self, app, session, fname):
        super().__init__(app, session, fname)
        self.coin = "gp"

    def build(self):
        c = self.sheet
        if not c:
            return self.back_only()
        out = []
        for i, (k, name) in enumerate(party.COIN_NAMES):
            t = Tile((20 + i * 154, 68, 144, 100), name, c["coins"].get(k, 0), lambda k=k: self.pick(k))
            t.selected = k == self.coin
            out.append(t)
        word = dict(party.COIN_NAMES)[self.coin].lower()
        out += [Button((20, 180, 375, 64), "Spend %s" % word, lambda: self.ask(-1), size=22),
                Button((405, 180, 375, 64), "Gain %s" % word, lambda: self.ask(1), size=22)]
        return out + self.back_only()

    def pick(self, k):
        self.coin = k
        self.refresh()

    def ask(self, sign):
        word = dict(party.COIN_NAMES)[self.coin].lower()
        def then(n):
            self.reload()
            try:
                ch.add_coins(self.sheet, **{self.coin: sign * n})
                self.store()
            except ValueError:
                self.reload()
                self.app.say("Not enough %s: %s has %d. A purse cannot go below nothing."
                             % (word, self.sheet["name"], self.sheet["coins"].get(self.coin, 0)))
            self.refresh()
        self.app.push(NumberPad(self.app, ("Spend " if sign < 0 else "Gain ") + word, then,
                                "How many %s coins does %s %s?" % (word, self.sheet["name"],
                                                                  "spend" if sign < 0 else "gain"),
                                low=1, high=9999, left=self.left))

    def draw(self, surf, pressed=None):
        super().draw(surf, pressed)
        for w in self.widgets:                      # the chosen coin gets the thick light edge
            if isinstance(w, Tile) and w.selected:
                pygame.draw.rect(surf, T.TEXT, w.rect, 3, border_radius=14)

    def draw_body(self, surf):
        if not self.sheet:
            return self.gone(surf)
        lines(surf, "Tap a coin, then spend or gain. I do not change one kind of coin into another; "
              "that is between %s and the shopkeeper." % self.sheet["name"], 20, 262, 760, 3, T.DIM, size=24, pitch=32)


class LevelUp(SheetBase):
    """One level: hit points by average or by roll, then what changes."""

    def __init__(self, app, session, fname):
        super().__init__(app, session, fname)
        self.cls_i, self.new_cls, self.roll = 0, None, None

    def cls(self):
        return self.new_cls or self.sheet["classes"][min(self.cls_i, len(self.sheet["classes"]) - 1)]["name"]

    def die(self):
        return ch.hit_die_for(self.sheet, self.cls())

    def preview(self):
        """(sheet after the level, list of things to do), or (None, why not)."""
        after = copy.deepcopy(self.sheet)
        try:
            return after, ch.level_up(after, self.cls(), self.roll)
        except ValueError as e:
            return None, ["Already level 20. There is nowhere further to go."] if "20" in str(e) else [str(e)]

    @property
    def heading(self):
        if not self.sheet:
            return "Level up"
        k = next((k for k in self.sheet["classes"] if k["name"] == self.cls()), None)
        return "%s: %s %d" % (self.sheet["name"], self.cls(), (k["level"] if k else 0) + 1)

    def build(self):
        if not self.sheet or not party.usable(self.sheet):
            return self.back_only()
        die = self.die() or 8
        out = [Button((36, 240, 165, 64), "Take %d" % ch.average_roll(die), self.average, selected=self.roll is None, size=22),
               Button((211, 240, 168, 64), "I rolled" if self.roll is None else "Rolled %d" % self.roll, self.rolled,
                      selected=self.roll is not None, size=22)]
        spec = [("Cancel", self.app.pop, 1, "plain"), ("Class: %s" % self.cls(), self.next_class, 1.6, "plain"),
                ("Done", self.done, 1.2, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def average(self):
        self.roll = None
        self.refresh()

    def rolled(self):
        die = self.die() or 8
        def then(n):
            self.roll = n
            self.refresh()
        self.app.push(NumberPad(self.app, "Hit die roll", then, "What did the d%d show? I add the Constitution "
                                "modifier. A level is never worth less than 1 hit point." % die,
                                low=1, high=die, left=self.left))

    def next_class(self):
        """Step through the character's classes; after the last, offer a new one."""
        n = len(self.sheet["classes"])
        self.roll = None
        if self.new_cls:                            # was on a new class: back to the first
            self.new_cls, self.cls_i = None, 0
            return self.refresh()
        if self.cls_i + 1 < n:
            self.cls_i += 1
            return self.refresh()

        def done(text):
            name = text.title()
            self.cls_i = 0
            if name and not any(k["name"].lower() == name.lower() for k in self.sheet["classes"]):
                if ch.HIT_DIE.get(name.lower()):
                    self.new_cls = name
                else:
                    self.app.say("I do not know the hit die for %s. Add that class from a phone." % name)
            self.refresh()
        self.app.push(TextEntry(self.app, "A new class", "", done, "Done", max_len=12))

    def done(self):
        after, todo = self.preview()
        if after is None:
            self.app.say(todo[0])
            return
        self.reload()
        todo = ch.level_up(self.sheet, self.cls(), self.roll)      # writes the change and one history line
        party.write(self.sheet, self.fname)
        self.game.resync(self.session)             # the tracker reads the sheet again; not an event, nothing to undo
        name = self.sheet["name"]
        self.app.pop()
        self.app.push(Pages(self.app, name, "Level up", [(todo[0], "\n\n".join(todo[1:]))]))

    def primary(self):
        self.done()

    def draw_body(self, surf):
        c = self.sheet
        if not c or not party.usable(c):
            return self.gone(surf)
        after, todo = self.preview()
        a = panel(surf, (20, 68, 375, 250), "Hit points")
        b = panel(surf, (405, 68, 375, 250), "What changes")
        if after is None:
            lines(surf, todo[0], a.x + 18, a.y + 44, a.w - 36, 4)
            return
        die, con = self.die(), ch.ability_mod(c["abilities"]["con"])
        raw = ch.average_roll(die) if self.roll is None else self.roll
        T.draw_text(surf, "%d to %d" % (c["hp"]["max"], after["hp"]["max"]), "head", 44, T.TEXT, (a.x + 18, a.y + 36),
                    max_w=a.w - 36)
        how = "%s %d on a d%d, %s %d for Constitution." % ("Took" if self.roll is None else "Rolled", raw, die,
                                                         "plus" if con >= 0 else "minus", abs(con))
        if raw + con < 1:
            how += " Never less than 1."
        lines(surf, how, a.x + 18, a.y + 96, a.w - 36, 2, T.TEXT)
        y = b.y + 44
        for item in [t for t in todo[1:] if not t.startswith("Hit point maximum")]:
            if y > b.bottom - 34:
                break
            pygame.draw.rect(surf, T.DIM, (b.x + 18, y + 9, 8, 8))
            y = lines(surf, item, b.x + 36, y, b.w - 54, min(3, (b.bottom - 8 - y) // 26), pitch=26) + 4
        T.draw_text(surf, "Done saves it and adds a line to the history.", "text", 22, T.DIM, (20, 354), "midleft",
                    max_w=760)


class Review(SheetBase):
    """Every uploaded sheet is checked here before it joins the party."""
    heading = "Check this sheet"
    PER = 4

    def __init__(self, app, session, fname):
        super().__init__(app, session, fname)
        self.page = 0

    def findings(self):
        """[(ok, words)] for this sheet."""
        c, table, out = self.sheet, self.state["edition"], []
        who = ", ".join(x for x in (c.get("name"), party.class_line(c), c.get("species")) if x)
        out.append((bool(c.get("name")), who or "No character name"))
        scores = [c["abilities"].get(a) for a in ch.ABILITIES]
        if all(isinstance(v, int) for v in scores):
            out.append((True, "Ability scores: " + ", ".join(str(v) for v in scores)))
        stamp = str(c.get("edition", "2014"))[:4]
        if stamp == table:
            out.append((True, "Rules: %s, the same as this table" % stamp))
        else:
            out.append((False, "Stamped for the %s rules. This table plays %s. Tap Rules to change it." % (stamp, table)))
        try:
            problems = ch.check(c)
        except (TypeError, KeyError, ValueError):
            problems = ["I cannot make sense of this sheet. Upload it again from a phone."]
        if party.usable(c) and not any("Hit point" in p for p in problems):
            out.append((True, "Hit points %d: fits %s" % (c["hp"]["max"], party.class_line(c))))
        out += [(False, p) for p in problems]
        if party.imported(c):
            out.append((False, "Skill and saving throw proficiencies are not read from a sheet. Tick them from a phone."))
        return out

    def build(self):
        c = self.sheet
        if not c:
            return self.back_only()
        n_pages = pages_for(len(self.findings()), self.PER)
        self.page = min(self.page, n_pages - 1)
        spec = [("Save", self.save, 1, "primary"), ("Rules: %s" % str(c.get("edition", "2014"))[:4], self.flip_rules, 1.4, "plain"),
                ("Set AC", self.set_ac, 1, "plain")]
        if n_pages > 1:
            spec.append(("More %d/%d" % (self.page + 1, n_pages), self.more_rows, 1.1, "plain"))
        spec.append(("Back", self.app.pop, 0.8, "plain"))
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def more_rows(self):
        self.page = (self.page + 1) % pages_for(len(self.findings()), self.PER)
        self.refresh()

    def flip_rules(self):
        self.reload()
        self.sheet["edition"] = "2014" if str(self.sheet.get("edition", "2014")).startswith("2024") else "2024"
        self.fname = party.save(self.sheet, self.fname)
        self.refresh()

    def set_ac(self):
        def then(n):
            self.reload()
            self.sheet["ac"], self.sheet["ac_note"] = n, "entered on the box"
            self.fname = party.save(self.sheet, self.fname)
            self.refresh()
        self.app.push(NumberPad(self.app, "Armour Class", then, "Armour Class, as written on the sheet.",
                                low=5, high=30, left=self.left))

    def save(self):
        self.reload()
        c = self.sheet
        if not party.usable(c):
            self.app.say("I cannot use a sheet without a name, a class, six ability scores and hit points. "
                         "Fix it from a phone.")
            return
        left = sum(1 for ok, _ in self.findings() if not ok)
        c["reviewed"] = True
        c.pop("needs_review", None)
        ch.log(c, "Sheet checked on the box (%s rules)" % str(c.get("edition", "2014"))[:4])
        self.fname = party.save(c, self.fname)
        self.app.pop()
        self.app.say("%s is in the party.%s" % (c["name"], " %d thing%s still to look at, when someone has a moment."
                                                % (left, "" if left == 1 else "s") if left else ""))

    def primary(self):
        self.save()

    def draw_body(self, surf):
        if not self.sheet:
            return self.gone(surf)
        found = self.findings()
        for i, (ok, words) in enumerate(found[self.page * self.PER:(self.page + 1) * self.PER]):
            r = panel(surf, (20, 68 + i * 78, 760, 72))
            badge = pygame.Rect(r.x + 12, r.centery - 20, 84, 40)
            if ok:
                pygame.draw.rect(surf, T.LINE, badge, 1, border_radius=10)
            else:                                   # filled, and a different word: not colour alone
                pygame.draw.rect(surf, T.WARN, badge, border_radius=10)
            T.draw_text(surf, "OK" if ok else "Check", "bold", 22, T.TEXT if ok else T.GROUND, badge.center, "center")
            got = T.wrap(words, "text", 22, r.w - 130)
            if len(got) == 1:
                T.draw_text(surf, got[0], "text", 22, T.TEXT, (r.x + 110, r.centery), "midleft", max_w=r.w - 126)
            else:
                lines(surf, words, r.x + 110, r.y + 8, r.w - 126, 2, pitch=28)
