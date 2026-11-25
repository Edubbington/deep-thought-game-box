"""Teach as we play: steps given at the right moment in a real game, read out
loud, and never twice. The voice here is a stand-in that writes down what it
was asked to say."""
import json, os, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from deepthought import engine, guide, hw, paths, theme as T
from deepthought.app import App
from deepthought.games import load_games
from deepthought.screens import common
from deepthought.screens.home import Home

fails = []
def check(name, cond, detail=""):
    line = ("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail))
    print(line.encode("ascii", "replace").decode())
    if not cond: fails.append(name)

games, _ = load_games()
by = {g["id"]: g["plugin"] for g in games}
box = hw.make("desktop", sound=False)
stops = []
box.stop_sound = lambda: stops.append(1)
app = App(box, games, headless=True)
app.push(Home(app))

class FakeVoice:
    def __init__(self): self.said = []
    def say(self, text, show=True): self.said.append(text)
    def hold(self, down): pass
    def can_speak(self): return True
voice = FakeVoice()
app.voice = voice

bounds = pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP)
def fits(screen):
    return [(getattr(w, "label", "?"), tuple(w.rect)) for w in screen.widgets
            if w.action and (w.rect.h < 64 or w.rect.w < 64 or not bounds.contains(w.rect))]
def labels(screen):
    return [getattr(w, "label", "") for w in screen.widgets if w.action]
def titles(screen):
    seen = []
    for heading, _ in screen.pages:
        if heading not in seen: seen.append(heading)
    return seen
def read_through(screen):
    """Press the button until the card is put away. Returns how many presses."""
    n = 0
    while app.screen is screen and n < 40:
        app.gesture("press"); app.render(); n += 1
    return n

# ---------------------------------------------------------------- the data
check("Risk, Magic and Any game offer Teach: As we play", all(guide.offered(by[g]) for g in ("risk", "mtg", "tally")))
check("Kill Team and 40k keep their own Teach mode; D&D is not offered it", not any(guide.offered(by[g]) for g in ("killteam", "wh40k", "dnd")))
bad = []
for g in games:
    keys = {k for k, _ in g["plugin"].phases()}
    for s in g["plugin"].teach():
        for field in ("after", "trigger"):
            conds = s.get(field) or []
            for c in ([conds] if isinstance(conds, str) else conds):
                if c.startswith("phase:") and c[6:] not in keys:
                    bad.append((g["id"], s["title"], c))
        if s.get("after") and s.get("trigger"):
            bad.append((g["id"], s["title"], "both"))
check("every step that waits for a phase names a phase the game really has", bad == [], bad)

# ---------------------------------------------------------------- set up
risk = by["risk"]
app.push(common.Setup(app, risk)); setup = app.screen; app.render()
check("Set up shows Teach, and it starts Off", "Teach: Off" in labels(setup) and fits(setup) == [], labels(setup))
setup.names = ["Ann", "Bob", "Cy"] + setup.names[3:]; setup.n = 3; setup.refresh(); setup.start()
check("with Teach off, a game starts with no card and no guide", isinstance(app.screen, common.PlayBase) and "guide" not in app.session.d and app.session.cards == [], type(app.screen).__name__)
app.session.finish(); app.go_home()
mtg_setup = common.Setup(app, by["mtg"]); app.push(mtg_setup); app.render()
check("Magic's Set up has room for its three options and Teach", len(mtg_setup.options) == 4 and fits(mtg_setup) == [], fits(mtg_setup))
app.go_home()

def start(game, names, **opts):
    app.go_home(); voice.said.clear(); stops.clear()
    s = common.Setup(app, game); app.push(s)
    s.n, s.names = len(names), names + s.names[len(names):]
    s.opts.update(opts); s.opts["guide"] = "As we play"
    s.refresh(); s.start()
    return app.session

# ---------------------------------------------------------------- Risk, from the top
s = start(risk, ["Ann", "Bob", "Cy"])
card = app.screen
check("Teach on: the game begins with a card on top of the play screen", isinstance(card, common.Pages) and card.title == "Teach" and isinstance(app.stack[-2], common.PlayBase))
check("it holds the four steps needed before the first turn, in order", titles(card) == ["The aim", "Setting up", "A turn has three parts", "New armies"], titles(card))
check("the first page is read out without being asked", len(voice.said) == 1 and voice.said[0].startswith("Take every territory"), voice.said)
check("the card's buttons are Skip, Again, Previous and Next, and they fit", [l.split("  ")[0] for l in labels(card)] == ["Skip", "Again", "Previous", "Next"] and fits(card) == [], labels(card))
app.render(); app.render()
check("drawing the screen again does not make her repeat herself", len(voice.said) == 1)
n_pages = len(card.pages)
presses = read_through(card)
check("the button turns the pages, and each page is read once", presses == n_pages and len(voice.said) == n_pages and len(set(voice.said)) == n_pages, (presses, n_pages, len(voice.said)))
check("after the last page the play screen is back, and nothing has been counted yet", isinstance(app.screen, common.PlayBase) and s.log == [] and s.state["phase"] == "reinforce")
check("putting a card away stops her talking", stops)
check("she is now waiting to teach attacking", guide.waiting_for(s)["title"] == "Attacking")

voice.said.clear()
app.gesture("press"); app.render()
card = app.screen
check("the press that begins the attack phase brings the Attacking card", s.state["phase"] == "attack" and isinstance(card, common.Pages) and titles(card) == ["Attacking"], type(card).__name__)
check("and it is read out", len(voice.said) == 1 and voice.said[0].startswith("Attack from one of your territories"), voice.said[:1])
read_through(card)
check("the game did not move while the card was read", s.state["phase"] == "attack" and len(s.log) == 1, (s.state["phase"], len(s.log)))

play = app.screen
play.do(ev="capture", defender=1); app.render()
card = app.screen
check("the first territory taken brings two cards: taking a territory, and cards", isinstance(card, common.Pages) and titles(card) == ["Taking a territory", "Cards"], titles(card) if isinstance(card, common.Pages) else type(card).__name__)
read_through(card)
play.do(ev="capture", defender=1)
check("the second territory taken brings nothing: once is enough", app.screen is play and s.cards == [])

play.on_button("press"); app.render()
card = app.screen
check("moving to fortify brings the Fortifying card", s.state["phase"] == "fortify" and isinstance(card, common.Pages) and titles(card) == ["Fortifying"])
read_through(card)
check("that was the last step in order", guide.waiting_for(s) is None)
for _ in range(7):
    app.gesture("press")
check("two more turns pass with no more cards", app.screen is play and s.cards == [] and s.state["active"] == 0 and s.state["turn"] > 1, (type(app.screen).__name__, s.state["active"]))

# ---------------------------------------------------------------- undo, double press, save and resume
s = start(risk, ["Ann", "Bob"])
read_through(app.screen)
play = app.screen
app.gesture("press"); read_through(app.screen)                # into attack: Attacking card read
play.undo(quiet=True)
check("undo steps the game back to reinforce", s.state["phase"] == "reinforce")
app.gesture("press")
check("doing it again does not teach attacking twice", app.screen is play and s.state["phase"] == "attack" and s.cards == [])
app.gesture("press")                                          # into fortify: the card comes up
card = app.screen
check("a card is up", isinstance(card, common.Pages))
app.gesture("press"); app.gesture("double")
check("a double press puts the card away and leaves the game alone", app.screen is play and s.state["phase"] == "fortify")
again = engine.Session.load(s.path, app.plugins)
check("the saved game remembers how far the teaching got", again.d["guide"] == s.d["guide"] and again.cards == [] and guide.waiting_for(again) is None, again.d.get("guide"))
s2 = start(risk, ["Ann", "Bob"])
path = s2.path
app.go_home(); voice.said.clear()
app.resume_game(path)
check("a resumed game does not start the lesson again", isinstance(app.screen, common.PlayBase) and voice.said == [] and guide.waiting_for(app.session)["title"] == "Attacking")
app.gesture("press")
check("but carries on from where it was", isinstance(app.screen, common.Pages) and titles(app.screen) == ["Attacking"])
read_through(app.screen)

# ---------------------------------------------------------------- from a phone
s = start(risk, ["Ann", "Bob"])
read_through(app.screen)
app.game_event({"ev": "next"})
check("Next pressed on a phone brings the card up on the box too", isinstance(app.screen, common.Pages) and titles(app.screen) == ["Attacking"])
read_through(app.screen)
app.session.finish(); app.end_game()
check("a finished game shows Game over, not a leftover card", isinstance(app.screen, common.GameOver))

# ---------------------------------------------------------------- Magic
mtg = by["mtg"]
s = start(mtg, ["Ann", "Bob"])
card = app.screen
check("Magic begins with the steps needed before the first turn", isinstance(card, common.Pages) and titles(card) == ["The aim", "Lands and mana", "Kinds of card", "What the button does", "A first game", "A turn: the beginning"], titles(card) if isinstance(card, common.Pages) else "")
app.gesture("press"); app.gesture("double")
check("Skip, or a double press, puts the whole card away at once", isinstance(app.screen, common.PlayBase))
seen = []
for _ in range(14):
    app.gesture("press")
    if isinstance(app.screen, common.Pages):
        seen.append((s.state["phase"], titles(app.screen)))
        app.gesture("press"); app.gesture("double")
check("each part of the turn is taught as the first turn reaches it", seen == [("main1", ["A turn: the middle"]), ("combat", ["Combat"]), ("end", ["A turn: the end"]), ("untap", ["Mistakes everyone makes"])], seen)
play = app.screen
play.do(ev="poison", player=1, delta=1)
check("the first poison counter brings the poison card", isinstance(app.screen, common.Pages) and titles(app.screen) == ["Poison and the monarch"])
app.gesture("press"); app.gesture("double")
play.do(ev="monarch", player=0)
check("the monarch does not bring it a second time", app.screen is play, type(app.screen).__name__)

s = start(mtg, ["Ann", "Bob"], steps="Whole turn")
app.gesture("press"); app.gesture("double")
seen = []
for _ in range(5):
    app.gesture("press")
    if isinstance(app.screen, common.Pages):
        seen.append(titles(app.screen)[0]); app.gesture("press"); app.gesture("double")
check("with the button passing whole turns, one step is taught each time the turn passes", seen == ["A turn: the middle", "Combat", "A turn: the end", "Mistakes everyone makes"], seen)

# ---------------------------------------------------------------- a game from the shelf
s = start(by["tally"], ["Ann", "Bob"])
card = app.screen
check("a game with plain notes reads them at the start", isinstance(card, common.Pages) and len(voice.said) == 1 and fits(card) == [])
read_through(card)
check("and then gets out of the way for good", isinstance(app.screen, common.PlayBase) and guide.waiting_for(s) is None)
app.gesture("press")
check("the next press is an ordinary press", isinstance(app.screen, common.PlayBase) and len(s.log) == 1)

app.push(common.Pages(app, "Risk", "Teach", [("One thing", "A short step.")], auto=True)); card = app.screen
check("a one-page card has Got it as its main button, then Again", labels(card) == ["Got it", "Again"] and fits(card) == [], labels(card))
app.gesture("press")
check("and the button puts it away", isinstance(app.screen, common.PlayBase))

# ---------------------------------------------------------------- no voice fitted
app.voice = None
s = start(risk, ["Ann", "Bob"])
card = app.screen
check("with no voice the cards still come, with no Again button", isinstance(card, common.Pages) and "Again" not in labels(card) and fits(card) == [], labels(card))
read_through(card)
check("and still go away", isinstance(app.screen, common.PlayBase))


# ---------------------------------------------------------------- found in review
A, B = (0, "reinforce"), (0, "attack")
check("a mark that is not words never matches, alone or in a list", not guide._hit(5, "next", A, B) and not guide._hit({"ev": "next"}, "next", A, B) and guide._hit(["next", 3], "next", A, B) and not guide._hit([3, None], "next", A, B))
check("a step can wait on a moment the game names, as well as on the event", guide._hit("knockout", "life", A, A, False, ["knockout"]) and not guide._hit("knockout", "life", A, A, False, []) and guide._hit(["poison", "knockout"], "life", A, A, False, ["knockout"]))
check("the base game names no extra moments", engine.Game().marks({}, {}, {"ev": "next"}) == [])
s = start(risk, ["Ann", "Bob", "Cy"]); read_through(app.screen)
play = app.screen
app.gesture("press")
check("a press into Attack brings the Attacking card", isinstance(app.screen, common.Pages) and s.state["phase"] == "attack")
read_through(app.screen)
s.do(ev="next"); s.do(ev="next"); play.refresh()
n = len(s.log)
app.gesture("press"); app.gesture("double")
check("double press on the play screen with no card: its own press and one more are taken back", app.screen is play and len(s.log) == n - 1, (len(s.log), n))
s2 = start(risk, ["Ann", "Bob", "Cy"]); read_through(app.screen)
play = app.screen
s2.do(ev="card", delta=1); play.refresh()
app.gesture("press"); app.gesture("double")
check("double press whose press brought a card up: the card is put away, the press and one more are taken back",
      app.screen is play and s2.state["phase"] == "reinforce" and len(s2.log) == 0 and s2.state["cards"] == [0, 0, 0], (type(app.screen).__name__, len(s2.log)))
app.go_home()

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
