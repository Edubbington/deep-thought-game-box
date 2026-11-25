"""Colours, fonts and text drawing. Values are the ones in CLAUDE.md."""
import os
import pygame

W, H, STRIP = 800, 480, 60
GROUND, PANEL, RAISED, LINE = (0x0B, 0x0F, 0x14), (0x15, 0x1C, 0x26), (0x1D, 0x26, 0x33), (0x2F, 0x3B, 0x4D)
TEXT, DIM = (0xEA, 0xF0, 0xF6), (0xA9, 0xB8, 0xCA)
PLAYERS = [(0x6C, 0xB6, 0xFF), (0xFF, 0xA6, 0x4D), (0x8F, 0xE3, 0xA0), (0xF2, 0x9B, 0xD4),
           (0xFF, 0xE0, 0x66), (0xB9, 0xA3, 0xFF)]       # five and six added for bigger tables
WARN = (0xFF, 0xA6, 0x4D)


def player_colour(i):
    return PLAYERS[i % len(PLAYERS)]


def wrap_paragraphs(text, kind, size, max_w):
    """Wrap text that has its own line breaks. Blank lines are kept as gaps."""
    out = []
    for para in text.split("\n"):
        out += wrap(para, kind, size, max_w) or [""]
    while out and not out[-1]:
        out.pop()
    return out
MIN_TEXT, MIN_BUTTON = 22, 64

_FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
_FILES = {"head": "space-grotesk-700.ttf", "head5": "space-grotesk-500.ttf",
          "text": "inter-400.ttf", "mid": "inter-500.ttf", "bold": "inter-600.ttf"}
_fonts, _renders = {}, {}
FIT_MAX = 300           # letters looked at when one line is fitted to a width


def safe(text):
    """Text that can always be measured and drawn. A NUL, an escape or half of
    a broken character makes the font refuse the whole line, and one typed
    name must never stop a screen: such characters are left out (a tab or a
    line break becomes a space)."""
    text = text if isinstance(text, str) else str(text)
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else (" " if ch.isspace() else "") for ch in text)


class _Font:
    """A pygame font that measures and draws only safe() text."""

    def __init__(self, f):
        self._f = f

    def size(self, text):
        return self._f.size(safe(text))

    def render(self, text, *a, **k):
        return self._f.render(safe(text), *a, **k)

    def __getattr__(self, name):
        return getattr(self._f, name)


def font(kind, size):
    size = max(MIN_TEXT, int(size))          # nothing under 22 px, ever
    key = (kind, size)
    if key not in _fonts:
        _fonts[key] = _Font(pygame.font.Font(os.path.join(_FONT_DIR, _FILES[kind]), size))
    return _fonts[key]


def fit(text, kind, size, max_w):
    """Shrink towards 22 px until the text fits; then cut it with an ellipsis.
    Returns (text, size)."""
    size = max(MIN_TEXT, int(size))
    text = safe(text)
    if len(text) > FIT_MAX:                  # one line never holds more; cutting a letter at a time from
        text = text[:FIT_MAX]                # a whole page of text would hold the screen up
    while size > MIN_TEXT and font(kind, size).size(text)[0] > max_w:
        size = max(MIN_TEXT, size - 2)
    f = font(kind, size)
    if f.size(text)[0] > max_w:
        while len(text) > 1 and f.size(text + "…")[0] > max_w:
            text = text[:-1]
        text = text.rstrip() + "…"
    return text, size


def render(text, kind, size, colour):
    text = safe(text) or " "                 # the font will not draw nothing at all
    key = (text, kind, size, colour)
    if key not in _renders:
        if len(_renders) > 400:              # a Pi 2 has little memory to spare
            _renders.clear()
        _renders[key] = font(kind, size).render(text, True, colour)
    return _renders[key]


def draw_text(surf, text, kind, size, colour, pos, anchor="topleft", max_w=None):
    if max_w is not None:
        text, size = fit(text, kind, size, max_w)
    img = render(text, kind, size, colour)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def wrap(text, kind, size, max_w):
    f, lines, cur = font(kind, size), [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and f.size(trial)[0] > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])
