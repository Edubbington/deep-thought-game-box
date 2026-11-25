"""Warhammer 40,000 screens for the screenshot run."""
from ...engine import Session
from ...screens.common import GameOver, Pages, Setup, TextEntry
from .plugin import W40kArmy, W40kArmyEdit, W40kCommand, W40kMenu, W40kRef, W40kScore, W40kSecPick


def shots(app, snap):
    game = app.plugins["wh40k"]

    def clear():
        app.toast = None

    def nexts(s, n):
        for _ in range(n):
            s.do(ev="next")

    snap("wh40k-setup", Setup(app, game))
    snap("wh40k-how-to-play", Pages(app, game.name, "How to play", [(x["title"], x["text"]) for x in game.teach()]))

    # ---- Teach mode, a tutorial game
    t = Session(game, ["Ethan", "Trevor"], {"mode": "Teach", "length": "Tutorial, 3 rounds", "necrons": "Player 1"})
    play = snap("wh40k-teach-intro", game.play_screen(app, t))       # the first-game steps come up by themselves
    app.pop()
    snap("wh40k-teach-command")
    play.do(ev="next")
    snap("wh40k-teach-card-movement")
    app.pop()
    snap("wh40k-teach-movement")
    play.do(ev="did", what="advance")
    snap("wh40k-teach-card-advance")
    app.pop()
    play.do(ev="next")
    app.pop()
    play.do(ev="next")
    app.pop()
    clear()
    snap("wh40k-teach-charge")

    # ---- Reminder mode, a full game in its second battle round
    s = Session(game, ["Ethan", "Trevor"], {"mode": "Reminder", "length": "Full, 5 rounds", "necrons": "Player 1"})
    for size in (10, 5, 5, 1, 3):
        s.do(ev="army", side=1, op="add", size=size)
    play = snap("wh40k-play-first-turn", game.play_screen(app, s))
    nexts(s, 10)                                                      # both turns of round 1
    for _ in range(10):
        s.do(ev="score", side=0, cat="primary", delta=1)
    s.do(ev="sec", side=0, op="name", slot=0, name="Assassination")
    for _ in range(4):
        s.do(ev="score", side=0, cat="sec", row=0, delta=1)
    s.do(ev="sec", side=0, op="name", slot=0, name="Behind Enemy Lines")   # the scored one is put away
    s.do(ev="sec", side=0, op="name", slot=1, name="Cleanse", cap=5)
    s.do(ev="score", side=0, cat="sec", row=1, delta=1)
    s.do(ev="sec", side=1, op="name", slot=1, name="Storm Hostile Objective")
    for _ in range(3):
        s.do(ev="score", side=1, cat="sec", row=1, delta=1)
    s.do(ev="cp", side=0, delta=-1)
    for _ in range(11):
        s.do(ev="model", side=0, unit=0, delta=-1)                    # Warriors: 9 of 20, below half
    s.do(ev="model", side=0, unit=5, delta=-1)                        # Doomstalker: below half its wounds
    for _ in range(5):
        s.do(ev="model", side=0, unit=3, delta=-1)                    # Lychguard: destroyed
    s.do(ev="shock", side=0, unit=0)
    for _ in range(3):
        s.do(ev="model", side=1, unit=1, delta=-1)
    play.do(ev="next")
    clear()
    play.do(ev="next")
    clear()
    snap("wh40k-play-shooting")
    play.tick(0.0)                                                    # the slow-play clock, with a made-up time
    play.tick(240.0)
    snap("wh40k-nudge-said")                                          # her one line when a phase runs long
    clear()
    play.show_ring()
    snap("wh40k-score", W40kScore(app, s))
    pick = snap("wh40k-secondary-pick", W40kSecPick(app, s, 1, 0))    # an unnamed row
    pick.more_names()
    snap("wh40k-secondary-pick-page-2")
    snap("wh40k-secondary-pick-change", W40kSecPick(app, s, 0, 1))    # a named row that has scored
    snap("wh40k-secondary-type", TextEntry(app, "Secondary name", "hold the bridge", None, "Done", max_len=24))
    snap("wh40k-menu", W40kMenu(app, s))
    snap("wh40k-command-points", W40kCommand(app, s))
    army = snap("wh40k-army", W40kArmy(app, s, 0))
    army.more_units()
    snap("wh40k-army-page-2")
    snap("wh40k-army-other-side", W40kArmy(app, s, 1))
    snap("wh40k-army-edit", W40kArmyEdit(app, s, 1))
    ref = snap("wh40k-ref-phases", W40kRef(app, s, 0))
    ref.turn(1)
    snap("wh40k-ref-sequence")
    ref.turn(1)
    snap("wh40k-ref-wound")
    nexts(s, 3)                                                       # Trevor's Command phase, round 2
    for _ in range(5):
        s.do(ev="score", side=1, cat="primary", delta=1)
    snap("wh40k-play-command-scoring", game.play_screen(app, s))
    nexts(s, 5)                                                       # Ethan's Command phase, round 3
    for _ in range(8):
        s.do(ev="cp", side=1, delta=1)
    snap("wh40k-play-command-shock", game.play_screen(app, s))
    nexts(s, 4)
    snap("wh40k-play-fight", game.play_screen(app, s))
    nexts(s, 26)                                                      # through round 5 to the final scores
    snap("wh40k-play-final-scores", game.play_screen(app, s))

    # ---- Silent mode: numbers only
    q = Session(game, ["Ethan", "Trevor"], {"mode": "Silent", "length": "Tutorial, 3 rounds", "necrons": "Nobody"})
    snap("wh40k-army-empty", W40kArmy(app, q, 0))
    nexts(q, 12)
    for _ in range(7):
        q.do(ev="score", side=0, cat="primary", delta=1)
    for _ in range(9):
        q.do(ev="score", side=1, cat="sec", row=0, delta=1)
    snap("wh40k-silent", game.play_screen(app, q))
    nexts(q, 18)                                                      # to the end of round 3
    snap("wh40k-final-scores", game.play_screen(app, q))
    q.do(ev="next")
    snap("wh40k-game-over", GameOver(app, q))
    clear()
