"""The screen that puts phones on the box: a code to scan and the address."""
import pygame
from .. import theme as T
from ..app import Screen
from ..widgets import row
from .common import BOTTOM_H, BOTTOM_Y

PAGES = [("/play", "My seat", "Your own buttons and reminders"), ("/", "Scoreboard", "For the screen at the end of the table"),
         ("/characters", "Characters", "Make or upload a D&D character"), ("/library", "Library", "Upload your own rulebooks"),
         ("/games", "Games", "Add a board game")]


def qr_matrix(text):
    """Rows of True/False for a QR code, or None if the qrcode package is missing."""
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(text)
    q.make()
    return q.get_matrix()


class PhoneLink(Screen):
    left, title = "Settings", "Phones"

    def __init__(self, app):
        super().__init__(app)
        self.i = 0

    def url(self):
        return self.app.web.url + PAGES[self.i][0]

    def locked(self):
        return bool(self.app.web.lock) and PAGES[self.i][0] != "/"

    def scan_url(self):
        """What the QR code holds: the address, with the table code so a scan needs no typing."""
        from .. import web
        return self.url() + ("?code=" + web.table_code() if self.locked() else "")

    def build(self):
        return row([("Back", self.app.pop, 0.8, "plain"), ("New code", self.new_code, 1.1, "plain"),
                    ("Free the seats", self.free_seats, 1.5, "plain"),
                    ("Next: %s" % PAGES[(self.i + 1) % len(PAGES)][1], self.next, 1.9, "primary")],
                   BOTTOM_Y, BOTTOM_H)

    def free_seats(self):
        """One phone holds each seat. This lets every seat be chosen afresh: for a
        phone that was swapped, or a seat somebody took by mistake."""
        from .common import Choice
        def free():
            self.app.web.free_seats()
            self.app.say("Every seat is free. Each phone chooses its seat again under My seat.")
        self.app.push(Choice(self.app, "Free the seats?", "Let every seat be chosen again?\nEach phone will have to "
                             "pick its seat once more under My seat.", [("Leave them", None), ("Free the seats", free)]))

    def new_code(self):
        from .. import web
        from .common import Choice
        def change():
            web.new_table_code()
            self.app.say("New table code. Every phone must enter it again.")
        self.app.push(Choice(self.app, "New code?", "Make a new table code?\nEvery phone will have to enter it again.",
                             [("Keep it", None), ("New code", change)]))

    def next(self):
        self.i = (self.i + 1) % len(PAGES)
        self.refresh()

    def draw_body(self, surf):
        matrix = qr_matrix(self.scan_url())
        x_text = 40
        if matrix:
            n = len(matrix)
            cell = 296 // n
            side = cell * n
            x0, y0 = 30, 76 + (296 - side) // 2
            pygame.draw.rect(surf, (255, 255, 255), (x0, y0, side, side))
            for r, line in enumerate(matrix):
                for c, on in enumerate(line):
                    if on:
                        pygame.draw.rect(surf, (0, 0, 0), (x0 + c * cell, y0 + r * cell, cell, cell))
            x_text = x0 + side + 28
        room = T.W - x_text - 20
        T.draw_text(surf, PAGES[self.i][1], "head", 40, T.TEXT, (x_text, 96), max_w=room)
        y = 150
        for line in T.wrap(PAGES[self.i][2], "text", 24, room):
            T.draw_text(surf, line, "text", 24, T.DIM, (x_text, y))
            y += 32
        hint = "Point a phone camera at the code, or type:" if matrix else "On a phone on the same Wi-Fi, type:"
        for line in T.wrap(hint, "text", 22, room):
            T.draw_text(surf, line, "text", 22, T.DIM, (x_text, y + 14))
            y += 28
        T.draw_text(surf, self.url().replace("http://", ""), "bold", 26, T.TEXT, (x_text, y + 26), max_w=room)
        if self.locked():
            from .. import web
            T.draw_text(surf, "Table code  " + " ".join(web.table_code()), "bold", 26, T.TEXT, (x_text, y + 66), max_w=room)
        elif self.app.web.lock:
            T.draw_text(surf, "No code needed", "text", 22, T.DIM, (x_text, y + 66), max_w=room)

    def on_button(self, gesture):
        if gesture == "press":
            self.next()
        elif gesture == "double":
            self.app.pop()
