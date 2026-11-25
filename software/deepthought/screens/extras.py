"""The in-game menu, reminders, the first-player spinner, and Settings."""
import random
import time
from .. import engine, settings
from .. import theme as T
from ..app import Screen
from ..widgets import Button, row
from .common import BOTTOM_H, BOTTOM_Y, Choice, Pages, TextEntry


def grid(i, cols=3, top=72, h=150, gap=10):
    w = (760 - gap * (cols - 1)) // cols
    return (20 + (i % cols) * (w + gap), top + (i // cols) * (h + gap), w, h)


class GameMenu(Screen):
    """Things every game offers, one tap from its play screen."""
    title = "Menu"

    def __init__(self, app, session):
        super().__init__(app)
        self.session, self.left = session, session.game.name

    def build(self):
        s = self.session
        tiles = [("Rules", "How to play", self.rules), ("Reminders", "%d set" % len(s.d["reminders"]), self.reminders),
                 ("Who first", "Spin for it", self.spin), ("Clock", "Time per player", self.clock),
                 ("End game", "Stop and record", self.end), ("Home", "Resume later", self.app.go_home)]
        out = [Button(grid(i), name, act, "tile", sub) for i, (name, sub, act) in enumerate(tiles)]
        return out + row([("Back to the game", self.app.pop, 2, "primary"), ("Lookup", self.lookup, 1, "plain"),
                          ("Dice", self.dice, 1, "plain")], BOTTOM_Y, BOTTOM_H)

    def dice(self):
        from .dice import Dice
        self.app.push(Dice(self.app))

    def lookup(self):
        from .lookup import Lookup
        self.app.push(Lookup(self.app, self.session.game.id))

    def rules(self):
        steps = [(x["title"], x["text"]) for x in self.session.game.teach()]
        self.app.push(Pages(self.app, self.session.game.name, "How to play", steps))

    def reminders(self):
        self.app.push(Reminders(self.app, self.session))

    def spin(self):
        self.app.push(Spinner(self.app, self.session.players))

    def clock(self):
        self.session._charge_clock()
        body = "\n".join("%s: %s" % (n, engine.duration_words(sec / 60)) for n, sec in
                         zip(self.session.players, self.session.d["seconds"]))
        self.app.push(Pages(self.app, self.session.game.name, "Clock", [("Time spent on each player's turns", body)],
                            speak=False))

    def end(self):
        def stop():
            self.session.finish()
            self.app.end_game()

        def scrap():                          # the wrong game, or a false start: no record of it is kept
            self.session.discard()
            self.app.session = None
            self.app.go_home()
        self.app.push(Choice(self.app, "End the game?", "End it: stop now and record the result.\n"
                             "Scrap it: throw this game away, as if it was never started.",
                             [("Keep playing", None), ("End it", stop), ("Scrap it", scrap)],
                             left=self.session.game.name))

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class Reminders(Screen):
    """Each player's own "don't forget" lines. The box says them at the right phase."""
    title = "Reminders"

    def __init__(self, app, session):
        super().__init__(app)
        self.session, self.left = session, session.game.name
        self.who, self.phase_i = None, 0          # None = everyone

    def phases(self):
        return [("*", "Every phase")] + list(self.session.game.phases())

    def build(self):
        s, out = self.session, []
        for i, r in enumerate(s.d["reminders"][:3]):
            who = s.players[r["player"]] if r["player"] is not None else "Everyone"
            phase = dict(self.phases()).get(r["phase"], r["phase"])
            out.append(Button((20, 72 + i * 70, 760, 64), "%s, %s: %s  (tap to remove)" % (who, phase, r["text"]),
                              lambda i=i: self.remove(i), size=22))
        who = "Everyone" if self.who is None else s.players[self.who]
        out += [Button((20, 300, 375, 64), "For: " + who, self.next_who, size=22),
                Button((405, 300, 375, 64), "When: " + self.phases()[self.phase_i][1], self.next_phase, size=22)]
        return out + row([("Back", self.app.pop, 1, "plain"), ("Add a reminder", self.add, 2, "primary")],
                         BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        if not self.session.d["reminders"]:
            T.draw_text(surf, "No reminders yet.", "head5", 28, T.TEXT, (T.W // 2, 130), "center")
            T.draw_text(surf, "Pick who and when, then add one. Phones can add them too.", "text", 22, T.DIM,
                        (T.W // 2, 176), "center")

    def next_who(self):
        n = len(self.session.players)
        self.who = 0 if self.who is None else (self.who + 1 if self.who + 1 < n else None)
        self.refresh()

    def next_phase(self):
        self.phase_i = (self.phase_i + 1) % len(self.phases())
        self.refresh()

    def remove(self, i):
        self.session.remove_reminder(i)
        self.refresh()

    def add(self):
        def done(text):
            self.session.add_reminder(self.who, self.phases()[self.phase_i][0], text.capitalize())
            self.refresh()
        self.app.push(TextEntry(self.app, "Don't forget…", "", done, "Add", max_len=60))

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()


class Spinner(Screen):
    """Who goes first. The ring spins and stops pointing at a seat."""
    left, title = "Deep Thought", "Who goes first?"

    def __init__(self, app, players, rng=None):
        super().__init__(app)
        self.players, self.rng, self.pick, self.at = players, rng or random.Random(), None, 0.0

    def enter(self):
        self.spin()
        super().enter()

    def spin(self):
        self.pick = self.rng.randrange(len(self.players))
        self.at = time.monotonic()
        self.app.hw.ring("spin", colour=T.player_colour(self.pick), side=self.pick * 16 // len(self.players))
        self.refresh()

    def build(self):
        return row([("Back", self.app.pop, 1, "plain"), ("Spin again", self.spin, 1.5, "primary")], BOTTOM_Y, BOTTOM_H)

    def draw_body(self, surf):
        T.draw_text(surf, self.players[self.pick], "head", 84, T.player_colour(self.pick), (T.W // 2, 190), "center",
                    max_w=720)
        T.draw_text(surf, "goes first. The ring points at seat %d." % (self.pick + 1), "text", 26, T.DIM,
                    (T.W // 2, 280), "center")

    def on_button(self, gesture):
        if gesture == "press":
            self.spin()
        elif gesture == "double":
            self.app.pop()


def about_pages(app):
    sections, cards = app.library.counts()
    cloud = app.voice.status().capitalize() if app.voice else "Not started."
    hardware = "; ".join(getattr(app.hw, "problems", [])) or "No problems reported."
    extra = [("Voice and cloud", cloud + "\n\nKeys go in config.toml. See VOICE.md."), ("Hardware", hardware)]
    return ABOUT + extra + [("Library", "%d sections of rules and notes, and %d Magic cards, are loaded.\n\n"
                     "To add your own books, see LIBRARY.md." % (sections, cards))]


ABOUT = [
    ("Deep Thought", "A game night box. She teaches in her own words and looks things up only in files "
     "the owner has loaded. A fan project for one living room; it distributes no rules text."),
    ("Credits", "D&D rules text, where loaded, is from the System Reference Document 5.2.1 by Wizards of the "
     "Coast LLC, licensed under CC BY 4.0.\n\nMagic card data, where loaded, is from Scryfall.\n\n"
     "Fonts: Inter and Space Grotesk, SIL Open Font License."),
]


class Settings(Screen):
    left, title = "Deep Thought", "Settings"

    def build(self):
        a, s = self.app, settings.load()
        sections, cards = a.library.counts()
        phone = a.web.url if a.web else "Not running"
        tiles = [("Volume %d" % s["volume"], "Tap to change", self.volume),
                 ("Chatty: %s" % s["chatty"], "How talkative", self.chatty),
                 ("DM mode", "Unlocked" if a.dm else "Locked", self.dm),
                 ("Phones", phone, self.phones),
                 ("Library", "%d sections" % sections, self.about),
                 ("Shut down", "Before unplugging", self.off)]
        out = [Button(grid(i), name, act, "tile", sub) for i, (name, sub, act) in enumerate(tiles)]
        return out + row([("Back", a.pop, 1, "primary")], BOTTOM_Y, BOTTOM_H)

    def volume(self):
        v = settings.get("volume") + 10
        v = settings.put("volume", 20 if v > 100 else v)
        self.app.hw.set_volume(v)
        self.app.hw.tick_sound()
        self.refresh()

    def chatty(self):
        c = settings.CHATTY
        settings.put("chatty", c[(c.index(settings.get("chatty")) + 1) % len(c)])
        self.refresh()

    def dm(self):
        if self.app.dm:
            self.app.dm = False
            self.refresh()
            return
        def done(text):
            self.app.dm = text.replace(" ", "") == str(settings.get("dm_code"))
            self.app.say("DM mode unlocked. Players, look away." if self.app.dm else "That is not the code.")
            self.refresh()
        self.app.push(TextEntry(self.app, "DM code", "", done, "Unlock", max_len=8))

    def phones(self):
        if not self.app.web:
            self.app.say("The web pages are not running.")
            return
        from .web_link import PhoneLink
        self.app.push(PhoneLink(self.app))

    def about(self):
        self.app.push(Pages(self.app, "Settings", "About", about_pages(self.app), speak=False))

    def off(self):
        self.app.push(Choice(self.app, "Shut down?", "Shut Deep Thought down safely?\nWait for the ring to go dark "
                             "before switching the power off.", [("Stay on", None), ("Shut down", self.app.shutdown)]))

    def on_button(self, gesture):
        if gesture in ("press", "double"):
            self.app.pop()
