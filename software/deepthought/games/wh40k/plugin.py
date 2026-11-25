"""Warhammer 40,000. The box keeps the battle round, the phase, whose turn it
is, both players' command and victory points, and how much of each army is
left. The players keep the table, the datasheets and the mission cards."""
import json
import os
import random
import pygame
from ... import theme as T
from ...app import Screen
from ...engine import Game
from ...screens.common import BOTTOM_H, BOTTOM_Y, Pages, PlayBase, TextEntry
from ...screens.extras import GameMenu
from ...widgets import Button, row
from . import rules

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE_NAME = dict(rules.PHASES)
BAR = ["Command", "Move", "Shoot", "Charge", "Fight"]          # the short names on the phase bar
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
MODES = ["Teach", "Reminder", "Silent"]
NECRONS = ["Player 1", "Player 2", "Nobody"]

# Teach mode: the steps read before the first turn, in order. Ids are in teach.json.
INTRO = ["premise", "datasheet", "table", "deploy", "first", "command"]
# The one word a player tells the box, the phase it belongs to, the card it
# earns the first time, and the line it earns after that.
DID = {
    "advance": ("movement", "advance", "Advance: one extra die of inches. No charge after, and only Assault weapons fire."),
    "fallback": ("movement", "fallback", "Fall Back: out of the fight. Normally no shooting and no charge this turn."),
    "charge": ("charge", "charge1", "Charge: two dice for the distance, then targets within it. End within two inches."),
}


def presets():
    """Ready-made lists: unit names and model counts only."""
    with open(os.path.join(HERE, "armies.json"), encoding="utf-8") as f:
        return json.load(f)


def secondary_table():
    """The names a player may pick a secondary from: [{"name", "cap", "scores"}].
    Read from secondaries.json each time, so an edit shows at once. A broken
    or missing file gives an empty list, and names are then typed."""
    try:
        with open(os.path.join(HERE, "secondaries.json"), encoding="utf-8") as f:
            rows = json.load(f)["secondaries"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        name = rules.sec_clean(r.get("name")) if isinstance(r, dict) else ""
        cap = r.get("cap") if name else None
        if name and name.lower() not in [x["name"].lower() for x in out]:
            out.append({"name": name, "cap": cap if isinstance(cap, int) and not isinstance(cap, bool) and cap > 0 else None,
                        "scores": " ".join(str(r.get("scores") or "").split())})
    return out


# What she says, once, when a phase runs past the limit. %s is the limit in words.
NUDGE_LINES = ["%s on one phase. I mention it only because I can count.",
               "This phase is still going. So, I observe, is the clock.",
               "%s have passed in this phase. I shall not bring it up again.",
               "Time passes. I notice it so that you need not."]
WARN_SECS = 3.2                               # how long the ring blinks amber: two double blinks


def nudge_secs(session):
    """The slow-play limit for this game, in seconds; 0 is off. It is kept
    with the session's options. Until a player chooses, it is the default,
    except in Teach mode, where a first game is allowed to be slow."""
    v = session.d["options"].get("nudge")
    if isinstance(v, int) and not isinstance(v, bool) and v in [secs for _, secs, _ in rules.NUDGES]:
        return v
    return 0 if session.state.get("mode") == "teach" else rules.NUDGES[0][1]


def nudge_label(secs):
    return next((label for label, v, _ in rules.NUDGES if v == secs), "Off")


def number(n):
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


class Plugin(Game):
    min_players, max_players = 2, 2
    options = [{"key": "mode", "label": "Mode", "choices": MODES},
               {"key": "length", "label": "Length", "choices": [name for name, _ in rules.LENGTHS]},
               {"key": "size", "label": "Size", "choices": rules.GAME_SIZES},
               {"key": "necrons", "label": "Necrons", "choices": NECRONS}]

    # ---- state
    def new_state(self, players, options):
        mode = str(options.get("mode", MODES[0])).lower()
        mode = mode if mode in ("teach", "reminder", "silent") else "teach"
        rounds = rules.rounds_for(options.get("length"))
        army = [[], []]
        side = {"player 1": 0, "player 2": 1}.get(str(options.get("necrons", NECRONS[0])).lower())
        if side is not None:
            army[side] = [rules.new_unit(u["name"], u["size"]) for u in presets()["necrons"]["units"]]
        return {"round": 1, "rounds": rounds, "active": 0, "first": 0, "phase": "command", "done": False,
                "mode": mode, "size": options.get("size", rules.GAME_SIZES[0]), "names": list(players),
                "cp": [rules.CP_PER_COMMAND, rules.CP_PER_COMMAND],      # the first Command phase has begun
                "primary": [[0] * (rounds + 1), [0] * (rounds + 1)],     # per battle round, then end of game
                "secs": [rules.new_secs(), rules.new_secs()],            # each player's named secondaries
                "army": army, "made": [0, 0],
                "taught": list(INTRO) if mode == "teach" else [],
                "pending": []}           # teach cards the last event made due (shown again if the power went)

    def phases(self):
        return rules.PHASES

    def active(self, s):
        return None if s["done"] or s["phase"] == rules.END else s["active"]

    def secs(self, s, side):
        """One side's secondary rows. A game saved before secondaries had
        names holds two bare numbers instead; they read as two unnamed rows."""
        if "secs" in s:
            return s["secs"][side]
        return rules.new_secs(points=s.get("sec", [[], []])[side])

    def score(self, s, side):
        """(primary, secondary, total) for one side."""
        return rules.totals(s["primary"][side], [r["pts"] for r in self.secs(s, side)])

    def pace_key(self, s):
        """What the slow-play clock is timing: this phase of this turn, or None."""
        if s["done"] or s["phase"] == rules.END:
            return None
        return (s["round"], s["active"], s["phase"])

    def tests(self, s, side):
        """Names of this side's units that take a battle-shock test."""
        return [u["name"] for u in s["army"][side] if rules.needs_test(u)]

    def can_swap(self, s):
        """Who takes the first turn can change until the first turn moves on."""
        return s["round"] == 1 and s["phase"] == "command" and s["active"] == s["first"] and not s["done"]

    def _teach(self, s, key):
        if s["mode"] == "teach" and key not in s["taught"]:
            s["taught"].append(key)
            s["pending"] = s.get("pending", []) + [key]

    def _cp_remark(self, s, side):
        return "%s has %d command points. More than %s is rare. I merely mention it." % (
            s["names"][side], s["cp"][side], number(rules.CP_WARN_ABOVE))

    def _enter(self, s, new_round):
        """A phase has just begun. Returns what to say."""
        said, names, me, talk = [], s["names"], s["active"], s["mode"] != "silent"
        if s["phase"] == rules.END:
            self._teach(s, "after")          # the last card: what to learn next
            return ["The last turn is done. Add any end-of-game points, then press the button."] if talk else []
        if s["phase"] == "command":
            for i in (0, 1):
                s["cp"][i] += rules.CP_PER_COMMAND
            need = self.tests(s, me)
            if talk:
                if new_round:
                    said.append("Final round." if s["round"] == s["rounds"] else "Battle round %s." % number(s["round"]))
                said.append("%s's turn. Command points: %s %d, %s %d." % (names[me], names[0], s["cp"][0],
                                                                          names[1], s["cp"][1]))
                said += [self._cp_remark(s, i) for i in (0, 1) if rules.cp_warning(s["cp"][i])]
                if need:
                    said.append("Battle-shock tests are due.")
            if not new_round:
                self._teach(s, "turn2")
            if s["round"] == rules.SCORING["primary_from_round"]:
                self._teach(s, "round2")
            if s["round"] == s["rounds"]:
                self._teach(s, "final")
            if need:
                self._teach(s, "shock")
        self._teach(s, s["phase"])
        return said

    # ---- every rule the box enforces
    def apply(self, s, ev):
        kind, names, talk = ev.get("ev"), s["names"], s["mode"] != "silent"
        side = ev.get("side", s["active"])
        if side not in (0, 1):
            raise ValueError("There are two sides in this exercise.")
        if "secs" not in s:                  # a game saved before secondaries had names
            s["secs"] = [self.secs(s, i) for i in (0, 1)]
            s.pop("sec", None)
        s["pending"] = []
        if kind == "next":
            if s["phase"] == rules.END:
                s["done"] = True
                return []
            before = s["round"]
            s["phase"], s["active"], s["round"] = rules.step(s["phase"], s["active"], s["first"], s["round"], s["rounds"])
            return self._enter(s, s["round"] != before)
        if kind == "first":
            if not self.can_swap(s):
                raise ValueError("The first turn has already begun. It is too late to swap.")
            s["first"] = s["active"] = side
            return ["%s takes the first turn." % names[side]] if talk else []
        if kind == "score":
            delta, final = int(ev.get("delta", 1)), s["phase"] == rules.END
            if ev.get("cat") == "primary":
                s["primary"][side] = rules.add_primary(s["primary"][side], s["round"], delta, final)
            elif ev.get("cat") == "sec":
                s["secs"][side] = rules.sec_score(s["secs"][side], int(ev.get("row", 0)), delta)
            else:
                raise ValueError("Points are primary or secondary. There is no third kind.")
            return []
        if kind == "sec":
            op, slot = ev.get("op"), ev.get("slot")
            if op == "name":
                name, cap = ev.get("name"), ev.get("cap")
                if name is None:             # from a phone: the name was picked or typed there, as "text"
                    name = rules.sec_clean(ev.get("text"))
                    cap = next((e["cap"] for e in secondary_table() if e["name"].lower() == name.lower()), None)
                s["secs"][side] = rules.sec_name(s["secs"][side], slot, name, cap)
            elif op == "away":
                s["secs"][side] = rules.sec_away(s["secs"][side], slot)
            else:
                raise ValueError("A secondary can be named or put away. Nothing else.")
            return []
        if kind == "cp":
            delta = int(ev.get("delta", -1))
            if s["cp"][side] + delta < 0:
                raise ValueError("%s has no command points to spend." % names[side])
            s["cp"][side] += delta
            if delta < 0:
                self._teach(s, "strat")
            if delta > 0 and rules.cp_warning(s["cp"][side]) and talk:
                return [self._cp_remark(s, side)]
            return []
        if kind == "model":
            u = self._unit(s, side, ev)
            was = rules.below_half(u["start"], u["alive"], u["hurt"])
            u["alive"], u["hurt"] = rules.step_model(u["start"], u["alive"], u["hurt"], int(ev.get("delta", -1)))
            if u["alive"] == 0:
                u["shocked"] = False
                return ["%s: destroyed. It is no longer participating." % u["name"]] if talk else []
            if not was and rules.below_half(u["start"], u["alive"], u["hurt"]) and talk:
                return ["%s is below half strength. A battle-shock test in %s's Command phase."
                        % (u["name"], names[side])]
            return []
        if kind == "shock":
            u = self._unit(s, side, ev)
            if u["alive"] == 0:
                raise ValueError("%s is destroyed. Nothing shocks it now." % u["name"])
            u["shocked"] = not u["shocked"]
            self._teach(s, "shock")
            return []
        if kind == "did":
            if ev.get("what") not in DID:
                raise ValueError("I do not know that move.")
            phase, card, line = DID[ev["what"]]
            if s["phase"] != phase:
                raise ValueError("That belongs to the %s phase." % PHASE_NAME[phase])
            if s["mode"] == "teach" and card not in s["taught"]:
                self._teach(s, card)
                return []
            return [line]
        if kind == "army":
            return self._edit(s, side, ev)
        raise ValueError("I do not know what %r means in Warhammer 40,000." % kind)

    def _unit(self, s, side, ev):
        k = ev.get("unit")
        if not isinstance(k, int) or not 0 <= k < len(s["army"][side]):
            raise ValueError("There is no such unit on %s's list." % s["names"][side])
        return s["army"][side][k]

    def _edit(self, s, side, ev):
        """Build or change a list. Changing a unit's size puts it back to full strength."""
        army, op = s["army"][side], ev.get("op")
        if op == "add":
            if len(army) >= rules.MAX_UNITS:
                raise ValueError("%d units is all I will list for one side." % rules.MAX_UNITS)
            s["made"][side] += 1
            army.append(rules.new_unit("Unit %d" % s["made"][side], ev.get("size", 5)))
        elif op == "size":
            u = self._unit(s, side, ev)
            size = u["start"] + int(ev.get("delta", 1))
            if not 1 <= size <= rules.MAX_MODELS:
                raise ValueError("A unit has between 1 and %d models." % rules.MAX_MODELS)
            army[ev["unit"]] = rules.new_unit(u["name"], size)
        elif op == "remove":
            self._unit(s, side, ev)
            del army[ev["unit"]]
        elif op == "preset":
            name = ev.get("name", "necrons")
            if name not in presets():
                raise ValueError("I have no list called %s." % name)
            s["army"][side] = [rules.new_unit(u["name"], u["size"]) for u in presets()[name]["units"]]
        else:
            raise ValueError("I do not know that change to a list.")
        return []

    # ---- results
    def over(self, s):
        if not s["done"]:
            return None
        a, b = self.score(s, 0), self.score(s, 1)
        names, win = s["names"], rules.winner(a[2], b[2])
        detail = "%s: %d primary, %d secondary. %s: %d and %d." % (names[0], a[0], a[1], names[1], b[0], b[1])
        if win is None:
            return {"winner": None, "lines": ["A draw: %d to %d" % (a[2], b[2]), detail]}
        hi, lo = max(a[2], b[2]), min(a[2], b[2])
        return {"winner": names[win], "lines": ["%d victory points to %d" % (hi, lo), detail]}

    def leader(self, s):
        return rules.winner(self.score(s, 0)[2], self.score(s, 1)[2])

    def standings(self, s, players):
        a, b = self.score(s, 0)[2], self.score(s, 1)[2]
        return ["Victory points: %s %d, %s %d" % (players[0], a, players[1], b),
                "Stopped in battle round %d of %d" % (s["round"], s["rounds"])]

    # ---- what is shown elsewhere
    def strip(self, session):
        s = session.state
        title = "Final scores" if s["phase"] == rules.END else PHASE_NAME[s["phase"]] + " phase"
        return "40k · Round %d of %d" % (s["round"], s["rounds"]), title

    def where(self, s):
        if s["phase"] == rules.END:
            return "Final scores"
        return "Battle round %d of %d, %s phase, %s's turn" % (s["round"], s["rounds"], PHASE_NAME[s["phase"]],
                                                              s["names"][s["active"]])

    def scoreboard(self, session):
        s, rows = session.state, []
        for i, name in enumerate(session.players):
            p, sec, total = self.score(s, i)
            mine = self.secs(s, i)
            rows.append({"name": name, "value": total, "primary": p, "secondary": sec, "cp": s["cp"][i],
                         "units": rules.units_alive(s["army"][i]), "units_start": len(s["army"][i]),
                         "sub": rules.sec_words(mine),          # the line under the name on the shared page
                         "secondaries": [{"name": r["name"], "points": r["pts"], "now": r["slot"] is not None}
                                         for r in mine if rules.sec_named(r) or r["pts"]]})
        return {"rows": rows, "note": self.where(s)}

    def phone(self, session, seat):
        """A player's phone: their own points, their own command points, their own models."""
        s = session.state
        if seat not in (0, 1):
            return {"lines": [self.where(s)], "actions": []}
        p, sec, total = self.score(s, seat)
        lines = [self.where(s), "Victory points: %d (%d primary, %d secondary)" % (total, p, sec),
                 "Command points: %d" % s["cp"][seat]]
        mine = self.secs(s, seat)
        if rules.sec_words(mine):
            lines.append("Secondaries: " + rules.sec_words(mine))
        actions = []
        if self.active(s) == seat or (s["phase"] == rules.END and not s["done"]):
            actions.append({"label": "Finish" if s["phase"] == rules.END else "Next phase", "ev": {"ev": "next"}})
        actions += [{"label": "Primary +1", "ev": {"ev": "score", "side": seat, "cat": "primary", "delta": 1}},
                    {"label": "Primary -1", "ev": {"ev": "score", "side": seat, "cat": "primary", "delta": -1}}]
        for k in range(len(rules.SCORING["secondary_rows"])):
            r = rules.sec_at(mine, k) or {"name": rules.sec_default(k)}
            actions += [{"label": "%s +1" % r["name"], "ev": {"ev": "score", "side": seat, "cat": "sec", "row": k, "delta": 1}},
                        {"label": "%s -1" % r["name"], "ev": {"ev": "score", "side": seat, "cat": "sec", "row": k, "delta": -1}}]
        actions.append({"label": "Spend 1 command point", "ev": {"ev": "cp", "side": seat, "delta": -1}})
        names = [e["name"] for e in secondary_table()]
        for k in range(len(rules.SCORING["secondary_rows"])):     # name your own secondaries, as on the box
            r = rules.sec_at(mine, k)
            named = bool(r) and rules.sec_named(r)
            actions.append({"label": "Change %s" % r["name"] if named else "Name %s" % rules.sec_default(k),
                            "ev": {"ev": "sec", "side": seat, "op": "name", "slot": k},
                            "ask": "Which secondary is it? Your card says what scores.",
                            "choices": names, "max": rules.MAX_SEC_NAME})
            if named:
                actions.append({"label": "Put away %s" % r["name"], "ev": {"ev": "sec", "side": seat, "op": "away", "slot": k}})
        for k, u in enumerate(s["army"][seat]):
            lines.append("%s: %s" % (u["name"], unit_words(u)))
            if u["alive"] > 0:
                actions.append({"label": "%s: lose a model" % u["name"],
                                "ev": {"ev": "model", "side": seat, "unit": k, "delta": -1}})
            if u["alive"] < u["start"] or u["hurt"]:
                actions.append({"label": "%s: restore a model" % u["name"],
                                "ev": {"ev": "model", "side": seat, "unit": k, "delta": 1}})
        return {"lines": lines, "actions": actions}

    def play_screen(self, app, session):
        return W40kPlay(app, session)

    def cards(self, keys):
        """Teach steps by id, in the order asked for: [(title, text)]."""
        by_id = {x.get("id"): x for x in self.teach()}
        return [(by_id[k]["title"], by_id[k]["text"]) for k in keys if k in by_id]


def unit_words(u):
    """'18 of 20, below half' and the like: how a unit stands, in words."""
    if u["alive"] <= 0:
        return "destroyed"
    out = "%d of %d" % (u["alive"], u["start"])
    if rules.below_half(u["start"], u["alive"], u["hurt"]):
        out += ", below half"
    if u["shocked"]:
        out += ", shocked"
    return out


def prompt(s):
    """The large line and the small line for the phase in hand."""
    me = s["names"][s["active"]]
    other = s["names"][1 - s["active"]]
    ph = s["phase"]
    if ph == rules.END:
        return "The last turn is done.", "Add any end-of-game points your mission gives. Then press the button."
    if ph == "command":
        if s["round"] >= rules.SCORING["primary_from_round"]:
            return ("%s, score first." % me,
                    "Count the objectives you hold now and tap Score. Then battle-shock tests.")
        if s["active"] == s["first"]:
            return ("%s takes the first turn." % me,
                    "Both of you gain a command point. I have added them. Nothing scores yet.")
        return "%s, Command phase." % me, "Both of you gain a command point. I have added them."
    if ph == "movement":
        return "%s, move your units." % me, "A normal move, an Advance, a Fall Back, or stay put. Reserves arrive now."
    if ph == "shooting":
        return "%s, pick a unit to shoot with." % me, "Roll to hit, then to wound. %s rolls the saves." % other
    if ph == "charge":
        return "%s, charge if you must." % me, "Roll two dice for the distance first. Then name targets within it."
    return ("Fight. Chargers strike first.",
            "Then take turns choosing a unit to fight. %s chooses first." % other)


# ---------------------------------------------------------------- widgets
class Versus:
    """A panel with one number for each player, each under or beside their
    name. Tap it if it has an action."""

    def __init__(self, rect, label, values, names, action=None, note=None):
        self.rect = pygame.Rect(rect)
        self.label, self.values, self.names, self.action, self.note = label, values, names, action, note
        self.style, self.selected = "number", False

    def draw(self, surf, pressed=False):
        r = self.rect
        pygame.draw.rect(surf, T.RAISED if pressed else T.PANEL, r, border_radius=14)
        pygame.draw.rect(surf, T.LINE, r, 1, border_radius=14)
        a, b = (str(v) for v in self.values)
        if r.h >= 100:                       # tall: each number over its player's name
            T.draw_text(surf, self.label, "text", 22, T.DIM, (r.x + 20, r.y + 8))
            if self.note:
                T.draw_text(surf, self.note, "bold", 22, T.WARN, (r.right - 20, r.y + 8), "topright", max_w=r.w - 260)
            for i, v in enumerate((a, b)):
                cx = r.x + r.w * (1 + 2 * i) // 4
                T.draw_text(surf, v, "head", 60, T.player_colour(i), (cx, r.y + 62), "center")
                T.draw_text(surf, self.names[i], "bold", 22, T.TEXT, (cx, r.bottom - 20), "center", max_w=r.w // 2 - 60)
            T.draw_text(surf, "to", "text", 26, T.DIM, (r.centerx, r.y + 62), "center")
            return
        x = r.right - 18                     # short: the numbers at the right, the names in words at the left
        box = T.draw_text(surf, b, "head", 40, T.player_colour(1), (x, r.centery), "midright")
        box = T.draw_text(surf, "to", "text", 24, T.DIM, (box.left - 10, r.centery), "midright")
        box = T.draw_text(surf, a, "head", 40, T.player_colour(0), (box.left - 10, r.centery), "midright")
        room = box.left - r.x - 28
        T.draw_text(surf, self.label, "text", 22, T.DIM, (r.x + 18, r.y + 9), max_w=room)
        if self.note:
            T.draw_text(surf, self.note, "bold", 22, T.WARN, (r.x + 18, r.y + 39), max_w=room)
        else:
            T.draw_text(surf, "%s to %s" % tuple(self.names), "text", 22, T.TEXT, (r.x + 18, r.y + 39), max_w=room)


class Cell:
    """A box with a word on the left and a number on the right. Tappable when
    it has an action. label is its name for the tests; it is not drawn."""
    style, selected = "cell", False

    def __init__(self, rect, label, text, value, action=None, value_colour=None):
        self.rect = pygame.Rect(rect)
        self.label, self.text, self.value, self.action, self.value_colour = label, text, str(value), action, value_colour

    def draw(self, surf, pressed=False):
        r = self.rect
        bg = (T.LINE if pressed else T.RAISED) if self.action else T.GROUND
        pygame.draw.rect(surf, bg, r, border_radius=12)
        pygame.draw.rect(surf, T.LINE, r, 1, border_radius=12)
        vw = T.font("head", 34).size(self.value)[0]
        T.draw_text(surf, self.text, "mid", 22, T.TEXT if self.action else T.DIM, (r.x + 14, r.centery), "midleft",
                    max_w=max(40, r.w - 40 - vw))
        T.draw_text(surf, self.value, "head", 34, self.value_colour or T.TEXT, (r.right - 14, r.centery), "midright")


class NameRow:
    """A name to pick, with a few words under it. The one in use has a thick
    light edge and the word 'now'."""
    style = "plain"

    def __init__(self, rect, label, sub, action, selected=False):
        self.rect = pygame.Rect(rect)
        self.label, self.sub, self.action, self.selected = label, sub, action, selected

    def draw(self, surf, pressed=False):
        r = self.rect
        pygame.draw.rect(surf, T.LINE if pressed else T.RAISED, r, border_radius=12)
        pygame.draw.rect(surf, T.TEXT if self.selected else T.LINE, r, 3 if self.selected else 1, border_radius=12)
        room = r.w - 28 - (56 if self.selected else 0)
        T.draw_text(surf, self.label, "bold", 24, T.TEXT, (r.x + 14, r.y + 3), max_w=room)
        T.draw_text(surf, self.sub, "text", 22, T.DIM, (r.x + 14, r.y + 33), max_w=r.w - 28)
        if self.selected:
            T.draw_text(surf, "now", "bold", 22, T.TEXT, (r.right - 14, r.y + 5), "topright")


# ---------------------------------------------------------------- screens
class W40kMenu(GameMenu):
    """The shared Menu, with one thing added for this game: how long a
    phase may run before she mentions it."""

    def __init__(self, app, session, changed=None):
        super().__init__(app, session)
        self.changed = changed

    def build(self):
        ws = super().build()
        bottom = [x for x in ws if x.rect.y >= BOTTOM_Y]
        spec = [(x.label, x.action, x.rect.w, x.style) for x in bottom]
        spec.append(("Nudge: " + nudge_label(nudge_secs(self.session)), self.nudge, 260, "plain"))
        return [x for x in ws if x.rect.y < BOTTOM_Y] + row(spec, BOTTOM_Y, BOTTOM_H)

    def nudge(self):
        secs = [v for _, v, _ in rules.NUDGES]
        now = secs[(secs.index(nudge_secs(self.session)) + 1) % len(secs)]
        self.session.d["options"]["nudge"] = now      # kept with the saved game
        self.session.save()
        if self.changed:
            self.changed()                            # the clock starts again from now
        words = next(w for _, v, w in rules.NUDGES if v == now)
        if now:
            self.app.say("%s a phase. Past that I will mention it, once." % words)
        else:
            self.app.say("I will keep the time to myself.")
        self.refresh()


class TeachCard(Pages):
    """One or more teach steps as cards. The button reads on, then closes."""

    def __init__(self, app, steps, opener=None):
        super().__init__(app, "40k · Teach", "Teach step", steps)
        self.opener = opener                  # the screen whose event brought this card up
        self.at = len(opener.session.log) if opener is not None else None

    def on_button(self, gesture):
        if gesture == "double" and self.opener is not None:
            # The press that came with this double only turned a page, so
            # exactly one event goes: the one that brought this card. If
            # anything has been logged since, nothing does.
            session = self.opener.session
            mine = len(session.log) == self.at and not session.finished
            self.close()
            if mine:
                self.opener.undo()
        else:
            super().on_button(gesture)

    def build(self):
        n, last = len(self.pages), self.i + 1 >= len(self.pages)
        spec = []
        if not last:
            spec.append(("Skip", self.app.pop, 1, "plain"))
        if self.speak and getattr(self.app, "voice", None):
            spec.append(("Read aloud", self.read, 1.3, "plain"))
        if self.i > 0:
            spec.append(("Previous", self.prev, 1.2, "plain"))
        spec.append(("Got it" if last else "Next  %d of %d" % (self.i + 1, n), self.next, 1.8, "primary"))
        return row(spec, BOTTOM_Y, BOTTOM_H)


class W40kBase(PlayBase):
    """Shared by every 40k screen: an event that teaches something new in
    Teach mode is followed by its card."""

    def do(self, **ev):
        before = list(self.state["taught"])
        logged = super().do(**ev)
        if logged and not self.session.finished and self.state["mode"] == "teach":
            new = [k for k in self.state["taught"] if k not in before]
            steps = self.game.cards(new)
            if steps:
                self.app.toast = None        # the card says it better
                self.app.push(TeachCard(self.app, steps, self))
        return logged

    def cards_seen(self):
        """The cards the last event made due have been shown and put away.
        Kept with the saved game, so a resume knows not to show them again."""
        d = self.session.d
        if d.get("cards_seen") != len(self.session.log):
            d["cards_seen"] = len(self.session.log)
            self.session.save()

    def enter(self):
        if getattr(self, "_shown", False):    # back on top: any card over this screen has gone
            self.cards_seen()
        self._shown = True
        super().enter()

    def undo(self, quiet=False):
        super().undo(quiet)
        self.cards_seen()                     # an undone event's cards are not owed

    def names(self):
        return self.session.players

    def more(self):
        self.app.push(W40kMenu(self.app, self.session, self.repace))

    def repace(self):
        pace = getattr(self, "pace", None)
        if pace:
            pace.restart()


class W40kPlay(W40kBase):
    def __init__(self, app, session):
        super().__init__(app, session)
        self._intro = False
        self.pace = rules.Pace()              # new with the screen, so a resumed game starts timing afresh
        self._warn_until = None
        self._line = random.randrange(len(NUDGE_LINES))
        self._tick_at = None                  # when tick was last called

    def ring_warning(self):
        ring = getattr(self.app.hw, "_ring", None)
        return ring is None or getattr(ring, "now", ("warn",))[0] == "warn"

    def tick(self, t):
        """The app calls this many times a second with the time. A phase that
        runs past the limit earns one line and an amber blink, once.
        Only while this screen is the one showing: under a menu, a card or the
        score sheet the clock stands still and nothing is said."""
        last, self._tick_at = self._tick_at, t
        on_top = self.app.screen is self
        if self._warn_until is not None and t >= self._warn_until:
            self._warn_until = None
            if on_top or self.ring_warning():
                self.show_ring()              # back to the turn colour
        if not on_top:
            if last is not None:
                self.pace.since += max(0.0, t - last)
            return False
        limit = nudge_secs(self.session)
        if self.session.finished or not self.pace.due(self.game.pace_key(self.state), t, limit):
            return False
        self.app.hw.ring("warn")
        self._warn_until = t + WARN_SECS
        if self.state["mode"] != "silent":    # Silent mode: the ring only
            line = NUDGE_LINES[self._line % len(NUDGE_LINES)]
            self._line += 1
            words = next((w for _, v, w in rules.NUDGES if v == limit), "")
            self.app.say(line % words if "%s" in line else line)
        return True

    def enter(self):
        first = not getattr(self, "_shown", False)
        super().enter()
        s = self.state
        if not self._intro and s["mode"] == "teach" and not self.session.log:
            self._intro = True                # the first-game steps, once, before anything happens
            steps = self.game.cards(INTRO)
            if steps:
                self.app.push(TeachCard(self.app, steps))
        elif (first and s["mode"] == "teach" and self.session.log and s.get("pending")
              and self.session.d.get("cards_seen") != len(self.session.log)):
            steps = self.game.cards(s["pending"])     # a resumed game: the card that was up when it stopped
            if steps:
                self.app.push(TeachCard(self.app, steps, self))

    def build(self):
        s, g, names = self.state, self.game, self.names()
        vp = [g.score(s, 0)[2], g.score(s, 1)[2]]
        high = [names[i] for i in (0, 1) if rules.cp_warning(s["cp"][i])]
        note = "More than %d is rare" % rules.CP_WARN_ABOVE if high else None
        if s["mode"] == "silent":
            boxes = [(20, 126, 760, 124), (20, 258, 760, 124)]
        else:
            boxes = [(20, 310, 375, 74), (405, 310, 375, 74)]
        out = [Versus(boxes[0], "Victory points", vp, names, self.score),
               Versus(boxes[1], "Command points", s["cp"], names, self.cps, note)]
        if s["mode"] == "teach" and s["phase"] == "movement":
            out += [Button((20, 238, 375, 64), "Advance", lambda: self.do(ev="did", what="advance"), size=22),
                    Button((405, 238, 375, 64), "Fall back", lambda: self.do(ev="did", what="fallback"), size=22)]
        elif s["mode"] == "teach" and s["phase"] == "charge":
            out.append(Button((20, 238, 375, 64), "Charge", lambda: self.do(ev="did", what="charge"), size=22))
        label = "Finish" if s["phase"] == rules.END else "End turn" if s["phase"] == "fight" else "Next phase"
        spec = [(label, lambda: self.do(ev="next"), 1.5, "primary"), ("Score", self.score, 1, "plain"),
                ("Army", self.army, 1, "plain"), ("Cards", self.cards, 1, "plain")]
        if g.can_swap(s):
            spec.append(("Swap first", lambda: self.do(ev="first", side=1 - s["active"]), 1.35, "plain"))
        else:
            spec.append(("Undo", self.undo, 1, "plain"))
        spec.append(("Menu", self.more, 1, "plain"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def score(self):
        self.app.push(W40kScore(self.app, self.session))

    def cps(self):
        self.app.push(W40kCommand(self.app, self.session))

    def army(self):
        self.app.push(W40kArmy(self.app, self.session))

    def cards(self):
        start = 1 if self.state["phase"] in ("shooting", "fight") else 0
        self.app.push(W40kRef(self.app, self.session, start))

    def draw_body(self, surf):
        s = self.state
        w = (760 - 6 * 4) / 5.0
        for i, name in enumerate(BAR):        # the five-phase bar: light and underlined is where you are
            box = pygame.Rect(round(20 + i * (w + 6)), 68, round(w), 42)
            now = s["phase"] == rules.ORDER[i]
            pygame.draw.rect(surf, T.TEXT if now else T.PANEL, box, border_radius=10)
            pygame.draw.rect(surf, T.TEXT if now else T.LINE, box, 1, border_radius=10)
            T.draw_text(surf, name, "bold", 22, T.GROUND if now else T.DIM, box.center, "center", max_w=box.w - 10)
            if now:
                pygame.draw.rect(surf, T.TEXT, (box.x + 10, box.bottom + 3, box.w - 20, 4), border_radius=2)
        if s["mode"] == "silent":
            return
        head, hint = prompt(s)
        T.draw_text(surf, head, "head", 38, T.TEXT, (20, 122), max_w=760)
        y = 174
        for line in T.wrap(hint, "text", 24, 760)[:2]:
            T.draw_text(surf, line, "text", 24, T.DIM, (20, y))
            y += 30
        if s["phase"] == "command":
            need = self.game.tests(s, s["active"])
            if need:
                T.draw_text(surf, "Battle-shock test: " + ", ".join(need), "bold", 22, T.WARN, (20, 254), max_w=760)
        if s["mode"] == "teach" and s["phase"] in ("movement", "charge"):
            return                             # the teach buttons have that space
        sides = (0, 1) if s["phase"] == rules.END else (s["active"],)
        y = 280 - 28 * (len(sides) - 1)
        for side in sides:                     # the secondaries in hand, by name
            words = rules.sec_words(self.game.secs(s, side))
            if words:
                T.draw_text(surf, "%s: %s" % (self.names()[side], words), "text", 22, T.DIM, (20, y), max_w=760)
            y += 28


COLS = (20, 410)                              # where each player's column starts
COL_W = 370
SHEET_Y = (94, 188, 282)                      # primary, then the two secondaries


class W40kScore(W40kBase):
    """The Command-phase score sheet: primary, then each player's two
    secondaries by name. Tap a secondary's number to name it or change it."""

    @property
    def title(self):
        return "Final scores" if self.state["phase"] == rules.END else "Score this turn"

    @property
    def pill(self):
        return None                           # both players score here; the title has the room

    def rows(self, side):
        """[(what the middle box says, points, the score event, slot or None)]"""
        out = [("Primary", sum(self.state["primary"][side]), {"cat": "primary"}, None)]
        mine = self.game.secs(self.state, side)
        for k in range(len(SHEET_Y) - 1):
            r = rules.sec_at(mine, k)
            out.append(("Change" if rules.sec_named(r) else "Name it", r["pts"], {"cat": "sec", "row": k}, k))
        return out

    def build(self):
        out, names = [], self.names()
        for side in (0, 1):
            x = COLS[side]
            for (text, pts, what, slot), y in zip(self.rows(side), SHEET_Y):
                pick = None if slot is None else (lambda side=side, slot=slot: self.pick(side, slot))
                label = "%s %s" % (names[side], "Primary" if slot is None else "Secondary %d" % (slot + 1))
                out += [Button((x, y, 64, 64), "−", lambda side=side, what=what:
                               self.do(ev="score", side=side, delta=-1, **what), size=30),
                        Cell((x + 70, y, COL_W - 140, 64), label, text, pts, pick, T.player_colour(side)),
                        Button((x + COL_W - 64, y, 64, 64), "+", lambda side=side, what=what:
                               self.do(ev="score", side=side, delta=1, **what), size=30)]
        return out + [Button((520, BOTTOM_Y, 260, BOTTOM_H), "Done", self.app.pop, "primary")]

    def pick(self, side, slot):
        self.app.push(W40kSecPick(self.app, self.session, side, slot))

    def draw_body(self, surf):
        s, names = self.state, self.names()
        for side in (0, 1):
            x, mine = COLS[side], self.game.secs(s, side)
            T.draw_text(surf, names[side], "head", 24, T.player_colour(side), (x + COL_W // 2, 77), "center", max_w=COL_W)
            for k, y in enumerate(SHEET_Y[1:]):       # each secondary's name sits over its row
                r = rules.sec_at(mine, k)
                cap = r["cap"] if r.get("cap") is not None else rules.SCORING["secondary_rows"][k].get("max")
                room = COL_W - 8 - (90 if cap is not None else 0)
                T.draw_text(surf, r["name"], "bold", 22, T.TEXT if rules.sec_named(r) else T.DIM, (x + 4, y - 28), max_w=room)
                if cap is not None:
                    T.draw_text(surf, "max %d" % cap, "text", 22, T.DIM, (x + COL_W - 4, y - 28), "topright")
            old = sum(r["pts"] for r in mine if r["slot"] is None)
            T.draw_text(surf, "Total, %d from earlier" % old if old else "Total", "text", 22, T.DIM, (x + 4, 369),
                        "midleft", max_w=COL_W - 110)
            T.draw_text(surf, str(self.game.score(s, side)[2]), "head", 34, T.player_colour(side),
                        (x + COL_W - 14, 369), "midright")
        cap = rules.SCORING["primary_per_round"]
        if s["phase"] != rules.END and s["round"] < rules.SCORING["primary_from_round"]:
            note, colour = "Primary starts in round %d" % rules.SCORING["primary_from_round"], T.WARN
        elif s["phase"] != rules.END and cap is not None:
            note, colour = "Primary: at most %d a round" % cap, T.DIM
        else:
            note, colour = "Your mission cards say what scores", T.DIM
        T.draw_text(surf, note, "text", 22, colour, (20, BOTTOM_Y + BOTTOM_H // 2), "midleft", max_w=480)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


PICK_PER_PAGE = 8


class W40kSecPick(W40kBase):
    """Name one secondary: pick it from the list in secondaries.json, or type
    it. Names only; the card in the player's hand says what scores."""

    def __init__(self, app, session, side, slot):
        super().__init__(app, session)
        self.side, self.slot, self.page = side, slot, 0
        self.table = secondary_table()

    @property
    def left(self):
        return "40k · %s" % self.names()[self.side]

    @property
    def title(self):
        return "Pick a secondary"

    @property
    def pill(self):
        return None

    def row_now(self):
        return rules.sec_at(self.game.secs(self.state, self.side), self.slot)

    def pages(self):
        return max(1, -(-len(self.table) // PICK_PER_PAGE))

    def build(self):
        out, now = [], self.row_now()["name"].lower()
        shown = self.table[self.page * PICK_PER_PAGE:(self.page + 1) * PICK_PER_PAGE]
        for i, e in enumerate(shown):
            sub = e["scores"] + (", max %d" % e["cap"] if e["cap"] is not None else "")
            out.append(NameRow((20 + (i % 2) * 385, 68 + (i // 2) * 68, 375, 64), e["name"], sub,
                               lambda e=e: self.choose(e["name"], e["cap"]), selected=e["name"].lower() == now))
        spec = [("Type a name", self.type, 1.4, "plain")]
        if self.pages() > 1:
            spec.append(("More names", self.more_names, 1.4, "plain"))
        if rules.sec_named(self.row_now()):
            spec.append(("Put away", self.away, 1.1, "plain"))
        spec.append(("Back", self.app.pop, 1, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def choose(self, name, cap=None):
        if self.do(ev="sec", side=self.side, op="name", slot=self.slot, name=name, cap=cap):
            self.app.pop()

    def away(self):
        if self.do(ev="sec", side=self.side, op="away", slot=self.slot):
            self.app.pop()

    def more_names(self):
        self.page = (self.page + 1) % self.pages()
        self.refresh()

    def type(self):
        def done(text):
            if text:
                self.choose(text)
        self.app.push(TextEntry(self.app, "Secondary name", "", done, "Done", max_len=rules.MAX_SEC_NAME))

    def draw_body(self, surf):
        r = self.row_now()
        if not self.table:
            T.draw_text(surf, "I have no list of names.", "head5", 28, T.TEXT, (T.W // 2, 150), "center")
            T.draw_text(surf, "Tap Type a name. The card in your hand says what scores.", "text", 22, T.DIM,
                        (T.W // 2, 196), "center", max_w=760)
        if rules.sec_named(r) and r["pts"]:
            foot = "%s has %d. A new name starts at 0; those points stay." % (r["name"], r["pts"])
        else:
            foot = "Names from memory: your deck decides. Page %d of %d." % (self.page + 1, self.pages())
        T.draw_text(surf, foot, "text", 22, T.DIM, (20, 362), "midleft", max_w=760)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class W40kCommand(W40kBase):
    """Command points for both sides. The box adds the one each Command phase;
    the players take away what they spend."""

    @property
    def title(self):
        return "Command points"

    @property
    def pill(self):
        return None

    def build(self):
        out = []
        for side in (0, 1):
            y = 84 + side * 84
            out += [Button((476, y, 64, 64), "−", lambda side=side: self.do(ev="cp", side=side, delta=-1), size=30),
                    Button((716, y, 64, 64), "+", lambda side=side: self.do(ev="cp", side=side, delta=1), size=30)]
        return out + [Button((520, BOTTOM_Y, 260, BOTTOM_H), "Done", self.app.pop, "primary")]

    def draw_body(self, surf):
        s, names = self.state, self.names()
        for side in (0, 1):
            y = 84 + side * 84
            pygame.draw.rect(surf, T.player_colour(side), (20, y + 8, 5, 48), border_radius=2)
            T.draw_text(surf, names[side], "head", 30, T.TEXT, (40, y + 32), "midleft", max_w=260)
            if rules.cp_warning(s["cp"][side]):
                T.draw_text(surf, "over %d" % rules.CP_WARN_ABOVE, "bold", 22, T.WARN, (462, y + 32), "midright")
            T.draw_text(surf, str(s["cp"][side]), "head", 44, T.player_colour(side), (628, y + 32), "center")
        y = 266
        for line in ("Both of you gain one in every Command phase. I add those.",
                     "Take one away when you spend it. Your cards say what it buys."):
            T.draw_text(surf, line, "text", 22, T.DIM, (20, y), max_w=760)
            y += 30

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


PER_PAGE = 4


def unit_row_y(i):
    return 68 + i * 68


class W40kArmy(W40kBase):
    """One side's units: models alive out of the starting size. Tap − when a
    model is removed, + to put one back."""

    def __init__(self, app, session, side=None):
        super().__init__(app, session)
        self.side = session.state["active"] if side is None else side
        self.page = 0

    @property
    def left(self):
        return "40k · %s's army" % self.names()[self.side]

    @property
    def title(self):
        return "Army"

    @property
    def pill(self):
        return None

    def army(self):
        return self.state["army"][self.side]

    def pages(self):
        return max(1, -(-len(self.army()) // PER_PAGE))

    def shown(self):
        self.page = min(self.page, self.pages() - 1)
        return list(enumerate(self.army()))[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]

    def build(self):
        out = []
        for i, (k, u) in enumerate(self.shown()):
            y = unit_row_y(i)
            if u["alive"] > 0:
                out.append(Button((326, y, 140, 64), "Shocked" if u["shocked"] else "Steady",
                                  lambda k=k: self.do(ev="shock", side=self.side, unit=k), selected=u["shocked"], size=22))
            out += [Button((476, y, 64, 64), "−", lambda k=k: self.do(ev="model", side=self.side, unit=k, delta=-1), size=30),
                    Button((716, y, 64, 64), "+", lambda k=k: self.do(ev="model", side=self.side, unit=k, delta=1), size=30)]
        spec = [("%s's army" % self.names()[1 - self.side], self.swap, 1.7, "plain")]
        if self.pages() > 1:
            spec.append(("More units", self.more_units, 1.3, "plain"))
        spec += [("Edit list", self.edit, 1.1, "plain"), ("Back", self.app.pop, 1, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def swap(self):
        self.side, self.page = 1 - self.side, 0
        self.refresh()

    def more_units(self):
        self.page = (self.page + 1) % self.pages()
        self.refresh()

    def edit(self):
        self.app.push(W40kArmyEdit(self.app, self.session, self.side))

    def draw_body(self, surf):
        army, shown = self.army(), self.shown()
        if not army:
            T.draw_text(surf, "No list for %s yet." % self.names()[self.side], "head5", 28, T.TEXT, (T.W // 2, 150), "center",
                        max_w=760)
            T.draw_text(surf, "Tap Edit list. Unit sizes are all I need.", "text", 22, T.DIM, (T.W // 2, 196), "center")
            return
        for i, (k, u) in enumerate(shown):
            y = unit_row_y(i)
            box = pygame.Rect(20, y, 760, 64)
            pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
            pygame.draw.rect(surf, T.LINE, box, 1, border_radius=12)
            dead = u["alive"] <= 0
            low = rules.below_half(u["start"], u["alive"], u["hurt"])
            if low:                            # a thick edge as well as the words
                pygame.draw.rect(surf, T.WARN, (box.x, box.y + 8, 5, box.h - 16), border_radius=2)
            T.draw_text(surf, u["name"], "bold", 24, T.DIM if dead else T.TEXT, (36, y + 3), max_w=280)
            if dead:
                state, colour = "Destroyed", T.DIM
            elif low:
                state, colour = ("Below half wounds" if u["start"] == 1 else "Below half strength"), T.WARN
            elif u["alive"] == u["start"]:
                state, colour = "Full strength", T.DIM
            else:
                state, colour = "Above half", T.DIM
            T.draw_text(surf, state, "text", 22, colour, (36, y + 33), max_w=280)
            T.draw_text(surf, "%d of %d" % (u["alive"], u["start"]), "head", 26, T.DIM if dead else T.TEXT,
                        (628, y + 32), "center", max_w=166)
        first = self.page * PER_PAGE + 1
        T.draw_text(surf, "Units %d to %d of %d. Tap − when a model is removed." % (first, first + len(shown) - 1, len(army)),
                    "text", 22, T.DIM, (20, 362), "midleft", max_w=760)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class W40kArmyEdit(W40kBase):
    """Make a simple list with taps: how many units, and how big each is.
    Names are typed on a phone later."""

    def __init__(self, app, session, side):
        super().__init__(app, session)
        self.side, self.page = side, 0

    @property
    def left(self):
        return "40k · %s's army" % self.names()[self.side]

    @property
    def title(self):
        return "Edit list"

    @property
    def pill(self):
        return None

    def army(self):
        return self.state["army"][self.side]

    def pages(self):
        return max(1, -(-len(self.army()) // PER_PAGE))

    def shown(self):
        self.page = min(self.page, self.pages() - 1)
        return list(enumerate(self.army()))[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]

    def change(self, **ev):
        self.do(ev="army", side=self.side, **ev)

    def build(self):
        out = []
        for i, (k, u) in enumerate(self.shown()):
            y = unit_row_y(i)
            out += [Button((330, y, 64, 64), "−", lambda k=k: self.change(op="size", unit=k, delta=-1), size=30),
                    Button((466, y, 64, 64), "+", lambda k=k: self.change(op="size", unit=k, delta=1), size=30),
                    Button((540, y, 74, 64), "+5", lambda k=k: self.change(op="size", unit=k, delta=5), size=24),
                    Button((624, y, 156, 64), "Remove", lambda k=k: self.change(op="remove", unit=k), size=22)]
        spec = [("Add unit", self.add, 1.2, "plain"), ("Use Necrons", lambda: self.change(op="preset", name="necrons"), 1.5, "plain")]
        if self.pages() > 1:
            spec.append(("More units", self.more_units, 1.4, "plain"))
        spec.append(("Done", self.app.pop, 1, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def add(self):
        n = len(self.army())
        self.change(op="add", size=5)
        if len(self.army()) > n:
            self.page = self.pages() - 1       # show the unit just added
            self.refresh()

    def more_units(self):
        self.page = (self.page + 1) % self.pages()
        self.refresh()

    def draw_body(self, surf):
        army, shown = self.army(), self.shown()
        if not army:
            T.draw_text(surf, "An empty list.", "head5", 28, T.TEXT, (T.W // 2, 150), "center")
            T.draw_text(surf, "Add a unit for each one on the table, then set its size.", "text", 22, T.DIM,
                        (T.W // 2, 196), "center", max_w=760)
            return
        for i, (k, u) in enumerate(shown):
            y = unit_row_y(i)
            box = pygame.Rect(20, y, 760, 64)
            pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
            pygame.draw.rect(surf, T.LINE, box, 1, border_radius=12)
            T.draw_text(surf, u["name"], "bold", 24, T.TEXT, (36, y + 32), "midleft", max_w=284)
            T.draw_text(surf, str(u["start"]), "head", 30, T.TEXT, (430, y + 32), "center")
        first = self.page * PER_PAGE + 1
        T.draw_text(surf, "Units %d to %d of %d. A new size puts the unit back to full." % (first, first + len(shown) - 1, len(army)),
                    "text", 22, T.DIM, (20, 362), "midleft", max_w=760)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


# ---------------------------------------------------------------- reference cards
SEQUENCE = [("Hit", "One die per attack. Roll the hit number or more."),
            ("Wound", "Compare Strength with Toughness: next card."),
            ("Save", "The defender rolls. AP makes the save worse."),
            ("Damage", "Each failed save does the Damage to one model.")]
PHASE_LINES = ["Both gain a point. Score. Battle-shock tests.",
               "Move, Advance, Fall Back or stay. Reserves arrive.",
               "Pick a unit, then targets. Roll the sequence.",
               "Two dice for the distance, then targets within it.",
               "Chargers first, then take turns. Same sequence."]
REF = [("Phase order", "A turn is five phases, in this order. Then the other player's turn."),
       ("Attack sequence", "Every attack, shooting or fighting, is the same four rolls."),
       ("Wound roll", "Compare the weapon's Strength with the target's Toughness.")]
REF_FOOT = ["Two turns make a battle round.",
            "A roll of 1 always fails. A 6 always hits.",
            "A roll of 1 always fails to wound."]


class W40kRef(Screen):
    """Three cards drawn by the box: phase order, the attack sequence, and
    the wound-roll chart."""
    left = "40k · Reference"

    def __init__(self, app, session=None, start=0):
        super().__init__(app)
        self.session, self.i = session, start % len(REF)

    @property
    def title(self):
        return REF[self.i][0]

    def build(self):
        spec = [("Previous card", lambda: self.turn(-1), 1.25, "plain")]
        if getattr(self.app, "voice", None):
            spec.append(("Read aloud", self.read, 1, "plain"))
        spec += [("Next card", lambda: self.turn(1), 1, "plain"), ("Close", self.app.pop, 0.8, "primary")]
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def turn(self, step):
        self.i = (self.i + step) % len(REF)
        self.refresh()

    def rows(self):
        """[(left text, right text, is this where the game is now)]"""
        if self.i == 0:
            now = self.session.state["phase"] if self.session else None
            return [("%d  %s" % (k + 1, name), PHASE_LINES[k], key == now) for k, (key, name) in enumerate(rules.PHASES)]
        if self.i == 1:
            return [("%d  %s" % (k + 1, name), text, False) for k, (name, text) in enumerate(SEQUENCE)]
        return [(text, "%d+" % need, False) for text, need in rules.WOUND_ROWS]

    def words(self):
        """The card as sentences, for reading aloud."""
        parts = [REF[self.i][1]]
        for a, b, _ in self.rows():
            parts.append("%s: %s." % (a.split("  ")[-1], b.replace("+", " or more").rstrip(".")))
        return " ".join(parts + [REF_FOOT[self.i]])

    def read(self):
        self.app.voice.say(self.words(), show=False)

    def draw_body(self, surf):
        T.draw_text(surf, REF[self.i][1], "text", 22, T.DIM, (20, 70), max_w=760)
        rows = self.rows()
        h = 50 if len(rows) == 5 else 60
        for k, (a, b, now) in enumerate(rows):
            box = pygame.Rect(20, 104 + k * h, 760, h - 6)
            if now:                            # a raised box, a light edge and the word "now"
                pygame.draw.rect(surf, T.RAISED, box, border_radius=10)
                pygame.draw.rect(surf, T.TEXT, box, 2, border_radius=10)
            if self.i == 2:
                T.draw_text(surf, a, "text", 24, T.TEXT, (box.x + 16, box.centery), "midleft", max_w=620)
                T.draw_text(surf, b, "head", 30, T.TEXT, (box.right - 16, box.centery), "midright")
            else:
                T.draw_text(surf, a, "head", 24, T.TEXT, (box.x + 16, box.centery), "midleft", max_w=150)
                T.draw_text(surf, b, "text", 22, T.TEXT if now else T.DIM, (box.x + 196, box.centery), "midleft",
                            max_w=500 if now else 554)
                if now:
                    T.draw_text(surf, "now", "bold", 22, T.TEXT, (box.right - 14, box.centery), "midright")
        T.draw_text(surf, REF_FOOT[self.i], "mid", 22, T.DIM, (20, 104 + len(rows) * h + 4), max_w=760)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()
