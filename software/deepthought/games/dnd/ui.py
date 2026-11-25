"""Widgets and small screens the D&D plugin shares: a list row, a tick row,
a panel, and the number pad for initiative, damage and coins."""
import pygame
from ... import theme as T
from ...app import Screen
from ...widgets import Button

ROW_Y, ROW_H, ROW_PITCH, PER_PAGE = 68, 68, 74, 4
HINT_Y = 375            # one line of words between the rows and the bottom buttons


def row_rect(i, x=20, w=760):
    return (x, ROW_Y + i * ROW_PITCH, w, ROW_H)


def pages_for(n, per=PER_PAGE):
    return max(1, -(-n // per))


class Row:
    """A wide button: a number at the left, a name, word tags, and a note at
    the right. 'selected' draws the thick light edge, never colour alone."""
    style = "row"

    def __init__(self, rect, label, action=None, num="", right="", tags=(), selected=False, dim=False, bar=None,
                 tick=None):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.num, self.right = label, action, str(num), right
        self.tags, self.selected, self.dim, self.bar, self.tick = list(tags), selected, dim, bar, tick

    def draw(self, surf, pressed=False):
        r = self.rect
        pygame.draw.rect(surf, T.RAISED if (self.selected or pressed) else T.PANEL, r, border_radius=12)
        if self.selected:
            pygame.draw.rect(surf, T.TEXT, r, 3, border_radius=12)
        else:
            pygame.draw.rect(surf, T.LINE, r, 1, border_radius=12)
        fg = T.DIM if self.dim else T.TEXT
        x, right = r.x + 16, r.right - 16
        if self.bar:
            pygame.draw.rect(surf, self.bar, (r.x + 6, r.y + 10, 5, r.h - 20), border_radius=2)
        if self.tick is not None:                       # a box, with a mark in it when done
            box = pygame.Rect(x, r.centery - 15, 30, 30)
            pygame.draw.rect(surf, T.TEXT, box, 2, border_radius=6)
            if self.tick:
                pygame.draw.rect(surf, T.TEXT, box.inflate(-12, -12), border_radius=3)
            x += 44
        if self.num != "":
            T.draw_text(surf, self.num, "head", 30, fg, (x, r.centery), "midleft", max_w=50)
            x += 58
        if self.right:
            got = T.draw_text(surf, self.right, "text", 22, T.DIM, (right, r.centery), "midright",
                              max_w=max(60, min(260, r.w // 3)))
            right = got.left - 12
        room_for_name = min(T.font("bold", 26).size(self.label)[0] + 12, max(120, (right - x) // 2))
        shown = 0
        for tag in self.tags:
            w = T.font("text", 22).size(tag)[0] + 24
            if right - w < x + room_for_name:
                break
            box = pygame.Rect(right - w, r.centery - 18, w, 36)
            pygame.draw.rect(surf, T.TEXT if self.selected else T.LINE, box, 1, border_radius=18)
            T.draw_text(surf, tag, "text", 22, T.TEXT, box.center, "center")
            right = box.left - 8
            shown += 1
        if shown < len(self.tags):
            got = T.draw_text(surf, "+%d more" % (len(self.tags) - shown), "text", 22, T.DIM, (right, r.centery), "midright")
            right = got.left - 8
        T.draw_text(surf, self.label, "bold", 26, fg, (x, r.centery), "midleft", max_w=max(60, right - x))


def panel(surf, rect, heading=None):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, T.PANEL, r, border_radius=14)
    pygame.draw.rect(surf, T.LINE, r, 1, border_radius=14)
    if heading:
        T.draw_text(surf, heading, "text", 22, T.DIM, (r.x + 18, r.y + 10), max_w=r.w - 36)
    return r


def lines(surf, text, x, y, max_w, limit, colour=None, kind="text", size=22, pitch=28):
    """Wrapped words, at most 'limit' lines. Returns the y after the last one."""
    out = T.wrap_paragraphs(text, kind, size, max_w)
    if len(out) > limit:
        out = out[:limit]
        out[-1] = out[-1].rstrip(" .,") + "…"
    for line in out:
        if line:
            T.draw_text(surf, line, kind, size, colour or T.TEXT, (x, y), max_w=max_w)
        y += pitch
    return y


class NumberPad(Screen):
    """Tap in a whole number. on_done gets it as an int."""

    def __init__(self, app, title, on_done, hint="", low=0, high=999, left="D&D", negative=False,
                 skip=None, done_label="Done", start=""):
        super().__init__(app)
        self.left, self.title, self.on_done, self.hint = left, title, on_done, hint
        self.low, self.high, self.negative, self.skip, self.done_label = low, high, negative, skip, done_label
        self.text, self.minus = str(start), False

    def value(self):
        if not self.text:
            return None
        return -int(self.text) if self.minus else int(self.text)

    def build(self):
        out = []
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Delete", "0", "−" if self.negative else None]
        for k, key in enumerate(keys):
            if key is None:
                continue
            rect = (20 + (k % 3) * 126, 140 + (k // 3) * 66, 120, 64)
            if key == "Delete":
                out.append(Button(rect, key, self.delete, size=22))
            elif key == "−":
                out.append(Button(rect, "−", self.sign, selected=self.minus, size=30))
            else:
                out.append(Button(rect, key, lambda key=key: self.type(key), size=30))
        if self.skip:
            out.append(Button((412, 206, 368, 64), self.skip[0], self.skipped, size=22))
        out += [Button((412, 272, 368, 64), "Cancel", self.app.pop, size=22),
                Button((412, 338, 368, 64), self.done_label, self.done, "primary")]
        return out

    def type(self, digit):
        if len(self.text) < 4:
            self.text = (self.text + digit).lstrip("0") or "0"
            self.app.dirty = True

    def delete(self):
        self.text = self.text[:-1]
        self.app.dirty = True

    def sign(self):
        self.minus = not self.minus
        self.refresh()

    def skipped(self):
        self.app.pop()
        self.skip[1]()

    def done(self):
        v = self.value()
        if v is None:
            self.app.say("A number would help. I cannot do sums with silence.")
            return
        if not self.low <= v <= self.high:
            self.app.say("That should be between %d and %d." % (self.low, self.high))
            return
        self.app.pop()
        self.on_done(v)

    def on_key(self, event):                  # a real keyboard, on the desktop
        if event.key == pygame.K_RETURN:
            self.done()
        elif event.key == pygame.K_BACKSPACE:
            self.delete()
        elif event.unicode and event.unicode.isdigit():
            self.type(event.unicode)

    def draw_body(self, surf):
        box = pygame.Rect(20, 68, 372, 64)
        pygame.draw.rect(surf, T.PANEL, box, border_radius=12)
        pygame.draw.rect(surf, T.TEXT, box, 1, border_radius=12)
        shown = ("−" if self.minus else "") + self.text
        r = T.draw_text(surf, shown or " ", "head", 40, T.TEXT, (box.x + 18, box.centery), "midleft", max_w=320)
        x = r.right + 4 if shown else box.x + 18
        pygame.draw.rect(surf, T.TEXT, (x, box.y + 14, 3, 36))
        limit = 4 if self.skip else 6
        lines(surf, self.hint, 412, 72, 368, limit, T.DIM, pitch=30)

    def on_button(self, gesture):
        if gesture == "press":
            self.done()
