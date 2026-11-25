"""Things you can tap."""
import pygame
from . import theme as T


def row(spec, y, h=72, x0=20, x1=780, gap=10):
    """A row of buttons that share the width. spec: [(label, action, flex, style)]."""
    total = sum(s[2] for s in spec)
    space = (x1 - x0) - gap * (len(spec) - 1)
    out, x = [], float(x0)
    for label, action, flex, style in spec:
        w = space * flex / total
        out.append(Button((round(x), y, round(w), h), label, action, style))
        x += w + gap
    return out


class Tile:
    """A panel with a small label and a big number. Tap it if it has an action."""

    def __init__(self, rect, label, value, action=None, colour=None, note=None):
        self.rect = pygame.Rect(rect)
        self.label, self.value, self.action, self.colour, self.note = label, str(value), action, colour, note
        self.style, self.selected = "number", False

    def draw(self, surf, pressed=False):
        r = self.rect
        pygame.draw.rect(surf, T.RAISED if pressed else T.PANEL, r, border_radius=14)
        pygame.draw.rect(surf, T.LINE, r, 1, border_radius=14)
        if self.colour:                      # a bar in the player's colour, beside their name
            pygame.draw.rect(surf, self.colour, (r.x + 8, r.y + 10, 5, r.h - 20), border_radius=2)
        if r.h >= 100:                       # tall: label on top, number under it
            T.draw_text(surf, self.label, "text", 22, T.DIM, (r.x + 20, r.y + 10), max_w=r.w - 30)
            T.draw_text(surf, self.value, "head", 44, T.TEXT, (r.x + 20, r.y + 38), max_w=r.w - 30)
            if self.note:
                T.draw_text(surf, self.note, "text", 22, T.DIM, (r.right - 12, r.bottom - 10), "bottomright",
                            max_w=r.w - 110)
        else:                                # short: label left, number right
            T.draw_text(surf, self.label, "text", 22, T.DIM, (r.x + 20, r.centery), "midleft", max_w=r.w - 120)
            T.draw_text(surf, self.value, "head", 40, T.TEXT, (r.right - 18, r.centery), "midright", max_w=110)


class Button:
    """style: 'plain' (raised panel), 'primary' (light, the main action),
    'tile' (big panel with a heading and a line under it)."""

    def __init__(self, rect, label, action=None, style="plain", sub=None,
                 selected=False, dim=False, size=24):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.style, self.sub = label, action, style, sub
        self.selected, self.dim, self.size = selected, dim, size

    def draw(self, surf, pressed=False):
        r = self.rect
        if self.style == "tile":
            bg = T.RAISED if (self.selected or pressed) else T.PANEL
            pygame.draw.rect(surf, bg, r, border_radius=18)
            if self.selected:                # thick light edge, not colour alone
                pygame.draw.rect(surf, T.TEXT, r, 3, border_radius=18)
            else:
                pygame.draw.rect(surf, T.LINE, r, 1, border_radius=18)
            inner = r.w - 48
            T.draw_text(surf, self.label, "head", 36, T.DIM if self.dim else T.TEXT,
                        (r.x + 24, r.y + 16), max_w=inner)
            if self.sub:
                T.draw_text(surf, self.sub, "text", 22, T.DIM,
                            (r.x + 24, r.bottom - 18), "bottomleft", max_w=inner)
            return
        if self.style == "primary":
            bg, fg, edge = (T.DIM if pressed else T.TEXT), T.GROUND, T.TEXT
        elif self.selected:
            bg, fg, edge = T.TEXT, T.GROUND, T.TEXT
        else:
            bg, fg, edge = (T.LINE if pressed else T.RAISED), T.TEXT, T.LINE
        pygame.draw.rect(surf, bg, r, border_radius=14)
        pygame.draw.rect(surf, edge, r, 1, border_radius=14)
        T.draw_text(surf, self.label, "bold", self.size, fg, r.center, "center", max_w=r.w - 24)
