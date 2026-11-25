"""Kill Team. The box runs the turning points, counts activations so nobody
goes twice, keeps command points and victory points, and teaches a first game
one rule at a time. The players keep the table and their own cards; the box
never sees either, so they tell it the one word that matters."""
import random
import pygame
from ... import theme as T
from ...engine import Game
from ...screens.common import BOTTOM_H, BOTTOM_Y, Pages, PlayBase
from ...screens.extras import GameMenu
from ...widgets import Button, row
from . import rules

PHASES = [("strategy", "Strategy"), ("firefight", "Firefight"), ("end", "End")]
PHASE_NAME = dict(PHASES, setup="Set up")
MODES = {"Teach": "teach", "Reminder": "reminder", "Silent": "silent"}
ORDINAL = {1: "one", 2: "two", 3: "three", 4: "four"}
DID = [("shoot", "Shoot"), ("charge", "Charge"), ("fight", "Fight"), ("injury", "Injured")]
# What she says when a rule that has already had its card comes up again.
AGAIN = {
    "shoot": "Shooting: Engage order, a target you can see. Attack dice, defence dice, block, damage.",
    "charge": "Charging: up to Move plus two inches, ending within an inch of an enemy. No other move.",
    "fight": "Fighting: both roll. Take turns, attacker first: strike or parry.",
    "injury": "Injured: two inches less movement, every Hit number one worse.",
}
TURNING_POINT_LINES = {2: "Turning point two. The part where plans meet other plans.",
                       3: "Turning point three. The dice have not improved overnight."}

# What she says, once, when one activation runs past the limit. %s is the limit in words.
NUDGE_LINES = ["%s on one operative. I mention it only because I can count.",
               "This activation is still going. So, I observe, is the clock.",
               "%s have passed in this activation. I shall not bring it up again.",
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


class Plugin(Game):
    min_players, max_players = 2, 2
    remind_each_turn = False                  # the phases are shared: a reminder is said once, as its phase begins
    options = [{"key": "mode", "label": "Mode", "choices": ["Teach", "Reminder", "Silent"]},
               {"key": "length", "label": "Length", "choices": ["Full, 4 rounds", "Tutorial, 2 rounds"]},
               {"key": "tacops", "label": "Tac Ops", "choices": ["On", "Off"]}]

    # ---------------------------------------------------------------- state
    def new_state(self, players, options):
        tutorial = str(options.get("length", "Full")).startswith("Tutorial")
        return {"tp": 0, "tp_max": rules.TUTORIAL if tutorial else rules.FULL, "phase": "setup",
                "mode": MODES.get(options.get("mode", "Teach"), "teach"),
                "tacops": options.get("tacops", "On") == "On",
                "names": list(players)[:2], "active": None,
                "start": [rules.DEFAULT_OPS] * 2, "lost": [0, 0], "left": [0, 0],
                "cp": [rules.START_CP] * 2, "gained": [0, 0], "init": None, "had": None,
                "vp": [{c: 0 for c, _ in rules.CATS} for _ in (0, 1)],
                "primary": [None, None], "bonus": [0, 0],
                "tacop": [None, None],        # each side's Tac Op by name, typed on its own phone. SECRET
                "tac_shown": [False, False],  # ...until that side reveals it; then anyone may see it
                "fallen": False,      # the operative activating now is already off the count
                "out": None,          # the side that ran out of activations this turning point
                "acts": 0,            # activations finished so far: the slow-play clock times each one
                "taught": [],
                "pending": [],        # rule cards the last event made due (shown again if the power went)
                "done": False}

    def phases(self):
        return PHASES

    def alive(self, s):
        return [s["start"][i] - s["lost"][i] for i in (0, 1)]

    def totals(self, s):
        return [rules.total(s["vp"][i], s["bonus"][i]) for i in (0, 1)]

    def grades(self, s):
        """Kill grade each side has reached, from the other side's losses."""
        return [rules.kill_grade(s["start"][1 - i], s["lost"][1 - i]) for i in (0, 1)]

    def pace_key(self, s):
        """What the slow-play clock is timing: this activation, or None
        outside the Firefight phase."""
        if s["done"] or s["phase"] != "firefight" or s["active"] is None:
            return None
        return (s["tp"], s.get("acts", 0))

    def cats(self, s):
        return [(c, name) for c, name in rules.CATS if c != "tac" or s["tacops"]]

    # ---- the secret Tac Op. Everything shown to the table goes through tac_public.
    @staticmethod
    def tac_name(s, side):
        """The name itself. Only for that side's own phone, until it is shown."""
        return (s.get("tacop") or [None, None])[side]

    @staticmethod
    def tac_shown(s, side):
        return bool((s.get("tac_shown") or [False, False])[side])

    def tac_public(self, s, side):
        """What anyone may know about a side's Tac Op: its name once revealed;
        before that only whether one has been chosen. '' when Tac Ops are off."""
        if not s["tacops"]:
            return ""
        name = self.tac_name(s, side)
        if name and self.tac_shown(s, side):
            return name
        return "chosen" if name else "not chosen"

    def cards(self, key):
        """The teaching steps that go with one trigger."""
        return [st for st in self.teach() if st.get("when") == key]

    # ---------------------------------------------------------------- events
    def apply(self, s, ev):
        fn = getattr(self, "_ev_%s" % ev.get("ev"), None)
        if fn is None:
            raise ValueError("I do not know what %r means in Kill Team." % ev.get("ev"))
        if s["done"]:
            raise ValueError("The game is over.")
        s["pending"] = []
        return fn(s, ev)

    @staticmethod
    def _side(ev):
        side = ev.get("side")
        if side not in (0, 1):
            raise ValueError("Kill Team has two sides. I need to know which one.")
        return side

    def _teach(self, s, *keys):
        """Mark rule cards as due. True if any is new: the screen then shows it."""
        if s["mode"] != "teach":
            return False
        new = [k for k in keys if k not in s["taught"]]
        s["taught"] += new
        s["pending"] = s.get("pending", []) + new
        return bool(new)

    def _counter(self, s):
        """One side has just run out of activations: (sentence, card shown)."""
        c = rules.counteract(s["active"], s["left"], self.alive(s))
        if c is None or s["out"] is not None:
            return None, False
        s["out"] = c
        n = s["names"]
        line = "%s has no ready operatives left. %s keeps activating. %s may counteract after each." % (
            n[c], n[1 - c], n[c])
        return line, self._teach(s, "counteract")

    def _ev_ops(self, s, ev):
        side = self._side(ev)
        if s["phase"] != "setup":
            raise ValueError("The teams are already on the table. Use Operative down for losses.")
        v = s["start"][side] + int(ev.get("delta", 0))
        if v < rules.MIN_OPS:
            raise ValueError("A kill team needs at least one operative.")
        if v > rules.MAX_OPS:
            raise ValueError("%d operatives is the most I will count." % rules.MAX_OPS)
        s["start"][side] = v
        return []

    def _ev_next(self, s, ev):
        n, talk, phase = s["names"], s["mode"] != "silent", s["phase"]
        if phase == "setup":
            s["tp"], s["phase"] = 1, "strategy"
            card = self._teach(s, "strategy1")
            return ["Turning point one. Roll for initiative."] if talk and not card else []
        if phase == "strategy":
            if s["init"] is None:
                raise ValueError("Who has the initiative? Tap a name first.")
            s["phase"], s["left"], s["fallen"], s["out"] = "firefight", self.alive(s), False, None
            s["active"] = rules.first_active(s["init"], s["left"])
            card = self._teach(s, "firefight1")
            if s["active"] is None:
                said = ["Nobody has an operative to activate. Press on."]
            else:
                said = ["Firefight. %s activates first." % n[s["active"]]]
            line, card2 = self._counter(s)
            if line:
                said.append(line)
            return said if talk and not (card or card2) else []
        if phase == "firefight":
            a = s["active"]
            if a is not None:
                if not s["fallen"]:
                    s["left"][a] = max(0, s["left"][a] - 1)
                s["fallen"] = False
                s["acts"] = s.get("acts", 0) + 1       # a game saved before the clock has no count yet
                s["active"] = rules.next_active(a, s["left"])
            if s["active"] is not None:
                line, card = self._counter(s)
                return [line] if line and talk and not card else []
            s["phase"] = "end"
            last = s["tp"] == s["tp_max"]
            keys = ["end1" if s["tp"] == 1 else "scoring"] + (["ending"] if last else [])
            card = self._teach(s, *keys)
            if last:
                line = "The last turning point ends. Score it, then reveal your primary ops."
            elif s["tp"] == 1:
                line = "Turning point one ends. The Crit Op does not score yet."
            else:
                line = "Turning point %s ends. Score it." % ORDINAL.get(s["tp"], s["tp"])
            return [line] if talk and not card else []
        # the End phase: on to the next turning point, or the end of the game
        if s["tp"] < s["tp_max"]:
            s["tp"] += 1
            s["phase"], s["had"], s["init"], s["gained"] = "strategy", s["init"], None, [0, 0]
            s["active"], s["out"], s["fallen"] = None, None, False
            card = self._teach(s, "strategy2")
            if s["tp"] == s["tp_max"]:
                line = "The last turning point. Score what can be scored; mourn the rest later."
            else:
                line = TURNING_POINT_LINES.get(s["tp"], "Turning point %s." % ORDINAL.get(s["tp"], s["tp"]))
            return [line] if talk and not card else []
        missing = [n[i] for i in (0, 1) if s["primary"][i] is None]
        if missing:
            raise ValueError("%s: reveal your primary op first." % " and ".join(missing))
        s["bonus"] = [rules.primary_bonus(s["vp"][i][s["primary"][i]]) for i in (0, 1)]
        s["tac_shown"] = [bool(self.tac_name(s, i)) or self.tac_shown(s, i) for i in (0, 1)]   # the game is over: nothing is secret
        s["done"] = True
        return []

    def _ev_tacop(self, s, ev):
        """A player records their Tac Op, from their own phone. What is said
        and what is refused never includes the name: the box is shared."""
        side, n = self._side(ev), s["names"]
        if not s["tacops"]:
            raise ValueError("Tac Ops are off for this game.")
        name = rules.tac_clean(ev.get("text"))
        if not name:
            raise ValueError("A Tac Op needs a name.")
        had = self.tac_name(s, side)
        if self.tac_shown(s, side):
            raise ValueError("%s's Tac Op has been revealed. It stays as it is." % n[side])
        if had and not rules.tac_open(s["tp"], s["phase"]):
            raise ValueError("%s has already chosen a Tac Op. It stays until it is revealed." % n[side])
        if had == name:
            raise ValueError("%s's Tac Op is unchanged: that is the one already recorded." % n[side])
        ops = list(s.get("tacop") or [None, None])
        ops[side] = name
        s["tacop"] = ops
        s.setdefault("tac_shown", [False, False])
        if s["mode"] == "silent":
            return []
        return ["%s has chosen a %sTac Op. I shall keep it to myself." % (n[side], "different " if had else "")]

    def _ev_reveal(self, s, ev):
        """A side shows its Tac Op (its own phone), or both do (side "all":
        the box, when the last scoring is done). From then on it is public."""
        n = s["names"]
        if not s["tacops"]:
            raise ValueError("Tac Ops are off for this game.")
        sides = (0, 1) if ev.get("side") == "all" else (self._side(ev),)
        new = [i for i in sides if self.tac_name(s, i) and not self.tac_shown(s, i)]
        if not new:
            if len(sides) == 1 and self.tac_shown(s, sides[0]):
                raise ValueError("%s's Tac Op is already revealed." % n[sides[0]])
            raise ValueError("There is no Tac Op to reveal.")
        s["tac_shown"] = [self.tac_shown(s, i) or i in new for i in (0, 1)]
        return ["%s's Tac Op: %s." % (n[i], self.tac_name(s, i)) for i in new] if s["mode"] != "silent" else []

    def _ev_init(self, s, ev):
        side, n = self._side(ev), s["names"]
        if s["phase"] != "strategy":
            raise ValueError("Initiative is rolled in the Strategy phase.")
        if s["init"] == side:
            raise ValueError("%s already has the initiative." % n[side])
        back = [s["cp"][i] - s["gained"][i] for i in (0, 1)]      # take back a gain given by mistake
        if min(back) < 0:
            raise ValueError("Those command points have already been spent. Undo instead.")
        s["gained"] = rules.cp_gain(s["tp"], side)
        s["cp"] = [back[i] + s["gained"][i] for i in (0, 1)]
        s["init"] = side
        if s["mode"] == "silent":
            return []
        now = "%s %d, %s %d." % (n[0], s["cp"][0], n[1], s["cp"][1])
        if s["tp"] == 1:
            return ["One command point each. " + now]
        return ["%s gains one command point, %s gains two. %s" % (n[side], n[1 - side], now)]

    def _ev_cp(self, s, ev):
        side = self._side(ev)
        v = s["cp"][side] + int(ev.get("delta", 0))
        if v < 0:
            raise ValueError("%s has no command points to spend." % s["names"][side])
        s["cp"][side] = v
        return []

    def _points(self, s, ev):
        side, cat, delta = self._side(ev), ev.get("cat"), int(ev.get("delta", 0))
        if cat not in rules.CAT_NAME:
            raise ValueError("There are three ops: Crit, Tac and Kill.")
        name = rules.CAT_NAME[cat]
        if cat == "tac" and not s["tacops"]:
            raise ValueError("Tac Ops are off for this game.")
        if cat == "crit" and delta > 0 and not rules.crit_open(s["tp"], s["phase"]):
            if s["tp"] <= 1:
                raise ValueError("Nothing scores from the Crit Op in the first turning point.")
            raise ValueError("The Crit Op has not scored yet. It first scores at the end of turning point two.")
        v = s["vp"][side][cat] + delta
        if v > rules.CAP:
            raise ValueError("%s stops at %d points." % (name, rules.CAP))
        if v < 0:
            raise ValueError("%s has no %s points to take away." % (s["names"][side], name))
        s["vp"][side][cat] = v
        return []

    def _ev_score(self, s, ev):
        if s["phase"] != "end":
            raise ValueError("Points are scored at the end of a turning point. To fix a number, use the scoreboard.")
        return self._points(s, ev)

    def _ev_correct(self, s, ev):
        """A correction from the scoreboard. Any phase; the caps still hold."""
        if s["phase"] == "setup":
            raise ValueError("Nothing has been scored yet.")
        return self._points(s, ev)

    def _ev_down(self, s, ev):
        side, n = self._side(ev), s["names"]
        if s["phase"] == "setup":
            raise ValueError("Nobody is down before the game begins.")
        if s["lost"][side] >= s["start"][side]:
            raise ValueError("%s has no operatives left to lose." % n[side])
        before = rules.kill_grade(s["start"][side], s["lost"][side])
        if s["phase"] == "firefight":
            mine = side == s["active"]
            if ev.get("ready"):                    # it had not activated: one fewer activation to come
                if s["left"][side] - (1 if mine and not s["fallen"] else 0) < 1:
                    raise ValueError("%s has no operative still waiting to activate." % n[side])
                s["left"][side] -= 1
            else:
                done = s["start"][side] - s["lost"][side] - s["left"][side]
                if mine and not s["fallen"] and done < 1:
                    s["left"][side] -= 1           # the one activating now: take it off the count once
                    s["fallen"] = True
                elif done < 1:
                    raise ValueError("None of %s's operatives has activated yet." % n[side])
        s["lost"][side] += 1
        after = rules.kill_grade(s["start"][side], s["lost"][side])
        if after > before and s["mode"] != "silent":
            return ["%s reaches kill grade %d." % (n[1 - side], after)]
        return []

    def _ev_revive(self, s, ev):
        side = self._side(ev)
        if s["lost"][side] < 1:
            raise ValueError("%s has lost nobody." % s["names"][side])
        s["lost"][side] -= 1
        if s["phase"] == "firefight" and s["mode"] != "silent":
            return ["Back on the table. It counts as already activated this turning point."]
        return []

    def _ev_did(self, s, ev):
        what = ev.get("what")
        if what not in AGAIN:
            raise ValueError("I do not know that action.")
        if s["phase"] != "firefight":
            raise ValueError("That happens in the Firefight phase.")
        if self._teach(s, what) or s["mode"] != "teach":
            return []
        return [AGAIN[what]]

    def _ev_primary(self, s, ev):
        side, cat = self._side(ev), ev.get("cat")
        if cat not in rules.CAT_NAME:
            raise ValueError("A primary op is the Crit Op, the Tac Op or the Kill Op.")
        if cat == "tac" and not s["tacops"]:
            raise ValueError("Tac Ops are off for this game.")
        if s["primary"][side] == cat:
            raise ValueError("%s has already named that one." % s["names"][side])
        s["primary"][side] = cat
        return []

    # ---------------------------------------------------------------- results
    def over(self, s):
        if not s["done"]:
            return None
        n = s["names"]
        totals, winner = rules.result(s["vp"], s["bonus"])
        head = "%d to %d" % tuple(totals)
        lines = [head if winner is not None else "A draw, " + head]
        for i in (0, 1):
            vp = s["vp"][i]
            parts = ["Crit %d" % vp["crit"]] + (["Tac %d" % vp["tac"]] if s["tacops"] else [])
            parts += ["Kill %d" % vp["kill"], "primary +%d" % s["bonus"][i]]
            lines.append("%s: %s" % (n[i], ", ".join(parts)))
        return {"winner": n[winner] if winner is not None else None, "lines": lines}

    def leader(self, s):
        t = self.totals(s)
        return None if t[0] == t[1] else t.index(max(t))

    def standings(self, s, players):
        t = self.totals(s)
        where = "before the first turning point" if s["tp"] == 0 else "in turning point %d of %d" % (s["tp"], s["tp_max"])
        return ["Victory points: %s %d, %s %d" % (players[0], t[0], players[1], t[1]), "Stopped " + where]

    # ---------------------------------------------------------------- what is shown
    def strip(self, session):
        s = session.state
        left = "Kill Team" if s["tp"] == 0 else "Turning point %d of %d" % (s["tp"], s["tp_max"])
        return left, PHASE_NAME[s["phase"]]

    def where(self, s):
        if s["tp"] == 0:
            return "Setting up"
        return "Turning point %d of %d, %s" % (s["tp"], s["tp_max"], PHASE_NAME[s["phase"]])

    def scoreboard(self, session):
        s, t, rows = session.state, self.totals(session.state), []
        for i, name in enumerate(session.players):
            vp = s["vp"][i]
            detail = ["%s %d / %d" % (label, vp[c], rules.CAP) for c, label in self.cats(s)]
            detail += ["CP %d" % s["cp"][i], "Lost %d of %d" % (s["lost"][i], s["start"][i])]
            if s["tacops"]:                   # the name only once it is revealed; before that, chosen or not
                detail.append("Tac Op: %s" % self.tac_public(s, i))
            rows.append({"name": name, "value": t[i], "detail": ", ".join(detail), "cp": s["cp"][i],
                         "crit": vp["crit"], "tac": vp["tac"], "kill": vp["kill"],
                         "lost": s["lost"][i], "start": s["start"][i], "tacop": self.tac_public(s, i)})
        return {"rows": rows, "note": self.where(s)}

    def phone(self, session, seat):
        """A player's own numbers and the things they may do to them. The other
        side's primary op is never shown, and every action is for this seat."""
        s = session.state
        if seat not in (0, 1):
            return {"lines": [self.where(s)], "actions": []}
        vp, cats = s["vp"][seat], self.cats(s)
        lines = [self.where(s),
                 "Victory points %d: %s" % (rules.total(vp), ", ".join(
                     "%s %d / %d" % (label, vp[c], rules.CAP) for c, label in cats)),
                 "Command points %d" % s["cp"][seat],
                 "Operatives lost %d of %d" % (s["lost"][seat], s["start"][seat])]
        if s["primary"][seat]:
            lines.append("Your primary op: %s" % rules.CAT_NAME[s["primary"][seat]])
        mine, shown = self.tac_name(s, seat), self.tac_shown(s, seat)
        if s["tacops"]:                       # your own by name; the other side's only as the table may know it
            if mine:
                lines.append("Your Tac Op: %s (%s)" % (mine, "revealed" if shown else "secret until you reveal it"))
            else:
                lines.append("Your Tac Op: not recorded yet")
            lines.append("%s's Tac Op: %s" % (s["names"][1 - seat], self.tac_public(s, 1 - seat)))
        actions = []
        if s["done"]:
            return {"lines": lines, "actions": actions}
        if s["phase"] == "firefight" and s["active"] == seat:
            actions.append({"label": "Activation done", "ev": {"ev": "next"}})
        if s["cp"][seat] > 0:
            actions.append({"label": "Spend 1 command point", "ev": {"ev": "cp", "side": seat, "delta": -1}})
        if s["phase"] == "end":
            for c, label in cats:
                if vp[c] < rules.CAP and (c != "crit" or rules.crit_open(s["tp"], s["phase"])):
                    actions.append({"label": "%s +1" % label, "ev": {"ev": "score", "side": seat, "cat": c, "delta": 1}})
        if s["primary"][seat] is None:
            for c, label in cats:
                actions.append({"label": "Primary op: %s" % label, "ev": {"ev": "primary", "side": seat, "cat": c}})
        if s["tacops"] and not shown:
            if not mine or rules.tac_open(s["tp"], s["phase"]):
                actions.append({"label": "Change my Tac Op" if mine else "Record my Tac Op",
                                "ev": {"ev": "tacop", "side": seat},
                                "ask": "The name on your Tac Op card. Only you will see it.", "max": rules.MAX_TAC_NAME})
            if mine:
                actions.append({"label": "Reveal my Tac Op", "ev": {"ev": "reveal", "side": seat}})
        return {"lines": lines, "actions": actions}

    def prompt(self, s):
        """(heading, line under it) for the play screen."""
        n, tp, phase = s["names"], s["tp"], s["phase"]
        if phase == "setup":
            return "How many operatives each?", "Count the models each side starts with. I count activations from them."
        if phase == "strategy":
            if s["init"] is None:
                if s["had"] is None:
                    return "Roll for initiative.", "Both roll one die. The higher roll has it. Tap the winner."
                return "Roll for initiative.", "A tie goes to %s, who did not have it. Tap the winner." % n[1 - s["had"]]
            i = s["init"]
            if tp == 1:
                return "%s has the initiative." % n[i], "One command point each. Ready every operative, then ploys."
            return "%s has the initiative." % n[i], "%s gains 1 command point, %s gains 2. Ready up." % (
                n[i], n[1 - i])
        if phase == "firefight":
            a = s["active"]
            if a is None:
                return "Nobody is left to activate.", "Press the button to end the turning point."
            c = rules.counteract(a, s["left"], self.alive(s))
            if c is not None:
                return "%s, keep activating." % n[a], "%s has none ready, and may counteract after each one." % n[c]
            if s["mode"] == "teach":
                return "%s, pick an operative." % n[a], "Choose its order, then spend its actions. Tell me what it does."
            return "%s, pick an operative." % n[a], "Order? Action?"
        head = "End of turning point %d." % tp
        if tp == 1:
            sub = "The Crit Op does not score yet. The Kill Op can. Open the score sheet."
        else:
            sub = "Score what the mission card says. Each op stops at 6."
        if tp == s["tp_max"]:
            sub += " Then reveal your primary ops."
        return head, sub

    def play_screen(self, app, session):
        return KTPlay(app, session)


# -------------------------------------------------------------------- widgets
class Cell:
    """A box with a word on the left and a number on the right. Tappable when
    it has an action. label is its name for the tests; it is not drawn."""
    style, selected = "cell", False

    def __init__(self, rect, label, text, value, action=None, text_colour=None, value_colour=None,
                 mark=False, size=34):
        self.rect = pygame.Rect(rect)
        self.label, self.text, self.value, self.action = label, text, str(value), action
        self.text_colour, self.value_colour, self.mark, self.size = text_colour, value_colour, mark, size

    def draw(self, surf, pressed=False):
        r = self.rect
        bg = (T.LINE if pressed else T.RAISED) if self.action else T.GROUND
        pygame.draw.rect(surf, bg, r, border_radius=12)
        if self.mark:                        # a thick light edge: whose go it is, not colour alone
            pygame.draw.rect(surf, T.TEXT, r, 3, border_radius=12)
        else:
            pygame.draw.rect(surf, T.LINE, r, 1, border_radius=12)
        vw = T.font("head", self.size).size(self.value)[0]
        T.draw_text(surf, self.text, "mid", 22, self.text_colour or T.DIM, (r.x + 14, r.centery), "midleft",
                    max_w=max(40, r.w - 40 - vw))
        T.draw_text(surf, self.value, "head", self.size, self.value_colour or T.TEXT, (r.right - 14, r.centery),
                    "midright")


def stepper(x, y, w, minus, plus):
    """A minus and a plus button at the two ends of a column, with room for a number between."""
    return [Button((x + w // 2 - 122, y, 64, 64), "−", minus, size=30),
            Button((x + w // 2 + 58, y, 64, 64), "+", plus, size=30)]


COLS = [(20, 370), (410, 370)]               # the two players' columns: (x, width)


# -------------------------------------------------------------------- screens
CARD_TOP, CARD_ROOM = 124, 260               # where a card's text starts, and how tall it may be


def card_pages(steps, max_w=T.W - 48):
    """steps: [(heading, body)] to pages [(heading, [lines])], by height: a
    line is 32 px and a gap between paragraphs 16. A step that is too long for
    one card runs on to a second."""
    pages = []
    for heading, body in steps:
        page, h = [], 0
        for line in T.wrap_paragraphs(body or "", "text", 24, max_w):
            need = 32 if line else 16
            if page and h + need > CARD_ROOM:
                pages.append((heading, page))
                page, h = [], 0
            if line or page:
                page.append(line)
                h += need
        pages.append((heading, page or [""]))
    return pages


class Card(Pages):
    """Teaching steps as cards the players step through. Press = next."""

    def __init__(self, app, session, steps, opener=None):
        super().__init__(app, "Kill Team · Teach", "", [])
        self.opener = opener                  # the screen whose event brought this card up
        self.session, self.at = session, len(session.log)     # that event is the last one in the log
        self.pages = card_pages([(st["title"], st["text"]) for st in steps])
        i = session.game.active(session.state)
        self.pill = ("%s's turn" % session.players[i], T.player_colour(i)) if i is not None else None
        self._read = None

    def build(self):
        n, last = len(self.pages), self.i + 1 >= len(self.pages)
        self.title = "Step %d of %d" % (self.i + 1, n) if n > 1 else "Rule card"
        spec = [("Back", self.prev if self.i else self.app.pop, 1, "plain")]
        if getattr(self.app, "voice", None):
            spec.append(("Say again", self.read, 1.4, "plain"))
        spec.append(("Got it" if last else "Next", self.next, 2.6, "primary"))
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def refresh(self):
        super().refresh()
        if getattr(self.app, "voice", None) and self._read != self.i:
            self._read = self.i               # she reads each card aloud once, as it appears
            self.read()

    @property
    def undoes_press(self):
        """The press that closed the score sheet moved the game on and brought
        this card: a double press may still take it back."""
        return bool(getattr(self.opener, "sheet_press", False))

    def on_button(self, gesture):
        if gesture == "double" and self.opener is not None:
            # Double press is undo here too. The press that came with it only
            # turned a page (or closed the score sheet), so exactly one event
            # goes: the one that brought this card. If anything has been
            # logged since, nothing does.
            mine = len(self.session.log) == self.at and not self.session.finished
            self.app.pop()
            if mine:
                self.opener.undo()
        else:
            super().on_button(gesture)

    def draw_body(self, surf):
        heading, lines = self.pages[self.i]
        T.draw_text(surf, heading, "head", 36, T.TEXT, (24, 70), max_w=T.W - 48)
        y = CARD_TOP
        for line in lines:
            if line:
                T.draw_text(surf, line, "text", 24, T.TEXT, (24, y))
            y += 32 if line else 16


class KTMenu(GameMenu):
    """The shared Menu, with one thing added for this game: how long an
    activation may run before she mentions it."""

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
            self.app.say("%s an activation. Past that I will mention it, once." % words)
        else:
            self.app.say("I will keep the time to myself.")
        self.refresh()


class KTBase(PlayBase):
    """Shared by every Kill Team screen: after an event, show any rule card it made due."""

    def do(self, **ev):
        before = list(self.state["taught"])
        ok = super().do(**ev)
        if ok and not self.session.finished:
            self.show_cards([k for k in self.state["taught"] if k not in before], self)
        return ok

    def show_cards(self, keys, opener=None):
        steps = [st for k in keys for st in self.game.cards(k)]
        if steps:
            self.app.push(Card(self.app, self.session, steps, opener))

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

    def more(self):
        self.app.push(KTMenu(self.app, self.session, self.repace))

    def repace(self):
        pace = getattr(self, "pace", None)
        if pace:
            pace.restart()

    def names_row(self, surf, y, size=30):
        for i, (x, w) in enumerate(COLS):
            T.draw_text(surf, self.session.players[i], "head", size, T.player_colour(i), (x + w // 2, y), "midtop",
                        max_w=w - 20)


class KTPlay(KTBase):
    """The main screen: the phase's prompt, the numbers that matter now, and the common events."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self._intro = False
        self.pace = rules.Pace()              # new with the screen, so a resumed game starts timing afresh
        self._warn_until = None
        self._line = random.randrange(len(NUDGE_LINES))
        self._tick_at = None                  # when tick was last called
        self.sheet_press = False              # the button on the score sheet has just moved the game on

    @property
    def undoes_press(self):
        return self.sheet_press

    def ring_warning(self):
        ring = getattr(self.app.hw, "_ring", None)
        return ring is None or getattr(ring, "now", ("warn",))[0] == "warn"

    def tick(self, t):
        """The app calls this many times a second with the time. An activation
        that runs past the limit earns one line and an amber blink, once.
        Only while this screen is the one showing: under a menu, a card or the
        scoreboard the clock stands still and nothing is said."""
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
        self.sheet_press = False
        super().enter()
        s = self.state
        if s["mode"] == "teach" and s["phase"] == "setup" and not self.session.log and not self._intro:
            self._intro = True                # the first-game steps, before anything is counted
            self.show_cards(["start"])
        elif (first and s["mode"] == "teach" and self.session.log and s.get("pending")
              and self.session.d.get("cards_seen") != len(self.session.log)):
            self.show_cards(s["pending"], self)   # a resumed game: the card that was up when it stopped

    def build(self):
        s, names, phase, out = self.state, self.session.players, self.state["phase"], []
        nxt = lambda: self.do(ev="next")
        if phase == "setup":
            for i, (x, w) in enumerate(COLS):
                out += stepper(x, 232, w, lambda i=i: self.do(ev="ops", side=i, delta=-1),
                               lambda i=i: self.do(ev="ops", side=i, delta=1))
            return out + row([("Begin", nxt, 1.8, "primary"), ("Undo", self.undo, 1, "plain"),
                              ("Menu", self.more, 1, "plain")], BOTTOM_Y, BOTTOM_H)
        if phase == "strategy":
            for i, (x, w) in enumerate(COLS):
                label = "%s has initiative" if s["init"] == i else "%s won the roll"
                out.append(Button((x, 200, w, 64), label % names[i], lambda i=i: self.do(ev="init", side=i),
                                  selected=(s["init"] == i)))
        elif phase == "firefight" and s["mode"] == "teach":
            w = (760 - 3 * 10) // 4
            for k, (what, label) in enumerate(DID):
                out.append(Button((20 + k * (w + 10), 200, w, 64), label, lambda what=what: self.do(ev="did", what=what)))
        for i in (0, 1):                      # command points: tap your own number to spend one
            out.append(Cell((28 + i * 183, 314, 176, 64), "Spend CP: " + names[i], names[i], s["cp"][i],
                            lambda i=i: self.do(ev="cp", side=i, delta=-1), T.player_colour(i), T.player_colour(i)))
        _, values = self.second_tile()
        for i in (0, 1):
            out.append(Cell((413 + i * 183, 314, 176, 64), "", names[i], values[i], None, T.player_colour(i),
                            T.player_colour(i), mark=(phase == "firefight" and s["active"] == i)))
        if phase == "end":
            spec = [("Score sheet", self.sheet, 1.9, "primary"), ("Operative down", self.down, 1.9, "plain"),
                    ("Undo", self.undo, 1, "plain"), ("Menu", self.more, 1.1, "plain")]
        else:
            spec = [("Next", nxt, 1.6, "primary"), ("Score", self.score, 1, "plain"),
                    ("Operative down", self.down, 1.9, "plain"), ("Undo", self.undo, 1, "plain"),
                    ("Menu", self.more, 1.1, "plain")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def second_tile(self):
        s = self.state
        if s["phase"] == "firefight":
            return "Activations left", s["left"]
        if s["phase"] == "end":
            return "Victory points", self.game.totals(s)
        return "Operatives left", self.game.alive(s)

    def score(self):
        self.app.push(KTScore(self.app, self.session))

    def sheet(self):
        self.app.push(KTSheet(self.app, self.session))

    def down(self):
        self.app.push(KTDown(self.app, self.session))

    def draw_body(self, surf):
        s, phase = self.state, self.state["phase"]
        head, sub = self.game.prompt(s)
        if phase == "setup":
            T.draw_text(surf, head, "head", 44, T.TEXT, (20, 72), max_w=760)
            if s["mode"] != "silent":
                T.draw_text(surf, sub, "text", 24, T.DIM, (20, 130), max_w=760)
            self.names_row(surf, 180)
            for i, (x, w) in enumerate(COLS):
                T.draw_text(surf, str(s["start"][i]), "head", 44, T.TEXT, (x + w // 2, 264), "center")
                if s["tacops"]:               # chosen or not, never which: the screen is shared
                    T.draw_text(surf, "Tac Op: %s" % self.game.tac_public(s, i), "text", 22, T.TEXT, (x + w // 2, 302),
                                "midtop", max_w=w - 20)
            if s["mode"] != "silent":
                T.draw_text(surf, "Both sides start with %d command points." % rules.START_CP, "text", 22, T.DIM,
                            (T.W // 2, 340 if s["tacops"] else 322), "midtop")
            return
        if s["mode"] == "silent":             # numbers only
            self.names_row(surf, 70)
            t = self.game.totals(s)
            for i, (x, w) in enumerate(COLS):
                T.draw_text(surf, str(t[i]), "head", 64, T.player_colour(i), (x + w // 2, 152), "center")
            T.draw_text(surf, "to", "text", 28, T.DIM, (T.W // 2, 152), "center")
        else:
            T.draw_text(surf, head, "head", 44, T.TEXT, (20, 72), max_w=760)
            room = 2 if phase in ("strategy",) or (phase == "firefight" and s["mode"] == "teach") else 4
            y = 130
            for line in T.wrap(sub, "text", 26, 760)[:room]:
                T.draw_text(surf, line, "text", 26, T.DIM, (20, y))
                y += 32
        for x, label in ((20, "Command points: tap to spend"), (405, self.second_tile()[0])):
            panel = pygame.Rect(x, 276, 375, 108)
            pygame.draw.rect(surf, T.PANEL, panel, border_radius=14)
            pygame.draw.rect(surf, T.LINE, panel, 1, border_radius=14)
            T.draw_text(surf, label, "text", 22, T.DIM, (x + 14, 282), max_w=347)

    def on_button(self, gesture):
        self.sheet_press = False
        if gesture == "press" and self.state["phase"] == "end":
            self._logged = False
            self.sheet()                      # scoring is this phase's "next"
        else:
            super().on_button(gesture)


class KTScore(KTBase):
    """The full-screen scoreboard. Tap a number to correct it."""

    @property
    def title(self):
        return "Scoreboard"

    @property
    def pill(self):
        return None

    def build(self):
        s, out = self.state, []
        for i, (x, w) in enumerate(COLS):
            x, w = (20, 373) if i == 0 else (407, 373)
            vp, who = s["vp"][i], self.session.players[i]
            for k, (c, label) in enumerate(rules.CATS):
                rect = (x + 8, 128 + k * 68, w - 16, 64)
                if c == "tac" and not s["tacops"]:
                    out.append(Cell(rect, "", label, "Off", None, value_colour=T.DIM, size=26))
                else:
                    text = "Tac Op: %s" % self.game.tac_public(s, i) if c == "tac" else label
                    out.append(Cell(rect, "%s %s" % (who, label), text, "%d / %d" % (vp[c], rules.CAP),
                                    lambda i=i, c=c: self.adjust(i, c), size=30))
            half = (w - 16 - 6) // 2
            out.append(Cell((x + 8, 332, half, 64), "%s CP" % who, "CP", s["cp"][i], lambda i=i: self.adjust(i, "cp"),
                            size=30))
            out.append(Cell((x + 8 + half + 6, 332, half, 64), "%s Lost" % who, "Lost",
                            "%d of %d" % (s["lost"][i], s["start"][i]), self.down, size=26))
        out.append(Button((500, 408, 280, 64), "Back to the game", self.app.pop, "primary"))
        return out

    def adjust(self, side, what):
        self.app.push(KTAdjust(self.app, self.session, side, what))

    def down(self):
        self.app.push(KTDown(self.app, self.session))

    def draw_body(self, surf):
        t = self.game.totals(self.state)
        for i, x in enumerate((20, 407)):
            panel = pygame.Rect(x, 66, 373, 336)
            pygame.draw.rect(surf, T.PANEL, panel, border_radius=18)
            pygame.draw.rect(surf, T.LINE, panel, 1, border_radius=18)
            colour = T.player_colour(i)
            pygame.draw.rect(surf, colour, (x + 10, 78, 5, 38), border_radius=2)
            T.draw_text(surf, self.session.players[i], "head", 30, colour, (x + 24, 97), "midleft", max_w=250)
            T.draw_text(surf, str(t[i]), "head", 52, colour, (panel.right - 18, 97), "midright")
        T.draw_text(surf, "Tap a number to correct it", "text", 22, T.DIM, (20, 440), "midleft")

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class KTAdjust(KTBase):
    """Correct one number: step it up or down, then confirm."""

    def __init__(self, app, session, side, what):
        super().__init__(app, session)
        self.side, self.what, self.delta = side, what, 0

    @property
    def title(self):
        return "Correct a number"

    @property
    def pill(self):
        return None

    def was(self):
        s = self.state
        return s["cp"][self.side] if self.what == "cp" else s["vp"][self.side][self.what]

    def build(self):
        spec = [("Back", self.app.pop, 1, "plain"), ("− 1", lambda: self.step(-1), 1, "plain"),
                ("+ 1", lambda: self.step(1), 1, "plain"), ("Set to %d" % (self.was() + self.delta), self.confirm, 1.6, "primary")]
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def step(self, d):
        v = self.was() + self.delta + d
        if v < 0:
            self.app.say("Less than nothing is not a score.")
        elif self.what != "cp" and v > rules.CAP:
            self.app.say("%s stops at %d points." % (rules.CAT_NAME[self.what], rules.CAP))
        else:
            self.delta += d
        self.refresh()

    def confirm(self):
        if self.delta == 0:
            self.app.pop()
        elif self.what == "cp":
            if self.do(ev="cp", side=self.side, delta=self.delta):
                self.app.pop()
        elif self.do(ev="correct", side=self.side, cat=self.what, delta=self.delta):
            self.app.pop()

    def draw_body(self, surf):
        colour = T.player_colour(self.side)
        T.draw_text(surf, self.session.players[self.side], "head", 36, colour, (T.W // 2, 76), "midtop", max_w=720)
        cp = self.what == "cp"
        T.draw_text(surf, "Command points" if cp else rules.CAT_NAME[self.what], "text", 26, T.DIM, (T.W // 2, 128),
                    "midtop")
        now = self.was() + self.delta
        T.draw_text(surf, str(now) if cp else "%d / %d" % (now, rules.CAP), "head", 96, T.TEXT, (T.W // 2, 232), "center")
        T.draw_text(surf, "It was %d. Step it, then set it." % self.was(), "text", 24, T.DIM, (T.W // 2, 312), "midtop")

    def on_button(self, gesture):
        if gesture == "press":
            self.confirm()
        elif gesture == "double":
            self.app.pop()


class KTSheet(KTBase):
    """End of a turning point: award this round's points, a tap at a time."""

    @property
    def left(self):
        return "End of turning point %d" % self.state["tp"]

    @property
    def title(self):
        return "Score this round"

    @property
    def pill(self):
        return None

    def last(self):
        return self.state["tp"] == self.state["tp_max"]

    def build(self):
        s, out = self.state, []
        for k, (c, _) in enumerate(rules.CATS):
            if c == "tac" and not s["tacops"]:
                continue
            for i, (x, w) in enumerate(self.cols()):
                out += stepper(x, 106 + k * 72, w, lambda i=i, c=c: self.do(ev="score", side=i, cat=c, delta=-1),
                               lambda i=i, c=c: self.do(ev="score", side=i, cat=c, delta=1))
        label = "Done: primary ops" if self.last() else "Done"
        return out + row([("Back", self.app.pop, 1, "plain"), (label, self.done, 2.2, "primary")], BOTTOM_Y, BOTTOM_H)

    @staticmethod
    def cols():
        return [(182, 293), (487, 293)]

    def done(self, button=False):
        if self.state["phase"] != "end":
            self.app.pop()
        elif self.last():
            s, g = self.state, self.game
            if s["tacops"] and any(g.tac_name(s, i) and not g.tac_shown(s, i) for i in (0, 1)):
                self.do(ev="reveal", side="all")      # the last scoring is done: the Tac Ops are shown with the primary ops
            self.app.push(KTReveal(self.app, self.session))
        else:
            self.app.pop()                    # the play screen takes the event, and shows any rule card
            below = self.app.screen
            (below.do if isinstance(below, KTBase) else self.session.do)(ev="next")
            if button and isinstance(below, KTPlay):
                below.sheet_press = below._logged     # a double press may now take this back

    def undo(self, quiet=False):
        super().undo(quiet)
        if self.state["phase"] != "end":      # undone right out of the End phase
            self.app.pop()

    def draw_body(self, surf):
        s, names = self.state, self.session.players
        for i, (x, w) in enumerate(self.cols()):
            T.draw_text(surf, names[i], "head", 24, T.player_colour(i), (x + w // 2, 68), "midtop", max_w=w - 10)
        for k, (c, label) in enumerate(rules.CATS):
            y = 106 + k * 72 + 32
            T.draw_text(surf, label, "bold", 24, T.TEXT, (20, y), "midleft")
            for i, (x, w) in enumerate(self.cols()):
                if c == "tac" and not s["tacops"]:
                    T.draw_text(surf, "Off", "text", 24, T.DIM, (x + w // 2, y), "center")
                else:
                    T.draw_text(surf, "%d / %d" % (s["vp"][i][c], rules.CAP), "head", 34, T.player_colour(i),
                                (x + w // 2, y), "center")
        g = self.game.grades(s)
        first = "Each op stops at %d." % rules.CAP
        if not rules.crit_open(s["tp"], s["phase"]):
            first += " The Crit Op does not score in turning point 1."
        T.draw_text(surf, first, "text", 22, T.DIM, (20, 324), max_w=760)
        T.draw_text(surf, "Kills so far: %s is at kill grade %d, %s at %d." % (names[0], g[0], names[1], g[1]),
                    "text", 22, T.DIM, (20, 354), max_w=760)

    def on_button(self, gesture):
        if gesture == "press":
            self.done(button=True)
        elif gesture == "double":
            self.undo()


class KTReveal(KTBase):
    """After the last scoring: each side reveals its primary op, and the bonus is added."""

    @property
    def left(self):
        return "End of the game"

    @property
    def title(self):
        return "Primary ops"

    @property
    def pill(self):
        return None

    def build(self):
        s, out = self.state, []
        for i, (x, w) in enumerate(COLS):
            for k, (c, label) in enumerate(self.game.cats(s)):
                chosen = s["primary"][i] == c
                if chosen:
                    label = "%s: %d, bonus +%d" % (label, s["vp"][i][c], rules.primary_bonus(s["vp"][i][c]))
                y = 124 + k * 68 if s["tacops"] else 110 + k * 72     # with Tac Ops: room for their names above
                out.append(Button((x, y, w, 64), label,
                                  lambda i=i, c=c: self.do(ev="primary", side=i, cat=c), selected=chosen))
        return out + row([("Back", self.app.pop, 1, "plain"), ("Finish the game", self.finish, 2.2, "primary")],
                         BOTTOM_Y, BOTTOM_H)

    def finish(self):
        self.do(ev="next")

    def draw_body(self, surf):
        s = self.state
        if s["tacops"]:
            self.names_row(surf, 62, 26)
            for i, (x, w) in enumerate(COLS):
                T.draw_text(surf, "Tac Op: %s" % self.game.tac_public(s, i), "text", 22, T.TEXT, (x + w // 2, 94), "midtop",
                            max_w=w - 20)
        else:
            self.names_row(surf, 70)
        if None in s["primary"]:
            T.draw_text(surf, "Each of you: reveal the primary op you wrote down.", "text", 24, T.DIM,
                        (T.W // 2, 338), "midtop", max_w=760)
            return
        final = [rules.total(s["vp"][i], rules.primary_bonus(s["vp"][i][s["primary"][i]])) for i in (0, 1)]
        T.draw_text(surf, "Final score: %d to %d" % tuple(final), "head", 34, T.TEXT, (T.W // 2, 334), "midtop",
                    max_w=760)

    def on_button(self, gesture):
        if gesture == "press":
            self.finish()
        elif gesture == "double":
            self.app.pop()


class KTDown(KTBase):
    """An operative is incapacitated. Which side, and had it activated yet?"""

    @property
    def title(self):
        return "Operative down"

    @property
    def pill(self):
        return None

    def build(self):
        s, out = self.state, []
        for i, (x, w) in enumerate(COLS):
            if s["phase"] == "firefight":
                spec = [("Not yet activated", lambda i=i: self.do(ev="down", side=i, ready=True)),
                        ("Already activated", lambda i=i: self.do(ev="down", side=i, ready=False))]
            else:
                spec = [("Lost one", lambda i=i: self.do(ev="down", side=i, ready=False))]
            spec.append(("Put one back", lambda i=i: self.do(ev="revive", side=i)))
            for k, (label, act) in enumerate(spec):
                out.append(Button((x, 148 + k * 70, w, 64), label, act))
        return out + row([("Back to the game", self.app.pop, 2.2, "primary"), ("Undo", self.undo, 1, "plain")],
                         BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        s, names, g = self.state, self.session.players, self.game.grades(self.state)
        for i, (x, w) in enumerate(COLS):
            T.draw_text(surf, names[i], "head", 30, T.player_colour(i), (x, 66), max_w=w - 150)
            T.draw_text(surf, "Lost %d of %d" % (s["lost"][i], s["start"][i]), "mid", 24, T.TEXT, (x + w, 72),
                        "topright")
            foe = 1 - i                       # this side's losses are the other side's kill grade
            for k in range(rules.GRADES):
                box = pygame.Rect(x + k * 26, 116, 22, 16)
                if k < g[foe]:
                    pygame.draw.rect(surf, T.TEXT, box, border_radius=4)
                else:
                    pygame.draw.rect(surf, T.LINE, box, 2, border_radius=4)
            T.draw_text(surf, "Kill grade %d: %s" % (g[foe], names[foe]), "text", 22, T.DIM, (x + w, 124), "midright",
                        max_w=w - 140)
        if s["phase"] == "firefight":
            T.draw_text(surf, "The one activating now counts as already activated.", "text", 22, T.DIM,
                        (T.W // 2, 358), "midtop", max_w=760)

    def on_button(self, gesture):
        if gesture == "press":
            self.app.pop()
        elif gesture == "double":
            self.undo()
