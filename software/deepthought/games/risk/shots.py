"""Risk screens for the screenshot run."""
import random
from ...engine import Session
from ...screens.common import GameOver, Setup
from .plugin import RiskBattle, RiskMap


def shots(app, snap):
    game = app.plugins["risk"]
    snap("risk-setup", Setup(app, game))
    s = Session(game, ["Ethan", "Trevor", "Sam", "Priya"], {"hints": "On"})
    play = snap("risk-reinforce", game.play_screen(app, s))
    s.do(ev="cont", player=0, name="Australia")
    s.do(ev="card", delta=3)
    play.do(ev="trade")
    snap("risk-trade")
    app.toast = None
    play.do(ev="next")
    snap("risk-attack")
    snap("risk-map", RiskMap(app, s))
    battle = snap("risk-battle", RiskBattle(app, s, random.Random(5)))
    battle.roll()
    snap("risk-battle-rolled")
    s.do(ev="capture", defender=1)
    s.do(ev="next")
    snap("risk-fortify", game.play_screen(app, s))
    s.finish()
    snap("risk-game-over", GameOver(app, s))
