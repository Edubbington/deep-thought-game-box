"""Dice screen. Press the button to roll."""
import random
import pygame
from .. import dice, persona, settings
from .. import theme as T
from ..app import Screen
from ..widgets import Button

ROW_Y = 398                     # the control row along the bottom


def dice_layout(n):
    """Where each die goes. Returns (size, [(x, y), ...]). Up to 16 dice are
    drawn large in rows of 8; more than that are drawn small in rows of 12."""
    size, gap, per_row = (84, 12, 8) if n <= 16 else (54, 8, 12)
    spots, top = [], 74
    for row in range(-(-n // per_row)):
        count = min(per_row, n - row * per_row)
        x0 = (T.W - (count * size + (count - 1) * gap)) // 2
        spots += [(x0 + i * (size + gap), top + row * (size + gap)) for i in range(count)]
    return size, spots


class Dice(Screen):
    left = "Dice"

    def __init__(self, app, rng=None):
        super().__init__(app)
        self.rng = rng or random.Random()
        self.n, self.sides = 6, 6
        self.results, self.line, self.recent = None, "", []

    @property
    def title(self):
        return "%d %s" % (self.n, "die" if self.n == 1 else "dice")

    def build(self):
        out = [Button((20, ROW_Y, 110, 68), "Back", self.app.pop),
               Button((140, ROW_Y, 68, 68), "−", lambda: self.count(-1), size=30),
               Button((284, ROW_Y, 68, 68), "+", lambda: self.count(+1), size=30)]
        x = 362
        for sides, w in ((6, 66), (3, 66), (20, 78)):
            out.append(Button((x, ROW_Y + 2, w, 64), "D%d" % sides, lambda s=sides: self.kind(s),
                              selected=(sides == self.sides), size=22))
            x += w + 8
        out.append(Button((x + 2, ROW_Y, T.W - 20 - x - 2, 68), "Roll", self.roll, "primary"))
        return out

    def count(self, step):
        self.n = max(1, min(dice.MAX_DICE, self.n + step))
        self.results = None
        self.refresh()

    def kind(self, sides):
        self.sides, self.results = sides, None
        self.refresh()

    def roll(self):
        self.results = dice.roll(self.n, self.sides, self.rng)
        self.line = dice.remark(self.results, self.sides, self.recent, self.rng)
        self.recent = (self.recent + [self.line])[-2:]
        if self.app.voice and persona.optional(settings.get("chatty")):
            self.app.voice.say(self.line, show=False)          # the remark is already on this screen
        if dice.mood(self.results, self.sides) == "all_high":
            self.app.hw.ring("flare", colour=(255, 255, 255))
        self.refresh()

    def draw_body(self, surf):
        T.draw_text(surf, str(self.n), "head", 40, T.TEXT, (246, ROW_Y + 34), "center")
        if self.results is None:
            T.draw_text(surf, "Press the button to roll", "head", 30, T.DIM, (T.W // 2, 200), "center")
            return
        size, spots = dice_layout(len(self.results))
        for value, (x, y) in zip(self.results, spots):
            top = value == self.sides          # the best face is drawn light with a thick edge
            box = pygame.Rect(x, y, size, size)
            pygame.draw.rect(surf, T.TEXT if top else T.RAISED, box, border_radius=size // 5)
            pygame.draw.rect(surf, T.TEXT if top else T.LINE, box, 1, border_radius=size // 5)
            T.draw_text(surf, str(value), "head", 48 if size > 60 else 28,
                        T.GROUND if top else T.TEXT, box.center, "center")
        y = spots[-1][1] + size + 12
        T.draw_text(surf, dice.summary(self.results, self.sides), "head", 30, T.TEXT,
                    (T.W // 2, y), "midtop", max_w=T.W - 40)
        y += 42
        for text in T.wrap("“%s”" % self.line, "text", 24, T.W - 60)[:2]:
            if y + 30 > ROW_Y - 4:             # no room left above the controls
                break
            T.draw_text(surf, text, "text", 24, T.DIM, (T.W // 2, y), "midtop")
            y += 32

    def on_button(self, gesture):
        if gesture == "press":
            self.roll()
        elif gesture == "double":
            self.app.pop()


def dice_shots(app, snap):
    d = snap("dice-ready", Dice(app, random.Random(4)))
    d.roll()
    snap("dice-rolled")
    d.sides, d.n = 6, 30
    d.roll()
    snap("dice-30")
    d.sides, d.n = 20, 1
    d.roll()
    snap("dice-d20")
