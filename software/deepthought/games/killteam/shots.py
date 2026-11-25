"""Kill Team screens for the screenshot run."""
from ...engine import Session
from ...screens.common import GameOver, Setup
from .plugin import Card, KTAdjust, KTDown, KTMenu, KTReveal, KTScore, KTSheet

NAMES = ["Ethan", "Trevor"]


def shots(app, snap):
    game = app.plugins["killteam"]

    def cards_away():
        while isinstance(app.screen, Card):
            app.pop()
        app.toast = None

    snap("kt-setup", Setup(app, game))

    # ---- a first game: Teach mode, two turning points, no Tac Ops
    s = Session(game, NAMES, {"mode": "Teach", "length": "Tutorial, 2 rounds", "tacops": "Off"})
    play = snap("kt-teach-first-step", game.play_screen(app, s))      # the first-game steps come up at once
    app.screen.next()
    snap("kt-teach-second-step")
    cards_away()
    snap("kt-operatives")
    play.do(ev="next")
    snap("kt-teach-strategy")
    cards_away()
    snap("kt-strategy")
    play.do(ev="init", side=0)
    snap("kt-strategy-said")                                           # with her line across the bottom
    app.toast = None
    snap("kt-strategy-initiative")
    play.do(ev="next")
    snap("kt-teach-activation")
    cards_away()
    snap("kt-firefight-teach")
    play.do(ev="did", what="shoot")
    snap("kt-teach-shooting")
    cards_away()
    play.do(ev="did", what="fight")
    snap("kt-teach-fighting")
    cards_away()
    for _ in range(11):
        play.do(ev="next")
        cards_away()
    snap("kt-firefight-last-activation")
    play.do(ev="next")
    snap("kt-teach-end-of-one")
    cards_away()
    snap("kt-end-turning-point-1")
    snap("kt-score-sheet-turning-point-1", KTSheet(app, s))

    # ---- a full game in Reminder mode
    s = Session(game, NAMES, {"mode": "Reminder", "length": "Full, 4 rounds", "tacops": "On"})
    play = snap("kt-operatives-reminder", game.play_screen(app, s))
    play.do(ev="tacop", side=0, text="a made-up name")                # typed on Ethan's phone; the box says only "chosen"
    snap("kt-operatives-tac-op-chosen-said")
    app.toast = None
    snap("kt-operatives-tac-op-chosen")
    for ev in ([dict(ev="ops", side=1, delta=1)] * 2 + [dict(ev="next"), dict(ev="init", side=0), dict(ev="next")]
               + [dict(ev="next")] * 3 + [dict(ev="down", side=1, ready=True), dict(ev="cp", side=0, delta=-1)]):
        play.do(**ev)
    app.toast = None
    snap("kt-firefight")
    play.tick(0.0)                                                     # the slow-play clock, with a made-up time
    play.tick(90.0)
    snap("kt-nudge-said")                                              # her one line when an activation runs long
    app.toast = None
    play.show_ring()
    snap("kt-menu", KTMenu(app, s))
    snap("kt-operative-down", KTDown(app, s))
    app.screen.do(ev="down", side=1, ready=False)
    snap("kt-operative-down-grade")
    app.toast = None
    play = snap("kt-firefight-after-kills", game.play_screen(app, s))
    for _ in range(40):                                                # until one side has nothing ready
        if s.state["out"] is None:
            play.do(ev="next")
    snap("kt-counteract-said")
    app.toast = None
    snap("kt-counteract")
    for _ in range(40):
        if s.state["phase"] == "firefight":
            play.do(ev="next")
    app.toast = None
    snap("kt-end-reminder")
    s.do(ev="score", side=0, cat="kill", delta=1)
    s.do(ev="next")
    s.do(ev="init", side=1)
    play = snap("kt-strategy-2", game.play_screen(app, s))
    s.do(ev="next")
    for _ in range(40):
        if s.state["phase"] == "firefight":
            s.do(ev="next")
    for side, cat, n in ((0, "crit", 3), (0, "tac", 2), (1, "crit", 2), (1, "tac", 2), (1, "kill", 1)):
        for _ in range(n):
            s.do(ev="score", side=side, cat=cat, delta=1)
    snap("kt-score-sheet", KTSheet(app, s))
    s.do(ev="next")
    s.do(ev="init", side=0)
    s.do(ev="next")
    s.do(ev="cp", side=1, delta=-2)
    snap("kt-scoreboard", KTScore(app, s))
    adj = snap("kt-correct-a-number", KTAdjust(app, s, 0, "crit"))
    adj.step(-1)
    snap("kt-correct-a-number-stepped")
    for _ in range(200):                                               # play on to the last End phase
        if s.state["tp"] == s.state["tp_max"] and s.state["phase"] == "end":
            break
        if s.state["phase"] == "strategy" and s.state["init"] is None:
            s.do(ev="init", side=s.state["tp"] % 2)
        s.do(ev="next")
    for side, cat, n in ((0, "crit", 2), (0, "kill", 2), (1, "crit", 3), (1, "tac", 1)):
        for _ in range(n):
            s.do(ev="score", side=side, cat=cat, delta=1)
    snap("kt-end-last", game.play_screen(app, s))
    snap("kt-score-sheet-last", KTSheet(app, s))
    snap("kt-primary-ops", KTReveal(app, s))                           # one Tac Op chosen, still secret
    s.do(ev="reveal", side="all")                                      # what Done on the last score sheet does
    snap("kt-primary-ops-tac-op-revealed", KTReveal(app, s))
    s.do(ev="primary", side=0, cat="crit")
    s.do(ev="primary", side=1, cat="tac")
    snap("kt-primary-ops-chosen", KTReveal(app, s))
    s.do(ev="next")
    snap("kt-game-over", GameOver(app, s))

    # ---- Silent mode: numbers only
    s = Session(game, NAMES, {"mode": "Silent", "length": "Full, 4 rounds", "tacops": "Off"})
    for ev in (dict(ev="next"), dict(ev="init", side=1), dict(ev="next"), dict(ev="next"), dict(ev="next")):
        s.do(**ev)
    snap("kt-silent", game.play_screen(app, s))
    snap("kt-scoreboard-no-tac-ops", KTScore(app, s))
