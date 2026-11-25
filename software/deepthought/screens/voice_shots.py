"""Answer card and phone-link screens for the screenshot run."""
from .common import Pages
from .web_link import PhoneLink


class _FakeWeb:
    url = "http://192.168.1.50:8080"
    lock = True

    def free_seats(self):
        pass


def shots(app, snap):
    snap("answer", Pages(app, "You asked", "Deep Thought", [(
        "How many armies do I get?",
        "Count your territories and divide by three, dropping the remainder. You never get fewer than three. "
        "Whole continents add more. I have done the sum for you on the main screen, as it happens."
        "\n\nSource: Deep Thought's notes: how to play, New armies")]))
    real, app.web = app.web, app.web or _FakeWeb()
    link = snap("phones", PhoneLink(app))
    link.free_seats()
    snap("phones-free-the-seats")
    app.pop()
    app.web = real
