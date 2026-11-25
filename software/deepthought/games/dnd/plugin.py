"""Dungeons & Dragons. The box keeps the initiative order, the conditions, the
concentration saves and the death saves, and writes damage through to the
character files. The DM keeps the monsters; the players keep their books.

State (all plain JSON):
  fight       False while people are still rolling initiative
  round, turn the round number and the id of whoever is acting
  combatants  [{id, name, kind, init, tie, cond, conc, saves, stable, dead, flag,
                hidden, and for characters: file, seat, cls, hp, max, temp;
                for the rest: hurt, max}]
  prompts     concentration saves waiting for an answer: [{who, dc, damage}]
  prep        the DM's ticks for tonight
The character file is the record of hit points; the copy in the state is what
undo puts back."""
import copy

import pygame
from ... import theme as T
from ...engine import Game
from ...screens.common import BOTTOM_H, BOTTOM_Y, Choice, PlayBase, TextEntry
from ...widgets import Button, row
from . import party, rules
from .party import ch
from .ui import HINT_Y, PER_PAGE, NumberPad, Row, lines, pages_for, panel, row_rect

PHASES = [("turn", "Start of turn"), ("setup", "Before the fight")]


class Plugin(Game):
    min_players, max_players = 2, 6
    options = [{"key": "edition", "label": "Rules", "choices": ["2024", "2014"]}]
    quiet_phases = ("wait",)                          # no reminders as the enemies' turns begin

    # ------------------------------------------------------------ state
    def new_state(self, players, options):
        s = {"edition": str(options.get("edition", "2024")), "names": list(players), "fight": False,
             "round": 0, "turn": None, "acted": [], "combatants": [], "next_id": 1, "prompts": [],
             "prep": [False] * (len(rules.PREP) + 1)}
        for fname, sheet in party.party():
            s["combatants"].append(self._character(s, fname, sheet))
        return s

    def _id(self, s):
        s["next_id"] += 1
        return s["next_id"] - 1

    def _character(self, s, fname, sheet, init=None):
        if party.stamp(sheet):                        # an id of its own, so a renamed sheet can be found again
            party.write(sheet, fname)
        who = str(sheet.get("player", "")).strip().lower()
        seat = next((i for i, n in enumerate(s["names"]) if who and n.strip().lower() == who), None)
        c = {"id": self._id(s), "name": sheet["name"], "kind": "character", "init": init, "tie": 0, "cond": [],
             "conc": False, "saves": [0, 0], "stable": False, "dead": False, "flag": False, "hidden": False,
             "file": fname, "seat": seat, "sid": sheet["id"]}
        self._mirror(c, sheet)
        if c["hp"] == 0 and "Unconscious" not in c["cond"]:
            c["cond"].append("Unconscious")
        return c

    @staticmethod
    def _mirror(c, sheet):
        c["hp"], c["max"], c["temp"] = sheet["hp"]["current"], sheet["hp"]["max"], sheet["hp"].get("temp", 0)
        c["cls"] = party.class_line(sheet) or c.get("cls", "")

    def locate(self, s, c):
        """(file name, sheet) for a character in the tracker, or (None, None).
        The file it was read from first. If that has gone, or now holds someone
        else, the sheet with the same id (a character renamed from a phone
        keeps its id), and failing that an unclaimed sheet of the same name."""
        sid = c.get("sid")
        sheet = party.load(c.get("file"))
        here = bool(sheet and party.usable(sheet))
        if here and (not sid or sheet.get("id") == sid):
            return c["file"], sheet
        taken = {x.get("file") for x in s["combatants"] if x is not c and x["kind"] == "character"}
        folk = [(n, sh) for n, sh in party.everyone() if n not in taken and party.usable(sh)]
        for n, sh in folk:
            if sid and sh.get("id") == sid:
                return n, sh
        if here and sheet.get("id") is None:          # a sheet with no id where ours was, and ours is nowhere else: take it
            return c["file"], sheet
        for n, sh in folk:
            if sh.get("name") == c["name"] and not (sid and sh.get("id") and sh["id"] != sid):
                return n, sh
        return None, None

    def _sheet(self, s, c):
        """The character's sheet, or a stand-in built from the tracker's copy
        if no file can be found for it."""
        fname, sheet = self.locate(s, c)
        if sheet:
            c["file"] = fname
            return sheet
        return {"name": c["name"], "ghost": True, "hp": {"max": c["max"], "current": c["hp"], "temp": c["temp"]}}

    def _write(self, c, sheet):
        if not sheet.get("ghost"):
            party.write(sheet, c["file"])             # back where it came from: the file is never renamed here
        self._mirror(c, sheet)

    def get(self, s, who):
        return next((c for c in s["combatants"] if c["id"] == who), None)

    def find(self, s, who):
        c = self.get(s, who)
        if not c:
            raise ValueError("That combatant has left the fight.")
        return c

    def order(self, s, dm=True):
        """Combatants in initiative order. Without DM mode the hidden ones are left out."""
        return [c for c in rules.order(s["combatants"]) if dm or not c["hidden"]]

    @staticmethod
    def acted(s):
        """Ids of those who have had their turn this round, whoever is acting
        included. A fight saved before this was kept works it out from the order."""
        got = s.get("acted")
        return list(got) if got is not None else rules.gone_by(s["combatants"], s["turn"])

    def _advance(self, s):
        """Pass the turn on. Returns (id, new_round)."""
        acted = self.acted(s)
        nid, wrapped = rules.next_up(s["combatants"], acted)
        if wrapped:
            s["round"] += 1
            acted = []
        if nid is not None and nid not in acted:
            acted.append(nid)
        s["turn"], s["acted"] = nid, acted
        return nid, wrapped

    def _join(self, s, c):
        """Someone arriving, or coming back, in the middle of a round: if their
        place in the order has already gone by, they wait for the next round."""
        if not s["fight"]:
            return
        acted = self.acted(s)
        if c["id"] not in acted and c["id"] in rules.gone_by(s["combatants"], s["turn"]):
            acted.append(c["id"])
        s["acted"] = acted

    def current(self, s, dm=True):
        c = self.get(s, s["turn"]) if s["fight"] else None
        return c if c and (dm or not c["hidden"]) else None

    def combatant_for(self, s, fname):
        return next((c for c in s["combatants"] if c["kind"] == "character" and c.get("file") == fname), None)

    @staticmethod
    def down(c):
        return c["kind"] == "character" and c["hp"] == 0 and not c["dead"]

    @staticmethod
    def _wake(c):
        c["saves"], c["stable"], c["flag"] = [0, 0], False, False
        if "Unconscious" in c["cond"]:
            c["cond"].remove("Unconscious")

    # ------------------------------------------------------------ the engine's questions
    def phases(self):
        return PHASES

    def phase(self, s):
        if not s["fight"]:
            return "setup"
        # A turn that belongs to no seat (an enemy, an ally, someone hidden) is its own
        # phase, with no reminders hung on it: the engine reads every player's reminders
        # out when a phase is nobody's, and "start of my turn" must not be said then.
        return "turn" if self.active(s) is not None else "wait"

    def active(self, s):
        c = self.current(s, dm=False)
        return c.get("seat") if c and c["kind"] == "character" else None

    def over(self, s):
        return None                                   # nobody wins D&D; the game ends from the menu

    def leader(self, s):
        return None

    def standings(self, s, players):
        out = ["Stopped in round %d of a fight" % s["round"] if s["fight"] else "Stopped between fights"]
        heroes = [c for c in s["combatants"] if c["kind"] == "character" and not c["hidden"]]
        if heroes:
            out.append(", ".join("%s %s" % (c["name"], "dead" if c["dead"] else "%d/%d" % (c["hp"], c["max"]))
                                 for c in heroes))
        return out

    def strip(self, session):
        self._hook(session)
        s = session.state
        return ("D&D · Round %d" % s["round"], "Initiative") if s["fight"] else ("D&D", "Before the fight")

    def scoreboard(self, session):
        """Initiative order only: names, and whose turn. No hit points, nobody hidden, no notes."""
        self._hook(session)
        s = session.state
        now = self.current(s, dm=False)
        rows = [{"name": c["name"], "value": "Now" if now and c["id"] == now["id"] else "",
                 "out": bool(c["dead"])} for c in self.order(s, dm=False)]
        return {"rows": rows, "note": "Round %d, initiative order" % s["round"] if s["fight"] else "Rolling initiative"}

    def phone(self, session, seat):
        """A player's own character: hit points, conditions, and the few things
        they may do to themselves."""
        self._hook(session)
        s = session.state
        mine = [c for c in s["combatants"] if c["kind"] == "character" and c.get("seat") == seat and not c["hidden"]]
        now = self.current(s, dm=False)
        where = ("Round %d." % s["round"] if s["fight"] else "No fight yet.") + (" %s's turn." % now["name"] if now else "")
        if not mine:
            return {"lines": ["No character of yours is in the fight.", where], "actions": []}
        c, out, actions = mine[0], [], []
        if c["dead"]:
            out.append("%s is dead." % c["name"])
        else:
            hp = "%s: %d of %d hit points" % (c["name"], c["hp"], c["max"])
            out.append(hp + (", plus %d temporary" % c["temp"] if c["temp"] else ""))
            if self.down(c):
                out.append("Stable, and out cold." if c["stable"] else
                           "Down. Death saves: %d passed, %d failed." % tuple(c["saves"]))
            if c["cond"]:
                out.append("Conditions: " + ", ".join(c["cond"]))
            if c["conc"]:
                out.append("Concentrating.")
            for dc in [p["dc"] for p in s["prompts"] if p["who"] == c["id"]]:
                out.append("Constitution save, DC %d, to keep concentrating." % dc)
            actions += [{"label": "Damage %d" % n, "ev": {"ev": "damage", "who": c["id"], "amount": n}} for n in (1, 5, 10)]
            actions += [{"label": "Heal %d" % n, "ev": {"ev": "heal", "who": c["id"], "amount": n}} for n in (1, 5, 10)]
            if self.down(c) and not c["stable"]:
                actions += [{"label": "Death save passed", "ev": {"ev": "save", "who": c["id"], "passed": True}},
                            {"label": "Death save failed", "ev": {"ev": "save", "who": c["id"], "passed": False}}]
            if now and now["id"] == c["id"]:
                actions.append({"label": "End my turn", "ev": {"ev": "next"}})
        out.append(where)
        return {"lines": out, "actions": actions}

    def play_screen(self, app, session):
        self._hook(session)
        return Tracker(app, session)

    # ------------------------------------------------------------ files and undo
    def _hook(self, session):
        """Undo must also put the character files back. The engine's undo only
        knows about the state, so wrap this one session's undo."""
        if getattr(session, "_dnd_hooked", False):
            return
        plain = session.undo

        def undo():
            rest = None
            if session.log and session.log[-1].get("ev") == "rest":
                rest = copy.deepcopy(session.state.get("rest_undo"))
            ok = plain()
            if ok:
                if rest:
                    self._unrest(rest)
                self.push_files(session.state)
                session.save()
            return ok
        session.undo, session._dnd_hooked = undo, True

    @staticmethod
    def _unrest(rest):
        """Take a long rest back out of the character files: hit points, slots,
        hit dice and the line in the history, for everyone who rested, in the
        tracker or not."""
        for fname, was in rest.items():
            sheet = party.load(fname)
            if was.get("id") and not (sheet and sheet.get("id") == was["id"]):
                # renamed from a phone since the rest: the file has moved, the id has not
                fname, sheet = next(((n, sh) for n, sh in party.everyone() if sh.get("id") == was["id"]), (fname, None))
            if not sheet:
                continue
            sheet["hp"]["current"], sheet["hp"]["temp"] = was["hp"], was["temp"]
            for key in ("slots_used", "pact_used", "hit_dice_spent"):
                if was.get(key) is None:
                    sheet.pop(key, None)
                else:
                    sheet[key] = was[key]
            history = sheet.get("history")
            if isinstance(history, list) and history and isinstance(history[-1], dict) and history[-1].get("what") == "Long rest":
                history.pop()
            party.write(sheet, fname)

    def push_files(self, s):
        """After an undo: write the tracker's hit points back to the character
        files, and take from the files what the tracker does not decide (the
        maximum, the name, the class), so a level gained since is not lost."""
        for c in s["combatants"]:
            if c["kind"] != "character":
                continue
            fname, sheet = self.locate(s, c)
            if not sheet:
                continue
            hp = max(0, min(sheet["hp"]["max"], c["hp"]))
            if (sheet["hp"]["current"], sheet["hp"].get("temp", 0)) != (hp, c["temp"]):
                sheet["hp"]["current"], sheet["hp"]["temp"] = hp, c["temp"]
                party.write(sheet, fname)
            c["file"], c["name"] = fname, sheet["name"]
            self._mirror(c, sheet)

    @staticmethod
    def _differs(c, fname, sheet):
        return ((fname, sheet["name"], sheet["hp"]["current"], sheet["hp"]["max"], sheet["hp"].get("temp", 0))
                != (c.get("file"), c["name"], c["hp"], c["max"], c["temp"])
                or (party.class_line(sheet) or c.get("cls", "")) != c.get("cls", ""))

    def stale(self, s):
        """True when a character file no longer matches the tracker's copy."""
        for c in s["combatants"]:
            fname, sheet = self.locate(s, c) if c["kind"] == "character" else (None, None)
            if sheet and self._differs(c, fname, sheet):
                return True
        return False

    def _take(self, c, fname, sheet, hp, temp):
        was = c["hp"]
        c["file"], c["name"] = fname, sheet["name"]
        self._mirror(c, sheet)
        c["hp"], c["temp"] = hp, temp
        if sheet.get("id"):
            c["sid"] = sheet["id"]
        if was == 0 and hp > 0:
            self._wake(c)
        elif was > 0 and hp == 0 and not c["dead"]:
            c["saves"], c["stable"] = [0, 0], False
            if "Unconscious" not in c["cond"]:
                c["cond"].append("Unconscious")

    def resync(self, session):
        """Read the character files again, after a level-up or a change made
        from a phone. This is not an event: it is not in the log and there is
        nothing of it to undo. The copies undo keeps are moved by the same
        amount, so undoing the event before it still undoes only that event.
        True when something changed."""
        s, changed = session.state, False
        for c in s["combatants"]:
            if c["kind"] != "character":
                continue
            fname, sheet = self.locate(s, c)
            if not sheet or not self._differs(c, fname, sheet):
                continue
            hp, top, temp = sheet["hp"]["current"], sheet["hp"]["max"], sheet["hp"].get("temp", 0)
            d_hp, d_temp = hp - c["hp"], temp - c["temp"]
            for old in session.d["undo"]:
                for x in old["combatants"]:
                    if x["id"] == c["id"] and x["kind"] == "character":
                        self._take(x, fname, sheet, max(0, min(top, x["hp"] + d_hp)), max(0, x["temp"] + d_temp))
            self._take(c, fname, sheet, hp, temp)
            if self.down(c) and c["conc"]:
                c["conc"] = False
                s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
            changed = True
        if changed:
            session.save()
        return changed

    # ------------------------------------------------------------ events
    def apply(self, s, ev):
        fn = getattr(self, "_ev_" + str(ev.get("ev")), None)
        if not fn:
            raise ValueError("I do not know what %r means in D&D." % ev.get("ev"))
        if s.get("fight") and s.get("acted") is None:     # a fight saved before 'acted' was kept: work it out once,
            s["acted"] = rules.gone_by(s["combatants"], s["turn"])     # before this event can move anybody in the order
        return fn(s, ev)

    @staticmethod
    def _amount(ev, low=1, high=999, what="That"):
        try:
            n = int(ev.get("amount"))
        except (TypeError, ValueError):
            raise ValueError("%s needs a number." % what)
        if not low <= n <= high:
            raise ValueError("%s should be between %d and %d." % (what, low, high))
        return n

    def _turn_lines(self, c):
        if c["hidden"]:
            return []
        out = ["%s is up." % c["name"]]
        if self.down(c):
            out.append("Stable, and still out cold." if c["stable"] else "At 0 hit points: roll a death save.")
        other = [x for x in c["cond"] if x != "Unconscious" or not self.down(c)]
        if other:
            out.append("Still %s." % rules.joined(x.lower() for x in other))
        if c["conc"]:
            out.append("Concentrating.")
        return out

    def _ev_next(self, s, ev):
        live = [c for c in s["combatants"] if not c["dead"]]
        if not live:
            raise ValueError("Nobody is in the fight. Add someone first.")
        if not s["fight"]:
            missing = [c for c in rules.order(live) if c["init"] is None]
            seen = [c for c in missing if not c["hidden"]]
            if seen:
                raise ValueError("%s has no initiative yet. Tap the name to enter it." % seen[0]["name"])
            if missing and ev.get("dm"):              # only the DM's own screen may name a hidden one
                raise ValueError("%s, who is hidden, has no initiative yet. Tap the name to enter it." % missing[0]["name"])
            if missing:
                raise ValueError("The DM is not ready to start yet.")
            s["fight"], s["round"] = True, 1
            first = rules.order(live)[0]
            s["turn"], s["acted"] = first["id"], [first["id"]]
            return ["Round 1."] + self._turn_lines(first)
        nid, wrapped = self._advance(s)
        said = ["Round %d." % s["round"]] if wrapped else []
        return said + self._turn_lines(self.get(s, nid))

    def _ev_add(self, s, ev):
        kind, base = ev.get("kind", "enemy"), " ".join(str(ev.get("base", "")).split())[:18]
        count = int(ev.get("count", 1))
        if kind not in ("enemy", "ally") or not base:
            raise ValueError("I can add an enemy or an ally, and it needs a name.")
        if not 1 <= count <= rules.MAX_GROUP:
            raise ValueError("One to %d at a time." % rules.MAX_GROUP)
        if len(s["combatants"]) + count > rules.MAX_COMBATANTS:
            raise ValueError("%d combatants is my limit. Remove someone first." % rules.MAX_COMBATANTS)
        init, hp = ev.get("init"), ev.get("hp")
        if init is None and s["fight"]:
            raise ValueError("The fight has started. A newcomer needs an initiative.")
        if init is not None and not -10 <= int(init) <= 50:
            raise ValueError("Initiative should be between -10 and 50.")
        names = rules.numbered([c["name"] for c in s["combatants"]], base, count, bool(ev.get("numbered", True)))
        for name in names:
            s["combatants"].append({"id": self._id(s), "name": name, "kind": kind,
                                    "init": None if init is None else int(init), "tie": 0, "cond": [], "conc": False,
                                    "saves": [0, 0], "stable": False, "dead": False, "flag": False,
                                    "hidden": bool(ev.get("hidden")), "hurt": 0,
                                    "max": int(hp) if hp else None})
            for key in ("ac", "bonus"):           # the DM's own numbers from his book; shown in DM mode only
                if isinstance(ev.get(key), int) and not isinstance(ev.get(key), bool):
                    s["combatants"][-1][key] = ev[key]
            self._join(s, s["combatants"][-1])
        return []

    def _ev_add_char(self, s, ev):
        fname = str(ev.get("file", ""))
        for c in s["combatants"]:                     # a sheet renamed since it joined is still the same character
            if c["kind"] == "character" and c.get("file") != fname and self.locate(s, c)[0] == fname:
                c["file"] = fname
        if self.combatant_for(s, fname):
            raise ValueError("That character is already in the fight.")
        sheet = party.load(fname)
        if not sheet or not party.usable(sheet):
            raise ValueError("I cannot read that character's sheet.")
        if party.needs_review(sheet):
            raise ValueError("%s's sheet has not been checked yet. Look under Party." % (sheet.get("name") or "That character"))
        init = ev.get("init")
        if init is None and s["fight"]:
            raise ValueError("The fight has started. A newcomer needs an initiative.")
        if len(s["combatants"]) >= rules.MAX_COMBATANTS:
            raise ValueError("%d combatants is my limit. Remove someone first." % rules.MAX_COMBATANTS)
        s["combatants"].append(self._character(s, fname, sheet, None if init is None else int(init)))
        self._join(s, s["combatants"][-1])
        return []

    def _ev_load(self, s, ev):
        """The DM's fight loader: named enemies, ahead of time."""
        if s["fight"]:
            raise ValueError("End this fight before loading the next one.")
        enemies = ev.get("enemies") or []
        total = sum(int(e.get("count", 1)) for e in enemies)
        if not total:
            raise ValueError("That fight has nobody in it.")
        if len(s["combatants"]) + total > rules.MAX_COMBATANTS:
            raise ValueError("%d combatants is my limit. Remove someone first." % rules.MAX_COMBATANTS)
        for e in enemies:
            self._ev_add(s, {"kind": "enemy", "base": e.get("name", "Enemy"), "count": int(e.get("count", 1)),
                             "hp": e.get("hp"), "hidden": bool(ev.get("hidden")), "ac": e.get("ac"),
                             "bonus": e.get("init_bonus"),
                             "numbered": int(e.get("count", 1)) > 1})
        return []

    def _ev_init(self, s, ev):
        c = self.find(s, ev.get("who"))
        c["init"] = self._amount({"amount": ev.get("value")}, -10, 50, "Initiative")
        return []

    def _ev_tie(self, s, ev):
        c = self.find(s, ev.get("who"))
        c["tie"] = max([x.get("tie", 0) for x in s["combatants"] if x["init"] == c["init"]] + [0]) + 1
        return []

    def _ev_damage(self, s, ev):
        c, n = self.find(s, ev.get("who")), self._amount(ev, what="Damage")
        if c["dead"]:
            raise ValueError("%s is past caring about damage." % c["name"])
        said, name = [], c["name"]
        if c["kind"] == "character":
            sheet = self._sheet(s, c)
            was = sheet["hp"]["current"]
            result = ch.damage(sheet, n)                    # temporary hit points go first
            self._write(c, sheet)
            if was == 0:
                if c["stable"]:                             # hurt again: the count starts over
                    c["saves"] = [0, 0]
                c["stable"] = False
                if result == "dead":
                    c["flag"] = True
                    said.append("%s was at 0 and took as much as the hit point maximum. That is death outright. "
                                "The DM decides." % name)
                else:
                    c["saves"][1] = min(3, c["saves"][1] + 1)
                    if c["saves"][1] >= 3:
                        c["dead"] = True
                        said.append("Damage at 0 hit points is a failed death save, and that was the third. "
                                    "%s is dead." % name)
                    else:
                        said.append("Damage at 0 hit points: a failed death save for %s, %d of 3." % (name, c["saves"][1]))
            elif result != "ok":
                c["saves"], c["stable"] = [0, 0], False
                if "Unconscious" not in c["cond"]:
                    c["cond"].append("Unconscious")
                if result == "dead":
                    c["flag"] = True
                    said.append("%s drops to 0, and the damage left over is as much as the hit point maximum. "
                                "That is death outright. The DM decides." % name)
                else:
                    said.append("%s is down, at 0 hit points. Death saves start next turn." % name)
        else:
            c["hurt"] += n
            if c["max"] is not None and c["hurt"] >= c["max"]:
                c["dead"] = True
                said.append("%s is defeated." % name)
        if c["conc"]:
            if c["dead"] or self.down(c):
                c["conc"] = False
                s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
                said.append("Concentration ends.")
            else:
                dc = rules.conc_dc(n, s["edition"])
                s["prompts"].append({"who": c["id"], "dc": dc, "damage": n})
                said.append("%s was concentrating: Constitution save, DC %d." % (name, dc))
        return [] if c["hidden"] else said

    def _ev_heal(self, s, ev):
        c, n = self.find(s, ev.get("who")), self._amount(ev, what="Healing")
        if c["dead"]:
            raise ValueError("%s is dead. Healing is for the living." % c["name"])
        if c["kind"] != "character":
            c["hurt"] = max(0, c["hurt"] - n)
            return []
        sheet = self._sheet(s, c)
        was = sheet["hp"]["current"]
        ch.heal(sheet, n)
        self._write(c, sheet)
        if was == 0 and c["hp"] > 0:
            self._wake(c)
            return [] if c["hidden"] else ["%s is back up, on %d hit points." % (c["name"], c["hp"])]
        return []

    def _ev_temp(self, s, ev):
        c = self.find(s, ev.get("who"))
        if c["kind"] != "character":
            raise ValueError("Temporary hit points are kept on a character sheet.")
        n = self._amount(ev, 0, 999, "Temporary hit points")
        sheet = self._sheet(s, c)
        sheet["hp"]["temp"] = n
        self._write(c, sheet)
        return []

    def _ev_cond(self, s, ev):
        c, name = self.find(s, ev.get("who")), ev.get("name")
        if name not in rules.CONDITIONS:
            raise ValueError("I do not know that condition. Your book may.")
        if name in c["cond"]:
            c["cond"].remove(name)
        else:
            c["cond"].append(name)
        return []

    def _ev_conc(self, s, ev):
        c = self.find(s, ev.get("who"))
        on = bool(ev.get("on", not c["conc"]))
        if on and c["dead"]:
            raise ValueError("%s is past concentrating on anything." % c["name"])
        c["conc"] = on
        if not c["conc"]:
            s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
        return []

    def _ev_conc_save(self, s, ev):
        c = self.find(s, ev.get("who"))
        mine = [p for p in s["prompts"] if p["who"] == c["id"]]
        if not mine:
            raise ValueError("%s has no concentration save waiting." % c["name"])
        if ev.get("passed"):
            s["prompts"].remove(mine[0])
            return []
        c["conc"] = False
        s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
        return [] if c["hidden"] else ["%s loses concentration." % c["name"]]

    def _ev_save(self, s, ev):
        c = self.find(s, ev.get("who"))
        if not self.down(c) or c["stable"]:
            raise ValueError("%s is not making death saves." % c["name"])
        p, f, result = rules.death_save(c["saves"][0], c["saves"][1], bool(ev.get("passed")), ev.get("nat"))
        c["saves"] = [p, f]
        quiet = c["hidden"]                           # nothing about a hidden combatant is said to the table
        if result == "up":
            sheet = self._sheet(s, c)
            ch.heal(sheet, 1)
            self._write(c, sheet)
            self._wake(c)
            return [] if quiet else ["A 20. %s is back, on 1 hit point." % c["name"]]
        if result == "dead":
            c["dead"], c["conc"] = True, False
            s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
            return [] if quiet else ["That is three failed death saves. %s is dead." % c["name"]]
        if result == "stable":
            c["stable"] = True
            return [] if quiet else ["Three passed. %s is stable: still out cold, no longer dying." % c["name"]]
        return [] if quiet else ["%s: death saves, %d passed, %d failed." % (c["name"], p, f)]

    def _ev_confirm(self, s, ev):
        c = self.find(s, ev.get("who"))
        if not c["flag"]:
            raise ValueError("Nothing about %s is waiting on the DM." % c["name"])
        c["flag"] = False
        if ev.get("dead"):
            c["dead"], c["conc"] = True, False
            s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
            return [] if c["hidden"] else ["%s is dead. I am told these things happen." % c["name"]]
        return [] if c["hidden"] else ["%s is down, not dead." % c["name"]]

    def _ev_revive(self, s, ev):
        c = self.find(s, ev.get("who"))
        if not c["dead"]:
            raise ValueError("%s is not dead." % c["name"])
        c["dead"], c["flag"], c["saves"], c["stable"] = False, False, [0, 0], False
        if c["kind"] != "character" and c["max"] is not None and c["hurt"] >= c["max"]:
            c["hurt"] = c["max"] - 1
        self._join(s, c)
        return []

    def _ev_remove(self, s, ev):
        c = self.find(s, ev.get("who"))
        acting = s["fight"] and s["turn"] == c["id"]
        if s["fight"]:
            s["acted"] = [i for i in self.acted(s) if i != c["id"]]
        s["combatants"].remove(c)
        s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
        if acting:                                    # whoever is next takes over; with nobody left, nobody does
            s["turn"] = None
            self._advance(s)
        return []

    def _ev_hide(self, s, ev):
        c = self.find(s, ev.get("who"))
        c["hidden"] = bool(ev.get("on", not c["hidden"]))
        return []

    def _ev_sethp(self, s, ev):
        c = self.find(s, ev.get("who"))
        if c["kind"] == "character":
            raise ValueError("A character's hit points live on the sheet.")
        c["max"] = self._amount({"amount": ev.get("max")}, 1, 9999, "Hit points")
        was, c["dead"] = c["dead"], c["hurt"] >= c["max"]
        if c["dead"]:                                 # the dead keep no spell going and owe no save
            c["conc"] = False
            s["prompts"] = [p for p in s["prompts"] if p["who"] != c["id"]]
        elif was:
            self._join(s, c)
        return []

    def _ev_end(self, s, ev):
        if not s["fight"]:
            raise ValueError("There is no fight to end.")
        rounds = s["round"]
        s["combatants"] = [c for c in s["combatants"] if c["kind"] != "enemy"]
        for c in s["combatants"]:
            c["init"], c["tie"], c["conc"] = None, 0, False
        s["fight"], s["round"], s["turn"], s["prompts"], s["acted"] = False, 0, None, [], []
        return ["The fight is over, after %d round%s." % (rounds, "" if rounds == 1 else "s")]

    def _ev_rest(self, s, ev):
        if s["fight"]:
            raise ValueError("A long rest in the middle of a fight is optimistic. End the fight first.")
        names = []
        for c in s["combatants"]:
            if c["kind"] == "character":
                fname, sheet = self.locate(s, c)
                if sheet:
                    c["file"] = fname
                    names.append(fname)
        dead = {c.get("file") for c in s["combatants"] if c["kind"] == "character" and c["dead"]}
        names += [n for n, _ in party.party() if n not in names]
        rested, before = {"2014": [], "2024": []}, {}
        for fname in names:
            sheet = party.load(fname)
            if not sheet or fname in dead:
                continue
            party.stamp(sheet)                        # so undo can find this sheet again if it is renamed meanwhile
            before[fname] = {"id": sheet["id"], "hp": sheet["hp"]["current"], "temp": sheet["hp"].get("temp", 0),
                             "slots_used": copy.deepcopy(sheet.get("slots_used")), "pact_used": sheet.get("pact_used"),
                             "hit_dice_spent": sheet.get("hit_dice_spent")}
            ch.long_rest(sheet)
            party.write(sheet, fname)
            rested["2024" if str(sheet.get("edition", "2014")).startswith("2024") else "2014"].append(sheet["name"])
            c = self.combatant_for(s, fname)
            if c:
                self._mirror(c, sheet)
                self._wake(c)
        if not rested["2014"] and not rested["2024"]:
            raise ValueError("There is nobody with a sheet to rest.")
        s["rest_undo"] = before                       # what undo needs to put the files back as they were
        said = ["A long rest. Hit points and spell slots are back."]
        if rested["2014"] and rested["2024"]:
            said.append("Hit dice: all back for %s (2024 rules), half back for %s (2014 rules)."
                        % (rules.joined(rested["2024"]), rules.joined(rested["2014"])))
        elif rested["2024"]:
            said.append("Hit dice: all back, under the 2024 rules.")
        else:
            said.append("Hit dice: half back, under the 2014 rules.")
        return said

    def _ev_prep(self, s, ev):
        i = int(ev.get("i", -1))
        if not 0 <= i < len(s["prep"]):
            raise ValueError("That is not one of the prep steps.")
        s["prep"][i] = not s["prep"][i]
        return []


# ====================================================================== screens
def short(name, n=14):
    return name if len(name) <= n else name[:n - 1].rstrip() + "…"


class DndBase(PlayBase):
    """Base for every D&D screen. The strip says 'DM only' while DM mode is on."""
    heading = None

    @property
    def left(self):
        return "D&D · DM only" if self.app.dm else self.game.strip(self.session)[0]

    @property
    def title(self):
        return self.heading or self.game.strip(self.session)[1]

    @property
    def pill(self):
        return None

    def primary(self):
        self.app.pop()

    def on_button(self, gesture):
        """On the side screens the button is the main action. A double press
        always arrives as a press and then a double (see gestures.py). The
        press has already done that action, so the double adds nothing here;
        and when the press closed this screen the shell drops the double, so
        it never reaches the tracker underneath as an undo."""
        if gesture == "press":
            self.primary()

    def waiting(self):
        """The concentration saves this screen may show: a hidden combatant's only in DM mode."""
        got = []
        for p in self.state["prompts"]:
            c = self.game.get(self.state, p["who"])
            if c and (self.app.dm or not c["hidden"]):
                got.append(p)
        return got

    def ask_conc(self):
        """Put up the concentration save that is waiting, if there is one."""
        waiting = self.waiting()
        if waiting:
            self.app.push(ConcPrompt(self.app, self.session, waiting[0]))
            return True
        return False

    def status(self, c):
        """A word for how a combatant is doing, or ''. Never colour alone."""
        if c["dead"]:
            return "Dead" if c["kind"] == "character" else "Defeated"
        if c["flag"]:
            return "Dead? DM decides"
        if self.game.down(c):
            return "Stable" if c["stable"] else "Down"
        return ""

    def hp_words(self, c):
        """Hit points as this screen may show them. Enemies' only in DM mode."""
        if c["kind"] == "character":
            return "HP %d/%d" % (c["hp"], c["max"]) + (" +%d" % c["temp"] if c["temp"] else "")
        kind = rules.KIND_NAME[c["kind"]]
        if not self.app.dm:
            return kind
        if c["max"] is not None:
            return "%s %d/%d" % (kind, max(0, c["max"] - c["hurt"]), c["max"])
        return "%s −%d" % (kind, c["hurt"]) if c["hurt"] else kind


class Tracker(DndBase):
    """The initiative order. The button is 'next turn'."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self.page = None                          # None = follow whoever's turn it is

    @property
    def pill(self):
        c = self.game.current(self.state, self.app.dm)
        if not c:
            return None
        colour = T.player_colour(c["seat"]) if c.get("seat") is not None else T.TEXT
        return ("%s's turn" % short(c["name"], 12), colour)

    def enter(self):
        self.game.resync(self.session)            # a sheet changed elsewhere (a phone, a level-up): not an event
        super().enter()

    def shown(self):
        return self.game.order(self.state, self.app.dm)

    def build(self):
        s, dm, out = self.state, self.app.dm, []
        order = self.shown()
        n_pages = pages_for(len(order))
        ids = [c["id"] for c in order]
        page = self.page if self.page is not None else (ids.index(s["turn"]) // PER_PAGE if s["turn"] in ids and s["fight"] else 0)
        page = min(page, n_pages - 1)
        for i, c in enumerate(order[page * PER_PAGE:(page + 1) * PER_PAGE]):
            tags = (["Hidden"] if c["hidden"] else []) + (["Concentrating"] if c["conc"] else []) + c["cond"]
            right = self.status(c) or self.hp_words(c)
            out.append(Row(row_rect(i, w=606), c["name"], lambda c=c: self.open(c["id"]),
                           num="–" if c["init"] is None else c["init"], right=right, tags=tags,
                           selected=s["fight"] and c["id"] == s["turn"], dim=c["dead"],
                           bar=T.player_colour(c["seat"]) if c.get("seat") is not None else None))
        side = [("Party", self.party), ("DM desk" if dm else "DM", self.dm),
                ("End fight", self.end) if s["fight"] else ("Long rest", self.rest)]
        if n_pages > 1:
            side.append(("List %d/%d" % (page + 1, n_pages), lambda: self.turn_page(page, n_pages)))
        for i, (label, act) in enumerate(side):
            out.append(Button(row_rect(i, x=636, w=144), label, act, size=22))
        spec = [("Next turn" if s["fight"] else "Start fight", lambda: self.do(ev="next"), 1.6, "primary")]
        waiting = self.waiting()
        if waiting:
            spec.append(("Save DC %d" % waiting[0]["dc"], self.ask_conc, 1.3, "plain"))
        spec += [("Add", self.add, 0.9, "plain"), ("Undo", self.undo, 0.9, "plain"), ("Menu", self.more, 0.9, "plain")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def do(self, **ev):
        self.page = None
        if ev.get("ev") == "next" and self.app.dm and not self.state["fight"]:
            # The DM's own screen may be told which hidden one holds things up. It is
            # said here, for his eyes: not aloud, and not on the scoreboard page.
            missing = [c for c in rules.order(self.state["combatants"]) if not c["dead"] and c["init"] is None]
            if missing and all(c["hidden"] for c in missing):
                self._logged = False
                self.app.say("%s, who is hidden, has no initiative yet. Tap the name to enter it." % missing[0]["name"],
                             private=True)
                self.refresh()
                return False
        return super().do(**ev)

    def turn_page(self, page, n_pages):
        self.page = (page + 1) % n_pages
        self.refresh()

    def open(self, who):
        self.app.push(Combatant(self.app, self.session, who))

    def add(self):
        self.app.push(AddCombatant(self.app, self.session))

    def party(self):
        from .sheets import Party
        self.app.push(Party(self.app, self.session))

    def dm(self):
        from .dm import open_desk
        open_desk(self.app, self.session)

    def end(self):
        if self.do(ev="end"):
            self.app.push(Choice(self.app, "Long rest?", "The fight is over.\nDoes the party take a long rest now?",
                                 [("Not now", None), ("Long rest", self.rest)], left="D&D"))

    def rest(self):
        self.do(ev="rest")

    def hint(self):
        s, dm = self.state, self.app.dm
        for p in s["prompts"]:
            c = self.game.get(s, p["who"])
            if c and (dm or not c["hidden"]):
                return "%s: Constitution save, DC %d, to keep concentrating." % (c["name"], p["dc"]), T.WARN
        if not s["combatants"]:
            return "Nobody is here yet. Tap Add, or make characters under Party.", T.DIM
        if not s["fight"]:
            return "Tap a name to enter initiative, then start the fight.", T.DIM
        acted = self.game.acted(s)                # the players are shown the next one they can see
        seen = [c for c in rules.order(s["combatants"]) if not c["dead"] and c["id"] != s["turn"] and (dm or not c["hidden"])]
        nxt = next((c for c in seen if c["id"] not in acted), seen[0] if seen else None)
        hidden = sum(1 for c in s["combatants"] if c["hidden"])
        words = "Up next: %s." % nxt["name"] if nxt else ""
        if dm and hidden:
            words = (words + "  %d hidden from the players." % hidden).strip()
        return words, T.DIM

    def draw_body(self, surf):
        words, colour = self.hint()
        if words:
            T.draw_text(surf, words, "mid" if colour == T.WARN else "text", 22, colour, (20, HINT_Y), "midleft", max_w=760)
        if not self.shown():
            T.draw_text(surf, "An empty battlefield.", "head", 36, T.TEXT, (323, 170), "center", max_w=590)
            T.draw_text(surf, "I have seen livelier voids.", "text", 24, T.DIM, (323, 220), "center", max_w=590)

    def on_button(self, gesture):                 # here the button is the game's: next turn, undo
        PlayBase.on_button(self, gesture)
        if gesture == "press":
            self.page = None


class Combatant(DndBase):
    """One combatant: hit points, conditions, concentration, death saves."""

    def __init__(self, app, session, who):
        super().__init__(app, session)
        self.who = who

    def c(self):
        c = self.game.get(self.state, self.who)
        return c if c and (self.app.dm or not c["hidden"]) else None

    @property
    def heading(self):
        c = self.c()
        if not c:
            return "Gone"
        return "%s, %s" % (short(c["name"], 16), c.get("cls") or rules.KIND_NAME[c["kind"]])

    def build(self):
        c, dm = self.c(), self.app.dm
        self.ghost = bool(c and c["kind"] == "character" and not self.game.locate(self.state, c)[1])
        if not c:
            return row([("Back", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)
        out, who = [], c["id"]
        if c["flag"] and dm:
            out += [Button((20, 204, 375, 64), "Confirm: dead", lambda: self.do(ev="confirm", who=who, dead=True), size=22),
                    Button((405, 204, 375, 64), "Not dead, only down", lambda: self.do(ev="confirm", who=who, dead=False), size=22)]
        elif self.game.down(c) and not c["stable"] and not c["flag"]:
            for k, (label, ev) in enumerate([("Pass", {"passed": True}), ("Fail", {"passed": False}),
                                             ("A 1", {"passed": False, "nat": 1}), ("A 20", {"passed": True, "nat": 20})]):
                out.append(Button((356 + k * 107, 204, 103, 64), label, lambda ev=ev: self.do(ev="save", who=who, **ev), size=22))
        mine = [p for p in self.state["prompts"] if p["who"] == who]
        if mine:
            first = ("Save DC %d" % mine[0]["dc"], lambda: self.app.push(ConcPrompt(self.app, self.session, mine[0])))
        else:
            first = ("Drop concentration" if c["conc"] else "Start concentrating", lambda: self.do(ev="conc", who=who, on=not c["conc"]))
        init = "Initiative %s" % ("–" if c["init"] is None else c["init"])
        out += [Button((20, 276, 300, 64), first[0], first[1], size=22),
                Button((330, 276, 220, 64), init, self.initiative, size=22),
                Button((560, 276, 220, 64), "More", self.more_menu, size=22)]
        spec = [("Damage", self.damage, 1.2, "plain"), ("Heal", self.heal, 1, "plain"),
                ("Condition", self.condition, 1.3, "plain"), ("Back", self.app.pop, 1, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def pad(self, title, hint, then, **kw):
        self.app.push(NumberPad(self.app, title, then, hint, left=self.left, **kw))

    def damage(self):
        c = self.c()
        def then(n):
            if self.do(ev="damage", who=self.who, amount=n):
                self.ask_conc()
        hint = "How much damage does %s take?" % c["name"]
        if c["kind"] == "character":
            hint += " Temporary hit points go first."
        if c["conc"]:
            hint += " Then I work out the concentration save."
        self.pad("Damage", hint, then, low=1)

    def heal(self):
        self.pad("Healing", "How many hit points does %s get back?" % self.c()["name"],
                 lambda n: self.do(ev="heal", who=self.who, amount=n), low=1)

    def initiative(self):
        c = self.c()
        hint = "What did %s roll for initiative? The d20 plus the Dexterity modifier." % c["name"]
        if self.app.dm and c.get("bonus") is not None:
            hint += " Your book gave %s." % party.signed(c["bonus"])
        self.pad("Initiative", hint,
                 lambda n: self.do(ev="init", who=self.who, value=n), low=-10, high=50, negative=True,
                 start="" if c["init"] is None or c["init"] < 0 else c["init"])

    def condition(self):
        self.app.push(Conditions(self.app, self.session, self.who))

    def more_menu(self):
        self.app.push(CombatantMore(self.app, self.session, self.who))

    def draw_body(self, surf):
        c, dm = self.c(), self.app.dm
        if not c:
            T.draw_text(surf, "That combatant has left the fight.", "head5", 28, T.TEXT, (T.W // 2, 200), "center")
            return
        a = panel(surf, (20, 68, 375, 128), "Hit points")
        if c["kind"] == "character":
            big, small = "%d / %d" % (c["hp"], c["max"]), ("plus %d temporary" % c["temp"] if c["temp"] else "")
            if getattr(self, "ghost", False):     # said in words: these numbers are going to no file
                small = " · ".join(x for x in (small, "no sheet file, kept here only") if x)
        elif not dm:
            big, small = rules.KIND_NAME[c["kind"]], "The DM keeps count."
        elif c["max"] is not None:
            big, small = "%d / %d" % (max(0, c["max"] - c["hurt"]), c["max"]), "DM only"
        else:
            big, small = "%d taken" % c["hurt"], "DM only. No maximum set."
        if dm and c["kind"] != "character" and (c.get("ac") is not None or c.get("bonus") is not None):
            small = " · ".join(x for x in ("DM only", "AC %d" % c["ac"] if c.get("ac") is not None else "",
                                            "Init %s" % party.signed(c["bonus"]) if c.get("bonus") is not None else "") if x)
        T.draw_text(surf, big, "head", 44, T.TEXT, (a.x + 18, a.y + 34), max_w=200)
        status = self.status(c)
        if status:
            T.draw_text(surf, status, "bold", 24, T.WARN, (a.right - 18, a.y + 62), "midright", max_w=150)
        if small:
            T.draw_text(surf, small, "text", 22, T.DIM, (a.x + 18, a.y + 92), max_w=a.w - 36)
        b = panel(surf, (405, 68, 375, 128), "Conditions")
        words = ", ".join(c["cond"]) or "None"
        y = lines(surf, words, b.x + 18, b.y + 40, b.w - 36, 2 if c["conc"] else 3)
        if c["conc"]:
            T.draw_text(surf, "Concentrating", "bold", 22, T.TEXT, (b.x + 18, b.bottom - 34), max_w=b.w - 36)
        if c["flag"] and not dm:
            lines(surf, "That blow may have killed outright. The DM decides.", 20, 222, 760, 1, T.WARN, "mid")
        elif self.game.down(c) and not c["stable"] and not c["flag"]:
            for k, (word, n) in enumerate((("Passed", c["saves"][0]), ("Failed", c["saves"][1]))):
                y = 208 + k * 32
                T.draw_text(surf, word, "text", 22, T.TEXT, (20, y))
                for j in range(3):
                    box = (112 + j * 34, y, 26, 26)
                    pygame.draw.rect(surf, T.TEXT, box, 2, border_radius=6)
                    if j < n:
                        pygame.draw.rect(surf, T.TEXT, pygame.Rect(box).inflate(-10, -10), border_radius=3)
                T.draw_text(surf, "%d of 3" % n, "text", 22, T.DIM, (222, y))
        elif c["conc"] and not c["flag"]:
            lines(surf, "If %s takes damage: a Constitution save, DC 10 or half the damage, whichever is higher."
                  % c["name"], 20, 208, 760, 2, T.DIM)
        elif self.game.down(c) and c["stable"]:
            lines(surf, "Stable: out cold at 0 hit points, but no more death saves unless hurt again.", 20, 208, 760, 2, T.DIM)


class CombatantMore(DndBase):
    """The less common things to do to a combatant."""
    heading = "More"

    def __init__(self, app, session, who):
        super().__init__(app, session)
        self.who = who

    def build(self):
        c, dm, items = self.game.get(self.state, self.who), self.app.dm, []
        if c and (dm or not c["hidden"]):
            who = c["id"]
            items.append(("Wins ties", lambda: self.then(ev="tie", who=who)))
            if c["kind"] == "character":
                items.append(("Temporary HP", self.temp))
                if c.get("file"):
                    items.append(("Open sheet", self.sheet))
            items.append(("Remove from fight", self.remove))
            if dm:
                items.append(("Show to players" if c["hidden"] else "Hide from players",
                              lambda: self.then(ev="hide", who=who, on=not c["hidden"])))
                if c["kind"] != "character":
                    items.append(("Set hit points", self.sethp))
                if c["dead"]:
                    items.append(("Bring back", lambda: self.then(ev="revive", who=who)))
        out = [Button((20 + (i % 3) * 257, 142 + (i // 3) * 74, 247, 64), label, act, size=22)
               for i, (label, act) in enumerate(items)]
        return out + row([("Back", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def then(self, **ev):
        if self.do(**ev):
            self.app.pop()

    def remove(self):
        if self.do(ev="remove", who=self.who):
            self.app.pop()
            self.app.pop()                         # the combatant's own screen has nothing left to show

    def temp(self):
        self.app.push(NumberPad(self.app, "Temporary HP", lambda n: self.then(ev="temp", who=self.who, amount=n),
                                "Temporary hit points are lost before real ones. They do not stack: enter the new total.",
                                left=self.left))

    def sethp(self):
        self.app.push(NumberPad(self.app, "Hit points", lambda n: self.then(ev="sethp", who=self.who, max=n),
                                "DM only. The hit point maximum from your own book. I count down from it and "
                                "show it to nobody else.", low=1, high=9999, left=self.left))

    def sheet(self):
        from .sheets import Sheet
        c = self.game.get(self.state, self.who)
        self.app.pop()                             # closing the sheet returns to the combatant
        self.app.push(Sheet(self.app, self.session, c["file"]))

    def draw_body(self, surf):
        c = self.game.get(self.state, self.who)
        if c and (self.app.dm or not c["hidden"]):
            T.draw_text(surf, c["name"], "head", 36, T.TEXT, (20, 76), max_w=760)


class Conditions(DndBase):
    """Tick the conditions on a combatant. Names only: the book says what they do."""
    heading = "Conditions"

    def __init__(self, app, session, who):
        super().__init__(app, session)
        self.who = who

    def build(self):
        c, out = self.game.get(self.state, self.who), []
        if c:
            for i, name in enumerate(rules.CONDITIONS):
                rect = (20 + (i % 4) * 192, 68 + (i // 4) * 70, 184, 64)
                out.append(Button(rect, name, lambda name=name: self.do(ev="cond", who=self.who, name=name),
                                  selected=name in c["cond"], size=22))
            out.append(Button((20 + 3 * 192, 68 + 3 * 70, 184, 64), "Concentrating",
                              lambda: self.do(ev="conc", who=self.who, on=not c["conc"]), selected=c["conc"], size=22))
        return out + row([("Done", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        c = self.game.get(self.state, self.who)
        if c:
            on = len(c["cond"]) + (1 if c["conc"] else 0)
            T.draw_text(surf, "%s: %d on. What each one does is in your book, under Conditions." % (c["name"], on),
                        "text", 22, T.DIM, (20, HINT_Y - 8), "midleft", max_w=760)


class ConcPrompt(DndBase):
    """A concentrating combatant took damage: did the save hold?"""
    heading = "Concentration"

    def __init__(self, app, session, prompt):
        super().__init__(app, session)
        self.prompt = prompt

    def build(self):
        return row([("Kept it", lambda: self.answer(True), 1.4, "primary"),
                    ("Lost it", lambda: self.answer(False), 1, "plain")], BOTTOM_Y, BOTTOM_H)

    def answer(self, passed):
        said = self.session.do(ev="conc_save", who=self.prompt["who"], passed=passed)
        self.app.pop()
        if said:
            self.app.say(" ".join(said))

    def primary(self):
        self.answer(True)

    def on_button(self, gesture):
        if gesture == "press":
            self.answer(True)

    def draw_body(self, surf):
        c = self.game.get(self.state, self.prompt["who"])
        name = c["name"] if c else "Someone"
        T.draw_text(surf, "%s took %d damage while concentrating." % (name, self.prompt["damage"]), "head5", 28,
                    T.TEXT, (40, 100), max_w=720)
        T.draw_text(surf, "Constitution save, DC %d" % self.prompt["dc"], "head", 52, T.TEXT, (40, 150), max_w=720)
        lines(surf, "Roll a d20 and add the Constitution save bonus. Equal or higher keeps the spell going. "
              "The number is 10, or half the damage rounded down, whichever is higher.", 40, 240, 720, 4, T.DIM,
              size=24, pitch=32)


class AddCombatant(DndBase):
    """Add enemies, allies or a character. Tap a name, then give the initiative."""
    heading = "Add to the fight"

    def __init__(self, app, session, collect=None):
        super().__init__(app, session)
        self.kind, self.count, self.hidden = "enemy", 1, False
        self.collect = collect                    # the DM's fight loader: hand the choice back, add nothing yet
        self.any = True

    def choices(self):
        if self.kind == "character":
            here = {c.get("file") for c in self.state["combatants"] if c["kind"] == "character"}
            return [(sheet["name"], lambda n=n: self.pick_character(n)) for n, sheet in party.roster() if n not in here][:12]
        names = rules.ENEMY_NAMES if self.kind == "enemy" else rules.ALLY_NAMES
        return [(n, lambda n=n: self.pick(n, True)) for n in names] + [("Type a name", self.type_name)]

    def build(self):
        out = []
        for k, kind in enumerate(() if self.collect else rules.KINDS[1:] + rules.KINDS[:1]):
            out.append(Button((20 + k * 158, 68, 150, 64), rules.KIND_NAME[kind], lambda kind=kind: self.set_kind(kind),
                              selected=kind == self.kind, size=22))
        if self.kind != "character":
            out += [Button((572, 68, 68, 64), "−", lambda: self.step(-1), size=30),
                    Button((712, 68, 68, 64), "+", lambda: self.step(1), size=30)]
        found = self.choices()
        self.any = bool(found)
        for i, (label, act) in enumerate(found):
            out.append(Button((20 + (i % 4) * 192, 142 + (i // 4) * 70, 184, 64), label, act, size=22))
        spec = [("Back", self.app.pop, 1.5, "primary")]
        if self.app.dm and self.kind != "character" and not self.collect:
            spec.append(("Hidden: %s" % ("yes" if self.hidden else "no"), self.toggle_hidden, 1, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def set_kind(self, kind):
        self.kind = kind
        self.refresh()

    def step(self, d):
        self.count = max(1, min(rules.MAX_GROUP, self.count + d))
        self.refresh()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        self.refresh()

    def ask_init(self, name, then):
        skip = None if self.state["fight"] else ("Enter it later", lambda: then(None))
        self.app.push(NumberPad(self.app, "Initiative", then,
                                "Initiative for %s: the d20 plus the Dexterity modifier." % name,
                                low=-10, high=50, negative=True, skip=skip, left=self.left))

    def pick(self, base, numbered):
        if self.collect:
            self.app.pop()
            return self.collect(base, self.count, numbered)

        def then(init):
            if self.do(ev="add", kind=self.kind, base=base, count=self.count, init=init, numbered=numbered,
                       hidden=self.hidden and self.app.dm):
                self.app.pop()
        self.ask_init(base if self.count == 1 else "%d × %s" % (self.count, base), then)

    def type_name(self):
        def done(text):
            if text:
                self.pick(text.title()[:18], self.count > 1)
        self.app.push(TextEntry(self.app, "Name", "", done, "Done", max_len=18))

    def pick_character(self, fname):
        def then(init):
            if self.do(ev="add_char", file=fname, init=init):
                self.app.pop()
        sheet = party.load(fname)
        self.ask_init(sheet["name"] if sheet else "them", then)

    def draw_body(self, surf):
        if self.kind != "character":
            T.draw_text(surf, "× %d" % self.count, "head", 34, T.TEXT, (676, 100), "center")
            words = "Tap a name. They are numbered for you, and share one initiative."
            if self.collect:
                words = "Tap a name for the enemies you expect. Next comes their hit points."
        elif self.any:
            words = "Tap a character. Sheets still to be checked are under Party."
        else:
            words = "Every checked character is already here. New ones start under Party."
        T.draw_text(surf, words, "text", 22, T.DIM, (20, HINT_Y - 4), "midleft", max_w=760)
