"""Tests for rules every screen and game relies on: which screen a double press
belongs to, and when reminders are said."""
import os, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import engine, hw, theme as T
from deepthought.app import App, Screen
from deepthought.games import load_games
from deepthought.screens import common, extras
from deepthought.screens.home import Home

fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

games, _ = load_games()
app = App(hw.make("desktop", sound=False), games, headless=True)
app.push(Home(app))
stops = []
app.hw.stop_sound = lambda: stops.append(1)


class Count(engine.Game):
    """Two players. Each press adds one and passes the turn."""
    id, name = "count", "Count"
    def new_state(self, players, options): return {"n": 0, "active": 0, "phase": "go"}
    def apply(self, state, ev):
        if ev["ev"] == "end":
            state["done"] = True
            return []
        state["n"] += ev.get("by", 1)
        state["active"] = 1 - state["active"]
        return []
    def over(self, state): return {"winner_index": 0, "lines": []} if state.get("done") else None
    def play_screen(self, app, session): return common.PlayBase(app, session)

def start():
    app.go_home()
    app.session = engine.Session(Count(), ["Ann", "Bob"], {}, os.path.join(DATA, "sessions"))
    play = Count().play_screen(app, app.session)
    app.push(play)
    return app.session, play

def double():                       # what the hardware sends: always a press first
    app.gesture("press"); app.gesture("double")

# ---------------------------------------------------------------- a double press belongs to the screen that was pressed
s, play = start()
for _ in range(4): app.gesture("press")
double()
check("on the play screen a double press takes its own press back and undoes one more", s.state["n"] == 3 and len(s.log) == 3, s.state)

play.do(ev="next"); play.do(ev="next")                    # two taps, n = 5
app.push(extras.GameMenu(app, s))
double()                                                  # the press closes the menu
check("a double press on the More menu closes it and undoes nothing in the game", app.screen is play and s.state["n"] == 5, s.state)

app.push(common.Pages(app, "x", "A card", [("One page", "text")], auto=True))
double()                                                  # the press is Got it
check("a double press on a one-page card puts it away and leaves the game alone", app.screen is play and s.state["n"] == 5, s.state)

app.push(common.Pages(app, "x", "A card", [("One", "a"), ("Two", "b"), ("Three", "c")]))
double()                                                  # press: next page. double: close
check("a double press on a longer card closes the card, and nothing else", app.screen is play and s.state["n"] == 5)

class Opens(common.PlayBase):
    """A play screen whose press brings a card up, as teach-as-we-play does."""
    def do(self, **ev):
        got = super().do(**ev)
        self.app.push(common.Pages(self.app, "x", "Teach", [("Step", "text")], auto=True))
        return got
app.go_home(); opener = Opens(app, s); app.push(opener)
stops.clear()
double()
check("when the press brings a card up, the double puts the card away and takes that press back, plus one more",
      app.screen is opener and s.state["n"] == 4 and len(s.log) == 4, (type(app.screen).__name__, s.state))
check("and the card stops being read out", stops == [1], stops)

s, play = start()
app.gesture("press")
play.do(ev="end")                                         # a tap ends the game: Game over is showing
check("Game over is showing", isinstance(app.screen, common.GameOver))
s, play = start()
app.gesture("press"); app.gesture("press")
play.game.press = lambda state: {"ev": "end"}
double()                                                  # the press ends the game; the double takes it back
check("a double press whose press ended the game takes that press back, and only that",
      isinstance(app.screen, common.PlayBase) and app.session is s and not s.finished and s.state["n"] == 2, type(app.screen).__name__)

app.go_home()
app.gesture("press")                                      # Home: press opens Pick a game
top = app.screen
app.gesture("double")
check("a double press after a press on Home just undoes the press: back on Home", app.screen is app.stack[0] and top is not app.screen)

# a teach card that a double press put away unread is given again
from deepthought import guide
risk = app.plugins["risk"]
app.go_home()
app.start_game(risk, ["Ann", "Bob"], {"guide": "As we play"})
while isinstance(app.screen, common.Pages):
    app.screen.close()
s = app.session
check("Risk with Teach on is waiting to teach attacking", guide.waiting_for(s)["title"] == "Attacking")
double()                                                  # the press goes into Attack and raises the card
check("the double took the press back and put the card away", isinstance(app.screen, common.PlayBase) and s.state["phase"] == "reinforce" and len(s.log) == 0, s.state["phase"])
check("and the lesson is still owed", guide.waiting_for(s)["title"] == "Attacking")
app.gesture("press")
check("so pressing again brings the Attacking card", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "Attacking")
app.screen.close(); app.gesture("press")
play = app.screen
if isinstance(play, common.Pages): play.close(); play = app.screen
play.undo(quiet=True); play.undo(quiet=True); app.gesture("press")
check("a card that was read is not given twice after an ordinary undo", not isinstance(app.screen, common.Pages) or app.screen.pages[0][0] != "Attacking")
while isinstance(app.screen, common.Pages):
    app.screen.close()
app.session.finish(); app.session = None; app.go_home()

# ---------------------------------------------------------------- reminders
class Shared(Count):
    """Phases belong to both players, who alternate inside them (as in Kill Team)."""
    id, name, remind_each_turn = "shared", "Shared", False
    def new_state(self, players, options): return {"active": None, "phase": "plan", "n": 0}
    def apply(self, state, ev):
        if ev["ev"] == "phase":
            state["phase"] = ev["to"]; state["active"] = None if ev["to"] == "plan" else 0
        else:
            state["active"] = 1 - state["active"]
        return []
    def phases(self): return [("plan", "Plan"), ("fight", "Fight")]

r = engine.Session(Shared(), ["Ann", "Bob"], {}, None)
r.add_reminder(1, "plan", "Bob plans")
r.add_reminder(0, "fight", "Ann fights")
r.add_reminder(None, "fight", "All fight")
said = r.do(ev="phase", to="fight")
check("a phase that both players share says every player's reminder for it, with the name",
      said == ["Reminder for Ann: Ann fights", "Reminder: All fight"], said)
again = [r.do(ev="next") for _ in range(6)]
check("and does not say it again each time the players alternate", again == [[]] * 6, again)
said = r.do(ev="phase", to="plan")
check("a reminder for a phase with nobody's name on it is still said to the player it is for", said == ["Reminder for Bob: Bob plans"], said)

t = engine.Session(Count(), ["Ann", "Bob"], {}, None)
t.add_reminder(1, "go", "Bob draws")
t.d["reminders"].append({"player": 7, "phase": "go"})    # a damaged entry
out = [t.do(ev="next") for _ in range(4)]
check("in a game of turns, a player's reminder is said each time their turn comes, and only then",
      out == [["Reminder for Bob: Bob draws"], [], ["Reminder for Bob: Bob draws"], []], out)

# ---------------------------------------------------------------- the strip
class Long(Screen):
    left, title = "Warhammer 40,000", "Battle round 3 of 5"
    pill = ("Wwwwwwwwwwwwww's turn", T.PLAYERS[0])
app.go_home(); app.push(Long(app)); app.render()
title_right = T.W // 2 + min(280, T.font("head", 24).size(Long.title)[0]) // 2
pill_w = T.font("bold", 22).size(T.fit(Long.pill[0], "bold", 22, 230)[0])[0] + 28
check("a fourteen-letter name in the turn pill does not run into the title", T.W - 20 - pill_w >= title_right, (T.W - 20 - pill_w, title_right))

# ---------------------------------------------------------------- found in the second review
import contextlib, io
import pygame

# a double press over Game over
s, play = start()
app.gesture("press"); app.gesture("press")
play.game.press = lambda state: {"ev": "end"}
app.gesture("press")                                      # this press ends the game
over = app.screen
check("Game over remembers which screen's press ended the game", isinstance(over, common.GameOver) and over.press_from is play)
app.push(common.Pages(app, "You asked", "Deep Thought", [("A question", "An answer.")]))   # as a spoken answer arrives
double()                                                  # the press puts the answer away
check("a double press that puts away an answer lying over Game over leaves the finished game alone",
      app.screen is over and bool(s.finished) and app.session is None, (type(app.screen).__name__, s.finished))
app.push(common.TextEntry(app, "Ask", "", lambda text: None, "Ask"))
double()                                                  # the press is Ask, and closes the typing screen
check("and so does one on the typing screen over Game over", app.screen is over and bool(s.finished), type(app.screen).__name__)
s, play = start()
play.do(ev="end")                                         # ended by a tap, not by the button
over = app.screen
app.push(common.Pages(app, "You asked", "Deep Thought", [("A question", "An answer.")]))
double()
check("the same when the game was ended by a tap", app.screen is over and bool(s.finished) and over.press_from is None)

# a phone's event between a press and its double
s, play = start()
app.gesture("press")                                      # the button: n = 1
app.game_event({"ev": "next", "by": 10})                  # a phone, before the second press lands: n = 11
app.gesture("double")
check("an event from a phone between a press and its double: the double undoes nothing, and she says so",
      s.state["n"] == 11 and len(s.log) == 2 and app.toast == "Something else happened in between; nothing undone.", (s.state, app.toast))
app.toast = None
app.gesture("press"); app.gesture("double")
check("and the next press and double work as ever: that press is taken back, and one more undone",
      s.state["n"] == 1 and len(s.log) == 1 and app.toast == "Undone.", (s.state, app.toast))
s, play = start()
app.gesture("press"); s.do(ev="next", by=10); app.gesture("double")
check("the same when another screen logged something in between", s.state["n"] == 11 and len(s.log) == 2 and "nothing undone" in app.toast, s.state)
s, play = start()
app.gesture("press"); app.push(extras.GameMenu(app, s)); app.pop(); app.gesture("press"); app.gesture("double")
check("a press made long before does not count as 'in between': only the last press is looked at", s.state["n"] == 0 and len(s.log) == 0, s.state)
s, play = start()
for _ in range(3): app.gesture("press")
double()
check("with nothing in between, a double press still takes its press back and undoes one more", s.state["n"] == 2 and len(s.log) == 2, s.state)

# one failing job does not lose the others
app.go_home(); app.toast = None
ran = []
app.later(lambda: 1 / 0); app.later(lambda: ran.append("second"))
app.window, real_flip, pygame.display.flip = pygame.Surface((T.W, T.H)), pygame.display.flip, lambda: None
app.hw.gestures = lambda t: []
with contextlib.redirect_stdout(io.StringIO()):
    try: app.frame(1.0)
    except ZeroDivisionError: app.trouble(1.0)
left = len(app._jobs)
app.frame(2.0)
check("a job that fails does not take the jobs queued behind it with it", left == 1 and ran == ["second"], (left, ran))
pygame.display.flip = real_flip; del app.hw.gestures; app._troubles = []; app.toast = None

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
