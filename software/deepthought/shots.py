"""Draw each screen to a PNG, without a window. Used to show the screens
and by the tests. Each part of the program adds its own screens here."""
import importlib
import os
import random

# Modules that have a shots(app, snap) function. A missing module is skipped.
PARTS = ["deepthought.games.risk.shots", "deepthought.games.mtg.shots", "deepthought.games.killteam.shots",
         "deepthought.games.wh40k.shots", "deepthought.games.dnd.shots", "deepthought.screens.voice_shots"]


def all_shots(app, folder):
    from .screens.common import Choice, Pages, Setup, TextEntry
    from .screens.dice import dice_shots
    from .screens.extras import GameMenu, Reminders, Settings, Spinner
    from .screens.home import Home
    from .screens.lookup import Lookup
    from .screens.pick_game import PickGame
    os.makedirs(folder, exist_ok=True)
    out = []

    def snap(name, screen=None):
        """Show a screen (or re-draw the current one) and save it."""
        if screen is not None:
            app.stack = [app.stack[0]] if app.stack else []
            app.toast = None
            app.push(screen)
        out.append(app.shot(os.path.join(folder, name + ".png")))
        return screen

    app.stack = []
    app.push(Home(app))
    snap("home")
    pick = snap("pick-game-1", PickGame(app))
    if pick.pages() > 1:
        pick.more()
        snap("pick-game-2")
    dice_shots(app, snap)
    snap("type", TextEntry(app, "Search", "continent"))
    look = snap("lookup-empty", Lookup(app))
    look.run("continent")
    snap("lookup-results")
    if look.results:
        look.open(look.results[0])
        out.append(app.shot(os.path.join(folder, "lookup-entry.png")))
    snap("settings", Settings(app))
    snap("shut-down", Choice(app, "Shut down?", "Shut Deep Thought down safely?\nWait for the ring to go dark "
                             "before switching the power off.", [("Stay on", None), ("Shut down", None)]))
    tally = app.plugins.get("tally")
    if tally:
        from .engine import Session
        snap("setup", Setup(app, tally))
        s = Session(tally, ["Ethan", "Trevor", "Sam"], {})
        play = snap("any-game", tally.play_screen(app, s))
        for i in (0, 0, 1, 2, 2, 2):
            play.bump(i)
        app.toast = None
        snap("any-game-scores")
        s.add_reminder(0, "*", "Draw a card before you roll")
        snap("game-menu", GameMenu(app, s))
        snap("reminders", Reminders(app, s))
        snap("spinner", Spinner(app, s.players, random.Random(2)))
        snap("how-to-play", Pages(app, tally.name, "How to play", [(x["title"], x["text"]) for x in tally.teach()]))
    risk = app.plugins.get("risk")
    if risk:
        snap("setup-teach", Setup(app, risk))
        steps = [(x["title"], x["text"]) for x in risk.teach()]
        snap("teach-card", Pages(app, risk.name, "Teach", steps[:4], auto=True))
        snap("teach-card-one", Pages(app, risk.name, "Teach", steps[7:8], auto=True))
    for name in PARTS:
        try:
            mod = importlib.import_module(name)
        except ImportError as e:
            if name.split(".")[-2] not in str(e) and name.split(".")[-1] not in str(e):
                raise                           # a real bug inside the module, not a missing one
            continue
        mod.shots(app, snap)
    app.stack = app.stack[:1]
    return out
