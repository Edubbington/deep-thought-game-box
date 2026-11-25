"""The generic board-game plugin. It runs any game described by data alone.

game.json fields it reads (all optional except one of trackers/phases):

  "players":  [2, 6]                      fewest and most players
  "phases":   ["Roll", "Trade", "Build"]  the parts of a turn, in order
  "trackers": [{"name": "Points", "start": 0, "step": 1, "min": 0, "max": null}]
  "win":      {"tracker": "Points", "at": 10}     first to reach it wins
  "lowest_wins": false                    for games where a low score is good

A teach.json beside it holds the "How to play" steps, in the box's own words.
"""
from .. import theme as T
from ..engine import Game
from ..screens.common import BOTTOM_H, BOTTOM_Y, PlayBase
from ..widgets import Tile, row


def _whole(value, what, none_ok=False):
    """A whole number from a hand-written file, or ValueError saying which field is wrong."""
    if value is None and none_ok:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("%s must be a whole number" % what)
    try:
        return int(value)
    except ValueError:
        raise ValueError("%s must be a whole number" % what)


class GenericGame(Game):
    def __init__(self, info):
        """Raises ValueError for a game.json that could not be played, so the
        game list reports it rather than the box falling over mid-game."""
        self.info = info
        players = info.get("players") or [1, 6]
        if not isinstance(players, list) or len(players) < 2:
            raise ValueError("players must be two numbers: fewest and most")
        lo, hi = _whole(players[0], "players"), _whole(players[1], "players")
        self.min_players, self.max_players = max(1, lo), min(6, hi)
        if self.min_players > self.max_players:
            raise ValueError("players: fewest %s and most %s leave nobody to play (one to six)" % (lo, hi))
        phases = info.get("phases") or []
        if not isinstance(phases, list):
            raise ValueError("phases must be a list of names")
        self.phase_names = [str(p) for p in phases]
        self.trackers = []
        trackers = info.get("trackers") or []
        if not isinstance(trackers, list) or not all(isinstance(t, dict) for t in trackers):
            raise ValueError("trackers must be a list of {name, start, step, min, max}")
        for t in trackers:
            if "name" not in t:
                raise ValueError("a tracker has no name")
            name = str(t["name"])
            if name in [x["name"] for x in self.trackers]:
                raise ValueError("two trackers are called %s" % name)
            new = {"name": name, "start": _whole(t.get("start", 0), name + " start"),
                   "step": _whole(t.get("step", 1), name + " step") or 1,
                   "min": _whole(t.get("min", 0), name + " min", none_ok=True),
                   "max": _whole(t.get("max"), name + " max", none_ok=True)}
            if (new["min"] is not None and new["start"] < new["min"]) or (new["max"] is not None and new["start"] > new["max"]):
                raise ValueError("%s starts outside its own min and max" % name)
            self.trackers.append(new)
        self.win = info.get("win") or None
        if self.win is not None:
            if not isinstance(self.win, dict) or "tracker" not in self.win or "at" not in self.win:
                raise ValueError('win must be {"tracker": name, "at": number}')
            self.win = {"tracker": str(self.win["tracker"]), "at": _whole(self.win["at"], "win at")}
            if self.win["tracker"] not in [t["name"] for t in self.trackers]:
                raise ValueError("win counts %s, which is not one of the trackers" % self.win["tracker"])
        self.lowest = bool(info.get("lowest_wins"))

    def new_state(self, players, options):
        return {"turn": 1, "active": 0, "phase": 0, "n": len(players),     # n from the start, so the saved game has it too
                "t": {t["name"]: [t["start"]] * len(players) for t in self.trackers}}

    def phases(self):
        return [(str(i), n) for i, n in enumerate(self.phase_names)]

    def phase(self, state):
        return str(state["phase"])

    def apply(self, state, ev):
        n = len(next(iter(state["t"].values()))) if state["t"] else ev.get("players", 0)
        if ev["ev"] == "next":
            if self.phase_names and state["phase"] + 1 < len(self.phase_names):
                state["phase"] += 1
                return []
            state["phase"] = 0
            state["active"] = (state["active"] + 1) % max(1, n or state.get("n", 1))
            if state["active"] == 0:
                state["turn"] += 1
            return []
        if ev["ev"] == "add":
            t = next((t for t in self.trackers if t["name"] == ev["tracker"]), None)
            if not t:
                raise ValueError("This game has no %s to count." % ev["tracker"])
            v = state["t"][t["name"]][ev["player"]] + int(ev["delta"])
            if t["min"] is not None and v < t["min"]:
                raise ValueError("%s cannot go below %s." % (t["name"], t["min"]))
            if t["max"] is not None and v > t["max"]:
                raise ValueError("%s cannot go above %s." % (t["name"], t["max"]))
            state["t"][t["name"]][ev["player"]] = v
            return []
        raise ValueError("I do not know what %r means in this game." % ev["ev"])

    def over(self, state):
        """The game ends when anybody reaches the winning number. Usually they
        win; where a low score is good, whoever is lowest at that moment wins."""
        if not self.win or self.win.get("tracker") not in state["t"]:
            return None
        name, at = self.win["tracker"], self.win["at"]
        vals = state["t"][name]
        start = next(t["start"] for t in self.trackers if t["name"] == name)
        if all(v == start for v in vals):
            return None                           # nothing has been scored yet: nobody has won
        hit = [i for i, v in enumerate(vals) if v >= at]
        if not hit:
            return None
        if not self.lowest:
            return {"winner_index": hit[0], "lines": ["%s: %s" % (name, at)]}
        low = [i for i, v in enumerate(vals) if v == min(vals)]
        return {"winner_index": low[0] if len(low) == 1 else None,
                "lines": ["%s reached %s" % (name, at), "Lowest: %s" % min(vals)]}

    def leader(self, state):
        if not self.trackers:
            return None
        vals = state["t"][self.trackers[0]["name"]]
        best = min(vals) if self.lowest else max(vals)
        return vals.index(best) if vals.count(best) == 1 else None

    def standings(self, state, players):
        if not self.trackers:
            return ["Stopped after %d turns" % state["turn"]]
        name = self.trackers[0]["name"]
        pairs = sorted(zip(state["t"][name], players), reverse=not self.lowest)
        return ["%s: %s" % (name, ", ".join("%s %d" % (p, v) for v, p in pairs))]

    def strip(self, session):
        s = session.state
        phase = self.phase_names[s["phase"]] if self.phase_names else ""
        return "%s · Turn %d" % (self.name, s["turn"]), phase

    def scoreboard(self, session):
        s = session.state
        name = self.trackers[0]["name"] if self.trackers else ""
        return {"rows": [{"name": p, "value": s["t"][name][i] if name else ""} for i, p in enumerate(session.players)],
                "note": name}

    def play_screen(self, app, session):
        session.state.setdefault("n", len(session.players))
        return GenericPlay(app, session)


class GenericPlay(PlayBase):
    def __init__(self, app, session):
        super().__init__(app, session)
        self.tracker, self.sign = 0, 1

    def build(self):
        g, s, out = self.game, self.state, []
        names = self.session.players
        if g.trackers:
            t = g.trackers[self.tracker]
            cols = 3 if len(names) > 2 else len(names)
            rows = -(-len(names) // cols)
            h = 100 if rows > 1 else 150
            w = (760 - 10 * (cols - 1)) // cols
            top = 156 if rows > 1 else 190
            for i, name in enumerate(names):
                rect = (20 + (i % cols) * (w + 10), top + (i // cols) * (h + 8), w, h)
                out.append(Tile(rect, name, s["t"][t["name"]][i], lambda i=i: self.bump(i), T.player_colour(i),
                                note="your turn" if i == s["active"] else None))
        spec = [("Next", lambda: self.do(ev="next"), 1.4, "primary")]
        if g.trackers:
            if len(g.trackers) > 1:
                spec.append((g.trackers[self.tracker]["name"], self.next_tracker, 1.5, "plain"))
            step = g.trackers[self.tracker]["step"]
            spec.append(("Tap: %s%d" % ("+" if self.sign > 0 else "−", step), self.flip_sign, 1.2, "plain"))
        spec += [("Undo", self.undo, 1, "plain"), ("Menu", self.more, 1, "plain")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def bump(self, i):
        t = self.game.trackers[self.tracker]
        self.do(ev="add", player=i, tracker=t["name"], delta=self.sign * t["step"])

    def next_tracker(self):
        self.tracker = (self.tracker + 1) % len(self.game.trackers)
        self.refresh()

    def flip_sign(self):
        self.sign = -self.sign
        self.refresh()

    def draw_body(self, surf):
        g, s = self.game, self.state
        who = self.session.players[s["active"]]
        phase = g.phase_names[s["phase"]] if g.phase_names else None
        text = "%s: %s" % (who, phase) if phase else "%s, your turn." % who
        T.draw_text(surf, text, "head", 40, T.TEXT, (20, 72), max_w=760)
        if g.trackers:
            hint = "Tap a name to change %s. Press the button for Next." % g.trackers[self.tracker]["name"].lower()
        else:
            hint = "Press the button when the turn is done."
        T.draw_text(surf, hint, "text", 22, T.DIM, (20, 122), max_w=760)
