"""Screens every game shares: typing, a question with choices, a pager for
reading, game setup, the base for play screens, and game over."""
import json
import os
import random
import pygame
from .. import engine, paths
from .. import theme as T
from ..app import Screen
from ..widgets import Button, row

BOTTOM_Y, BOTTOM_H = 392, 72


# ---------------------------------------------------------------- typing
KEY_ROWS = ["1234567890", "qwertyuiop", "asdfghjkl'", "zxcvbnm+-&"]


def title_case(text):
    """Capital letter on each word. Unlike str.title(), leaves the s in "man's" alone."""
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))


class TextEntry(Screen):
    """An on-screen keyboard for short text: a search term or a name."""

    def __init__(self, app, title, text="", on_done=None, done_label="Search", max_len=40):
        super().__init__(app)
        self.left, self.title = "Type", title
        self.text, self.on_done, self.done_label, self.max_len = text, on_done, done_label, max_len

    def build(self):
        out = []
        for r, keys in enumerate(KEY_ROWS):
            for c, ch in enumerate(keys):
                out.append(Button((12 + c * 78, 140 + r * 68, 74, 64), ch.upper() if ch.isalpha() else ch,
                                  lambda ch=ch: self.type(ch), size=26))
        y = 140 + 4 * 68
        out += [Button((12, y, 110, 64), "Cancel", self.app.pop, size=22),
                Button((126, y, 110, 64), "Delete", self.delete, size=22),
                Button((240, y, 336, 64), "space", lambda: self.type(" "), size=22),
                Button((580, y, 208, 64), self.done_label, self.done, "primary")]
        return out

    def type(self, ch):
        if len(self.text) < self.max_len:
            self.text = (self.text + ch).lstrip()
            self.app.dirty = True

    def delete(self):
        self.text = self.text[:-1]
        self.app.dirty = True

    def done(self):
        text = " ".join(self.text.split())
        self.app.pop()
        if self.on_done:
            self.on_done(text)

    def on_key(self, event):                  # a real keyboard, on the desktop
        if event.key == pygame.K_RETURN:
            self.done()
        elif event.key == pygame.K_BACKSPACE:
            self.delete()
        elif event.unicode and event.unicode.isprintable():
            self.type(event.unicode.lower())

    def draw_body(self, surf):
        box = pygame.Rect(12, 68, 776, 64)
        pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
        pygame.draw.rect(surf, T.TEXT, box, 1, border_radius=12)
        shown = title_case(self.text) if self.done_label != "Search" else self.text
        r = T.draw_text(surf, shown or " ", "mid", 30, T.TEXT, (box.x + 18, box.centery), "midleft", max_w=720)
        x = r.right + 3 if self.text else box.x + 18
        pygame.draw.rect(surf, T.TEXT, (x, box.y + 14, 3, 36))

    def on_button(self, gesture):
        if gesture == "press":
            self.done()
        elif gesture == "double":
            pass                              # the press already closed this screen


# ---------------------------------------------------------------- a question
class Choice(Screen):
    """A question and up to three answers. The first answer is the button's."""

    def __init__(self, app, title, text, answers, left="Deep Thought"):
        super().__init__(app)
        self.left, self.title, self.text, self.answers = left, title, text, answers

    def build(self):
        spec = [(label, lambda act=act: self.pick(act), 1, "primary" if i == 0 else "plain")
                for i, (label, act) in enumerate(self.answers)]
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def pick(self, act):
        self.app.pop()
        if act:
            act()

    def draw_body(self, surf):
        y = 130
        for line in T.wrap_paragraphs(self.text, "head", 32, T.W - 80)[:5]:
            T.draw_text(surf, line, "head", 32, T.TEXT, (40, y))
            y += 44

    def on_button(self, gesture):
        if gesture == "press":
            self.pick(self.answers[0][1])


# ---------------------------------------------------------------- reading
LINES_PER_PAGE = 8


def paginate(steps, max_w=T.W - 48):
    """steps: [(heading, body)]. Returns pages: [(heading, [lines])]."""
    pages = []
    for heading, body in steps:
        lines = T.wrap_paragraphs(body or "", "text", 24, max_w)
        if not lines:
            lines = [""]
        for i in range(0, len(lines), LINES_PER_PAGE):
            chunk = lines[i:i + LINES_PER_PAGE]
            while chunk and not chunk[0]:
                chunk = chunk[1:]
            pages.append((heading, chunk))
    return pages or [("", ["Nothing here yet."])]


class Pages(Screen):
    """Read something a page at a time. Press = next page; double = back."""

    def __init__(self, app, left, title, steps, note=None, speak=True, auto=False):
        super().__init__(app)
        self.left, self.title, self.note = left, title, note
        self.pages, self.i, self.speak = paginate(steps), 0, speak
        self.auto, self._read = auto, None        # auto: read each page out as it comes up

    def enter(self):
        super().enter()
        self.read_new()

    def read_new(self):
        if self.auto and self._read != self.i and getattr(self.app, "voice", None):
            self._read = self.i
            self.read()

    def close(self):
        if self.auto and self._read is not None:
            self.app.hw.stop_sound()              # do not talk over the game once the card is put away
        self.app.pop()

    def build(self):
        n = len(self.pages)
        spec = [("Back" if not self.auto else "Skip", self.close, 1, "plain" if n > 1 else "primary")]
        if n == 1 and self.auto:
            spec = [("Got it", self.close, 1, "primary")]
        if self.speak and getattr(self.app, "voice", None):
            spec.append(("Read aloud" if not self.auto else "Again", self.read, 1.3, "plain"))
        if n > 1:
            spec.append(("Previous", self.prev, 1.2, "plain"))
            spec.append(("Next  %d of %d" % (self.i + 1, n), self.next, 1.8, "primary"))
        return row(spec, BOTTOM_Y, BOTTOM_H)

    def read(self):
        heading, lines = self.pages[self.i]
        self.app.voice.say(" ".join(l for l in lines if l), show=False)

    def prev(self):
        self.i = max(0, self.i - 1)
        self.refresh()
        self.read_new()

    def next(self):
        if self.i + 1 < len(self.pages):
            self.i += 1
            self.refresh()
            self.read_new()
        else:
            self.close()

    def draw_body(self, surf):
        heading, lines = self.pages[self.i]
        y = 72
        if heading:
            T.draw_text(surf, heading, "head", 30, T.TEXT, (24, y), max_w=T.W - 48)
            y += 44
        if self.note:
            T.draw_text(surf, self.note, "mid", 22, T.WARN, (24, y))
            y += 32
        for line in lines[:LINES_PER_PAGE - (1 if self.note else 0)]:
            if line:
                T.draw_text(surf, line, "text", 24, T.TEXT, (24, y))
            y += 32 if line else 16

    def on_button(self, gesture):
        if gesture == "press":
            self.next()
        elif gesture == "double":
            self.close()


# ---------------------------------------------------------------- setup
def recent_names():
    try:
        with open(paths.data("players.json"), encoding="utf-8") as f:
            return [str(n) for n in json.load(f)][:12]
    except (OSError, ValueError):
        return []


def remember_names(names):
    keep = [n for n in names if not n.startswith("Player ")]
    out = keep + [n for n in recent_names() if n not in keep]
    with open(paths.data("players.json"), "w", encoding="utf-8") as f:
        json.dump(out[:12], f)


class Setup(Screen):
    """Who is playing, and the game's own options."""
    title = "Set up"

    def __init__(self, app, game):
        super().__init__(app)
        self.game, self.left = game, game.name
        known = recent_names()
        self.n = max(game.min_players, min(game.max_players, 2 if game.min_players <= 2 else game.min_players))
        self.names = [known[i] if i < len(known) else "Player %d" % (i + 1) for i in range(game.max_players)]
        from .. import guide
        self.options = (list(game.options) + ([guide.OPTION] if guide.offered(game) else []))[:4]
        self.opts = {o["key"]: o["choices"][0] for o in self.options}

    def build(self):
        g, out = self.game, []
        if g.min_players < g.max_players:
            out += [Button((20, 72, 68, 64), "−", lambda: self.count(-1), size=30),
                    Button((176, 72, 68, 64), "+", lambda: self.count(+1), size=30)]
        w = (760 - 10 * (self.n - 1)) // self.n
        for i in range(self.n):
            out.append(Button((20 + i * (w + 10), 146, w, 64), self.names[i], lambda i=i: self.rename(i), size=22))
        for k, o in enumerate(self.options):
            rect = (20 + (k % 2) * 385, 222 + (k // 2) * 74, 375, 64)
            out.append(Button(rect, "%s: %s" % (o["label"], self.opts[o["key"]]), lambda o=o: self.cycle(o), size=22))
        spec = [("Back", self.app.pop, 1, "plain")]
        if g.teach():
            spec.append(("How to play", self.how, 1.5, "plain"))
        spec.append(("Start game", self.start, 1.8, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        g = self.game
        if g.min_players < g.max_players:
            T.draw_text(surf, str(self.n), "head", 40, T.TEXT, (132, 104), "center")
            T.draw_text(surf, "players. Tap a name to change it.", "text", 22, T.DIM, (262, 104), "midleft")
        else:
            T.draw_text(surf, "%d players. Tap a name to change it." % self.n, "text", 22, T.DIM, (20, 104), "midleft")
        for i in range(self.n):               # a colour bar under each name, as well as the name
            w = (760 - 10 * (self.n - 1)) // self.n
            pygame.draw.rect(surf, T.player_colour(i), (20 + i * (w + 10) + 14, 204, w - 28, 4), border_radius=2)

    def count(self, step):
        self.n = max(self.game.min_players, min(self.game.max_players, self.n + step))
        self.refresh()

    def rename(self, i):
        def done(text):
            if text:
                self.names[i] = title_case(text)[:14]
            self.refresh()
        start = "" if self.names[i].startswith("Player ") else self.names[i].lower()
        self.app.push(TextEntry(self.app, "Player %d's name" % (i + 1), start, done, "Done", max_len=14))

    def cycle(self, o):
        c = o["choices"]
        self.opts[o["key"]] = c[(c.index(self.opts[o["key"]]) + 1) % len(c)]
        self.refresh()

    def how(self):
        self.app.push(Pages(self.app, self.game.name, "How to play",
                            [(s["title"], s["text"]) for s in self.game.teach()]))

    def start(self):
        names = self.names[:self.n]
        if len(set(n.lower() for n in names)) < len(names):
            self.app.say("Two players share a name. Even I would find that confusing.")
            return
        remember_names(names)
        self.app.start_game(self.game, names, self.opts)

    def on_button(self, gesture):
        if gesture == "press":
            self.start()
        elif gesture == "double":
            self.app.pop()


# ---------------------------------------------------------------- playing
class PlayBase(Screen):
    """Base for a game's play screens. Gives every game the same button:
    press = next, double = undo, hold = ask."""

    def __init__(self, app, session):
        super().__init__(app)
        self.session, self.game = session, session.game
        self._logged = False

    @property
    def state(self):
        return self.session.state

    @property
    def left(self):
        return self.game.strip(self.session)[0]

    @property
    def title(self):
        return self.game.strip(self.session)[1]

    @property
    def pill(self):
        i = self.game.active(self.state)
        if i is None:
            return None
        return ("%s's turn" % self.session.players[i], T.player_colour(i))

    def enter(self):
        self.show_ring()
        super().enter()

    def show_ring(self):
        i = self.game.active(self.state)
        if i is None:
            self.app.hw.ring("breathe")
        else:
            self.app.hw.ring("turn", colour=T.player_colour(i))

    def do(self, **ev):
        """Apply an event, say what the game said, and move on if the game ended."""
        n = len(self.session.log)
        said = self.session.do(**ev)
        self._logged = len(self.session.log) > n
        self._at = len(self.session.log)      # where the log stood after this event
        if said:
            self.app.say(" ".join(said))
        self.show_ring()
        if self.session.finished:
            self.app.end_game()
        else:
            self.refresh()
            self.app.show_cards()
        return self._logged

    def undo(self, quiet=False):
        if self.session.undo():
            if not quiet:
                self.app.say("Undone.")
        elif not quiet:
            self.app.say("There is nothing left to undo.")
        self.show_ring()
        self.refresh()

    def lookup(self):
        from .lookup import Lookup
        self.app.push(Lookup(self.app, self.game.id))

    def rules(self):
        self.app.push(Pages(self.app, self.game.name, "How to play",
                            [(s["title"], s["text"]) for s in self.game.teach()]))

    def more(self):
        """The 'More' menu every game gets: rules, reminders, leave."""
        from .extras import GameMenu
        self.app.push(GameMenu(self.app, self.session))

    def on_button(self, gesture):
        if gesture == "press":
            self._logged = False              # only this press may be taken back by a double
            self.do(**self.game.press(self.state))
            self.pressed_at(self.session)
        elif gesture == "double":
            self.double()

    def pressed_at(self, session):
        """Note where the log stood once the button's press was dealt with. The
        shell does the same after every press, on whatever screen it landed."""
        self.app.press_mark = (session, len(session.log))

    def double(self):
        """The double that follows a press: take that press back, then undo one
        more. If anything else was logged in between (a phone's event landed in
        that third of a second), undo would take back the wrong thing: then
        nothing is undone, and she says so."""
        mark, self.app.press_mark = getattr(self.app, "press_mark", None), None
        if mark is not None and (mark[0] is not self.session or mark[1] != len(self.session.log)):
            self._logged = False
            self.app.say("Something else happened in between; nothing undone.")
            self.show_ring()
            self.refresh()
            return
        if self._logged and getattr(self, "_at", None) == len(self.session.log):
            self.session.undo()               # the press that came with the double
        self._logged = False
        self.undo()


# ---------------------------------------------------------------- game over
CLOSING = [
    "A result. I had it worked out some time ago, but do go on.",
    "It is over. I shall file it with the other inevitabilities.",
    "Concluded. The universe, I note, is unchanged.",
    "There we are. I trust that was worth the electricity.",
    "A winner emerges. I shall try to contain my circuits.",
    "Finished. I enjoyed keeping the score more than I expected to.",
    "The game is done. Somebody won. The rest of you took part.",
    "And so it ends. I have the full record, should anyone dispute it.",
    "Over. Shake hands. I am told that is the custom.",
    "A conclusion. Not the one all of you wanted.",
    "Done. I have saved the result where it cannot be argued with.",
    "That is the end of that. Shall we do it again, or have you suffered enough.",
    "Victory, of a sort. Savour it while the others sulk.",
]


class GameOver(Screen):
    title = "Game over"
    undoes_press = True       # a double press here takes back the press that ended the game

    def __init__(self, app, session):
        super().__init__(app)
        self.session, self.left = session, session.game.name
        self.line = random.choice(CLOSING)

    def enter(self):
        self.app.hw.ring("flare", colour=(255, 255, 255))
        super().enter()

    def build(self):
        return row([("Undo", self.undo, 1, "plain"), ("New game", self.again, 1.3, "plain"),
                    ("Home", self.app.go_home, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def undo(self):
        """The game was ended by a slip: step back one event and carry on. A
        game ended by hand (End game) was ended by no event, so nothing is
        stepped back: it is simply not over any more."""
        s = self.session
        if (s.finished or {}).get("by_hand") or not s.undo():
            s.d["finished"] = None
            s.save()
        self.app.session = s
        self.app.go_home()
        self.app.push(s.game.play_screen(self.app, s))
        self.app.say("Undone. The game goes on.")

    def again(self):
        game = self.session.game
        self.app.go_home()
        self.app.push(Setup(self.app, game))

    def draw_body(self, surf):
        fin = self.session.finished or {}
        head = fin.get("headline") or ("%s wins" % fin["winner"] if fin.get("winner") else "No winner")
        T.draw_text(surf, head, "head", 52, T.TEXT, (T.W // 2, 76), "midtop", max_w=T.W - 40)
        y = 148
        for line in (fin.get("lines") or [])[:3]:
            T.draw_text(surf, line, "head5", 28, T.TEXT, (T.W // 2, y), "midtop", max_w=T.W - 40)
            y += 38
        T.draw_text(surf, engine.duration_words(fin.get("minutes", 0)), "text", 22, T.DIM, (T.W // 2, y + 4), "midtop")
        y += 44
        for line in T.wrap("“%s”" % self.line, "text", 24, T.W - 80)[:2]:
            if y + 30 < BOTTOM_Y:
                T.draw_text(surf, line, "text", 24, T.DIM, (T.W // 2, y), "midtop")
            y += 32

    def on_button(self, gesture):
        if gesture == "press":
            self.app.go_home()
        elif gesture == "double":
            self.undo()
