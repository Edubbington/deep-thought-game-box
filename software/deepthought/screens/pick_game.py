"""Pick a game. The first page has four big tiles; every page after it has eight names,
so a full shelf of games is a few taps away and not a dozen."""
from .. import theme as T
from ..app import Screen
from ..widgets import Button
from .home import tile_rect, GAP, PAD, ROW_Y, TILE_W

BIG, SMALL = 4, 8         # games on the first page, and on each page after it


class PickGame(Screen):
    left = "Play"
    title = "Which game?"

    def __init__(self, app):
        super().__init__(app)
        self.page, self.sel = 0, 0           # sel is an index into app.games

    def pages(self):
        n = len(self.app.games)
        return 1 if n <= BIG else 1 + -(-(n - BIG) // SMALL)

    def span(self, page):
        """The games on this page, as indexes into app.games."""
        n = len(self.app.games)
        first = 0 if page == 0 else BIG + (page - 1) * SMALL
        return range(first, min(n, first + (BIG if page == 0 else SMALL)))

    def build(self):
        games = self.app.games
        out = []
        for slot, i in enumerate(self.span(self.page)):
            g = games[i]
            ready = g["status"] == "ready"
            if self.page == 0:
                out.append(Button(tile_rect(slot), g["name"], lambda i=i: self.choose(i), "tile",
                                  g["blurb"] if ready else "Not built yet",
                                  selected=(i == self.sel), dim=not ready))
            else:                             # two columns of four names
                rect = (PAD + (slot % 2) * (TILE_W + GAP), T.STRIP + PAD + (slot // 2) * 76, TILE_W, 68)
                out.append(Button(rect, g["name"], lambda i=i: self.choose(i), selected=(i == self.sel),
                                  dim=not ready, size=24))
        out.append(Button((PAD, ROW_Y, 160, 64), "Back", self.app.pop))
        if self.pages() > 1:
            out.append(Button((PAD + 174, ROW_Y, 230, 64),
                              "More  %d of %d" % (self.page + 1, self.pages()), self.more))
        return out

    def more(self):
        self.page = (self.page + 1) % self.pages()
        self.sel = self.span(self.page)[0]
        self.refresh()

    def choose(self, i):
        self.sel = i
        self.refresh()
        self.confirm()

    def confirm(self):
        g = self.app.games[self.sel]
        if g["status"] != "ready":
            self.app.say("%s is not built yet. I am aware of the irony." % g["name"])
            return
        from .common import Setup
        self.app.push(Setup(self.app, g["plugin"]))

    def draw_body(self, surf):
        if not self.app.games:
            return
        x = PAD + 174 + (244 if self.pages() > 1 else 0)
        T.draw_text(surf, "Press for " + self.app.games[self.sel]["name"], "text", 22, T.DIM,
                    (T.W - PAD, ROW_Y + 32), "midright", max_w=T.W - PAD - x)

    def on_button(self, gesture):
        if gesture == "press":
            self.confirm()
        elif gesture == "double":
            self.app.pop()
