"""Tests for the session engine, Risk, the generic board-game plugin, the
library and Lookup, and the screens that go with them."""
import contextlib, io, json, os, random, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dt_content
from deepthought import engine, paths, theme as T
from deepthought.games import load_games
from deepthought.games.generic import GenericGame
from deepthought.games.risk import rules

fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

games, problems = load_games()
plugins = {g["id"]: g["plugin"] for g in games if g["plugin"]}
risk = plugins["risk"]

# ---------------------------------------------------------------- Risk sums
check("start territories: 3 players 14 each", rules.start_territories(3) == ([14, 14, 14], 0))
check("start territories: 4 players 11, 11, 10, 10", rules.start_territories(4) == ([11, 11, 10, 10], 0))
check("start territories: 5 players 9, 9, 8, 8, 8", rules.start_territories(5) == ([9, 9, 8, 8, 8], 0))
check("start territories: 6 players 7 each", rules.start_territories(6) == ([7] * 6, 0))
check("start territories: 2 players 14 each and 14 neutral", rules.start_territories(2) == ([14, 14], 14))
check("continents: 42 territories, bonuses 7 5 5 3 2 2", sum(rules.SIZE.values()) == 42 and sorted(rules.BONUS.values()) == [2, 2, 3, 5, 5, 7])
check("card sets: 4, 6, 8, 10, 12, 15, 20, 25, 30", [rules.set_value(i) for i in range(9)] == [4, 6, 8, 10, 12, 15, 20, 25, 30])
R = lambda *a, **k: rules.reinforcements(*a, **k)[0]
check("armies: 11 territories give 3", R(11) == 3)
check("armies: 8 territories still give the minimum 3", R(8) == 3 and R(1) == 3)
check("armies: 12 give 4, 14 give 4, 15 give 5", (R(12), R(14), R(15)) == (4, 4, 5))
check("armies: 20 territories with Asia and Australia: 6 + 7 + 2 = 15", R(20, ["Asia", "Australia"]) == 15)
check("armies: cards add on top: 3 + 2 + 8 = 13", R(9, ["South America"], 8) == 13)
check("armies: the working is shown", "14 territories ÷ 3 = 4" in rules.reinforcements(14, ["Africa"])[1] and "Africa +3" in rules.reinforcements(14, ["Africa"])[1])

class Fixed:
    def __init__(self, rolls): self.rolls = list(rolls)
    def randint(self, a, b): return self.rolls.pop(0)
B = lambda a, d, rolls: rules.battle(a, d, Fixed(rolls))
check("battle: 6 5 1 against 5 5: attacker wins the first, ties lose the second", B(3, 2, [1, 6, 5, 5, 5]) == ([6, 5, 1], [5, 5], 1, 1))
check("battle: 6 6 2 against 5 4: defender loses two", B(3, 2, [6, 2, 6, 4, 5])[2:] == (0, 2))
check("battle: 3 2 against 3 3: attacker loses two", B(2, 2, [3, 2, 3, 3])[2:] == (2, 0))
check("battle: one die each, a tie goes to the defender", B(1, 1, [4, 4])[2:] == (1, 0))
check("battle: three dice against one: only one army is at stake", B(3, 1, [2, 5, 1, 4])[2:] == (0, 1))
def bad(fn):
    try: fn()
    except ValueError: return True
    return False
check("battle: no four attack dice, no three defence dice", bad(lambda: rules.battle(4, 1)) and bad(lambda: rules.battle(1, 3)))
rng, wins = random.Random(7), 0
for _ in range(20000):
    a, d, al, dl = rules.battle(3, 2, rng)
    wins += dl - al
check("battle: over 20,000 rolls, 3 dice against 2 favour the attacker slightly", 0.05 < wins / 20000 < 0.25, wins / 20000)

# ---------------------------------------------------------------- the engine, with Risk
class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t
clock = Clock()
folder = paths.data("sessions")
s = engine.Session(risk, ["Ethan", "Trevor", "Sam"], {"hints": "On"}, folder, clock)
check("new game: saved at once, three players with 14 territories", os.path.isfile(s.path) and s.state["terr"] == [14, 14, 14] and s.active_name() == "Ethan")
check("first turn: Ethan places 4 armies", risk.armies(s.state)[0] == 4)
clock.t += 60
said = s.do(ev="next")
check("next: reinforce to attack, nothing said", s.state["phase"] == "attack" and said == [] and len(s.log) == 1)
said = s.do(ev="capture", defender=1)
check("capture: Ethan 15, Trevor 13", s.state["terr"] == [15, 13, 14] and s.state["captured"])
check("a refused event changes nothing and is not logged", s.do(ev="trade") != [] and len(s.log) == 2 and s.state["sets"] == 0)
s.do(ev="next")
clock.t += 30
said = s.do(ev="next")
check("end of turn: Ethan takes one card, Trevor is up with 4 armies",
      s.state["cards"] == [1, 0, 0] and s.active_name() == "Trevor" and "Ethan takes a card." in said and "Trevor: 4 armies to place." in said, said)
check("the clock charged Ethan's 90 seconds to Ethan", s.d["seconds"] == [90.0, 0.0, 0.0], s.d["seconds"])
check("undo: back to Ethan's fortify phase, card taken away", s.undo() and s.state["phase"] == "fortify" and s.active_name() == "Ethan" and s.state["cards"] == [0, 0, 0] and len(s.log) == 3)
s.do(ev="next")
again = engine.Session.load(s.path, plugins, clock)
check("a saved game loads back exactly", again.state == s.state and again.log == s.log and again.players == s.players)
check("the unfinished game is offered for resuming", engine.unfinished(folder)[0] == s.path)
for _ in range(3): s.do(ev="next")                    # Trevor's turn passes, no capture
check("no capture, no card", s.state["cards"] == [1, 0, 0] and s.active_name() == "Sam")
for _ in range(3): s.do(ev="next")
check("after Sam it is turn 2 and Ethan again", s.state["turn"] == 2 and s.active_name() == "Ethan")
s.do(ev="card", delta=2)
said = s.do(ev="trade")
check("trading the first set: 4 armies, three cards gone", s.state["cards"][0] == 0 and s.state["bonus"] == 4 and risk.armies(s.state)[0] == 5 + 4 and "worth 4 armies" in said[0], said)
check("continents: cannot hold Asia with too few territories for it and Australia", s.do(ev="cont", player=0, name="Australia") == [] and s.do(ev="cont", player=0, name="Asia") != [] and s.state["cont"][0] == ["Australia"])
check("continents: two players cannot hold the same one", "already holds" in s.do(ev="cont", player=1, name="Australia")[0])
check("territories: the board only has 42", "only 42" in s.do(ev="terr", player=2, delta=1)[0])
s.do(ev="terr", player=1, delta=-2); s.do(ev="terr", player=0, delta=2)
check("territories: moved by hand, still 42 in all", sum(s.state["terr"]) == 42 and s.state["terr"][0] == 17)
s.add_reminder(1, "attack", "use the cannons"); s.add_reminder(None, "*", "drink water")
s.do(ev="next")
check("reminders: only the ones for this player and phase are said", s.due_reminders() == ["Reminder: drink water"], s.due_reminders())
s.do(ev="next"); said = s.do(ev="next"); said = s.do(ev="next")
check("reminders: Trevor's attack reminder is said when his attack phase starts", any("use the cannons" in x and "Trevor" in x for x in said), said)
s2 = engine.Session(risk, ["A", "B"], {}, None, clock)
check("two players: a neutral army holds 14", s2.state["neutral"] == 14 and risk.over(s2.state) is None)
s2.do(ev="next")
for _ in range(14): s2.do(ev="capture", defender="neutral")
s2.do(ev="card", player=1, delta=4)
for _ in range(13): s2.do(ev="capture", defender=1)
check("not over while B holds one territory", s2.finished is None and s2.state["terr"] == [41, 1])
said = s2.do(ev="capture", defender=1)
check("taking the last territory: B is out, A takes B's cards and wins",
      s2.finished and s2.finished["winner"] == "A" and s2.state["out"] == [False, True] and s2.state["cards"] == [4, 0] and any("eliminated" in x for x in said), (s2.finished, said))
check("a finished game takes no more events", s2.do(ev="next") == ["The game is over."])
check("undo reopens a finished game", s2.undo() and s2.finished is None and s2.state["terr"] == [41, 1])
s3 = engine.Session(risk, ["A", "B", "C"], {}, folder, clock)
s3.do(ev="next"); s3.do(ev="capture", defender=2); s3.finish()
check("stopped early: the leader is named and the game is recorded", s3.finished["winner"] == "A" and "Territories: A 15" in s3.finished["lines"][0], s3.finished)
check("Home's last-game line", engine.last_game_line(folder, {"risk": "Risk"}) == "Last game: Risk, A won", engine.last_game_line(folder, {"risk": "Risk"}))
check("durations in words", [engine.duration_words(m) for m in (1, 45, 60, 112)] == ["1 minute", "45 minutes", "1 hour", "1 hour 52 minutes"])
many = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
for _ in range(100): many.do(ev="next")
check("undo history is capped so the save file stays small", len(many.d["undo"]) == engine.UNDO_DEPTH and len(many.log) == 100)

# ---------------------------------------------------------------- generic board games
cat = GenericGame({"id": "x", "name": "Settlers", "blurb": "", "order": 1, "players": [3, 4], "phases": ["Roll", "Trade", "Build"],
                   "trackers": [{"name": "Points", "start": 2, "min": 0}, {"name": "Knights"}], "win": {"tracker": "Points", "at": 10}})
cat.id, cat.name = "x", "Settlers"
g = engine.Session(cat, ["A", "B", "C"], {}, None, clock)
g.state["n"] = 3
check("generic: trackers start where the data says", g.state["t"] == {"Points": [2, 2, 2], "Knights": [0, 0, 0]} and (cat.min_players, cat.max_players) == (3, 4))
g.do(ev="next"); g.do(ev="next")
check("generic: next walks the phases", cat.strip(g) == ("Settlers · Turn 1", "Build"))
g.do(ev="next")
check("generic: then the next player", g.active_name() == "B" and g.state["phase"] == 0)
g.do(ev="next"); g.do(ev="next"); g.do(ev="next"); g.do(ev="next"); g.do(ev="next"); g.do(ev="next")
check("generic: after the last player, turn 2", g.state["turn"] == 2 and g.active_name() == "A")
check("generic: a tracker cannot go below its minimum", "cannot go below" in g.do(ev="add", player=0, tracker="Points", delta=-3)[0] and g.state["t"]["Points"][0] == 2)
for _ in range(7): g.do(ev="add", player=1, tracker="Points", delta=1)
check("generic: not over at 9", g.finished is None and g.state["t"]["Points"][1] == 9)
g.do(ev="add", player=1, tracker="Points", delta=1)
check("generic: first to 10 points wins", g.finished and g.finished["winner"] == "B", g.finished)
golf = GenericGame({"id": "g", "name": "Golf", "blurb": "", "order": 1, "trackers": [{"name": "Strokes"}], "lowest_wins": True})
golf.id, golf.name = "g", "Golf"
gs = engine.Session(golf, ["A", "B"], {}, None, clock); gs.state["n"] = 2
gs.do(ev="add", player=0, tracker="Strokes", delta=5); gs.do(ev="add", player=1, tracker="Strokes", delta=3); gs.finish()
check("generic: lowest-wins games name the low scorer", gs.finished["winner"] == "B" and gs.finished["lines"] == ["Strokes: B 3, A 5"], gs.finished)

# ---------------------------------------------------------------- the library
from deepthought.library import Library
empty = Library()
check("no content.db: the library is empty and searching is safe", empty.counts() == (0, 0) and empty.search("anything") == [] and empty.games() == [])
src = tempfile.mkdtemp()
os.makedirs(os.path.join(src, "free", "risk")); os.makedirs(os.path.join(src, "mine", "dnd", "campaigns")); os.makedirs(os.path.join(src, "mine", "catan"))
open(os.path.join(src, "free", "risk", "Made Up Rules.md"), "w", encoding="utf-8").write("# Armies\n\nThe grobnar gets three armies for each continent it holds.\n\n# Dice\n\nRoll the zibble die when you attack.\n")
open(os.path.join(src, "mine", "dnd", "campaigns", "Secret.md"), "w", encoding="utf-8").write("# The twist\n\nThe grobnar was the innkeeper all along.\n")
open(os.path.join(src, "mine", "catan", "House Rules.txt"), "w", encoding="utf-8").write("The robber never moves on a grobnar turn.\n")
json.dump([{"object": "card", "oracle_id": "id-1", "name": "Grobnar Bear", "mana_cost": "{1}{G}", "cmc": 2, "type_line": "Creature — Bear",
            "oracle_text": "Trample", "power": "2", "toughness": "2", "layout": "normal", "legalities": {}}],
          open(os.path.join(src, "cards.json"), "w"))
con = dt_content.connect(os.environ["DT_CONTENT_DB"])
dt_content.sync(con, src, log=lambda *a: None); dt_content.load_cards(con, os.path.join(src, "cards.json"), log=lambda *a: None); con.close()
lib = Library()
check("the loader takes a folder for a game it has never heard of", "catan" in lib.games() and lib.search("robber", "catan")[0]["title"].startswith("House Rules"), lib.games())
r = lib.search("grobnar")
check("search: card first, then sections; campaign pages hidden from players",
      r[0]["kind"] == "card" and r[0]["title"] == "Grobnar Bear" and len(r) == 3 and not any("Secret" in x["title"] for x in r), r)
check("search: DM mode shows campaign pages", any("Secret" in x["title"] for x in lib.search("grobnar", dm=True)))
check("search: by game", [x["title"] for x in lib.search("grobnar", "risk")] == ["Made Up Rules, Armies"], lib.search("grobnar", "risk"))
d = lib.doc(lib.search("zibble", "risk")[0]["id"])
check("opening a section gives its full text and where it came from", d["title"] == "Made Up Rules, Dice" and "zibble die" in d["body"] and not d["dm_only"], d)
c = lib.card("id-1")
check("opening a card: type, cost in words, text, stats, credit", "Creature — Bear" in c["body"] and "one and one green" in c["body"] and "2/2" in c["body"] and "Scryfall" in c["heading"], c)
check("excerpts for a spoken question: at most three, never campaign pages", len(lib.excerpts("grobnar")) == 2 and len(lib.excerpts("grobnar", dm=True)) == 3)

# ---------------------------------------------------------------- screens
# found by tools/scenarios.py on the real Pi, 23 Nov 2026: cards asked for by name, and long sections
from deepthought.library import window
ex = lib.excerpts("what does grobnar bear do", "mtg")
check("a Magic card asked for by name: its own text comes first, credited to Scryfall",
      ex and ex[0][0] == "Card data from Scryfall, Grobnar Bear" and "Trample" in ex[0][1], ex)
check("a card is found whatever else is in the question, and with no game on the table",
      lib.named_card("can grobnar bear block flyer")["title"] == "Grobnar Bear" and lib.excerpts("grobnar bear")[0][0].startswith("Card data"))
check("half a card's name is not the card, and one word in a sentence is a rule, not a card",
      lib.named_card("how many armies grobnar get") is None and lib.named_card("does bear trample") is None)
check("in another game a card's name brings no card", not any(w.startswith("Card data") for w, _ in lib.excerpts("grobnar bear", "risk")))
long = "Opening remarks. " * 100 + "\nThe zibble die is rolled twice on a zibble turn.\n" + "Closing remarks. " * 100
check("a long section: the stretch about the question is taken, starting on a line, 1,200 letters at most",
      window(long, "zibble die").startswith("The zibble die") and len(window(long, "zibble die")) <= 1200 and "zibble" not in long[:1200])
check("a short section, or one with none of the question's words, is taken from its start",
      window("Short one.", "zibble") == "Short one." and window(long, "quux") == long[:1200].strip())

import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens import common, extras
from deepthought.screens.home import Home
from deepthought.screens.lookup import Lookup
from deepthought.screens.pick_game import PickGame
from deepthought.games.risk.plugin import RiskBattle, RiskMap, RiskPlay

app = App(hw.make("desktop", sound=False), games, headless=True)
app.push(Home(app))
def screen_ok(screen=None):
    screen = screen or app.screen
    ws, out = [w for w in screen.widgets if w.action], []
    for w in ws:
        if w.rect.h < T.MIN_BUTTON or w.rect.w < T.MIN_BUTTON: out.append(("small", w.label, tuple(w.rect)))
        if not pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP).contains(w.rect): out.append(("outside", w.label, tuple(w.rect)))
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if a.rect.colliderect(b.rect): out.append(("overlap", a.label, b.label))
    app.render()
    return out
def tap(label):
    w = next(w for w in app.screen.widgets if w.action and w.label.startswith(label))
    app.toast = None
    w.action()

clock.t += 500
s4 = engine.Session(risk, ["Old", "Game"], {}, folder, clock); s4.do(ev="next")
check("Home offers to resume the unfinished Risk game", (tap("Play"), app.screen.title)[1] == "Resume?" and "Risk" in app.screen.text, app.screen.title)
tap("New game")
check("New game goes to Pick a game", isinstance(app.screen, PickGame))
app.screen.choose([g["id"] for g in games].index("risk"))
setup = app.screen
check("choosing Risk opens Set up with two players", isinstance(setup, common.Setup) and setup.n == 2 and screen_ok() == [], screen_ok())
tap("+"); tap("+"); tap("+"); tap("+"); tap("+")
check("Set up: six players at most, all buttons still fit", setup.n == 6 and screen_ok() == [], screen_ok())
tap("−"); tap("−"); tap("−")
setup.rename(0)
entry = app.screen
check("tapping a name opens the keyboard", isinstance(entry, common.TextEntry) and screen_ok() == [], screen_ok())
for ch in "ethanx": entry.type(ch)
entry.delete(); entry.done()
check("typed name is used, with a capital", setup.names[0] == "Ethan" and app.screen is setup, setup.names)
setup.names[1] = "Ethan"; tap("Start game")
check("two players with one name are refused", app.screen is setup and "share a name" in app.toast, app.toast)
setup.names[1] = "Trevor"; setup.names[2] = "Sam"
tap("Hints"); check("an option button cycles its choices", setup.opts["hints"] == "Off"); tap("Hints")
tap("How to play")
check("How to play opens the Risk steps", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "The aim" and screen_ok() == [], screen_ok())
n_pages = len(app.screen.pages)
for _ in range(n_pages): app.gesture("press")
check("pressing through every page comes back to Set up", app.screen is setup, n_pages)
tap("Start game")
play = app.screen
check("Start game: Risk play screen, Ethan's turn, ring in his colour",
      isinstance(play, RiskPlay) and play.pill[0] == "Ethan's turn" and app.hw._ring.now == ("turn", {"colour": T.player_colour(0)}) and screen_ok() == [], screen_ok())
check("names are remembered for next time", common.recent_names()[:3] == ["Ethan", "Trevor", "Sam"], common.recent_names())
check("strip says Risk, turn 1, Reinforce", (play.left, play.title) == ("Risk · Turn 1", "Reinforce"))
app.gesture("press")
check("the button moves to Attack and the Battle button appears", app.session.state["phase"] == "attack" and any(w.label == "Battle" for w in play.widgets) and screen_ok() == [])
app.gesture("press"); app.gesture("double")
check("double press: takes back its own press and undoes one more", app.session.state["phase"] == "reinforce" and len(app.session.log) == 0, (app.session.state["phase"], len(app.session.log)))
app.gesture("press"); tap("Battle")
battle = app.screen; battle.rng = random.Random(1)
check("Battle screen fits", isinstance(battle, RiskBattle) and screen_ok() == [], screen_ok())
app.gesture("press")
check("the button rolls 3 against 2", battle.result and len(battle.result[0]) == 3 and len(battle.result[1]) == 2 and battle.result[2] + battle.result[3] == 2 and screen_ok() == [])
tap("vs "); check("the defender button moves to the next opponent", battle.target_name() == "Sam")
tap("Territory taken")
check("Territory taken: Ethan 15, Sam 13, back on the play screen", app.session.state["terr"] == [15, 14, 13] and app.screen is play, app.session.state["terr"])
tap("Map"); m = app.screen
check("Map fits", isinstance(m, RiskMap) and screen_ok() == [], screen_ok())
tap("Australia")
check("Map: ticking Australia adds 2 armies a turn", app.session.state["cont"][0] == ["Australia"] and any(w.label == "Holds Australia" and w.selected for w in m.widgets))
tap("Back to the game"); tap("Menu"); menu = app.screen
check("More menu fits", isinstance(menu, extras.GameMenu) and screen_ok() == [], screen_ok())
tap("Reminders"); rem = app.screen; tap("For:"); tap("When:"); tap("When:"); tap("Add a reminder")
for ch in "roll first": app.screen.type(ch)
app.screen.done()
check("a reminder typed on the box is saved for that player and phase",
      app.session.d["reminders"] == [{"player": 0, "phase": "attack", "text": "Roll first"}] and screen_ok() == [], app.session.d["reminders"])
tap("Ethan, Attack"); check("tapping a reminder removes it", app.session.d["reminders"] == [])
tap("Back"); tap("Who first")
sp = app.screen
check("spinner picks a player and points the ring at their seat", 0 <= sp.pick < 3 and app.hw._ring.now[0] == "spin" and screen_ok() == [])
f0 = app.hw.ring_frame(100.0); f1 = app.hw.ring_frame(104.0)
check("spinner: the ring ends with one bright light on that seat", f1.index(max(f1)) == sp.pick * 16 // 3 and sum(1 for c in f1 if c == max(f1)) == 1, f1)
tap("Back"); tap("Clock")
check("Clock page lists every player", all(n in " ".join(app.screen.pages[0][1]) for n in ("Ethan", "Trevor", "Sam")))
tap("Back"); tap("Lookup"); look = app.screen
check("Lookup opens on this game", isinstance(look, Lookup) and look.game == "risk" and screen_ok() == [], screen_ok())
tap("Search")
for ch in "grobnar": app.screen.type(ch)
app.gesture("press")
check("typing and pressing the button searches this game", look.query == "grobnar" and [r["title"] for r in look.results] == ["Made Up Rules, Armies"] and screen_ok() == [], look.results)
tap("This game")
check("All games finds the card and the other book too, but not the campaign", len(look.results) == 3 and look.results[0]["kind"] == "card" and screen_ok() == [], look.results)
app.dm = True; look.run("grobnar"); check("with DM mode on, the campaign page is found", len(look.results) == 4); app.dm = False
look.open(look.results[0])
check("opening a result shows it as pages", isinstance(app.screen, common.Pages) and app.screen.left == "Grobnar Bear" and screen_ok() == [])
app.gesture("press"); app.gesture("double"); look.run("zzzz")
check("nothing found is said plainly", look.results == [] and screen_ok() == [])
tap("Back"); tap("Home")
check("Home from the menu leaves the game resumable", isinstance(app.screen, Home) and engine.unfinished(folder)[1]["players"] == ["Ethan", "Trevor", "Sam"])
tap("Play"); tap("Resume it")
check("Resume puts the game back as it was", isinstance(app.screen, RiskPlay) and app.session.state["terr"] == [15, 14, 13] and app.session.state["cont"][0] == ["Australia"])
tap("Menu"); tap("End game")
check("End game asks first; the button's answer is Keep playing", app.screen.title == "End the game?")
tap("End it")
over = app.screen
check("ending shows Game over with the leader", isinstance(over, common.GameOver) and over.session.finished["winner"] == "Ethan" and screen_ok() == [], over.session.finished)
app.gesture("press")
check("the button goes Home, which now shows the last game", isinstance(app.screen, Home) and app.last_game == "Last game: Risk, Ethan won", app.last_game)
tap("Settings"); st = app.screen
check("Settings fits", screen_ok() == [], screen_ok())
tap("DM mode"); [app.screen.type(c) for c in "1234"]; app.screen.done()
check("wrong DM code keeps DM mode locked", app.dm is False and "not the code" in app.toast)
tap("DM mode"); [app.screen.type(c) for c in "0000"]; app.screen.done()
check("right DM code unlocks it", app.dm is True)
tap("Volume"); from deepthought import settings
check("volume steps and is remembered", settings.get("volume") == 80)
tap("Chatty"); check("chatty setting cycles", settings.get("chatty") == "terse")
tap("Library"); check("About page carries the D&D and Scryfall credits", any("CC BY 4.0" in " ".join(p[1]) for p in app.screen.pages) and any("Scryfall" in " ".join(p[1]) for p in app.screen.pages))
tap("Back"); tap("Back"); tap("Play"); app.screen.choose([g["id"] for g in games].index("tally")); tap("Start game")
any_ = app.screen
check("the any-game scorekeeper starts with two players", any_.game.id == "tally" and screen_ok() == [], screen_ok())
tap("Ethan"); tap("Ethan"); tap("Tap: +1"); tap("Ethan")
check("tap a name to add, switch the tap to take away", app.session.state["t"]["Score"] == [1, 0], app.session.state["t"])
app.gesture("press"); check("the button passes the turn", app.session.active_name() == "Trevor")

# ---------------------------------------------------------------- faults, odd files, and not reading every game
class Faulty(engine.Game):
    id, name = "faulty", "Faulty"
    def new_state(self, players, options): return {"n": 0, "active": 0}
    def apply(self, state, ev):
        state["n"] += 1
        if ev["ev"] == "boom":
            state["half"] = "done"
            raise KeyError("a fault in the plugin")
        return []
fdir = tempfile.mkdtemp()
fs = engine.Session(Faulty(), ["A", "B"], {}, fdir)
fs.do(ev="next")
try:
    fs.do(ev="boom"); raised = False
except KeyError:
    raised = True
check("a fault inside a game's rules leaves the state as it was, with nothing logged",
      raised and fs.state == {"n": 1, "active": 0} and len(fs.log) == 1 and len(fs.d["undo"]) == 1, fs.state)
check("and the game on disk is still the good one", json.load(open(fs.path))["state"] == {"n": 1, "active": 0})
for name, text in (("a-list.json", "[1, 2]"), ("a-number.json", "7"), ("half.json", '{"game": "risk"'),
                   ("no-players.json", '{"game": "risk", "log": []}')):
    open(os.path.join(fdir, name), "w").write(text)
check("files in the sessions folder that are not saved games are passed over", [p for p, _ in engine.list_sessions(fdir)] == [fs.path])
check("the last-game line and the resume check survive them", engine.last_game_line(fdir, {}) is None and engine.unfinished(fdir)[0] == fs.path)
fs.finish()
check("the last-game line changes as soon as a game is recorded", engine.last_game_line(fdir, {"faulty": "Faulty"}) == "Last game: Faulty, no winner")
opened = []
real_load = json.load
json.load = lambda f, **k: (opened.append(f.name), real_load(f, **k))[1]
for i in range(30):                                       # thirty older games on the card
    shutil.copy(fs.path, os.path.join(fdir, "2020010%d-old%d.json" % (i % 10, i)))
    os.utime(os.path.join(fdir, "2020010%d-old%d.json" % (i % 10, i)), (1e9 + i, 1e9 + i))
engine._last_line.clear()
for _ in range(50):
    engine.last_game_line(fdir, {})
check("the last-game line reads one file, once, however many games are stored or times it is asked", len(opened) == 1, len(opened))
opened.clear(); engine.unfinished(fdir)
check("the resume check reads only the newest game", len(opened) == 1, len(opened))
json.load = real_load
shutil.rmtree(fdir)

# the main loop carries on after a fault in a screen
from deepthought.app import TROUBLE
class Bad(common.Pages):
    def on_button(self, gesture): raise RuntimeError("a fault in a screen")
app.go_home(); app.push(Bad(app, "x", "y", [("a", "b")]))
app.hw.gestures = lambda t: ["press"]
quiet = io.StringIO()
with contextlib.redirect_stdout(quiet):
    try: app.frame(1.0)
    except RuntimeError: app.trouble(1.0)
check("a fault in a screen is written to errors.log and said, and the box carries on",
      app.toast == TROUBLE and "a fault in a screen" in open(paths.data("errors.log")).read() and isinstance(app.screen, Bad))
with contextlib.redirect_stdout(quiet):
    for t in (2.0, 3.0):
        try: app.frame(t)
        except RuntimeError: app.trouble(t)
check("the same fault three times in ten seconds goes back to Home", len(app.stack) == 1)
app._troubles = [5.0] * 5
gave_up = False
with contextlib.redirect_stdout(quiet):
    try:
        try: raise RuntimeError("again")
        except RuntimeError: app.trouble(6.0)
    except RuntimeError:
        gave_up = True
check("six in ten seconds and she gives up, so the service can start her again", gave_up)
del app.hw.gestures; app._troubles = []; app.toast = None

from deepthought.shots import all_shots
# ---------------------------------------------------------------- found in review: Risk
from deepthought.games.risk.plugin import RiskPlay as _RP, RiskMap as _RM, RiskBattle as _RB
r2 = engine.Session(risk, ["A", "B"], {}, None, clock)
r2.do(ev="next"); r2.state["terr"] = [27, 1]
r2.do(ev="capture", defender=1)
check("two players: taking the opponent's last territory wins, neutral army or not",
      r2.finished and r2.finished["winner"] == "A" and r2.state["neutral"] == 14 and r2.finished["lines"][0] == "The last player standing", r2.finished)
r3 = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
r3.do(ev="next")
for _ in range(4): r3.do(ev="card", delta=1)
for _ in range(3): r3.do(ev="card", player=1, delta=1)
check("a set cannot be traded mid-attack in the ordinary way", "start of a turn" in r3.do(ev="trade")[0] and not risk.may_trade(r3.state))
r3.state["terr"] = [27, 1, 14]
said = r3.do(ev="capture", defender=1)
check("knocking a player out with seven cards in hand: told to trade at once", r3.state["cards"] == [7, 0, 0] and any("trade sets at once" in x for x in said) and risk.may_trade(r3.state), said)
said = r3.do(ev="trade")
check("and the trade is taken, there in the attack phase", r3.state["phase"] == "attack" and r3.state["cards"][0] == 4 and r3.state["bonus"] == 4 and "worth 4 armies" in said[0], said)
check("down to four cards: no second trade until the next turn", not risk.may_trade(r3.state) and "start of a turn" in r3.do(ev="trade")[0])
r3.do(ev="next"); r3.do(ev="next")
check("the turn ends: the leave to trade mid-attack ends with it", r3.state["spoils"] is False and r3.state["bonus"] == 0 and r3.state["active"] == 2)
r3b = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
r3b.do(ev="card", delta=1); r3b.do(ev="card", delta=1); r3b.do(ev="card", delta=1); r3b.do(ev="trade")
r3b.do(ev="next")
check("armies from a set traded at the start are not carried into the attack phase", r3b.state["phase"] == "attack" and r3b.state["bonus"] == 0)
r5 = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
r5.state["terr"] = [20, 12, 10]
r5.do(ev="cont", player=1, name="Asia"); r5.do(ev="next")
said = r5.do(ev="capture", defender=1)
check("a capture that leaves too few territories for the one continent held takes it away",
      r5.state["cont"][1] == [] and risk.armies(r5.state, 1)[0] == 3 and said == ["B no longer holds Asia."], (said, r5.state["cont"]))
r6 = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
r6.state["terr"] = [10, 22, 10]
r6.do(ev="cont", player=1, name="Asia"); r6.do(ev="cont", player=1, name="Europe"); r6.do(ev="next")
for _ in range(4): said = r6.do(ev="capture", defender=1)
check("with two continents held I cannot tell which broke: it is left ticked and B is asked", r6.state["cont"][1] == ["Asia", "Europe"] and "untick it under Map" in said[0] and risk.broken(r6.state, 1))
r6.do(ev="next"); r6.do(ev="next")
check("and B cannot leave Reinforce until Map is put right", r6.state["active"] == 1 and "Untick one under Map" in r6.do(ev="next")[0] and r6.state["phase"] == "reinforce")
r6.do(ev="cont", player=1, name="Europe")
check("unticking one lets the turn go on", r6.do(ev="next") == [] and r6.state["phase"] == "attack")
r7 = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
r7.do(ev="next")
for _ in range(13): r7.do(ev="terr", player=0, delta=-1)
said = r7.do(ev="terr", player=0, delta=-1)
check("Map: the active player set to no territories is out and the turn passes", r7.state["out"] == [True, False, False] and r7.state["active"] == 1 and r7.state["phase"] == "reinforce" and said[0] == "A is out of the game.", (said, r7.state["active"]))
for _ in range(14): r7.do(ev="terr", player=1, delta=-1)
check("Map: the next one down to nothing ends the game for the one left", r7.finished and r7.finished["winner"] == "C")
old = engine.Session(risk, ["A", "B", "C"], {}, None, clock)
del old.state["spoils"]; old.do(ev="next")
check("a game saved before this change still plays", old.do(ev="trade")[0].startswith("Sets are traded") and old.do(ev="capture", defender=1) == [] and old.do(ev="next") == [])

app.start_game(risk, ["Ann", "Bob", "Cy"], {"hints": "On", "guide": "As we play"})
while isinstance(app.screen, common.Pages): app.gesture("press")
app.gesture("press")
while isinstance(app.screen, common.Pages): app.gesture("press")
tap("Battle"); tap("Territory taken")
card = app.screen
check("Teach on, first capture: the two cards come up and the Battle screen is the one put away",
      isinstance(card, common.Pages) and [h for h, _ in card.pages][0] == "Taking a territory" and not any(isinstance(x, _RB) for x in app.stack)
      and isinstance(app.stack[-2], _RP), [type(x).__name__ for x in app.stack])
while isinstance(app.screen, common.Pages): app.gesture("press")
check("the cards are read and the game is back on the play screen", isinstance(app.screen, _RP) and app.session.state["terr"] == [15, 13, 14])
app.start_game(risk, ["Ann", "Bob", "Cy"], {"hints": "On", "guide": "Off"})
app.gesture("press")
for _ in range(3): app.session.do(ev="card", delta=1)
for _ in range(3): app.session.do(ev="card", player=1, delta=1)
app.session.state["terr"] = [27, 1, 14]
tap("Battle"); tap("Territory taken")
check("after a knock-out with six cards the attack screen offers Trade set, and everything still fits",
      isinstance(app.screen, _RP) and [w.label for w in app.screen.widgets if w.action][2:] == ["Next", "Battle", "Trade set", "Map", "Undo", "Menu"] and screen_ok() == [], [w.label for w in app.screen.widgets if w.action])
tap("Trade set")
check("trading there shows the card armies to place", app.session.state["cards"][0] == 3 and any(w.label == "Card armies" and w.value == "4" for w in app.screen.widgets) and screen_ok() == [])
app.start_game(risk, ["Ann", "Bob", "Cy"], {"hints": "On", "guide": "Off"})
app.session.state["terr"] = [1, 1, 40]; app.session.state["out"] = [False, False, False]
tap("Map"); app.screen.pick(1); tap("−")
check("Map: a correction that knocks one of three out just does it", isinstance(app.screen, _RM) and app.session.state["out"] == [False, True, False])
app.screen.pick(0); tap("−")
ask = app.screen
check("Map: a correction that would end the game asks first", isinstance(ask, common.Choice) and "ends the game" in ask.text and "Cy wins" in ask.text and app.session.state["terr"][0] == 1 and screen_ok() == [], getattr(ask, "text", ask))
app.gesture("press")
check("the button keeps playing: nothing changed", isinstance(app.screen, _RM) and app.session.finished is None and app.session.state["terr"][0] == 1)
tap("−"); tap("End the game")
check("End the game ends it", isinstance(app.screen, common.GameOver) and app.screen.session.finished["winner"] == "Cy")

# ---- the double press, on screens above the play screen (the real button always sends press first)
app.start_game(risk, ["Ann", "Bob", "Cy"], {"hints": "On", "guide": "Off"})
tap("Next"); tap("Map"); tap("−"); tap("−")
n = len(app.session.log)
app.gesture("press"); app.gesture("double")
check("a double press on Map closes it and undoes nothing", isinstance(app.screen, _RP) and len(app.session.log) == n and app.session.state["terr"] == [12, 14, 14] and app.session.state["phase"] == "attack", (len(app.session.log), n))
tap("Menu"); app.gesture("press"); app.gesture("double")
check("a double press on the More menu closes it and undoes nothing", isinstance(app.screen, _RP) and len(app.session.log) == n and app.session.state["phase"] == "attack")
tap("Next")
app.gesture("press"); app.gesture("double")
check("a double press on the play screen still takes back its own press and one more", len(app.session.log) == n and app.session.state["phase"] == "attack" and app.session.state["active"] == 0, (len(app.session.log), n))

# ---- a game ended by hand: Undo on Game over only un-ends it
app.start_game(risk, ["Ann", "Bob", "Cy"], {"hints": "On", "guide": "Off"})
tap("Next"); kept = app.session; before_end = json.loads(json.dumps(kept.state))
tap("Menu"); tap("End game"); tap("End it")
check("End game marks the game as ended by hand", isinstance(app.screen, common.GameOver) and kept.finished.get("by_hand") is True)
tap("Undo")
check("Undo on Game over after End game takes back no event: the game is just not over any more",
      isinstance(app.screen, _RP) and app.session is kept and kept.finished is None and len(kept.log) == 1 and kept.state == before_end, (len(kept.log), kept.state))
tap("Menu"); tap("End game"); tap("End it"); app.gesture("press"); app.gesture("double")
check("the button on Game over goes Home, and the double that follows undoes nothing either", len(kept.log) == 1 and kept.state == before_end and len(app.stack) == 1)
app.start_game(risk, ["Ann", "Bob"], {"hints": "On", "guide": "Off"})
app.session.state["terr"] = [27, 1]; tap("Next"); kept = app.session
tap("Battle"); tap("Territory taken")
check("a game an event ended is not marked by hand", isinstance(app.screen, common.GameOver) and not kept.finished.get("by_hand"))
tap("Undo")
check("and Undo there still steps back the event that ended it", kept.finished is None and len(kept.log) == 1 and kept.state["terr"] == [27, 1])

# ---- the wrong game: Scrap it throws the game away and leaves nothing to resume
app.start_game(risk, ["Wrong", "Game"], {"hints": "On", "guide": "Off"})
tap("Next"); wrong = app.session; was = wrong.path; others = sorted(os.listdir(folder))
check("a started game has a file", os.path.exists(was))
tap("Menu"); tap("End game")
check("End game offers Keep playing, End it and Scrap it, and fits", [w.label for w in app.screen.widgets if w.action] == ["Keep playing", "End it", "Scrap it"] and screen_ok() == [], screen_ok())
app.gesture("press")
check("the button's answer is still Keep playing", isinstance(app.screen, extras.GameMenu) and app.session is wrong and os.path.exists(was))
tap("End game"); tap("Scrap it")
check("Scrap it goes Home with no game on", isinstance(app.screen, Home) and app.session is None and len(app.stack) == 1)
check("its file is gone and no other game's file was touched", not os.path.exists(was) and sorted(os.listdir(folder)) == [f for f in others if f != os.path.basename(was)], os.listdir(folder))
check("and it is not offered to resume", not any(u.get("players") == ["Wrong", "Game"] for u in [engine.unfinished(folder)[1]] if u))
wrong.save()
check("a scrapped game never writes its file again", not os.path.exists(was))

# ---- phases that carry no reminders
class Quiet(engine.Game):
    id, quiet_phases = "quiet", ("lull",)
    def new_state(self, players, options): return {"active": 0, "phase": "go"}
    def apply(self, s, ev):
        s["active"], s["phase"] = (None, "lull") if s["phase"] == "go" else (1, "go")
        return []
qs = engine.Session(Quiet(), ["Ann", "Bob"])
qs.add_reminder(1, "*", "Bob every phase"); qs.add_reminder(None, "*", "Everyone"); qs.add_reminder(1, "go", "Bob go")
lull, go = qs.do(ev="next"), qs.do(ev="next")
check("a phase the game calls quiet has no reminders read out as it begins, not even Every phase ones", lull == [], lull)
check("the next phase has its reminders as usual", go == ["Reminder for Bob: Bob every phase", "Reminder: Everyone", "Reminder for Bob: Bob go"], go)
check("no game is quiet unless it says so", engine.Game.quiet_phases == () and plugins["risk"].quiet_phases == ())

tally_g = plugins["tally"]
app.start_game(tally_g, ["Ann", "Bob"], {"guide": "Off"})
tiles = [w for w in app.screen.widgets if w.action and w.label in ("Ann", "Bob")]
tiles[0].action(); tiles[0].action(); tiles[1].action()
app.session.cards = [{"title": "A card", "text": "One page."}]
app.gesture("press")
check("a press that moves on brings its teaching card up", isinstance(app.screen, common.Pages) and app.session.state["active"] == 1 and len(app.session.log) == 4)
app.gesture("press"); app.gesture("double")
check("two quick presses to put a one-page card away undo nothing", isinstance(app.screen, common.PlayBase) and app.session.state["t"]["Score"] == [2, 1] and app.session.state["active"] == 1 and len(app.session.log) == 4, app.session.state)
app.session.cards = [{"title": "Another", "text": "One page."}]
app.gesture("press"); app.gesture("double")
check("a double press whose first press brought a card up: the card is put away, the press and one more are taken back",
      isinstance(app.screen, common.PlayBase) and app.session.state["active"] == 0 and len(app.session.log) == 3 and app.session.state["t"]["Score"] == [2, 1], (type(app.screen).__name__, len(app.session.log)))

# ---------------------------------------------------------------- found in review: data-only games
def gen(**kw):
    g_ = GenericGame(dict({"id": "q", "name": "Q", "blurb": "", "order": 1}, **kw)); g_.id, g_.name = "q", "Q"
    return g_
hearts = gen(players=[3, 4], trackers=[{"name": "Points", "start": 0, "step": 1, "min": None}], lowest_wins=True, win={"tracker": "Points", "at": 100})
hs = engine.Session(hearts, ["A", "B", "C"], {}, None, clock); hs.state["n"] = 3
hs.do(ev="next")
check("lowest wins with a winning score: the game is not over before anything is scored", hs.finished is None)
hs.do(ev="add", player=1, tracker="Points", delta=30); hs.do(ev="add", player=0, tracker="Points", delta=99); hs.do(ev="add", player=2, tracker="Points", delta=12)
check("nor while everyone is under it", hs.finished is None)
hs.do(ev="add", player=0, tracker="Points", delta=1)
check("somebody reaches 100: it ends and the LOWEST scorer wins", hs.finished and hs.finished["winner"] == "C" and hs.finished["lines"] == ["Points reached 100", "Lowest: 12"], hs.finished)
hs.undo(); hs.do(ev="add", player=1, tracker="Points", delta=-18); hs.do(ev="add", player=0, tracker="Points", delta=1)
check("two tied for lowest: it ends with no winner named", hs.finished and hs.finished["winner"] is None, hs.finished)
zero = gen(trackers=[{"name": "Points", "min": None}], win={"tracker": "Points", "at": 0})
zs = engine.Session(zero, ["A", "B"], {}, None, clock); zs.state["n"] = 2
zs.do(ev="next")
check("a winning score everyone starts on does not end the game on the first press", zs.finished is None)
def refused(**kw):
    try: gen(**kw)
    except ValueError as e: return str(e)
    return None
T1 = [{"name": "P"}]
check("game.json: fewest above most is refused", "nobody to play" in (refused(players=[4, 2], trackers=T1) or ""), refused(players=[4, 2], trackers=T1))
check("game.json: no players at all, or seven and up, is refused", refused(players=[0, 0], trackers=T1) and refused(players=[7, 9], trackers=T1) and refused(players=[3], trackers=T1))
check("game.json: two to eight is cut to six, and numbers written as words are read", (gen(players=[2, 8], trackers=T1).max_players, gen(players=["2", "4"], trackers=T1).min_players) == (6, 2))
check("game.json: a min or max that is not a number is refused", refused(trackers=[{"name": "P", "min": "none"}]) and refused(trackers=[{"name": "P", "max": [1]}]))
check("game.json: a min written as \"0\" is read as 0", gen(trackers=[{"name": "P", "min": "0"}]).trackers[0]["min"] == 0 and gen(trackers=[{"name": "P", "min": None}]).trackers[0]["min"] is None)
check("game.json: a start outside min and max is refused", "outside" in (refused(trackers=[{"name": "P", "start": -5, "min": 0}]) or ""))
check("game.json: a tracker with no name, trackers that are not a list, two with one name: refused", refused(trackers=[{"start": 0}]) and refused(trackers="Points") and refused(trackers=[{"name": "P"}, {"name": "P"}]))
check("game.json: win must name a tracker and a whole number", refused(trackers=T1, win={"tracker": "P"}) and refused(trackers=T1, win="P") and refused(trackers=T1, win={"tracker": "P", "at": "ten"}) and refused(trackers=T1, win={"tracker": "Nope", "at": 3}))
check("game.json: a winning score written as \"10\" is read as 10", gen(trackers=T1, win={"tracker": "P", "at": "10"}).win["at"] == 10)
check("game.json: phases must be a list", refused(phases="Roll") and gen(phases=["Roll"]).phase_names == ["Roll"])
gdir = tempfile.mkdtemp()
def put(gid, teach=None, **kw):
    os.makedirs(os.path.join(gdir, gid))
    with open(os.path.join(gdir, gid, "game.json"), "w") as f: json.dump(dict({"id": gid, "name": gid, "blurb": "x", "order": 100, "trackers": [{"name": "P"}]}, **kw), f)
    if teach is not None:
        with open(os.path.join(gdir, gid, "teach.json"), "w") as f: f.write(teach if isinstance(teach, str) else json.dumps(teach))
put("badorder", order="10"); put("numname", name=12345); put("badwin", win={"tracker": "P"}); put("badplayers", players=[4, 2])
put("t_broken", teach="[{\"title\": \"T\", "); put("t_dict", teach={"title": "One", "text": "a"}); put("t_null", teach="null")
put("t_mixed", teach=["a string", {"text": "no title", "trigger": "next"}, {"title": "No text", "after": "next"}, {"title": "Good", "text": "Kept."},
                      {"title": "Num", "text": "a", "after": 5}, {"title": "Dict", "text": "b", "trigger": {"ev": "next"}}, {"title": "List", "text": "c", "trigger": ["add", 3]}])
gl, gp = load_games(gdir)
ids = [x["id"] for x in gl]
check("the game list reports the unplayable hand-written games and loads the rest", sorted(p.split(":")[0] for p in gp) == ["badorder", "badplayers", "badwin"] and "numname" in ids and "badorder" not in ids, gp)
check("a name written as a number is turned into words", next(x for x in gl if x["id"] == "numname")["plugin"].name == "12345")
pl = {x["id"]: x["plugin"] for x in gl}
check("teach.json that is broken, not a list, or null teaches nothing rather than stopping the box", pl["t_broken"].teach() == [] and pl["t_dict"].teach() == [] and pl["t_null"].teach() == [])
check("teach.json: steps without a title and text are dropped, the rest kept", [x["title"] for x in pl["t_mixed"].teach()] == ["Good", "Num", "Dict", "List"])
for gid in ("numname", "t_broken", "t_dict", "t_null", "t_mixed"):
    app.go_home(); app.push(common.Setup(app, pl[gid])); app.render()
    opts = {o["key"]: o["choices"][-1] for o in app.screen.options}
    app.start_game(pl[gid], ["Ann", "Bob"], opts); app.render()
    seen = []
    for _ in range(6):
        while isinstance(app.screen, common.Pages): seen += [h for h, _ in app.screen.pages]; app.render(); app.screen.close()
        app.gesture("press"); app.render()
    while isinstance(app.screen, common.Pages): seen += [h for h, _ in app.screen.pages]; app.render(); app.screen.close()
    [w for w in app.screen.widgets if w.action and w.label == "Ann"][0].action(); app.render()
    while isinstance(app.screen, common.Pages): seen += [h for h, _ in app.screen.pages]; app.render(); app.screen.close()
    check("hand-written game %s: Set up opens, the game plays, and a mark that is not words never fires" % gid,
          app.session is not None and app.session.state["t"]["P"][0] == 1 and seen == (["Good", "List"] if gid == "t_mixed" else []), seen)
app.go_home(); shutil.rmtree(gdir)

shots = tempfile.mkdtemp()
made = all_shots(app, shots)
check("%d screenshots drawn, all 800x480" % len(made), len(made) >= 25 and {pygame.image.load(p).get_size() for p in made} == {(800, 480)})
shutil.rmtree(shots); shutil.rmtree(src)


# ---------------------------------------------------------------- text nobody can draw or save must not stop the box
import pygame as _pg
_pg.font.init()
_surf = _pg.Surface((T.W, T.H))
def _draws(text):
    try:
        T.draw_text(_surf, text, "text", 22, T.TEXT, (10, 100))
        T.draw_text(_surf, text, "bold", 26, T.TEXT, (10, 100), max_w=300)
        T.wrap(text, "text", 22, 300); T.wrap_paragraphs(text, "text", 22, 300); T.font("head", 30).size(text)
        return True
    except Exception as e:
        return repr(e)
check("drawing: a NUL in a name is left out, not a fault", _draws("A\x00B") is True and T.safe("A\x00B") == "AB", _draws("A\x00B"))
check("drawing: half of a broken character is left out, not a fault", _draws("A\ud800B") is True and T.safe("A\ud800B") == "AB", _draws("A\ud800B"))
check("drawing: an escape goes, a tab or a line break becomes a space, and plain text is untouched",
      T.safe("A\x1b[31mB") == "A[31mB" and T.safe("one\ttwo\nthree") == "one two three" and T.safe("Caf\u00e9 \U0001F409") == "Caf\u00e9 \U0001F409"
      and _draws("") is True and _draws("\x00") is True)
import time as _time
_t = _time.time(); _cut, _ = T.fit("W" * 30000, "bold", 26, 300); _took = _time.time() - _t
check("fitting a whole page of text to one line is quick, and still fits", _took < 1.0 and T.font("bold", 22).size(_cut)[0] <= 300 and _cut.endswith("\u2026"), (_took, len(_cut)))
_folder = tempfile.mkdtemp()
_s = engine.Session(risk, ["Ethan", "Trev\ud800or", "Sam"], {}, _folder)
_s.add_reminder(0, "*", "roll \ud83d now")              # half an emoji, as a hostile page could send it
with open(_s.path, encoding="utf-8") as _f: _disk = json.load(_f)
check("saving: text that cannot be written as it stands is still saved, and reads back exactly as it is in memory",
      _disk == _s.d and _disk["players"][1] == "Trev\ud800or" and _disk["reminders"][0]["text"] == "roll \ud83d now", _disk.get("players"))
_n = len(_s.log)
_s.do(**risk.press(_s.state))
with open(_s.path, encoding="utf-8") as _f: _disk = json.load(_f)
_back = engine.Session.load(_s.path, plugins)
check("saving: the game goes on being saved after that, and resumes", len(_disk["log"]) == len(_s.log) == _n + 1 and _back is not None and _back.d == _s.d)
check("saving: a game with only ordinary text is written as before, readable letters and all",
      "\\u" not in paths.json_text({"name": "Caf\u00e9"}, ensure_ascii=False) and json.loads(paths.json_text({"x": "a\ud800"}, ensure_ascii=False)) == {"x": "a\ud800"})
shutil.rmtree(_folder)

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
