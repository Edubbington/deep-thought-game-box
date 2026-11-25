"""Tests for the app shell: button gestures, ring behaviours, the game list,
the dice, and the screens drawn without a window."""
import json, os, random, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import dice, ring, theme as T
from deepthought.gestures import Gestures
from deepthought.games import load_games

fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

# ---------------------------------------------------------------- gestures
def play(edges, ticks=()):
    """edges: [(time, down)]. ticks: extra times to call tick. Returns [(time, gesture)]."""
    g, out = Gestures(), []
    events = sorted([(t, 0, d) for t, d in edges] + [(t, 1, None) for t in ticks])
    for t, kind, d in events:
        g.edge(d, t) if kind == 0 else g.tick(t)
        out += [(t, name) for name in g.take()]
    return out

r = play([(0, True), (0.10, False)])
check("press is sent on release, with no wait", r == [(0.10, "press")], r)
r = play([(0, True), (0.10, False), (0.30, True), (0.40, False)])
check("second press inside 350 ms is a double", [n for _, n in r] == ["press", "double"], r)
r = play([(0, True), (0.10, False), (0.50, True), (0.60, False)])
check("second press after 350 ms is just another press", [n for _, n in r] == ["press", "press"], r)
r = play([(0, True), (0.1, False), (0.3, True), (0.4, False), (0.6, True), (0.7, False)])
check("three quick presses: press, double, press", [n for _, n in r] == ["press", "double", "press"], r)
r = play([(0, True), (2.0, False)], ticks=[0.3, 0.59, 0.61, 1.0])
check("hold starts at 600 ms and ends on release", r == [(0.61, "hold_start"), (2.0, "hold_end")], r)
r = play([(0, True), (0.7, False)])
check("a hold is noticed even with no frame in between", [n for _, n in r] == ["hold_start", "hold_end"], r)
r = play([(0, True), (6.0, False)], ticks=[1, 4.9, 5.1])
check("long hold at 5 s", [n for _, n in r] == ["hold_start", "long_hold", "hold_end"], r)
r = play([(0, True), (0.005, False), (0.010, True), (0.2, False)])
check("contact bounce inside 30 ms is ignored", r == [(0.2, "press")], r)
r = play([(0, True), (1.0, False), (1.1, True), (1.2, False)])
check("a press straight after a hold is not a double", [n for _, n in r] == ["hold_start", "hold_end", "press"], r)

# ---------------------------------------------------------------- ring
ok = True
for b in ring.BEHAVIOURS:
    for t in (0, 0.4, 1.3, 7.7):
        f = ring.frame(b, t, level=0.5)
        ok &= len(f) == 16 and all(len(c) == 3 and all(0 <= v <= 127 for v in c) for c in f)
check("every behaviour gives 16 colours, none above half brightness", ok)
check("off is dark", ring.frame("off", 3) == [(0, 0, 0)] * 16)
check("flare has gone after 1.5 s", ring.frame("flare", 1.6, t0=0) == [(0, 0, 0)] * 16 and max(ring.frame("flare", 0, t0=0)[0]) > 100)
f = ring.frame("thinking", 0.5)
check("thinking: one brightest dot", sum(1 for c in f if c == max(f)) == 1, f)
lit = [sum(1 for c in ring.frame("listening", 0, level=l) if c[0] > 100) for l in (0, 0.25, 0.5, 1)]
check("listening fills with the level", lit == [0, 4, 8, 16], lit)
f = ring.frame("round", 0.5, colour=ring.ROUND_COLOURS["red"], side=1)
check("round: the active side's half is the brighter one", min(f[8:]) > max(f[:8]), f)
try:
    ring.frame("disco", 0); bad = False
except ValueError:
    bad = True
check("an unknown behaviour is an error", bad)
rs = ring.RingState(); rs.set("round", colour=(255, 0, 0), side=0); rs.set("flare", colour=(255, 255, 255))
a = rs.frame(10.0); b = rs.frame(10.5); c = rs.frame(11.6)
check("a flare plays once, then the ring goes back to what it was doing",
      a[0][2] > 100 and 0 < b[0][2] < a[0][2] and rs.now[0] == "round" and c[0][2] == 0, (a[0], b[0], c[0], rs.now))

# ---------------------------------------------------------------- game list
os.environ["DT_DATA"] = tempfile.mkdtemp()
os.environ["DT_CONTENT_DB"] = os.path.join(os.environ["DT_DATA"], "none.db")
games, problems = load_games()
ids = [g["id"] for g in games]
check("the launch games load, in order, with no problems",
      ids[:5] == ["killteam", "wh40k", "dnd", "mtg", "risk"] and "tally" in ids and not problems, (ids, problems))
check("Risk and the any-game scorekeeper are playable", all(g["status"] == "ready" and g["plugin"] for g in games if g["id"] in ("risk", "tally")))
tmp = tempfile.mkdtemp()
for name, body in (("good", {"id": "good", "name": "Good", "blurb": "x", "order": 1, "trackers": [{"name": "Points"}]}),
                   ("plain", {"id": "plain", "name": "Plain", "blurb": "x", "order": 2}),
                   ("noname", {"id": "noname", "blurb": "x", "order": 2}),
                   ("wrongid", {"id": "other", "name": "W", "blurb": "x", "order": 3})):
    os.makedirs(os.path.join(tmp, name))
    json.dump(body, open(os.path.join(tmp, name, "game.json"), "w"))
os.makedirs(os.path.join(tmp, "broken"))
open(os.path.join(tmp, "broken", "game.json"), "w").write("{not json")
os.makedirs(os.path.join(tmp, "empty_folder"))
g2, p2 = load_games(tmp)
check("a new folder with trackers in its game.json is a playable game",
      [(g["id"], g["status"]) for g in g2] == [("good", "ready"), ("plain", "planned")], [(g["id"], g["status"]) for g in g2])
check("bad game files are reported, not fatal", len(p2) == 3 and all(n in " ".join(p2) for n in ("broken", "noname", "wrongid")), p2)
shutil.rmtree(tmp)

# ---------------------------------------------------------------- dice
rng = random.Random(1)
ok = True
for sides in dice.SIDES:
    for n in (1, 6, 36):
        res = dice.roll(n, sides, rng)
        ok &= len(res) == n and all(1 <= v <= sides for v in res) and res == sorted(res, reverse=True)
check("rolls: right count, in range, highest first", ok)
check("dice count is held between 1 and 36", len(dice.roll(0, 6, rng)) == 1 and len(dice.roll(99, 6, rng)) == 36)
counts = [0] * 7
for v in dice.roll(36, 6, random.Random(2)) * 1 + [x for _ in range(200) for x in dice.roll(36, 6, rng)]:
    counts[v] += 1
check("7,236 D6 rolls: every face within 15% of even", all(abs(c - 1206) < 181 for c in counts[1:]), counts)
try:
    dice.roll(2, 8); bad = False
except ValueError:
    bad = True
check("no D8", bad)
S = dice.summary
check("summary: two sixes", S([6, 6, 5, 4, 2, 1]) == "Two sixes, one one", S([6, 6, 5, 4, 2, 1]))
check("summary: one six", S([6, 5, 4, 3, 2, 2]) == "One six", S([6, 5, 4, 3, 2, 2]))
check("summary: ones only", S([5, 4, 1, 1, 1]) == "Three ones", S([5, 4, 1, 1, 1]))
check("summary: neither", S([5, 4, 3, 2]) == "No sixes, no ones", S([5, 4, 3, 2]))
check("summary: three dice or fewer add the total", S([6, 3]) == "One six · total 9", S([6, 3]))
check("summary: D3 total", S([3, 2, 2], 3) == "Total 7")
check("summary: D20", S([20], 20) == "Natural twenty" and S([1], 20) == "Natural one" and S([13], 20) == "Rolled 13" and S([17, 4], 20) == "Highest 17, lowest 4")
M = dice.mood
check("mood", [M([6, 6]), M([1, 1, 1]), M([6, 6, 3, 2]), M([5, 4, 3, 2]), M([5, 4, 2]), M([20], 20), M([1], 20), M([6])] ==
      ["all_high", "all_low", "good", "poor", "plain", "all_high", "all_low", "plain"])
recent, ok = [], True
for _ in range(60):
    line = dice.remark([5, 4, 2], 6, recent, rng)
    ok &= line not in recent[-2:]
    recent.append(line)
check("remarks: never one of the last two again", ok)
all_lines = [l for ls in dice.REMARKS.values() for l in ls]
check("remarks: no exclamation marks, none repeated", not any("!" in l for l in all_lines) and len(set(all_lines)) == len(all_lines))

# ---------------------------------------------------------------- screens
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens.home import Home
from deepthought.screens.pick_game import PickGame
from deepthought.screens.dice import Dice, dice_layout
from deepthought.shots import all_shots

fake = [dict(id="g%d" % i, name=n, blurb="A blurb", order=i, status="planned", plugin=None)
        for i, n in enumerate(["Alpha", "Beta", "Gamma", "Delta", "Omega"])]
app = App(hw.make("desktop", sound=False), fake, headless=True)

def screen_ok(screen):
    """Buttons at least 64 px tall, inside the screen, under the strip, not overlapping."""
    ws, bad = [w for w in screen.widgets if w.action], []
    for w in ws:
        if w.rect.h < T.MIN_BUTTON or w.rect.w < T.MIN_BUTTON: bad.append(("small", w.label, tuple(w.rect)))
        if not pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP).contains(w.rect): bad.append(("outside", w.label))
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if a.rect.colliderect(b.rect): bad.append(("overlap", a.label, b.label))
    return bad

app.stack = []; app.push(Home(app)); home = app.screen
check("Home: buttons big enough, on screen, not overlapping", screen_ok(home) == [], screen_ok(home))
app.surface.fill((255, 0, 255)); app.render()
check("Home: strip and ground are the theme colours", app.surface.get_at((5, 5))[:3] == T.PANEL and app.surface.get_at((5, 470))[:3] == T.GROUND)
app.gesture("press")
check("Home: the button opens Pick a game", isinstance(app.screen, PickGame))
pick = app.screen
check("Pick a game: buttons fine on page 1", screen_ok(pick) == [], screen_ok(pick))
check("Pick a game: 5 games make 2 pages, 4 tiles then 1", pick.pages() == 2 and sum(w.style == "tile" for w in pick.widgets) == 4)
pick.more()
check("Pick a game: page 2 shows the fifth game, selected", [w.label for w in pick.widgets if w.action][:1] == ["Omega"] and tuple(pick.widgets[0].rect.size) == (373, 68) and pick.widgets[0].selected and screen_ok(pick) == [])
app.toast = None; app.gesture("press")
check("Pick a game: an unbuilt game says so and stays put", app.toast and "Omega is not built yet" in app.toast and app.screen is pick, app.toast)
app.toast = None; app.tap((60, 420))
check("Pick a game: Back returns to Home", isinstance(app.screen, Home))
app.tap((100, 300))
check("Home: tapping Dice opens Dice", isinstance(app.screen, Dice))
d = app.screen; d.rng = random.Random(3)
check("Dice: buttons fine", screen_ok(d) == [], screen_ok(d))
app.gesture("press")
check("Dice: the button rolls six D6", d.results is not None and len(d.results) == 6 and d.line in sum(dice.REMARKS.values(), []))
app.tap((318, 430)); app.tap((318, 430))
check("Dice: plus twice makes 8 and clears the old roll", d.n == 8 and d.results is None and d.title == "8 dice")
for _ in range(10): app.tap((174, 430))
check("Dice: minus stops at 1", d.n == 1 and d.title == "1 die")
app.tap((550, 430)); app.tap((700, 430))
check("Dice: D20 then Roll gives one D20", d.sides == 20 and len(d.results) == 1 and 1 <= d.results[0] <= 20)
ok = True
for n in range(1, 37):
    size, spots = dice_layout(n)
    ok &= len(spots) == n and all(20 <= x and x + size <= 780 and y + size <= 256 for x, y in spots)
check("Dice: 1 to 36 dice all fit above the summary line", ok)
texts_ok = all(T.font("text", 22).size(g["blurb"])[0] <= 325 for g in games)
check("every game blurb fits its tile without being cut", texts_ok, [(g["blurb"], T.font("text", 22).size(g["blurb"])[0]) for g in games])
check("no font under 22 px can be asked for", T.font("text", 10).get_height() == T.font("text", 22).get_height())
app.gesture("press"); app.gesture("double")
check("Dice: double press goes back", isinstance(app.screen, Home))
app.gesture("long_hold")
check("Home: a 5 second hold asks before shutting down", app.screen.title == "Shut down?" and app.running)
app.gesture("press")
check("Shut down prompt: the button's answer is Stay on", isinstance(app.screen, Home) and app.running)
app.gesture("long_hold"); app.tap((600, 430))
check("Shut down prompt: tapping Shut down stops the loop", app.running is False)
app.flip = True
check("flipped display: a touch at one corner lands on the opposite one", app._pos((0, 0)) == (799, 479) and app._pos((799, 479)) == (0, 0))

real = App(hw.make("desktop", sound=False), games, headless=True)
real.push(Home(real))
shots = tempfile.mkdtemp()
paths_ = all_shots(real, shots)
sizes = [pygame.image.load(p).get_size() for p in paths_]
check("%d screenshots drawn, all 800x480" % len(paths_), len(paths_) >= 8 and set(sizes) == {(800, 480)}, sizes)
shutil.rmtree(shots)

# the strip across the top of the screen stands in for the button (the real one's switch does not work)
import pygame as pg
from deepthought import theme as T2
from deepthought.gestures import HOLD as HOLD_S
strip_app = App(hw.make("desktop", sound=False), games, headless=True)
strip_app.push(Home(strip_app))
seen = []
strip_app.gesture = lambda name: seen.append(name)
def finger(down, pos, t):
    strip_app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN if down else pg.MOUSEBUTTONUP, button=1, pos=pos), t)
    for name in strip_app.hw.gestures(t): strip_app.gesture(name)
def later(t):
    for name in strip_app.hw.gestures(t): strip_app.gesture(name)
finger(True, (400, 30), 100.0); finger(False, (400, 30), 100.1)
check("a tap on the strip across the top is a press of the button", seen == ["press"], seen)
finger(True, (400, 30), 100.2); finger(False, (400, 30), 100.3)
check("a second tap straight after is a double, as with the real button", seen == ["press", "double"], seen)
del seen[:]
finger(True, (400, 30), 110.0); later(110.0 + HOLD_S + 0.1)
held = list(seen) == ["hold_start"] and strip_app.strip_down
finger(False, (700, 300), 112.0)
check("a finger held on the strip is a hold, ended wherever it lifts", held and seen == ["hold_start", "hold_end"] and not strip_app.strip_down, seen)
del seen[:]
strip_app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(400, 30)), 120.0)
strip_app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=(400, 30)), 120.0)
later(120.0); later(120.1)
check("a tap that comes and goes inside one frame is still one press", seen == ["press"], seen)
del seen[:]
finger(True, (400, T2.STRIP + 5), 130.0); finger(False, (400, T2.STRIP + 5), 130.1)
check("a touch below the strip is never the button", seen == [], seen)
strip_app.strip_down = True; strip_app.render()
check("while the strip is held a thick bar shows under it", strip_app.surface.get_at((400, T2.STRIP - 3))[:3] == pg.Color(T2.TEXT)[:3])
strip_app.strip_down = False


print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
