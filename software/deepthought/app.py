"""The app shell: one window, a stack of screens, one loop."""
import collections
import math
import time
import pygame
from . import engine, paths
from . import theme as T

SIDE = 220          # desktop only: a strip beside the screen for the ring
TROUBLE = "Something went wrong there. I have written it down in errors.log and carried on."
FPS = 30


class Screen:
    """One screen. Subclasses set the strip text and build their widgets."""
    left = ""           # dim text at the left of the top strip
    title = ""          # heading in the middle of the strip
    pill = None         # (text, colour) at the right, e.g. whose turn

    def __init__(self, app):
        self.app = app
        self.widgets = []

    def enter(self):                 # called each time the screen comes to the front
        self.refresh()

    def refresh(self):
        self.widgets = self.build()
        self.app.dirty = True

    def build(self):
        return []

    def draw_body(self, surf):
        pass

    def on_button(self, gesture):    # press, double, hold_start, hold_end, long_hold
        pass

    def draw(self, surf, pressed=None):
        surf.fill(T.GROUND)
        pygame.draw.rect(surf, T.PANEL, (0, 0, T.W, T.STRIP))
        pygame.draw.line(surf, T.LINE, (0, T.STRIP - 1), (T.W, T.STRIP - 1))
        if self.left:
            if self.title:                   # as much room as the centred title leaves
                room = (T.W - min(280, T.font("head", 24).size(self.title)[0])) // 2 - 36
            else:
                room = 480 if self.pill else 760
            T.draw_text(surf, self.left, "text", 22, T.DIM, (20, T.STRIP // 2), "midleft", max_w=room)
        if self.title:
            T.draw_text(surf, self.title, "head", 24, T.TEXT, (T.W // 2, T.STRIP // 2), "center", max_w=280)
        if self.pill:
            text, colour = self.pill
            text, _ = T.fit(text, "bold", 22, 230)       # a long name must not run into the title
            img = T.render(text, "bold", 22, T.GROUND)
            box = img.get_rect().inflate(28, 12)
            box.midright = (T.W - 20, T.STRIP // 2)
            pygame.draw.rect(surf, colour, box, border_radius=box.h // 2)
            surf.blit(img, img.get_rect(center=box.center))
        self.draw_body(surf)
        for w in self.widgets:
            w.draw(surf, pressed is w)


class App:
    def __init__(self, hw, games, headless=False, flip=False):
        pygame.display.init()
        pygame.font.init()
        self.hw, self.games, self.headless, self.flip = hw, games, headless, flip
        self.side = SIDE if hw.name == "desktop" and not headless else 0
        if not headless and hw.name == "pi":
            self.window = pygame.display.set_mode((T.W, T.H), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)
        elif not headless:
            self.window = pygame.display.set_mode((T.W + self.side, T.H))
            pygame.display.set_caption("Deep Thought")
        self.surface = pygame.Surface((T.W, T.H))
        self.stack, self.dirty, self.running = [], True, True
        self.pressed = None
        self._jobs = collections.deque()
        self.toast, self.toast_until = None, 0.0
        self.plugins = {g["id"]: g["plugin"] for g in games if g.get("plugin")}
        self.session = None          # the game being played, if any
        self.dm = False              # DM mode unlocked (D&D)
        self.voice = None            # set by voice.attach() when speech is available
        self.web = None              # set when the web server is running
        self._library = None
        self.press_mark = None       # (session, length of its log) after the last press of the button

    @property
    def library(self):
        if self._library is None:
            from .library import Library
            self._library = Library()
        return self._library

    def reload_library(self):
        self.close_library()

    def close_library(self):
        """Let go of content.db, so nothing new is left waiting beside it in
        content.db-wal. The next use opens it again."""
        old, self._library = self._library, None
        if old is not None:
            old.close()

    @property
    def last_game(self):
        return engine.last_game_line(paths.data("sessions"), {g["id"]: g["name"] for g in self.games})

    def game_name(self, game_id):
        return next((g["name"] for g in self.games if g["id"] == game_id), game_id or "")

    # ---- games
    def start_game(self, game, names, options):
        from . import persona, settings
        self.session = engine.Session(game, names, options, paths.data("sessions"))
        self.go_home()
        self.push(game.play_screen(self, self.session))
        if options.get("guide") == "As we play":
            from . import guide
            self.session.cards = guide.start(self.session)
            self.session.save()
            self.show_cards()
        elif self.voice and persona.optional(settings.get("chatty")):
            self.say(persona.line("game_start"))

    def resume_game(self, path):
        s = engine.Session.load(path, self.plugins)
        if not s:
            self.say("I no longer know how to play that game.")
            return
        self.session = s
        self.go_home()
        self.push(s.game.play_screen(self, s))

    def end_game(self):
        """The game finished: show the result."""
        from .screens.common import GameOver
        s, self.session = self.session, None
        over = GameOver(self, s)
        over.press_from = getattr(self, "_handling", None)    # the screen whose press ended it, if a press did
        self.go_home()
        self.push(over)

    def show_cards(self):
        """Show any teaching steps the game has just made due, and read them out."""
        s = self.session
        if not s or not s.cards or s.finished:
            return False
        from .screens.common import Pages
        steps, s.cards = s.cards, []
        card = Pages(self, s.game.name, "Teach", [(x["title"], x["text"]) for x in steps], auto=True)
        card.guide_was = (s, getattr(s, "guide_was", None))
        self.push(card)
        return True

    def go_home(self):
        del self.stack[1:]
        self.hw.ring("breathe")
        self.screen.enter()

    def game_event(self, ev):
        """Apply a game event that came from outside the screen (a phone).
        Goes through the play screen when it is showing, so the ring, the
        message and the end of the game are handled the same way."""
        from .screens.common import PlayBase
        if not self.session:
            return
        play = next((s for s in reversed(self.stack) if isinstance(s, PlayBase)), None)
        if play and play.session is self.session:
            play.do(**ev)
            play._logged = False             # not the button's: a double press must not take it back as its own press
            if self.session and self.screen is not play:
                self.screen.refresh()        # another screen is on top (a map, a menu): redraw it too
        else:
            said = self.session.do(**ev)
            if said:
                self.say(" ".join(said))
            if self.session.finished:
                self.end_game()
        self.show_cards()

    def reload_games(self):
        """Read the game folders again (a game was added from the web page)."""
        from .games import load_games
        self.games, _ = load_games(extra=paths.data("games"))
        self.plugins = {g["id"]: g["plugin"] for g in self.games if g.get("plugin")}
        self.screen.refresh()

    def shutdown(self):
        from . import persona
        self.say(persona.line("power_off"))
        self.render()
        self.hw.ring("off")
        self.running = False
        self.hw.shutdown()

    # ---- screens
    @property
    def screen(self):
        return self.stack[-1]

    def push(self, screen):
        self.stack.append(screen)
        screen.enter()

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.screen.enter()

    def say(self, text, secs=None, speak=True, private=False):
        """A line from Deep Thought: shown on screen, and spoken if she has a voice.
        private: for the DM's eyes. Shown on the box only: never spoken, never on a web page."""
        secs = secs or max(4.0, len(text) / 14.0)
        self.toast, self.toast_until, self.dirty = text, time.monotonic() + secs, True
        self.toast_private = bool(private)
        if speak and not private and self.voice:
            self.voice.say(text, show=False)

    # ---- drawing
    def render(self):
        self.screen.draw(self.surface, self.pressed)
        if getattr(self, "strip_down", False):       # a thick bar under the strip while it is held: shape, not colour alone
            pygame.draw.rect(self.surface, T.TEXT, (0, T.STRIP - 6, T.W, 6))
        if self.toast:
            lines = T.wrap(self.toast, "mid", 22, T.W - 80)[:3]
            h = 24 + 30 * len(lines)
            box = pygame.Rect(20, T.H - 20 - h, T.W - 40, h)
            pygame.draw.rect(self.surface, T.RAISED, box, border_radius=14)
            pygame.draw.rect(self.surface, T.TEXT, box, 1, border_radius=14)
            for i, line in enumerate(lines):
                T.draw_text(self.surface, line, "mid", 22, T.TEXT, (box.x + 20, box.y + 12 + 30 * i))
        self.dirty = False

    def shot(self, path):
        self.render()
        pygame.image.save(self.surface, path)
        return path

    def _draw_side(self, t):
        x0 = T.W
        pygame.draw.rect(self.window, (0, 0, 0), (x0, 0, self.side, T.H))
        cx, cy, rad = x0 + self.side // 2, 130, 70
        for i, (r, g, b) in enumerate(self.hw.ring_frame(t)):
            a = 2 * math.pi * i / 16 - math.pi / 2
            colour = tuple(min(255, c * 2) for c in (r, g, b))     # ring is capped at half
            centre = (cx + rad * math.cos(a), cy + rad * math.sin(a))
            pygame.draw.circle(self.window, (30, 30, 30), centre, 11)
            pygame.draw.circle(self.window, colour, centre, 9)
        for i, line in enumerate(("LED ring", "", "Space = button", "tap = next", "hold = talk", "double = undo")):
            T.draw_text(self.window, line, "text", 22, T.DIM, (cx, 240 + 30 * i), "midtop")

    # ---- input
    def _pos(self, pos):
        x, y = pos
        return (T.W - 1 - x, T.H - 1 - y) if self.flip else (x, y)

    def _hit(self, pos):
        for w in reversed(self.screen.widgets):
            if w.action and w.rect.collidepoint(pos):
                return w
        return None

    def tap(self, pos):
        """A whole tap at a screen position. Used by the tests."""
        w = self._hit(pos)
        if w:
            w.action()
        return w

    def handle(self, event, t):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP):
            # Found on the real Pi, 22 Nov 2026: with no desktop, a touch arrives only as a
            # finger and never as a mouse click. A finger's place is a fraction of the window.
            w, h = self.window.get_size()
            pos = (min(w - 1, int(event.x * w)), min(h - 1, int(event.y * h)))
            down = event.type == pygame.FINGERDOWN
            event = pygame.event.Event(pygame.MOUSEBUTTONDOWN if down else pygame.MOUSEBUTTONUP, button=1, pos=pos)
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and getattr(event, "touch", False):
            return                           # the same touch again, where the system also sends it as a click
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
                self.say("Saved " + self.shot(time.strftime("shot-%H%M%S.png")))
            elif event.key == pygame.K_SPACE:
                self.hw.key_event(event, t)
            elif event.type == pygame.KEYDOWN and hasattr(self.screen, "on_key"):
                self.screen.on_key(event)
                self.dirty = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.toast:                   # a tap puts the message away, and still counts
                self.toast, self.dirty = None, True
            self.pressed, self.dirty = self._hit(self._pos(event.pos)), True
            # The strip across the top is the button too: tap = press, hold = talk, two taps = undo.
            # Added 23 Nov 2026, when the real button's switch turned out to read closed all the time.
            if self.pressed is None and self._pos(event.pos)[1] < T.STRIP:
                self.strip_down = True
                self.hw.touch_button(True, t)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            w, self.pressed, self.dirty = self.pressed, None, True
            if getattr(self, "strip_down", False):
                self.strip_down = False
                self.hw.touch_button(False, t)
            if w and w is self._hit(self._pos(event.pos)):
                w.action()

    def gesture(self, name):
        if name == "press":
            self.hw.tick_sound()
        if name in ("hold_start", "hold_end") and self.voice:
            self.voice.hold(name == "hold_start")      # push to talk, on every screen
        elif name == "hold_start":
            self.say("I am listening, in principle. My ears have not been fitted yet.")
        if name == "press":
            self._pressed_on = self.screen
        elif name == "double":
            # A double always follows its own press, and belongs to the screen that
            # press went to. It must never land on whatever happens to be showing now.
            #   The press opened something on top (a teach card, a menu): put that away,
            #   and give the double to the screen that was pressed.
            #   The press closed its own screen: there is nothing left to take back,
            #   unless the new screen says it can undo that press itself (Game over,
            #   and only when it was that press which ended the game: a double that
            #   puts away an answer lying over Game over leaves the game alone).
            was, self._pressed_on = getattr(self, "_pressed_on", None), None
            if was is not None and was is not self.screen:
                if was in self.stack:
                    i = self.stack.index(was)
                    if any(getattr(s, "auto", False) for s in self.stack[i + 1:]):
                        self.hw.stop_sound()
                    for s in self.stack[i + 1:]:      # a teach card put away unread is owed again
                        session, g = getattr(s, "guide_was", (None, None))
                        if session is not None and g is not None and session.d.get("guide"):
                            session.d["guide"] = g
                            break
                    del self.stack[i + 1:]
                    was.on_button("double")
                    if self.screen is was:
                        getattr(was, "show_ring", lambda: None)()
                        was.refresh()
                    self.dirty = True
                    return
                top = self.screen
                if not (getattr(top, "undoes_press", False) and getattr(top, "press_from", was) is was):
                    self.dirty = True
                    return
        self._handling = self.screen if name == "press" else None
        try:
            self.screen.on_button(name)
        finally:
            self._handling = None
        if name == "press":                  # where the game's log stood once this press was dealt with: a
            s = self.session                 # double that finds it has moved since undoes nothing
            self.press_mark = (s, len(s.log)) if s else None
        self.dirty = True

    def later(self, fn):
        """Run fn on the main loop. Safe to call from another thread."""
        self._jobs.append(fn)

    def jobs(self):
        out = []
        while self._jobs:
            out.append(self._jobs.popleft())
        return out

    # ---- the loop
    def frame(self, t):
        """One turn of the loop."""
        for event in pygame.event.get():
            self.handle(event, t)
        for name in self.hw.gestures(t):
            self.gesture(name)
        for _ in range(len(self._jobs)):     # one at a time: if a job fails, the rest are still
            if not self._jobs:               # in the queue for the next frame
                break
            self._jobs.popleft()()
        for screen in list(self.stack):      # screens that keep time (the slow-play clock),
            tick = getattr(screen, "tick", None)   # even when another screen is on top
            if tick:
                tick(t)
        self.show_cards()
        if self.toast and t > self.toast_until:
            self.toast, self.dirty = None, True
        if self.dirty:                   # redraw only when something changed
            self.render()
            out = pygame.transform.rotate(self.surface, 180) if self.flip else self.surface
            self.window.blit(out, (0, 0))
        if self.side:
            self._draw_side(t)
        pygame.display.flip()

    def trouble(self, t):
        """Something in a screen or a game went wrong. A game night should not
        end on it: write it down, say so, and carry on. If it keeps happening,
        go back to Home; if even that does not help, give up and let the
        service start the program again (the game is saved after every event)."""
        import traceback
        text = traceback.format_exc()
        try:
            path = paths.data("errors.log")
            old = ""
            try:
                with open(path, encoding="utf-8") as f:
                    old = f.read()[-60000:]
            except OSError:
                pass
            with open(path, "w", encoding="utf-8") as f:
                f.write(old + "\n" + time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + text)
        except OSError:
            pass
        print(text)
        self._troubles = [x for x in getattr(self, "_troubles", []) if t - x < 10.0] + [t]
        if len(self._troubles) >= 6:
            raise
        if len(self._troubles) >= 3 and len(self.stack) > 1:
            del self.stack[1:]
            try:
                self.hw.ring("breathe")
                self.screen.enter()
            except Exception:
                pass
        self.pressed = None
        self.toast, self.toast_until, self.dirty = TROUBLE, time.monotonic() + 6.0, True

    def run(self):
        clock = pygame.time.Clock()
        try:
            while self.running:
                t = time.monotonic()
                try:
                    self.frame(t)
                except Exception:
                    self.trouble(t)
                clock.tick(FPS)
        finally:
            self.close_library()             # content.db is whole on disk once she has stopped
        pygame.quit()
