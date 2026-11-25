"""Play-through simulations: a careless, random table plays every game on her, many times.

    python tools/simulate.py                    every game, 10 tables each, 400 moves a table
    python tools/simulate.py --tables 50 --moves 1000
    python tools/simulate.py --game risk --seed 7 --tables 1 --show     one table again, move by move

Each table sets a game up with a random number of players and random options, then
makes random moves: taps on whatever buttons are showing, presses of the button,
double presses, holds. Time is hurried along so the slow clocks fire. It wanders
wherever the buttons lead: menus, Settings, Lookup, the dice, Game over, a new game.

After every move it checks that nothing crashed, that every button showing is on the
screen and big enough to touch, and that the scoreboard and each phone's page can be
sent. Every twentieth move it checks that the saved game loads back exactly.

It runs with no window, no sound, no network and no voice, on a data folder of its
own, so it is safe on the PC and on the Pi while she is running. The same seed plays
the same table again. Ends with "0 failed" or a list of what went wrong and how to
see it again.
"""
import argparse, json, os, random, sys, tempfile, time, traceback

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

NAMES = ["Ann", "Bob", "Cy", "Dee", "Eve", "Fay", "Gus", "Hal"]
BOUNDS = pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP)


class Table:
    def __init__(self, app, plugin, seed, show):
        self.app, self.plugin, self.seed, self.show = app, plugin, seed, show
        self.rng = random.Random("%s/%d" % (plugin.id if hasattr(plugin, "id") else plugin.name, seed))
        self.clock = time.monotonic()
        self.recent, self.found, self.step = [], [], 0
        self.counts = {"moves": 0, "games started": 0, "games finished": 0, "screens": set()}

    def fail(self, kind, detail):
        self.found.append((kind, str(detail), self.step, list(self.recent[-8:])))

    def note(self, what):
        self.recent.append(what)
        if self.show:
            print("  %4d  %-28s %s" % (self.step, type(self.app.screen).__name__, what))

    def start_game(self):
        app, p, rng = self.app, self.plugin, self.rng
        app.go_home(); app.toast = None
        app.push(common.Setup(app, p))
        setup = app.screen
        setup.n = rng.randint(p.min_players, p.max_players)
        setup.names = NAMES[:p.max_players]
        for o in setup.options:
            for _ in range(rng.randrange(len(o["choices"]))):
                setup.cycle(o)
        setup.refresh()
        self.note("set up %d players, %s" % (setup.n, dict(setup.opts)))
        setup.start()
        if app.session:
            self.counts["games started"] += 1

    def settle(self):
        """What the main loop does between moves, with the clock hurried along."""
        app = self.app
        self.clock += self.rng.choice((0.05, 0.3, 1.0, 4.0, 30.0))
        for _ in range(len(app._jobs)):
            if not app._jobs:
                break
            app._jobs.popleft()()
        for screen in list(app.stack):
            tick = getattr(screen, "tick", None)
            if tick:
                tick(self.clock)
        app.show_cards()
        if app.toast and self.rng.random() < 0.5:
            app.toast = None
        app.render()

    def move(self):
        app, rng = self.app, self.rng
        touchable = [w for w in app.screen.widgets if w.action]
        r = rng.random()
        if r < 0.50 and touchable:
            w = rng.choice(touchable)
            self.note("tap %r" % getattr(w, "label", "?"))
            app.tap(w.rect.center)
        elif r < 0.88:
            self.note("press")
            app.gesture("press")
        elif r < 0.96:
            self.note("press, double")
            app.gesture("press"); app.gesture("double")
        else:
            self.note("hold")
            app.gesture("hold_start"); app.gesture("hold_end")

    def look(self):
        """What must be true after any move."""
        app = self.app
        self.counts["screens"].add(type(app.screen).__name__)
        if not app.stack:
            self.fail("no screen left", "")
            app.push(Home(app))
        if len(app.stack) > 14:
            self.fail("screens piled up", [type(s).__name__ for s in app.stack])
            app.go_home()
        for w in app.screen.widgets:
            if w.action and (w.rect.h < 64 or w.rect.w < 64 or not BOUNDS.contains(w.rect)):
                self.fail("button does not fit", (type(app.screen).__name__, getattr(w, "label", "?"), tuple(w.rect)))
        s = app.session
        if s:
            board = s.game.scoreboard(s)
            if "rows" not in board:
                self.fail("scoreboard has no rows", board)
            json.dumps(board); json.dumps(web.state(app))
            for seat in range(len(s.players)):
                json.dumps(web.phone(app, seat))
            if self.step % 20 == 0 and os.path.isfile(s.path):
                again = engine.Session.load(s.path, app.plugins)
                if json.dumps(again.state, sort_keys=True) != json.dumps(s.state, sort_keys=True) or len(again.log) != len(s.log):
                    self.fail("saved game differs from the game in play", s.path)

    def play(self, moves):
        app = self.app
        idle = 0
        for self.step in range(1, moves + 1):
            try:
                if app.session is None:
                    idle += 1
                    if idle > 12 or self.step == 1:           # wandered the menus long enough: play again
                        self.start_game(); idle = 0
                else:
                    idle = 0
                was_over = any(isinstance(x, common.GameOver) for x in app.stack)
                self.move()
                self.settle()
                if not was_over and any(isinstance(x, common.GameOver) for x in app.stack):
                    self.counts["games finished"] += 1
                self.look()
                if not app.running:                           # it tapped Shut down; she would power off here
                    self.note("(shut down asked for; switched back on)")
                    app.running = True
                    app.go_home()
            except Exception as e:
                where = traceback.extract_tb(e.__traceback__)[-1]
                self.fail("crash", "%s: %s   at %s line %d" % (type(e).__name__, e, os.path.basename(where.filename), where.lineno))
                if self.show:
                    traceback.print_exc()
                try:
                    app.toast = None
                    app.go_home()
                except Exception:
                    del app.stack[:]; app.session = None; app.push(Home(app))
            self.counts["moves"] += 1
        try:
            if app.session:
                app.session.finish(); app.end_game()
            app.go_home()
        except Exception as e:
            self.fail("crash", "ending the game: %s: %s" % (type(e).__name__, e))


def main():
    ap = argparse.ArgumentParser(description="Random tables play every game.")
    ap.add_argument("--tables", type=int, default=10, help="tables per game")
    ap.add_argument("--moves", type=int, default=400, help="moves per table")
    ap.add_argument("--seed", type=int, default=1, help="number of the first table")
    ap.add_argument("--game", help="only this game (its id, such as risk)")
    ap.add_argument("--show", action="store_true", help="print every move")
    a = ap.parse_args()
    games, problems = load_games()
    for p in problems:
        print("game not loaded:", p)
    if a.game:
        games = [g for g in games if g["id"] == a.game]
        if not games:
            sys.exit("No game with that id.")
    app = App(hw.make("desktop", sound=False), load_games()[0], headless=True)
    app.push(Home(app))
    kinds, total = {}, 0
    began = time.time()
    for g in games:
        moves = started = finished = 0
        screens, bad = set(), 0
        for seed in range(a.seed, a.seed + a.tables):
            random.seed(seed)                                 # the dice and her remarks, the same each time
            t = Table(app, g["plugin"], seed, a.show)
            t.play(a.moves)
            moves += t.counts["moves"]; started += t.counts["games started"]; finished += t.counts["games finished"]
            screens |= t.counts["screens"]
            for kind, detail, step, recent in t.found:
                bad += 1
                key = (g["id"], kind, detail)
                if key not in kinds:
                    kinds[key] = [0, seed, step, recent]
                kinds[key][0] += 1
        total += moves
        print("%-9s %2d tables, %6d moves, %3d games started, %3d reached Game over, %2d kinds of screen: %s"
              % (g["id"], a.tables, moves, started, finished, len(screens), "nothing wrong" if not bad else "%d things wrong" % bad))
    print("\n%d moves in %.0f seconds" % (total, time.time() - began))
    for (gid, kind, detail), (n, seed, step, recent) in sorted(kinds.items(), key=lambda kv: -kv[1][0]):
        print("\nFAIL  %s: %s, %d times\n      %s" % (gid, kind, n, detail.encode("ascii", "replace").decode()))
        print("      first at move %d of: python tools/simulate.py --game %s --seed %d --tables 1 --moves %d --show" % (step, gid, seed, step))
        print("      the moves before it: " + "; ".join(recent).encode("ascii", "replace").decode())
    print("\n%d failed" % len(kinds))
    sys.exit(1 if kinds else 0)


if __name__ == "__main__":
    main()
