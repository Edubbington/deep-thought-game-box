"""Magic screens for the screenshot run."""
from ...engine import Session
from ...screens.common import GameOver, Pages, Setup
from ...screens.lookup import Lookup
from .plugin import MtgCounters, MtgPlayer


def shots(app, snap):
    game = app.plugins["mtg"]
    snap("mtg-setup", Setup(app, game))
    snap("mtg-how-to-play", Pages(app, game.name, "How to play", [(x["title"], x["text"]) for x in game.teach()]))

    # two players, 20 life, every step, hints on
    s = Session(game, ["Ethan", "Trevor"], {"format": "Standard 20 life", "steps": "Every step", "hints": "On"})
    snap("mtg-life-2-start", game.play_screen(app, s))
    for _ in range(6):
        s.do(ev="next")
    s.do(ev="life", player=1, delta=-6)
    s.do(ev="poison", player=1, delta=2)
    snap("mtg-life-2", game.play_screen(app, s))
    s.do(ev="life", player=1, delta=-13)
    s.do(ev="poison", player=0, delta=9)
    s.do(ev="monarch", player=0)
    snap("mtg-life-2-warnings", game.play_screen(app, s))
    snap("mtg-player-standard", MtgPlayer(app, s, 1))
    snap("mtg-counters-2", MtgCounters(app, s))
    play = snap("mtg-life-2-ask", game.play_screen(app, s))
    play.change(ev="life", player=1, delta=-1)
    snap("mtg-game-over-ask")

    # two players, hints off: the mockup's sizes
    s = Session(game, ["Ethan", "Trevor"], {"format": "Standard 20 life", "steps": "Every step", "hints": "Off"})
    for _ in range(6):
        s.do(ev="next")
    s.do(ev="life", player=1, delta=-6)
    s.do(ev="poison", player=1, delta=2)
    snap("mtg-life-2-no-hints", game.play_screen(app, s))

    # two players, Commander
    s = Session(game, ["Ethan", "Trevor"], {"format": "Commander 40 life", "steps": "Whole turn", "hints": "Off"})
    s.do(ev="cmd", player=1, source=0, delta=9)
    s.do(ev="poison", player=1, delta=3)
    s.do(ev="monarch", player=1)
    snap("mtg-life-2-commander", game.play_screen(app, s))

    # three players
    s = Session(game, ["Ethan", "Trevor", "Sam"], {"format": "Commander 40 life", "steps": "Every step", "hints": "On"})
    s.do(ev="next")
    s.do(ev="cmd", player=2, source=0, delta=5)
    s.do(ev="life", player=1, delta=65)
    snap("mtg-life-3", game.play_screen(app, s))
    snap("mtg-player-3", MtgPlayer(app, s, 2))

    # four players, Commander, whole turns
    s = Session(game, ["Ethan", "Trevor", "Sam", "Jo"],
                {"format": "Commander 40 life", "steps": "Whole turn", "hints": "Off"})
    s.do(ev="next")
    s.do(ev="next")
    s.do(ev="cmd", player=0, source=1, delta=6)
    s.do(ev="cmd", player=1, source=0, delta=10)
    s.do(ev="cmd", player=1, source=2, delta=3)
    s.do(ev="monarch", player=2)
    s.do(ev="life", player=3, delta=-21)
    s.do(ev="poison", player=3, delta=3)
    snap("mtg-life-4", game.play_screen(app, s))
    s.do(ev="cmd", player=1, source=0, delta=4)
    snap("mtg-commander-damage", MtgPlayer(app, s, 1))
    snap("mtg-counters-4", MtgCounters(app, s))

    # one step from each knockout, then a player out
    s.do(ev="cmd", player=1, source=0, delta=6)
    s.do(ev="poison", player=3, delta=6)
    s.do(ev="life", player=0, delta=-33)
    snap("mtg-life-4-warnings", game.play_screen(app, s))
    snap("mtg-commander-damage-warning", MtgPlayer(app, s, 1))
    snap("mtg-counters-4-warning", MtgCounters(app, s))
    s.do(ev="poison", player=3, delta=1)
    s.do(ev="cmd", player=1, source=0, delta=1)
    snap("mtg-life-4-out", game.play_screen(app, s))
    snap("mtg-player-out", MtgPlayer(app, s, 1))
    snap("mtg-counters-4-out", MtgCounters(app, s))
    four = s

    # every step, hints on, four players
    s = Session(game, ["Ethan", "Trevor", "Sam", "Jo"],
                {"format": "Commander 40 life", "steps": "Every step", "hints": "On"})
    for _ in range(5):
        s.do(ev="next")
    s.do(ev="life", player=2, delta=-8)
    snap("mtg-life-4-steps", game.play_screen(app, s))

    # card lookup: the shared Lookup screen, opened on Magic
    look = snap("mtg-lookup", Lookup(app, "mtg"))
    look.run("bear")
    snap("mtg-lookup-results")

    four.do(ev="life", player=0, delta=-1)
    snap("mtg-game-over", GameOver(app, four))
