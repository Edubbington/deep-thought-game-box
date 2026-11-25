"""Lookup: search the library (content.db). Nothing here uses the network."""
import pygame
from .. import theme as T
from ..app import Screen
from ..widgets import Button, row
from .common import BOTTOM_H, BOTTOM_Y, Pages, TextEntry

PER_PAGE = 3
ROW_Y, ROW_H, ROW_GAP = 144, 76, 6


class Lookup(Screen):
    title = "Lookup"

    def __init__(self, app, game=None, query=""):
        super().__init__(app)
        self.game, self.home_game = game, game      # game None = every game
        self.query, self.results, self.page = query, [], 0
        if query:
            self.run(query)

    @property
    def left(self):
        return self.app.game_name(self.game) if self.game else "All games"

    def pages(self):
        return max(1, -(-len(self.results) // PER_PAGE))

    def build(self):
        out = [Button((20, 68, 560, 64), "", self.type), Button((590, 68, 190, 64), self.scope_label(), self.scope, size=22)]
        for slot, r in enumerate(self.results[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            out.append(Button((20, ROW_Y + slot * (ROW_H + ROW_GAP), 760, ROW_H), "", lambda r=r: self.open(r)))
        spec = [("Back", self.app.pop, 1, "plain")]
        if self.pages() > 1:
            spec.append(("More  %d of %d" % (self.page + 1, self.pages()), self.more, 1.6, "plain"))
        spec.append(("Search", self.type, 1.4, "primary"))
        return out + row(spec, BOTTOM_Y, BOTTOM_H)

    def scope_label(self):
        return "This game" if self.game else "All games"

    def scope(self):
        """Switch between the current game and every game."""
        if self.home_game is None:
            games = [None] + self.app.library.games()
            self.game = games[(games.index(self.game) + 1) % len(games)] if self.game in games else None
        else:
            self.game = None if self.game else self.home_game
        self.run(self.query)

    def type(self):
        self.app.push(TextEntry(self.app, "Search", self.query, self.run))

    def run(self, query):
        self.query, self.page = query, 0
        self.results = self.app.library.search(query, self.game, dm=self.app.dm) if query else []
        if self.app.stack and self.app.screen is self:
            self.refresh()

    def more(self):
        self.page = (self.page + 1) % self.pages()
        self.refresh()

    def open(self, r):
        lib = self.app.library
        entry = lib.card(r["id"]) if r["kind"] == "card" else lib.doc(r["id"])
        if not entry:
            return
        self.app.push(Pages(self.app, entry["title"], "", [(entry["heading"], entry["body"])],
                            note="DM only" if entry["dm_only"] else None))

    def draw(self, surf, pressed=None):
        super().draw(surf, pressed)
        box = self.widgets[0].rect                       # the search box, drawn over its button
        shown = self.query or "Tap to type a search"
        T.draw_text(surf, shown, "mid", 26, T.TEXT if self.query else T.DIM, (box.x + 18, box.centery),
                    "midleft", max_w=box.w - 36)
        rows = [w for w in self.widgets if w.rect.h == ROW_H]
        for w, r in zip(rows, self.results[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            T.draw_text(surf, r["title"], "bold", 22, T.TEXT, (w.rect.x + 16, w.rect.y + 8), max_w=728)
            T.draw_text(surf, r["snippet"] or r["sub"], "text", 22, T.DIM, (w.rect.x + 16, w.rect.y + 40), max_w=728)
        if not rows:
            sections, cards = self.app.library.counts()
            if not sections and not cards:
                lines = ["The library is empty.", "Put your books in content/mine and the free rules in",
                         "content/free, then run the loader. Steps are in LIBRARY.md."]
            elif self.query:
                lines = ["Nothing found for “%s”." % self.query[:30],
                         "Try one plain word, or switch to All games."]
            else:
                lines = ["%d sections and %d cards loaded." % (sections, cards), "Tap Search and type a word or two."]
            for i, line in enumerate(lines):
                T.draw_text(surf, line, "head5" if i == 0 else "text", 28 if i == 0 else 22,
                            T.TEXT if i == 0 else T.DIM, (T.W // 2, 190 + i * 40), "center", max_w=760)

    def on_button(self, gesture):
        if gesture == "press":
            self.more() if self.pages() > 1 else self.type()
        elif gesture == "double":
            self.app.pop()
