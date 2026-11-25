"""Every game on the box, driven the same way: set up, start, press the button
many times, undo, look at the scoreboard and each phone, save and resume, end.
This is the check that the games and the shared parts fit together."""
import json, os, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from deepthought import engine, hw, paths, web, theme as T
from deepthought.app import App
from deepthought.games import load_games
from deepthought.screens import common
from deepthought.screens.home import Home
from deepthought.screens.pick_game import PickGame

fails = []
def check(name, cond, detail=""):
    line = ("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail))
    print(line.encode("ascii", "replace").decode())
    if not cond: fails.append(name)

games, problems = load_games()
check("the six launch games and the any-game scorekeeper come first, in their old order", [g["id"] for g in games][:6] == ["killteam", "wh40k", "dnd", "mtg", "risk", "tally"], [g["id"] for g in games])
SHELF = ["bears_vs_babies", "cards_for_all_people", "checkers", "chess", "clank", "digimon", "dominoes", "doomlings",
         "dungeon_mayhem", "exploding_kittens", "far_away", "guilty_gear", "here_to_slay", "heroes_of_barcadia",
         "monster_rejects", "munchkin", "pit", "pixel_tactics", "poker", "stratego", "tic_tac_ko", "uno", "pong"]
check("the shelf games follow, in name order", [g["id"] for g in games][6:] == SHELF, [g["id"] for g in games][6:])
from deepthought import persona
import re
for g in games[6:]:
    steps = g["plugin"].teach()
    words = " ".join(x["title"] + " " + x["text"] for x in steps)
    check("%s: teaches something, with no shouting and nothing her voice may not say" % g["id"],
          len(steps) >= 1 and persona.in_voice(words) and not re.search(r"[*#_`]", words), words[:80])
    check("%s: every step has a title and a body, and no step is too long to read aloud" % g["id"],
          all(x["title"].strip() and x["text"].strip() and len(x["text"]) <= 620 for x in steps),
          [(x["title"], len(x["text"])) for x in steps])
check("no game failed to load", problems == [], problems)
check("every game is ready to play", all(g["status"] == "ready" for g in games), [(g["id"], g["status"]) for g in games])
app = App(hw.make("desktop", sound=False), games, headless=True)
app.push(Home(app))
check("every blurb fits its tile", all(T.font("text", 22).size(g["blurb"])[0] <= 325 for g in games),
      [(g["blurb"], T.font("text", 22).size(g["blurb"])[0]) for g in games])
bounds = pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP)
def fits(screen):
    out = []
    for w in screen.widgets:
        if w.action and (w.rect.h < 64 or w.rect.w < 64 or not bounds.contains(w.rect)):
            out.append((type(screen).__name__, getattr(w, "label", "?"), tuple(w.rect)))
    return out

# ---- the picker: four big tiles, then eight names a page, every game on exactly one page
pick = PickGame(app); app.push(pick)
seen, clash, wide = [], [], []
check("the picker needs few pages for a full shelf", pick.pages() == 1 + -(-(len(games) - 4) // 8) and pick.pages() <= 5, pick.pages())
for _ in range(pick.pages()):
    tiles = [w for w in pick.widgets if w.label in [g["name"] for g in games]]
    seen += [w.label for w in tiles]
    clash += fits(pick) + [(a.label, b.label) for a in pick.widgets for b in pick.widgets if a is not b and a.rect.colliderect(b.rect)]
    wide += [w.label for w in tiles if pick.page and T.font("bold", 24).size(w.label)[0] > w.rect.w - 24]
    check("page %d of the picker selects its own first game" % (pick.page + 1), games[pick.sel]["name"] == tiles[0].label, (pick.sel, tiles[0].label))
    pick.more()
check("every game is on exactly one page of the picker", seen == [g["name"] for g in games], seen)
check("every page of the picker fits, with nothing overlapping", clash == [], clash)
check("every name on the small pages fits its button", wide == [], wide)
check("after the last page the picker is back at the first", pick.page == 0 and pick.sel == 0)
app.pop()

for g in games:
    gid, plugin = g["id"], g["plugin"]
    app.go_home(); app.toast = None
    app.push(PickGame(app)); app.screen.choose(games.index(g))
    setup = app.screen
    check("%s: choosing it opens Set up, and the buttons fit" % gid, isinstance(setup, common.Setup) and fits(setup) == [], fits(setup))
    check("%s: it teaches: How to play has steps, each with a title and text" % gid,
          len(plugin.teach()) >= 1 and all(s.get("title") and s.get("text") for s in plugin.teach()))
    for n in sorted({plugin.min_players, plugin.max_players}):
        app.go_home(); app.push(common.Setup(app, plugin)); setup = app.screen
        setup.n = n
        setup.names = ["Ann", "Bob", "Cy", "Dee", "Eve", "Fay"][:plugin.max_players]
        setup.refresh(); setup.start()
        s = app.session
        ok = s is not None and s.game is plugin and len(s.players) == n
        check("%s, %d players: Start game begins a saved session" % (gid, n), ok and os.path.isfile(s.path))
        if not ok:
            continue
        fresh = engine.Session.load(s.path, app.plugins)       # found by tools/simulate.py, 23 Nov 2026
        check("%s, %d players: the game as first saved is the game in play" % (gid, n),
              json.dumps(fresh.state, sort_keys=True) == json.dumps(s.state, sort_keys=True))
        bad, crashed = [], None
        try:
            for i in range(60):
                app.toast = None
                bad += fits(app.screen)
                app.render()
                if not app.session:
                    break
                app.gesture("press")
                while app.session and not isinstance(app.screen, common.PlayBase) and len(app.stack) > 2:
                    app.gesture("press")            # step through any cards or questions the game raised
                    bad += fits(app.screen)
                    app.render()
                    if len(app.stack) > 12:
                        break
        except Exception as e:
            crashed = "%s: %s" % (type(e).__name__, e)
        check("%s, %d players: sixty presses of the button, no crash" % (gid, n), crashed is None, crashed)
        check("%s, %d players: every screen passed through fits" % (gid, n), bad == [], bad[:3])
        s = app.session or s
        board = plugin.scoreboard(s)
        check("%s, %d players: the scoreboard can be sent as JSON" % (gid, n), isinstance(json.dumps(board), str) and "rows" in board)
        phones_ok = True
        for seat in range(n):
            view = web.phone(app, seat) if app.session else {"playing": False}
            phones_ok &= isinstance(json.dumps(view), str)
        check("%s, %d players: every phone view can be sent as JSON" % (gid, n), phones_ok)
        if app.session:
            st = web.state(app)
            check("%s, %d players: the shared scoreboard state is complete" % (gid, n), st["playing"] and st["game"] == plugin.name and len(st["players"]) == n)
            before = json.dumps(s.state, sort_keys=True)
            n_log = len(s.log)
            again = engine.Session.load(s.path, app.plugins)
            check("%s, %d players: the saved game loads back exactly" % (gid, n), json.dumps(again.state, sort_keys=True) == before and len(again.log) == n_log)
            if s.d["undo"]:
                s.undo()
                check("%s, %d players: undo steps the log back by one" % (gid, n), len(s.log) == max(0, n_log - 1))
            app.go_home()
            found = engine.unfinished(paths.data("sessions"))
            check("%s, %d players: leaving for Home keeps the game resumable" % (gid, n), (found is not None and found[1]["game"] == gid) or len(s.log) == 0, found and found[1]["game"])
            app.resume_game(s.path)
            check("%s, %d players: Resume shows its play screen again" % (gid, n), app.session is not None and app.session.game is plugin and fits(app.screen) == [])
            app.session.finish(); app.end_game()
        over = app.screen
        check("%s, %d players: ending shows Game over, and it fits" % (gid, n), isinstance(over, common.GameOver) and fits(over) == [] and over.session.finished is not None, type(over).__name__)
        app.render()

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
