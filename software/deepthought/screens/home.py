"""Home: four big tiles."""
from .. import engine, paths
from .. import theme as T
from ..app import Screen
from ..widgets import Button

TILE_W, TILE_H, GAP, PAD = 373, 140, 14, 20
ROW_Y = T.STRIP + PAD + 2 * (TILE_H + GAP)      # top of the row under the tiles


def tile_rect(i):
    col, row = i % 2, i // 2
    return (PAD + col * (TILE_W + GAP), T.STRIP + PAD + row * (TILE_H + GAP), TILE_W, TILE_H)


class Home(Screen):
    left = "Deep Thought"

    def build(self):
        tiles = [("Play", "Start or resume a game", self.play),
                 ("Lookup", "Search rules, books and cards", self.lookup),
                 ("Dice", "Roll and let it judge you", self.dice),
                 ("Settings", "Volume, phones, shut down", self.settings)]
        out = [Button(tile_rect(i), name, act, "tile", sub) for i, (name, sub, act) in enumerate(tiles)]
        self.last = self.app.last_game
        if self.last:                          # tap the last-game line for the history
            out.append(Button((PAD, ROW_Y, 400, 64), self.last, self.history, size=22))
        return out

    def history(self):
        from .common import Pages
        names = {g["id"]: g["name"] for g in self.app.games}
        steps = []
        for _, d in engine.iter_sessions(paths.data("sessions")):
            fin = d.get("finished")
            if len(steps) >= 10:
                break
            if not isinstance(fin, dict):
                continue
            who = "%s won." % fin["winner"] if fin.get("winner") else "No winner."
            body = "%s %s\n%s\n%s" % (who, engine.duration_words(fin.get("minutes", 0)).capitalize() + ".",
                                      ", ".join(str(p) for p in d["players"]),
                                      "\n".join(str(x) for x in fin.get("lines") or []))
            steps.append(("%s, %s" % (names.get(d["game"], d["game"]), str(d.get("started", ""))[:10]), body))
        self.app.push(Pages(self.app, "Deep Thought", "Last ten games", steps))

    def play(self):
        from .common import Choice
        from .pick_game import PickGame
        new = lambda: self.app.push(PickGame(self.app))
        found = engine.unfinished(paths.data("sessions"))
        if found and found[1].get("game") in self.app.plugins:
            path, d = found
            text = "A %s game from %s was left unfinished.\n%s." % (
                self.app.game_name(d["game"]), str(d.get("started", ""))[11:16], ", ".join(str(p) for p in d["players"]))
            self.app.push(Choice(self.app, "Resume?", text,
                                 [("Resume it", lambda: self.app.resume_game(path)), ("New game", new)]))
        else:
            new()

    def lookup(self):
        from .lookup import Lookup
        self.app.push(Lookup(self.app))

    def dice(self):
        from .dice import Dice
        self.app.push(Dice(self.app))

    def settings(self):
        from .extras import Settings
        self.app.push(Settings(self.app))

    def draw_body(self, surf):
        y = ROW_Y + 32
        if not getattr(self, "last", None):
            T.draw_text(surf, "No games played yet", "text", 22, T.DIM, (PAD, y), "midleft", max_w=400)
        T.draw_text(surf, "Hold the button to ask anything", "text", 22, T.DIM, (T.W - PAD, y), "midright", max_w=340)

    def on_button(self, gesture):
        if gesture == "press":
            self.play()
        elif gesture == "long_hold":
            from .common import Choice
            self.app.push(Choice(self.app, "Shut down?", "Shut Deep Thought down safely?\nWait for the ring to go dark "
                                 "before switching the power off.",
                                 [("Stay on", None), ("Shut down", self.app.shutdown)]))
