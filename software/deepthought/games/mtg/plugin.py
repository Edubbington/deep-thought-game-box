"""Magic: The Gathering. The box keeps life, poison, commander damage and the
monarch, walks the steps of a turn, and says when somebody is out. It does
not know what any card does; the card decides that."""
import copy
import pygame
from ... import theme as T
from ...engine import Game
from ...screens.common import BOTTOM_H, BOTTOM_Y, Choice, PlayBase
from ...widgets import Button, row
from . import rules

FORMATS = ["Standard 20 life", "Commander 40 life"]
SAY_WARN = {"life": "%s has one life left.",
            "poison": "%s has nine poison counters. One more and that is that.",
            "commander": "%s has taken 20 from one commander. One more and that is that."}


class Plugin(Game):
    min_players, max_players = 2, 4
    options = [{"key": "format", "label": "Format", "choices": FORMATS},
               {"key": "steps", "label": "Button", "choices": ["Every step", "Whole turn"]},
               {"key": "hints", "label": "Hints", "choices": ["On", "Off"]}]

    def new_state(self, players, options):
        fmt, n = rules.format_key(options.get("format")), len(players)
        steps = options.get("steps", "Every step") != "Whole turn"
        return {"turn": 1, "active": 0, "phase": rules.FIRST_STEP if steps else rules.WHOLE_TURN,
                "format": fmt, "steps": steps, "hints": options.get("hints", "On") == "On",
                "life": [rules.start_life(fmt)] * n, "poison": [0] * n, "cmd": rules.grid(n),
                "out": [False] * n, "why": [None] * n, "fell": [], "monarch": None, "names": list(players)}

    def phases(self):
        return rules.STEPS

    # ---- helpers
    def commander(self, s):
        return s["format"] == "commander"

    def skips_draw(self, s):
        """Two players, turn one, the player who went first: no draw."""
        return len(s["names"]) == 2 and s["turn"] == 1 and s["active"] == 0

    def warnings(self, s, p):
        return rules.warnings(s["life"][p], s["poison"][p], s["cmd"][p], self.commander(s))

    def step_name(self, s):
        return rules.STEP_NAME[s["phase"]] if s["steps"] else "Main phase"

    def hint(self, s):
        """The teaching line for this step, or None when hints are off."""
        if not (s["hints"] and s["steps"]):
            return None
        if s["phase"] == "draw" and self.skips_draw(s):
            return rules.NO_DRAW
        return rules.HINTS[s["phase"]]

    def status(self, s, p):
        """Short lines about one player: [(text, is a warning)]."""
        if s["out"][p]:
            return [("Out: " + rules.WHY[s["why"][p]], False)]
        warn, out = self.warnings(s, p), []
        worst = rules.worst(s["cmd"][p])
        if "life" in warn:
            out.append(("Warning: 1 life left", True))
        if "poison" in warn:
            out.append(("Warning: 9 poison", True))
        elif s["poison"][p]:
            out.append(("Poison %d" % s["poison"][p], False))
        if "commander" in warn:
            out.append(("Warning: cmdr 20", True))
        elif self.commander(s) and worst:
            out.append(("Commander %d/21" % worst, False))
        if s["monarch"] == p:
            out.append(("Monarch", False))
        return sorted(out, key=lambda x: not x[1])       # warnings first

    def marks(self, before, s, ev):
        """Moments the teaching steps may wait on: "knockout" when this event put
        a player out, by life, poison, commander damage or by hand; "warning"
        when it left a player one step from that."""
        out = []
        if any(now and not was for was, now in zip(before["out"], s["out"])):
            out.append("knockout")
        if any(set(self.warnings(s, p)) - set(self.warnings(before, p)) for p in range(len(s["out"])) if not s["out"][p]):
            out.append("warning")
        return out

    def _seat(self, s, p, what="player"):
        if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p < len(s["names"]):
            raise ValueError("I do not know which %s that is." % what)
        return p

    def _pass_turn(self, s):
        me = s["active"]
        nxt = rules.next_alive(s["out"], me)
        if nxt is None:
            return
        if nxt <= me:
            s["turn"] += 1
        s["active"] = nxt
        s["phase"] = rules.FIRST_STEP if s["steps"] else rules.WHOLE_TURN

    def _next(self, s):
        me, name, said = s["active"], s["names"][s["active"]], []
        if s["steps"]:
            nxt = rules.next_step(s["phase"])
            if nxt:
                s["phase"] = nxt
                if nxt == "draw" and self.skips_draw(s):
                    said.append("%s went first, so no draw this turn." % name)
                if nxt == "end" and s["monarch"] == me:
                    said.append("%s is the monarch: draw a card." % name)
                return said
        elif s["monarch"] == me:
            said.append("%s is the monarch: draw a card as the turn ends." % name)
        self._pass_turn(s)
        return said

    def _settle(self, s, p, before, forced=False):
        """After a change to player p: are they out, or one step from it?"""
        names, said = s["names"], []
        why = "other" if forced else rules.lost(s["life"][p], s["poison"][p], s["cmd"][p], self.commander(s))
        if not why:
            return [SAY_WARN[w] % names[p] for w in self.warnings(s, p) if w not in before]
        s["out"][p], s["why"][p] = True, why
        s["fell"].append(p)
        said.append("%s is out: %s." % (names[p], rules.WHY[why]))
        alive = [i for i, o in enumerate(s["out"]) if not o]
        if s["monarch"] == p:
            # the crown goes to whoever's turn it is; if that was the player leaving, to the next in line
            heir = s["active"] if s["active"] != p else rules.next_alive(s["out"], p)
            s["monarch"] = heir
            if heir is not None and len(alive) > 1:
                said.append("%s takes the crown." % names[heir])
        if s["active"] == p and len(alive) > 1:
            self._pass_turn(s)
            said.append("%s is up." % names[s["active"]])
        return said

    # ---- the rules
    def apply(self, s, ev):
        kind, names = ev.get("ev"), s["names"]
        if kind == "next":
            return self._next(s)
        if kind == "monarch":
            p = ev.get("player")
            if p is None:
                if s["monarch"] is None:
                    raise ValueError("Nobody is the monarch. There is no one to depose.")
                s["monarch"] = None
                return ["Nobody is the monarch now."]
            p = self._seat(s, p)
            if s["out"][p]:
                raise ValueError("%s is out of the game and cannot be the monarch." % names[p])
            if s["monarch"] == p:
                raise ValueError("%s is already the monarch." % names[p])
            s["monarch"] = p
            return ["%s is the monarch." % names[p]]
        if kind not in ("life", "poison", "cmd", "out"):
            raise ValueError("I do not know what %r means in Magic." % kind)
        p = self._seat(s, ev.get("player"))
        if s["out"][p]:
            raise ValueError("%s is already out of the game." % names[p])
        before = self.warnings(s, p)
        if kind == "out":
            return self._settle(s, p, before, forced=True)
        delta = ev.get("delta")
        if not isinstance(delta, int) or isinstance(delta, bool) or delta == 0:
            raise ValueError("Tell me how much, as a whole number.")
        if kind == "life":
            s["life"][p] += delta
        elif kind == "poison":
            if s["poison"][p] + delta < 0:
                raise ValueError("%s has no poison counters to remove." % names[p])
            s["poison"][p] += delta
        else:
            if not self.commander(s):
                raise ValueError("Commander damage only counts in a Commander game.")
            src = self._seat(s, ev.get("source"), "commander")
            if src == p:
                raise ValueError("I only count damage from the other players' commanders.")
            if s["out"][src] and delta > 0:
                raise ValueError("%s has left the game, commander and all." % names[src])
            if s["cmd"][p][src] + delta < 0:
                raise ValueError("%s's commander has dealt %s no damage to take back." % (names[src], names[p]))
            s["cmd"][p][src] += delta
            s["life"][p] -= delta                 # commander damage is damage: it comes off life too
        return self._settle(s, p, before)

    def over(self, s):
        alive = [i for i, o in enumerate(s["out"]) if not o]
        if len(alive) != 1:
            return None
        w, lines = alive[0], []
        if s["fell"]:
            last = s["fell"][-1]
            lines.append("%s fell last: %s" % (s["names"][last], rules.WHY[s["why"][last]]))
        lines += ["%s had %d life left" % (s["names"][w], s["life"][w]), "Turn %d" % s["turn"]]
        return {"winner": s["names"][w], "lines": lines}

    def leader(self, s):
        alive = [i for i, o in enumerate(s["out"]) if not o]
        best = max(s["life"][i] for i in alive) if alive else None
        top = [i for i in alive if s["life"][i] == best]
        return top[0] if len(top) == 1 else None

    def standings(self, s, players):
        order = sorted(range(len(players)), key=lambda i: (s["out"][i], -s["life"][i]))
        return ["Life: " + ", ".join("%s %s" % (players[i], "out" if s["out"][i] else s["life"][i]) for i in order),
                "Stopped on turn %d" % s["turn"]]

    def strip(self, session):
        s = session.state
        return "%s · Turn %d" % ("Commander" if self.commander(s) else "Magic", s["turn"]), self.step_name(s)

    def scoreboard(self, session):
        s, rows = session.state, []
        for i, p in enumerate(session.players):
            rows.append({"name": p, "value": s["life"][i], "out": s["out"][i],
                         "detail": ", ".join(t for t, _ in self.status(s, i))})
        return {"rows": rows, "note": "Life · %s" % self.step_name(s)}

    def phone(self, session, seat):
        s = session.state
        if not isinstance(seat, int) or not 0 <= seat < len(s["names"]):
            return {"lines": [], "actions": []}
        if s["out"][seat]:
            return {"lines": ["You are out: %s." % rules.WHY[s["why"][seat]]], "actions": []}
        lines = ["Life %d" % s["life"][seat], "Poison %d" % s["poison"][seat]]
        if self.commander(s):
            for src, v in enumerate(s["cmd"][seat]):
                if v:
                    lines.append("%d from %s's commander" % (v, s["names"][src]))
        if s["monarch"] == seat:
            lines.append("You are the monarch")
        lines += [t for t, w in self.status(s, seat) if w]
        actions = [{"label": "Life %s" % lab, "ev": {"ev": "life", "player": seat, "delta": d}}
                   for lab, d in (("+1", 1), ("−1", -1), ("+5", 5), ("−5", -5))]
        actions.append({"label": "Poison +1", "ev": {"ev": "poison", "player": seat, "delta": 1}})
        if s["poison"][seat]:
            actions.append({"label": "Poison −1", "ev": {"ev": "poison", "player": seat, "delta": -1}})
        if s["active"] == seat:
            actions.append({"label": "Next step" if s["steps"] else "Next turn", "ev": self.press(s)})
        return {"lines": lines, "actions": actions}

    def play_screen(self, app, session):
        return MtgPlay(app, session)


# ---------------------------------------------------------------- screens
class Panel:
    """One player's life total. `frame` is what is drawn; `rect` is where a tap lands."""
    style, selected = "panel", False

    def __init__(self, screen, i, frame, rect=None, big=False, action=None):
        self.screen, self.i, self.big, self.action = screen, i, big, action
        self.frame = pygame.Rect(frame)
        self.rect = pygame.Rect(rect or frame)
        self.label = screen.session.players[i]

    def draw(self, surf, pressed=False):
        s, i, f = self.screen.state, self.i, self.frame
        out, active = s["out"][i], s["active"] == i
        colour = T.DIM if out else T.player_colour(i)
        status = self.screen.game.status(s, i)
        label = self.label

        def squeeze(lines, room):
            """No room for every line: the crown moves up beside the name, so a warning is never the one cut."""
            if len(lines) > room and ("Monarch", False) in lines:
                return [x for x in lines if x != ("Monarch", False)], self.label + " · monarch"
            return lines, self.label
        if self.big:
            status, label = squeeze(status, 2)
            warns = [text for text, warn in status if warn]
            if len(status) > 2 and len(warns) > 1:    # two lines of room: the last two warnings share one, none is dropped
                warns[-2:] = [warns[-2] + " · " + warns[-1].replace("Warning: ", "")]
                status = [(text, True) for text in warns] + [x for x in status if not x[1]]
            pygame.draw.rect(surf, T.RAISED if pressed else T.PANEL, f, border_radius=18)
            pygame.draw.rect(surf, T.LINE, f, 1, border_radius=18)
            roomy = f.h >= 300
            T.draw_text(surf, label, "head", 30, colour, (f.centerx, f.y + (10 if roomy else 6)), "midtop",
                        max_w=f.w - 36)
            T.draw_text(surf, str(s["life"][i]), "head", 128 if roomy else 108, colour,
                        (f.centerx, f.y + (112 if roomy else 96)), "center", max_w=f.w - 36)
            y = f.y + (190 if roomy else 160)
            for text, warn in (status or [("No poison", False)])[:2]:
                T.draw_text(surf, text, "bold" if warn else "text", 22, T.WARN if warn else T.DIM,
                            (f.centerx, y), "center", max_w=f.w - 28)
                y += 26
            return
        pygame.draw.rect(surf, T.RAISED if (active or pressed) else T.PANEL, f, border_radius=16)
        if active:                                   # a thick light edge, not colour alone
            pygame.draw.rect(surf, T.TEXT, f, 3, border_radius=16)
        else:
            pygame.draw.rect(surf, T.LINE, f, 1, border_radius=16)
        num, size = T.fit(str(s["life"][i]), "head", 84, 170)
        T.draw_text(surf, num, "head", size, colour, (f.right - 18, f.centery), "midright")
        room = f.w - 36 - T.font("head", size).size(num)[0] - 14
        def fold(status):                            # long lines fold rather than being cut short
            lines = []
            for text, warn in status:
                lines += [(part, warn) for part in T.wrap(text, "bold" if warn else "text", 22, room)]
            return lines
        if len(fold(status)) > 3:
            status, label = squeeze(status, 0)
        if len(fold(status)) > 3:                    # a long life total leaves little room: the bold line is the warning
            status = [(text.replace("Warning: ", ""), warn) for text, warn in status]
        lines = fold(status)[:3]
        y = f.centery - (36 + 26 * len(lines)) // 2
        T.draw_text(surf, label, "head", 28, colour, (f.x + 18, y), max_w=room)
        y += 38
        for text, warn in lines:
            T.draw_text(surf, text, "bold" if warn else "text", 22, T.WARN if warn else T.DIM, (f.x + 18, y),
                        max_w=room)
            y += 26


class MtgBase(PlayBase):
    def change(self, **ev):
        """Apply an event, but ask first if it would end the game: a slip of
        the thumb should not hand somebody the win."""
        trial = copy.deepcopy(self.state)
        try:
            self.game.apply(trial, ev)
            end = self.game.over(trial)
        except (ValueError, KeyError, TypeError):
            end = None
        if not end:
            return self.do(**ev)
        loser = self.session.players[trial["fell"][-1]]
        text = "That puts %s out and ends the game.\n%s wins. Is that right?" % (loser, end["winner"])
        self.app.push(Choice(self.app, "Game over?", text,
                             [("Keep playing", None), ("End the game", lambda: self.do(**ev))], left=self.left))
        return False

    def player(self, i):
        self.app.push(MtgPlayer(self.app, self.session, i))

    def counters(self):
        self.app.push(MtgCounters(self.app, self.session))


class MtgPlay(MtgBase):
    """Life totals: two big panels for two players, a grid for three or four."""

    def build(self):
        s, n, out = self.state, len(self.session.players), []
        bottom = 356 if self.game.hint(s) else 384
        if n == 2:
            for i in range(2):
                frame = pygame.Rect(20 + i * 387, 68, 373, bottom - 68)
                by = frame.bottom - 10 - 72
                out.append(Panel(self, i, frame, (frame.x, frame.y, frame.w, by - 6 - frame.y), big=True,
                                 action=lambda i=i: self.player(i)))
                if s["out"][i]:
                    continue
                x = frame.x + 10
                for label, delta, w in (("−5", -5, 72), ("−", -1, 92), ("+", 1, 92), ("+5", 5, 72)):
                    out.append(Button((x, by, w, 72), label, lambda i=i, d=delta: self.change(ev="life", player=i, delta=d),
                                      size=36 if abs(delta) == 1 else 26))
                    x += w + 8
        else:
            h = (bottom - 68 - 12) // 2
            for i in range(n):
                wide = n == 3 and i == 2
                frame = (20 + (i % 2) * 386, 68 + (i // 2) * (h + 12), 760 if wide else 374, h)
                out.append(Panel(self, i, frame, action=lambda i=i: self.player(i)))
        spec = [("Next step" if s["steps"] else "Next turn", lambda: self.do(**self.game.press(self.state)), 1.5, "primary"),
                ("Counters", self.counters, 1.2, "plain"), ("Card", self.lookup, 0.8, "plain"),
                ("Undo", self.undo, 0.8, "plain"), ("Dice", self.dice, 0.8, "plain"), ("Menu", self.more, 0.8, "plain")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def dice(self):
        from ...screens.dice import Dice
        self.app.push(Dice(self.app))

    def draw_body(self, surf):
        hint = self.game.hint(self.state)
        if hint:
            T.draw_text(surf, hint, "text", 22, T.DIM, (T.W // 2, 373), "center", max_w=760)


class MtgPlayer(MtgBase):
    """One player: life, and the damage each other commander has dealt them."""
    pill = None

    def __init__(self, app, session, who):
        super().__init__(app, session)
        self.who = who

    @property
    def title(self):
        return self.session.players[self.who]

    def rows(self):
        """What the three rows hold: ('cmd', seat) for each other commander, then ('poison', None)."""
        s, out = self.state, []
        if self.game.commander(s):
            out = [("cmd", i) for i in range(len(s["names"])) if i != self.who]
        return out + ([("poison", None)] if len(out) < 3 else [])

    def build(self):
        s, p, out = self.state, self.who, []
        if not s["out"][p]:
            for label, delta, x in (("−5", -5, 180), ("−", -1, 260), ("+", 1, 468), ("+5", 5, 548)):
                out.append(Button((x, 66, 72, 64), label, lambda d=delta: self.change(ev="life", player=p, delta=d),
                                  size=30 if abs(delta) == 1 else 26))
            for k, (kind, src) in enumerate(self.rows()):
                y = 138 + k * 74 + 2
                if kind == "cmd":
                    if s["out"][src]:
                        continue
                    ev = dict(ev="cmd", player=p, source=src)
                else:
                    ev = dict(ev="poison", player=p)
                out += [Button((572, y, 64, 64), "−", lambda ev=ev: self.change(delta=-1, **ev), size=30),
                        Button((700, y, 64, 64), "+", lambda ev=ev: self.change(delta=1, **ev), size=30)]
        spec = [("Poison and counters", self.counters, 1.6, "plain"), ("Undo", self.undo, 1, "plain"),
                ("Back", self.app.pop, 1, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        s, p, names = self.state, self.who, self.state["names"]
        out = s["out"][p]
        T.draw_text(surf, "Life", "text", 22, T.DIM, (20, 98), "midleft")
        T.draw_text(surf, str(s["life"][p]), "head", 64, T.DIM if out else T.player_colour(p), (400, 98), "center",
                    max_w=120)
        if s["monarch"] == p:
            T.draw_text(surf, "Monarch", "text", 22, T.DIM, (780, 98), "midright")
        for k, (kind, src) in enumerate(self.rows()):
            box = pygame.Rect(20, 138 + k * 74, 760, 68)
            if kind == "cmd":
                value, limit, gone = s["cmd"][p][src], rules.COMMANDER_OUT, s["out"][src]
            else:
                value, limit, gone = s["poison"][p], rules.POISON_OUT, False
            left = rules.to_go(value, limit)
            warn = left == 1 and not out
            pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
            pygame.draw.rect(surf, T.WARN if warn else T.LINE, box, 2 if warn else 1, border_radius=12)
            if kind == "cmd":
                r = T.draw_text(surf, "From ", "text", 24, T.TEXT, (box.x + 16, box.centery), "midleft")
                r = T.draw_text(surf, names[src] + "'s", "bold", 24, T.player_colour(src), (r.right, box.centery),
                                "midleft", max_w=130)
                T.draw_text(surf, " commander", "text", 24, T.TEXT, (r.right, box.centery), "midleft")
            else:
                T.draw_text(surf, "Poison counters", "text", 24, T.TEXT, (box.x + 16, box.centery), "midleft")
            if gone:
                note = "Out of the game"
            elif left == 0:
                note = "Knockout"
            elif warn:
                note = "Warning: 1 left"
            elif value * 2 > limit:
                note = "%d to knockout" % left
            else:
                note = ""
            if note:
                T.draw_text(surf, note, "bold" if warn else "text", 22, T.WARN if warn else (T.DIM if gone else T.TEXT),
                            (560, box.centery), "midright", max_w=180)
            T.draw_text(surf, str(value), "head", 38, T.TEXT, (668, box.centery), "center", max_w=56)
        if out:
            note, colour = "%s is out: %s." % (names[p], rules.WHY[s["why"][p]]), T.TEXT
        elif "life" in self.game.warnings(s, p):
            note, colour = "Warning: 1 life left.", T.WARN
        elif self.game.commander(s):
            note, colour = "21 from one commander is a knockout. It comes off life too.", T.DIM
        else:
            note, colour = "No life left, or ten poison counters, is a knockout.", T.DIM
        T.draw_text(surf, note, "bold" if colour == T.WARN else "text", 22, colour, (20, 373), "midleft", max_w=760)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class MtgCounters(MtgBase):
    """Poison for every player, who is the monarch, and a way to put a player
    out for a reason the box cannot count (an empty library, a card)."""
    pill = None
    ROW_Y, ROW_H, ROW_STEP = 68, 72, 80

    @property
    def title(self):
        return "Counters"

    def build(self):
        s, out = self.state, []
        for i, name in enumerate(self.session.players):
            if s["out"][i]:
                continue
            y = self.ROW_Y + i * self.ROW_STEP + 4
            mon = s["monarch"] == i
            out += [Button((262, y, 64, 64), "−", lambda i=i: self.change(ev="poison", player=i, delta=-1), size=30),
                    Button((382, y, 64, 64), "+", lambda i=i: self.change(ev="poison", player=i, delta=1), size=30),
                    Button((456, y, 190, 64), "Is monarch" if mon else "Make monarch",
                           lambda i=i, mon=mon: self.do(ev="monarch", player=None if mon else i), selected=mon, size=22),
                    Button((656, y, 108, 64), "Out", lambda i=i: self.put_out(i), size=22)]
        spec = [("Undo", self.undo, 1, "plain"), ("Back", self.app.pop, 2, "primary")]
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def put_out(self, i):
        alive = self.state["out"].count(False)
        if alive <= 2:                               # this ends the game: change() asks the one question
            self.change(ev="out", player=i)
            return
        name = self.session.players[i]
        text = "Take %s out of the game?\nFor an empty library, or a card that says so." % name
        self.app.push(Choice(self.app, "Out of the game?", text,
                             [("Keep playing", None), ("%s is out" % name, lambda: self.do(ev="out", player=i))],
                             left=self.left))

    def draw_body(self, surf):
        s = self.state
        for i, name in enumerate(self.session.players):
            box = pygame.Rect(20, self.ROW_Y + i * self.ROW_STEP, 760, self.ROW_H)
            out = s["out"][i]
            warn = not out and s["poison"][i] == rules.POISON_OUT - 1
            pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
            pygame.draw.rect(surf, T.WARN if warn else T.LINE, box, 3 if warn else 1, border_radius=12)
            pygame.draw.rect(surf, T.DIM if out else T.player_colour(i), (box.x + 8, box.y + 10, 5, box.h - 20),
                             border_radius=2)
            T.draw_text(surf, name, "head", 26, T.DIM if out else T.TEXT, (box.x + 22, box.centery), "midleft",
                        max_w=136)
            if out:
                T.draw_text(surf, "Out: " + rules.WHY[s["why"][i]], "text", 22, T.DIM, (186, box.centery), "midleft",
                            max_w=570)
                continue
            T.draw_text(surf, "9 of 10" if warn else "Poison", "bold" if warn else "text", 22,
                        T.WARN if warn else T.DIM, (254, box.centery), "midright", max_w=76)
            T.draw_text(surf, str(s["poison"][i]), "head", 34, T.TEXT, (354, box.centery), "center", max_w=52)

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()
