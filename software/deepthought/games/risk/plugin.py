"""Risk. The box runs the turn, does the army sums, counts card sets and
rolls the battles. The players keep the map; the box keeps the numbers."""
import copy
import random
import pygame
from ... import theme as T
from ...engine import Game
from ...screens.common import BOTTOM_H, BOTTOM_Y, Choice, PlayBase
from ...widgets import Button, Tile, row
from . import rules

PHASES = [("reinforce", "Reinforce"), ("attack", "Attack"), ("fortify", "Fortify")]
PHASE_NAME = dict(PHASES)


class Plugin(Game):
    min_players, max_players = 2, 6
    options = [{"key": "hints", "label": "Hints", "choices": ["On", "Off"]}]

    def new_state(self, players, options):
        terr, neutral = rules.start_territories(len(players))
        return {"turn": 1, "active": 0, "phase": "reinforce", "terr": terr, "neutral": neutral,
                "cont": [[] for _ in players], "cards": [0] * len(players), "out": [False] * len(players),
                "sets": 0, "bonus": 0, "captured": False, "spoils": False, "names": list(players),
                "hints": options.get("hints", "On") == "On"}

    def phases(self):
        return PHASES

    def armies(self, state, i=None):
        i = state["active"] if i is None else i
        return rules.reinforcements(state["terr"][i], state["cont"][i], state["bonus"] if i == state["active"] else 0)

    def may_trade(self, s):
        """At the start of a turn; or mid-attack, straight after knocking a player
        out, while their cards leave the attacker holding five or more."""
        return s["phase"] == "reinforce" or (s["phase"] == "attack" and bool(s.get("spoils"))
                                             and s["cards"][s["active"]] >= 5)

    def broken(self, s, p):
        """Does this player hold too few territories for the continents ticked as theirs?"""
        return s["terr"][p] < sum(rules.SIZE[c] for c in s["cont"][p])

    def _pass_turn(self, s):
        """The turn goes to the next player still in the game."""
        me, names, said = s["active"], s["names"], []
        s["captured"], s["spoils"], s["bonus"], s["phase"] = False, False, 0, "reinforce"
        nxt = me
        for _ in range(len(names)):
            nxt = (nxt + 1) % len(names)
            if not s["out"][nxt]:
                break
        if nxt <= me:
            s["turn"] += 1
        s["active"] = nxt
        total, _ = self.armies(s)
        said.append("%s: %d armies to place." % (names[nxt], total))
        if s["cards"][nxt] >= 5:
            said.append("Five cards in hand: a set must be traded now.")
        return said

    def apply(self, s, ev):
        kind, me, names = ev["ev"], s["active"], s["names"]
        if kind == "next":
            order = [p for p, _ in PHASES]
            if s["phase"] == "reinforce" and self.broken(s, me):
                raise ValueError("%s holds too few territories for the continents ticked. Untick one under Map first."
                                 % names[me])
            if s["phase"] != "fortify":
                if s["phase"] == "reinforce":
                    s["bonus"] = 0               # those armies are placed; a set traded mid-attack starts from nought
                s["phase"] = order[order.index(s["phase"]) + 1]
                return []
            said = []
            if s["captured"]:
                s["cards"][me] += 1
                said.append("%s takes a card." % names[me])
            return said + self._pass_turn(s)
        if kind == "trade":
            if not self.may_trade(s):
                raise ValueError("Sets are traded at the start of a turn, before attacking.")
            if s["cards"][me] < 3:
                raise ValueError("%s has %d cards. A set needs three." % (names[me], s["cards"][me]))
            value = rules.set_value(s["sets"])
            s["sets"] += 1
            s["cards"][me] -= 3
            s["bonus"] += value
            return ["Set %d is worth %d armies. Two more on any territory shown on those cards that %s holds."
                    % (s["sets"], value, names[me])]
        if kind == "card":
            p = ev.get("player", me)
            if s["cards"][p] + ev["delta"] < 0:
                raise ValueError("%s has no cards to give up." % names[p])
            s["cards"][p] += ev["delta"]
            return []
        if kind == "capture":
            if s["phase"] != "attack":
                raise ValueError("Territories are only taken in the attack phase.")
            d = ev["defender"]
            if d == "neutral":
                if s["neutral"] < 1:
                    raise ValueError("The neutral army has no territories left.")
                s["neutral"] -= 1
                s["terr"][me] += 1
                s["captured"] = True
                return []
            if d == me or s["out"][d] or s["terr"][d] < 1:
                raise ValueError("%s has no territory to lose." % names[d])
            s["terr"][d] -= 1
            s["terr"][me] += 1
            s["captured"] = True
            said = []
            if len(s["cont"][d]) == 1 and self.broken(s, d):
                said.append("%s no longer holds %s." % (names[d], s["cont"][d][0]))    # too few left: it cannot be whole
                s["cont"][d] = []
            elif s["cont"][d]:
                said.append("%s: if that broke a continent, untick it under Map." % names[d])
            if s["terr"][d] == 0:
                s["out"][d], s["cont"][d] = True, []
                said.append("%s is eliminated. %s takes their %d cards." % (names[d], names[me], s["cards"][d]))
                s["cards"][me] += s["cards"][d]
                s["cards"][d] = 0
                s["spoils"] = True
                if s["cards"][me] >= 6:
                    said.append("Six or more cards: trade sets at once.")
            return said
        if kind == "terr":
            p, v = ev["player"], s["terr"][ev["player"]] + ev["delta"]
            if v < 0:
                raise ValueError("Nobody holds fewer than no territories.")
            if sum(s["terr"]) + s["neutral"] + ev["delta"] > rules.TERRITORIES:
                raise ValueError("There are only 42 territories on the board.")
            if v < sum(rules.SIZE[c] for c in s["cont"][p]):
                raise ValueError("%s's continents need more territories than that. Untick one first." % names[p])
            if v == 0 and not any(not o for i, o in enumerate(s["out"]) if i != p):
                raise ValueError("Somebody has to hold something.")
            s["terr"][p] = v
            s["out"][p] = v == 0
            if v == 0 and p == me and s["out"].count(False) > 1:
                return ["%s is out of the game." % names[p]] + self._pass_turn(s)    # no turns for a player with no territory
            return []
        if kind == "cont":
            p, c = ev["player"], ev["name"]
            if c in s["cont"][p]:
                s["cont"][p].remove(c)
                return []
            holder = next((i for i, cs in enumerate(s["cont"]) if c in cs), None)
            if holder is not None:
                raise ValueError("%s already holds %s." % (names[holder], c))
            if sum(rules.SIZE[x] for x in s["cont"][p]) + rules.SIZE[c] > s["terr"][p]:
                raise ValueError("%s has too few territories to hold %s as well." % (names[p], c))
            s["cont"][p].append(c)
            return []
        raise ValueError("I do not know what %r means in Risk." % kind)

    def over(self, s):
        alive = [i for i, out in enumerate(s["out"]) if not out]
        if len(alive) == 1:                      # with two players the neutral army need not be beaten as well
            line = "The world, all 42 territories" if s["neutral"] == 0 else "The last player standing"
            return {"winner": s["names"][alive[0]], "lines": [line, "Turn %d" % s["turn"]]}
        return None

    def standings(self, s, players):
        order = sorted(range(len(players)), key=lambda i: -s["terr"][i])
        return ["Territories: " + ", ".join("%s %d" % (players[i], s["terr"][i]) for i in order),
                "Stopped on turn %d" % s["turn"]]

    def leader(self, s):
        best = max(s["terr"])
        return s["terr"].index(best) if s["terr"].count(best) == 1 else None

    def strip(self, session):
        s = session.state
        return "Risk · Turn %d" % s["turn"], PHASE_NAME[s["phase"]]

    def scoreboard(self, session):
        s = session.state
        return {"rows": [{"name": p, "value": s["terr"][i], "out": s["out"][i]} for i, p in enumerate(session.players)],
                "note": "Territories"}

    def play_screen(self, app, session):
        return RiskPlay(app, session)


class RiskPlay(PlayBase):
    def build(self):
        s, me = self.state, self.state["active"]
        total, _ = self.game.armies(s)
        tiles = [Tile((20, 300, 245, 80), "Territories", s["terr"][me], self.map),
                 Tile((277, 300, 245, 80), "Cards", s["cards"][me], lambda: self.do(ev="card", delta=1))]
        if s["phase"] == "reinforce":
            tiles.append(Tile((534, 300, 246, 80), "Armies", total))
        elif s["phase"] == "attack" and s["bonus"]:
            tiles.append(Tile((534, 300, 246, 80), "Card armies", s["bonus"]))     # from a set traded mid-attack
        else:
            tiles.append(Tile((534, 300, 246, 80), "Sets traded", s["sets"]))
        spec = [("Next", lambda: self.do(ev="next"), 1.3, "primary")]
        if s["phase"] == "reinforce":
            spec.append(("Trade set", lambda: self.do(ev="trade"), 1.5, "plain"))
        elif s["phase"] == "attack" and self.game.may_trade(s):
            spec += [("Battle", self.battle, 1.1, "plain"), ("Trade set", lambda: self.do(ev="trade"), 1.5, "plain")]
        elif s["phase"] == "attack":
            spec.append(("Battle", self.battle, 1.5, "plain"))
        spec += [("Map", self.map, 1, "plain"), ("Undo", self.undo, 1, "plain"), ("Menu", self.more, 1, "plain")]
        return tiles + row(spec, BOTTOM_Y, BOTTOM_H)

    def map(self):
        self.app.push(RiskMap(self.app, self.session))

    def battle(self):
        self.app.push(RiskBattle(self.app, self.session))

    def draw_body(self, surf):
        s, me = self.state, self.state["active"]
        name = self.session.players[me]
        total, how = self.game.armies(s)
        if s["phase"] == "reinforce":
            head, hint = "%s, place %d armies." % (name, total), how
        elif s["phase"] == "attack":
            head = "%s, attack or press Next." % name
            hint = "Attacker rolls up to 3 dice, defender up to 2. Ties go to the defender."
        else:
            head = "%s, fortify once." % name
            hint = "Move armies between two of your territories that touch. Leave one behind."
        T.draw_text(surf, head, "head", 44, T.TEXT, (20, 84), max_w=760)
        if s["hints"] or s["phase"] == "reinforce":
            y = 150
            for line in T.wrap(hint, "text", 24, 760)[:3]:
                T.draw_text(surf, line, "text", 24, T.DIM, (20, y))
                y += 32
        if s["cards"][me] >= 5 and self.game.may_trade(s):
            T.draw_text(surf, "Five cards: a set must be traded.", "bold", 22, T.WARN, (20, 262))
        elif s["phase"] == "reinforce" and self.game.broken(s, me):
            T.draw_text(surf, "Too few territories for the continents ticked. See Map.", "bold", 22, T.WARN, (20, 262),
                        max_w=760)


class RiskMap(PlayBase):
    """Who holds what. The players tell the box; the box does the sums."""

    def __init__(self, app, session):
        super().__init__(app, session)
        self.who = session.state["active"]

    @property
    def title(self):
        return "Map"

    def build(self):
        s, names, out = self.state, self.session.players, []
        w = (760 - 8 * (len(names) - 1)) // len(names)
        for i, n in enumerate(names):
            out.append(Button((20 + i * (w + 8), 68, w, 64), n, lambda i=i: self.pick(i), selected=(i == self.who), size=22))
        out += [Button((20, 142, 68, 64), "−", self.fewer, size=30),
                Button((176, 142, 68, 64), "+", lambda: self.do(ev="terr", player=self.who, delta=1), size=30)]
        for k, (c, bonus, _) in enumerate(rules.CONTINENTS):
            rect = (20 + (k % 3) * 257, 216 + (k // 3) * 72, 247, 64)
            held = c in s["cont"][self.who]
            out.append(Button(rect, ("Holds %s" if held else "%s +%d") % ((c,) if held else (c, bonus)),
                              lambda c=c: self.do(ev="cont", player=self.who, name=c), selected=held, size=22))
        return out + row([("Back to the game", self.app.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def pick(self, i):
        self.who = i
        self.refresh()

    def fewer(self):
        """One territory fewer. Ask first if that ends the game: this is a screen for corrections."""
        ev = dict(ev="terr", player=self.who, delta=-1)
        trial = copy.deepcopy(self.state)
        try:
            self.game.apply(trial, ev)
            end = self.game.over(trial)
        except (ValueError, KeyError, TypeError):
            end = None
        if not end:
            return self.do(**ev)
        text = "That leaves %s with no territory and ends the game.\n%s wins. Is that right?" % (
            self.session.players[self.who], end["winner"])
        self.app.push(Choice(self.app, "Game over?", text,
                             [("Keep playing", None), ("End the game", lambda: self.do(**ev))], left=self.left))

    def draw_body(self, surf):
        s = self.state
        T.draw_text(surf, str(s["terr"][self.who]), "head", 40, T.TEXT, (132, 174), "center")
        total, _ = rules.reinforcements(s["terr"][self.who], s["cont"][self.who])
        text = "territories. Out of the game." if s["out"][self.who] else "territories: %d armies a turn" % total
        T.draw_text(surf, text, "text", 24, T.DIM, (262, 174), "midleft", max_w=510)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class RiskBattle(PlayBase):
    """Roll one attack. Pick the dice and the defender, then Roll."""

    def __init__(self, app, session, rng=None):
        super().__init__(app, session)
        self.rng = rng or random.Random()
        self.a, self.d, self.result = 3, 2, None
        s = session.state
        self.targets = [i for i in range(len(session.players)) if i != s["active"] and not s["out"][i]]
        if s["neutral"]:
            self.targets.append("neutral")
        self.t = 0

    @property
    def title(self):
        return "Battle"

    def target_name(self):
        t = self.targets[self.t]
        return "Neutral" if t == "neutral" else self.session.players[t]

    def build(self):
        out = []
        for n in (1, 2, 3):
            out.append(Button((224 + (n - 1) * 72, 68, 64, 64), str(n), lambda n=n: self.dice(n, None),
                              selected=(n == self.a), size=26))
        for n in (1, 2):
            out.append(Button((224 + (n - 1) * 72, 140, 64, 64), str(n), lambda n=n: self.dice(None, n),
                              selected=(n == self.d), size=26))
        out.append(Button((480, 140, 300, 64), "vs " + self.target_name(), self.next_target, size=22))
        spec = [("Back", self.app.pop, 1, "plain"), ("Territory taken", self.taken, 1.8, "plain"),
                ("Roll", self.roll, 1.6, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def dice(self, a, d):
        self.a, self.d, self.result = a or self.a, d or self.d, None
        self.refresh()

    def next_target(self):
        self.t = (self.t + 1) % len(self.targets)
        self.refresh()

    def roll(self):
        self.result = rules.battle(self.a, self.d, self.rng)
        self.refresh()

    def taken(self):
        if self.do(ev="capture", defender=self.targets[self.t]) and not self.session.finished:
            if self in self.app.stack:           # a teaching card may now be on top: close this screen, not that one
                self.app.stack.remove(self)
                self.app.screen.enter()

    def draw_body(self, surf):
        me = self.state["active"]
        T.draw_text(surf, "Attacker dice", "text", 22, T.DIM, (20, 100), "midleft")
        T.draw_text(surf, "Defender dice", "text", 22, T.DIM, (20, 172), "midleft")
        T.draw_text(surf, self.session.players[me], "bold", 22, T.player_colour(me), (480, 100), "midleft", max_w=300)
        if not self.result:
            T.draw_text(surf, "Press the button to roll", "head", 30, T.DIM, (T.W // 2, 290), "center")
            return
        a, d, a_loss, d_loss = self.result
        for y, label, rolls, other in ((222, "Attack", a, d), (296, "Defend", d, a)):
            T.draw_text(surf, label, "text", 22, T.DIM, (20, y + 32), "midleft")
            for k, v in enumerate(rolls):
                if label == "Attack":
                    won = k < len(other) and v > other[k]
                else:
                    won = k < len(other) and v >= other[k]
                box = pygame.Rect(130 + k * 76, y, 64, 64)
                pygame.draw.rect(surf, T.TEXT if won else T.RAISED, box, border_radius=12)
                pygame.draw.rect(surf, T.TEXT if won else T.LINE, box, 1, border_radius=12)
                T.draw_text(surf, str(v), "head", 36, T.GROUND if won else T.TEXT, box.center, "center")
        words = ["no armies", "one army", "two armies"]
        T.draw_text(surf, "Attacker loses %s." % words[a_loss], "head5", 26, T.TEXT, (380, 254), "midleft", max_w=400)
        T.draw_text(surf, "Defender loses %s." % words[d_loss], "head5", 26, T.TEXT, (380, 328), "midleft", max_w=400)

    def on_button(self, gesture):
        if gesture == "press":
            self.roll()
        elif gesture == "double":
            self.app.pop()
