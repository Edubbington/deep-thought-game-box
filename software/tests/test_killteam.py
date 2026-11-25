"""Tests for the Kill Team plugin: every sum the box enforces, worked by hand,
and every screen driven the way a table would drive it, in all three modes."""
import json, os, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import engine, paths, theme as T
from deepthought.games import load_games
from deepthought.games.killteam import rules

fails, count = [], [0]
def check(name, cond, detail=""):
    count[0] += 1
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

games, problems = load_games()
plugins = {g["id"]: g["plugin"] for g in games if g["plugin"]}
kt = plugins.get("killteam")
info = next(g for g in games if g["id"] == "killteam")
check("the game list loads Kill Team with no problems of its own", kt is not None and not [p for p in problems if "killteam" in p], problems)
check("game.json is as it was: id, name, order", (info["id"], info["name"], info["order"]) == ("killteam", "Kill Team", 10) and len(info["blurb"]) <= 28, info)
check("two players, no more, no fewer", (kt.min_players, kt.max_players) == (2, 2))
check("three set-up options: mode, length, Tac Ops", [o["key"] for o in kt.options] == ["mode", "length", "tacops"] and kt.options[0]["choices"] == ["Teach", "Reminder", "Silent"])

# ---------------------------------------------------------------- the sums
check("command points: turning point 1 gives one each, whoever has the initiative", rules.cp_gain(1, 0) == [1, 1] and rules.cp_gain(1, 1) == [1, 1])
check("command points: afterwards 1 for the initiative holder, 2 for the other", rules.cp_gain(2, 0) == [1, 2] and rules.cp_gain(3, 1) == [2, 1] and rules.cp_gain(4, 0) == [1, 2])
check("both sides start with 2 command points (Knowledge Base, Part 2)", rules.START_CP == 2)
check("kill grades: a team of 5 gives a grade per operative", rules.grade_marks(5) == [1, 2, 3, 4, 5])
check("kill grades: a team of 6: 1.2, 2.4, 3.6, 4.8, 6 round to 1, 2, 4, 5, 6", rules.grade_marks(6) == [1, 2, 4, 5, 6], rules.grade_marks(6))
check("kill grades: a team of 8: 1.6, 3.2, 4.8, 6.4, 8 round to 2, 3, 5, 6, 8", rules.grade_marks(8) == [2, 3, 5, 6, 8], rules.grade_marks(8))
check("kill grades: a team of 10: 2, 4, 6, 8, 10", rules.grade_marks(10) == [2, 4, 6, 8, 10])
check("kill grades: a team of 14: 2.8, 5.6, 8.4, 11.2, 14 round to 3, 6, 8, 11, 14", rules.grade_marks(14) == [3, 6, 8, 11, 14], rules.grade_marks(14))
check("kill grades: never more kills than operatives, never fewer than one", rules.grade_marks(1) == [1, 1, 1, 1, 1] and rules.grade_marks(2) == [1, 1, 1, 2, 2] and all(rules.grade_marks(n)[-1] == n for n in range(1, 21)))
check("kill grade: 6 strong, none lost is 0, 1 lost is 1, 3 lost is 2, 4 lost is 3, all lost is 5",
      [rules.kill_grade(6, k) for k in (0, 1, 3, 4, 6)] == [0, 1, 2, 3, 5], [rules.kill_grade(6, k) for k in (0, 1, 3, 4, 6)])
check("kill grade: 8 strong, 1 lost is still 0; 2 lost is 1; 7 lost is 4", [rules.kill_grade(8, k) for k in (1, 2, 7)] == [0, 1, 4])
check("primary bonus: half, rounded up: 0 1 1 2 2 3 3 for scores 0 to 6", [rules.primary_bonus(v) for v in range(7)] == [0, 1, 1, 2, 2, 3, 3])
check("primary bonus: never more than 3", rules.primary_bonus(7) == 3 and rules.primary_bonus(12) == 3 and rules.BONUS_MAX == 3)
check("each op stops at 6, so the most a side can score is 6 + 6 + 6 + 3 = 21", rules.CAP == 6 and rules.total({"crit": 6, "tac": 6, "kill": 6}, rules.primary_bonus(6)) == 21)
check("activations: the other side goes next while it has any", rules.next_active(0, [2, 2]) == 1 and rules.next_active(1, [2, 1]) == 0)
check("activations: when the other side has none, the same side keeps going", rules.next_active(0, [2, 0]) == 0)
check("activations: when nobody has any, the phase is over", rules.next_active(0, [0, 0]) is None)
check("activations: the initiative holder starts, unless they have nobody", rules.first_active(1, [3, 3]) == 1 and rules.first_active(1, [3, 0]) == 0 and rules.first_active(0, [0, 0]) is None)
check("counteract: the side with nothing ready, while the other still activates", rules.counteract(0, [2, 0], [3, 3]) == 1 and rules.counteract(1, [0, 1], [2, 2]) == 0)
check("counteract: not while both have operatives ready", rules.counteract(0, [2, 1], [3, 3]) is None)
check("counteract: not for a side with nobody left on the table", rules.counteract(0, [2, 0], [3, 0]) is None)
check("Crit Op first scores at the end of turning point 2", [rules.crit_open(1, "end"), rules.crit_open(2, "strategy"), rules.crit_open(2, "firefight"), rules.crit_open(2, "end"), rules.crit_open(3, "strategy")] == [False, False, False, True, True])
check("result: higher total wins, equal totals are a draw", rules.result([{"crit": 2, "tac": 0, "kill": 1}, {"crit": 1, "tac": 0, "kill": 0}], [1, 0]) == ([4, 1], 0) and rules.result([{"crit": 2, "tac": 0, "kill": 0}, {"crit": 0, "tac": 0, "kill": 2}], [1, 1])[1] is None)

# ---------------------------------------------------------------- a session
class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t
clock = Clock()

def new(mode="Reminder", length="Full", tac="On", a=6, b=6, folder=None):
    s = engine.Session(kt, ["Ethan", "Trevor"], {"mode": mode, "length": length, "tacops": tac}, folder, clock)
    for side, n in ((0, a), (1, b)):
        for _ in range(abs(n - 6)):
            s.do(ev="ops", side=side, delta=1 if n > 6 else -1)
    return s
def begin(s, init=0):
    """From set-up or a Strategy phase into the Firefight phase."""
    if s.state["phase"] == "setup": s.do(ev="next")
    s.do(ev="init", side=init); s.do(ev="next")
def fight(s):
    """Press Next until the Firefight phase is over. Returns how many presses it took."""
    n = 0
    while s.state["phase"] == "firefight" and n < 100:
        s.do(ev="next"); n += 1
    return n
def score(s, side, cat, n=1):
    return [s.do(ev="score", side=side, cat=cat, delta=1) for _ in range(n)]

s = new()
st = s.state
check("new game: set-up, no turning point yet, 6 operatives and 2 command points each",
      (st["tp"], st["phase"], st["start"], st["cp"], st["tp_max"]) == (0, "setup", [6, 6], [2, 2], 4) and kt.active(st) is None, st)
check("new game: strip says Kill Team, Set up", kt.strip(s) == ("Kill Team", "Set up"))
check("modes and options are read from Set up", new("Teach").state["mode"] == "teach" and new("Silent").state["mode"] == "silent" and new(tac="Off").state["tacops"] is False and st["tacops"] is True)
check("tutorial length: 2 turning points; the Set up screen's own wording works too",
      new(length="Tutorial").state["tp_max"] == 2 and new(length="Tutorial, 2 rounds").state["tp_max"] == 2 and new(length="Full, 4 rounds").state["tp_max"] == 4)
check("with no options at all: Teach, full length, Tac Ops on", (lambda z: (z["mode"], z["tp_max"], z["tacops"]))(engine.Session(kt, ["A", "B"], {}, None, clock).state) == ("teach", 4, True))
s.do(ev="ops", side=0, delta=-3); s.do(ev="ops", side=1, delta=-4)
check("operatives per side are set by taps: 3 against 2", st["start"] == [3, 2])
z = new(a=1)
check("a kill team needs at least one operative", "at least one" in z.do(ev="ops", side=0, delta=-1)[0] and z.state["start"][0] == 1)
z = new(a=20)
check("20 operatives is the most the box counts", "the most" in z.do(ev="ops", side=0, delta=1)[0] and z.state["start"][0] == 20)
check("nothing is scored, lost or initiated during set-up",
      "before the game" in s.do(ev="down", side=0, ready=False)[0] and "Strategy phase" in s.do(ev="init", side=0)[0] and "end of a turning point" in s.do(ev="score", side=0, cat="kill", delta=1)[0] and "Nothing has been scored" in s.do(ev="correct", side=0, cat="kill", delta=1)[0] and len(s.log) == 2)
said = s.do(ev="next")
check("Begin: turning point 1, Strategy phase, and she says so", (st["tp"], st["phase"]) == (1, "strategy") and said == ["Turning point one. Roll for initiative."] and kt.strip(s) == ("Turning point 1 of 4", "Strategy"), said)
check("operatives cannot be changed once the game has begun", "already on the table" in s.do(ev="ops", side=0, delta=1)[0] and st["start"] == [3, 2])
check("Strategy: Next is refused until someone has the initiative", "initiative" in s.do(ev="next")[0] and st["phase"] == "strategy" and len(s.log) == 3)
said = s.do(ev="init", side=0)
check("turning point 1: one command point each: 2 + 1 = 3 and 3", st["cp"] == [3, 3] and st["init"] == 0 and said == ["One command point each. Ethan 3, Trevor 3."], (st["cp"], said))
check("tapping the same winner again changes nothing", "already has" in s.do(ev="init", side=0)[0] and st["cp"] == [3, 3])
s.do(ev="init", side=1)
check("changing the winner in turning point 1: still 3 and 3, not 4 and 4", st["cp"] == [3, 3] and st["init"] == 1)
s.do(ev="init", side=0)
said = s.do(ev="next")
check("Firefight: Ethan has the initiative and activates first; 3 and 2 activations", (st["phase"], st["active"], st["left"]) == ("firefight", 0, [3, 2]) and said == ["Firefight. Ethan activates first."] and s.active_name() == "Ethan", (st["left"], said))
trail = []
for _ in range(3):
    s.do(ev="next"); trail.append((st["active"], list(st["left"])))
check("activations alternate: Trevor [2,2], Ethan [2,1], Trevor [1,1]", trail == [(1, [2, 2]), (0, [2, 1]), (1, [1, 1])], trail)
check("no counteract while both sides have someone ready", rules.counteract(st["active"], st["left"], kt.alive(st)) is None and st["out"] is None)
said = s.do(ev="next")
check("Trevor runs out: Ethan keeps activating and the box prompts counteract",
      (st["active"], st["left"], st["out"]) == (0, [1, 0], 1) and said == ["Trevor has no ready operatives left. Ethan keeps activating. Trevor may counteract after each."], (st, said))
check("the play prompt says the same", kt.prompt(st) == ("Ethan, keep activating.", "Trevor has none ready, and may counteract after each one."), kt.prompt(st))
said = s.do(ev="next")
check("after 3 + 2 = 5 activations the Firefight phase ends", (st["phase"], st["active"], st["left"]) == ("end", None, [0, 0]) and len([e for e in s.log if e["ev"] == "next"]) == 7, st["left"])
check("end of turning point 1: she says the Crit Op does not score yet", said == ["Turning point one ends. The Crit Op does not score yet."], said)

# ---- scoring rules
check("turning point 1: Crit Op scoring is refused", s.do(ev="score", side=0, cat="crit", delta=1) == ["Nothing scores from the Crit Op in the first turning point."] and st["vp"][0]["crit"] == 0)
check("turning point 1: Kill Op and Tac Op can score", s.do(ev="score", side=0, cat="kill", delta=1) == [] and s.do(ev="score", side=1, cat="tac", delta=1) == [] and st["vp"][0]["kill"] == 1 and st["vp"][1]["tac"] == 1)
check("a score cannot go below nothing", "no Crit Op points" in s.do(ev="score", side=0, cat="crit", delta=-1)[0] and "no Kill Op points" in s.do(ev="score", side=1, cat="kill", delta=-1)[0])
check("there are only three ops, and only two sides", "three ops" in s.do(ev="score", side=0, cat="bonus", delta=1)[0] and "two sides" in s.do(ev="score", side=2, cat="kill", delta=1)[0] and "do not know" in s.do(ev="dance")[0])
n_log = len(s.log)
check("undo takes back the last score, and only that", s.undo() and st is not s.state and s.state["vp"][1]["tac"] == 0 and s.state["vp"][0]["kill"] == 1 and len(s.log) == n_log - 1)
st = s.state
said = s.do(ev="next")
check("next turning point: 2 of 4, Strategy, initiative open again, a line from her", (st["tp"], st["phase"], st["init"], st["had"]) == (2, "strategy", None, 0) and said == ["Turning point two. The part where plans meet other plans."], said)
check("turning point 2 prompt: a tie goes to whoever did not have it", kt.prompt(st)[1] == "A tie goes to Trevor, who did not have it. Tap the winner.", kt.prompt(st))
said = s.do(ev="init", side=1)
check("turning point 2: Trevor has the initiative and gains 1 (4); Ethan gains 2 (5)", st["cp"] == [5, 4] and said == ["Trevor gains one command point, Ethan gains two. Ethan 5, Trevor 4."], (st["cp"], said))
s.do(ev="init", side=0)
check("changing the winner takes the gain back first: Ethan 3 + 1 = 4, Trevor 3 + 2 = 5", st["cp"] == [4, 5])
check("spending: one command point by tap", s.do(ev="cp", side=0, delta=-1) == [] and st["cp"] == [3, 5])
for _ in range(3): s.do(ev="cp", side=0, delta=-1)
check("spending: none left means none to spend", st["cp"] == [0, 5] and s.do(ev="cp", side=0, delta=-1) == ["Ethan has no command points to spend."] and st["cp"] == [0, 5])
check("a gain already spent cannot be handed to the other side; undo instead", "already been spent" in s.do(ev="init", side=1)[0] and st["init"] == 0 and st["cp"] == [0, 5])
check("gaining: a command point by tap, and there is no upper limit", s.do(ev="cp", side=1, delta=20) == [] and st["cp"] == [0, 25])
s.do(ev="next")
check("no scoring in a phase that does not score: Firefight", s.do(ev="score", side=0, cat="kill", delta=1) == ["Points are scored at the end of a turning point. To fix a number, use the scoreboard."] and st["vp"][0]["kill"] == 1)
check("a correction from the scoreboard is allowed in the Firefight phase", s.do(ev="correct", side=0, cat="kill", delta=2) == [] and st["vp"][0]["kill"] == 3)
check("but not a Crit Op point before the end of turning point 2", "first scores at the end of turning point two" in s.do(ev="correct", side=0, cat="crit", delta=1)[0] and st["vp"][0]["crit"] == 0)
check("and a correction cannot pass the cap: 3 + 4 = 7", s.do(ev="correct", side=0, cat="kill", delta=4) == ["Kill Op stops at 6 points."] and st["vp"][0]["kill"] == 3)
fight(s)
check("turning point 2 ends: she says to score it", st["phase"] == "end" and s.log[-1]["ev"] == "next")
check("turning point 2: the Crit Op now scores, up to 6", score(s, 0, "crit", 6) == [[]] * 6 and st["vp"][0]["crit"] == 6)
check("Crit Op cap: a seventh point is refused", s.do(ev="score", side=0, cat="crit", delta=1) == ["Crit Op stops at 6 points."] and st["vp"][0]["crit"] == 6)
check("Tac Op cap: six, then no more", score(s, 1, "tac", 6) == [[]] * 6 and s.do(ev="score", side=1, cat="tac", delta=1) == ["Tac Op stops at 6 points."] and st["vp"][1]["tac"] == 6)
check("Kill Op cap: 3 + 3 = 6, then no more", score(s, 0, "kill", 3) == [[]] * 3 and s.do(ev="score", side=0, cat="kill", delta=1) == ["Kill Op stops at 6 points."] and st["vp"][0]["kill"] == 6)
check("totals: Ethan 6 + 0 + 6 = 12, Trevor 6", kt.totals(st) == [12, 6] and kt.leader(st) == 0)
s.do(ev="next"); s.do(ev="init", side=1)
check("turning point 3 strategy: a Crit Op correction is now allowed", s.do(ev="correct", side=1, cat="crit", delta=1) == [] and st["vp"][1]["crit"] == 1)

# ---- Tac Ops off
z = new(tac="Off", a=1, b=1); begin(z); fight(z)
check("Tac Ops off: Tac Op points and a Tac Op primary are refused", z.do(ev="score", side=0, cat="tac", delta=1) == ["Tac Ops are off for this game."] and z.do(ev="primary", side=0, cat="tac") == ["Tac Ops are off for this game."] and kt.cats(z.state) == [("crit", "Crit Op"), ("kill", "Kill Op")])

# ---- operatives down
z = new(); begin(z); zs = z.state
check("six against six: 6 activations each to come", zs["left"] == [6, 6] and zs["active"] == 0)
check("down, not yet activated: Trevor has one fewer activation to come", z.do(ev="down", side=1, ready=True) == ["Ethan reaches kill grade 1."] and zs["lost"] == [0, 1] and zs["left"] == [6, 5])
check("down, 'already activated', when none of that side has: refused", z.do(ev="down", side=1, ready=False) == ["None of Trevor's operatives has activated yet."] and zs["lost"] == [0, 1])
check("the one activating now dies: Ethan's count drops once, now", z.do(ev="down", side=0, ready=False) == ["Trevor reaches kill grade 1."] and zs["lost"] == [1, 1] and zs["left"] == [5, 5] and zs["fallen"])
z.do(ev="next")
check("and Next does not take it off a second time", (zs["active"], zs["left"], zs["fallen"]) == (1, [5, 5], False))
z.do(ev="next")
check("Trevor finishes one: 5 and 4, Ethan to go", (zs["active"], zs["left"]) == (0, [5, 4]))
check("an expended Trevor operative dies: no activation is lost; 2 of 6 gone is grade 2", z.do(ev="down", side=1, ready=False) == ["Ethan reaches kill grade 2."] and zs["lost"] == [1, 2] and zs["left"] == [5, 4])
check("Ethan mid-activation has 4 others waiting, so 4 can die unactivated", [z.do(ev="down", side=0, ready=True) for _ in range(4)][-1] != [] and zs["left"] == [1, 4] and zs["lost"] == [5, 2])
check("the fifth cannot: only the one activating is left", z.do(ev="down", side=0, ready=True) == ["Ethan has no operative still waiting to activate."] and zs["left"] == [1, 4])
check("Trevor's kill grade against Ethan's 6: 5 lost is grade 4; Ethan's against Trevor: 2 lost is grade 2", kt.grades(zs) == [2, 4], kt.grades(zs))
check("put one back: the count of lost drops; it counts as already activated", "already activated" in z.do(ev="revive", side=0)[0] and zs["lost"] == [4, 2] and zs["left"] == [1, 4])
n = fight(z)
check("the phase then takes 1 + 4 = 5 more activations", n == 5 and zs["phase"] == "end", n)
z = new(a=2, b=1); z.do(ev="next")
check("a loss outside the Firefight phase needs no question; a team of one, gone, is grade 5", z.do(ev="down", side=1) == ["Ethan reaches kill grade 5."] and z.state["lost"] == [0, 1])
check("kills cannot exceed starting operatives", z.do(ev="down", side=1) == ["Trevor has no operatives left to lose."] and z.state["lost"] == [0, 1])
check("nobody can come back who was never lost", z.do(ev="revive", side=0) == ["Ethan has lost nobody."])
z.do(ev="init", side=1); said = z.do(ev="next")
check("a wiped-out side cannot activate or counteract: Ethan just activates", (z.state["active"], z.state["left"], z.state["out"]) == (0, [2, 0], None) and said == ["Firefight. Ethan activates first."] and kt.prompt(z.state)[0] == "Ethan, pick an operative.", said)
check("it takes Ethan's 2 activations to end the phase", fight(z) == 2)
z = new(a=1, b=3); z.do(ev="next"); z.do(ev="init", side=0); said = z.do(ev="next"); said2 = z.do(ev="next")
check("one against three: after Ethan's only activation Trevor keeps going and Ethan may counteract", z.state["active"] == 1 and z.state["left"] == [0, 3] and z.state["out"] == 0 and "Ethan may counteract" in said2[0], said2)
check("the counteract prompt is said once in a turning point, not after every activation", z.do(ev="next") == [] and z.do(ev="next") == [] and z.state["left"] == [0, 1])

# ---- a whole game, by hand
g = new(a=2, b=2)
cps = []
for tp in (1, 2, 3, 4):
    begin(g, 0); cps.append(list(g.state["cp"]))
    check("turning point %d: 2 + 2 = 4 activations" % tp, fight(g) == 4 and g.state["tp"] == tp)
    if tp < 4:
        if tp == 2: score(g, 0, "crit", 2); score(g, 1, "crit", 2); score(g, 0, "tac", 2); score(g, 1, "kill", 1)
        if tp == 3: score(g, 0, "crit", 1); score(g, 1, "crit", 3); score(g, 1, "tac", 3)
        last_line = g.do(ev="next")
gs = g.state
check("command points over four turning points, Ethan always with the initiative: 3-3, 4-5, 5-7, 6-9", cps == [[3, 3], [4, 5], [5, 7], [6, 9]], cps)
check("the last turning point has its own line", last_line == ["The last turning point. Score what can be scored; mourn the rest later."] and gs["tp"] == 4 and gs["phase"] == "end", last_line)
score(g, 0, "crit", 2); score(g, 0, "kill", 3)
check("before the bonus: Ethan 5 + 2 + 3 = 10, Trevor 5 + 3 + 1 = 9", kt.totals(gs) == [10, 9] and gs["vp"][0] == {"crit": 5, "tac": 2, "kill": 3} and gs["vp"][1] == {"crit": 5, "tac": 3, "kill": 1})
check("the game cannot end until both primary ops are named", g.do(ev="next") == ["Ethan and Trevor: reveal your primary op first."] and g.finished is None)
g.do(ev="primary", side=0, cat="crit")
check("still not with only one named", g.do(ev="next") == ["Trevor: reveal your primary op first."] and kt.over(gs) is None)
check("a primary op is one of the three", "Crit Op, the Tac Op or the Kill Op" in g.do(ev="primary", side=1, cat="luck")[0])
g.do(ev="primary", side=1, cat="kill"); g.do(ev="primary", side=1, cat="tac")
check("a primary op can be changed before the end", gs["primary"] == ["crit", "tac"])
said = g.do(ev="next")
check("the bonus: Ethan half of 5 rounded up = 3; Trevor half of 3 rounded up = 2", gs["bonus"] == [3, 2] and gs["done"])
check("game over after the last End phase: 13 to 11, Ethan wins", g.finished and g.finished["winner"] == "Ethan" and g.finished["lines"][0] == "13 to 11", g.finished)
check("the result lines carry each side's working", g.finished["lines"][1:] == ["Ethan: Crit 5, Tac 2, Kill 3, primary +3", "Trevor: Crit 5, Tac 3, Kill 1, primary +2"], g.finished["lines"])
check("a finished game takes no more events", g.do(ev="next") == ["The game is over."] and g.do(ev="score", side=0, cat="kill", delta=1) == ["The game is over."])
check("undo reopens the finished game with the bonus taken back off", g.undo() and g.finished is None and g.state["bonus"] == [0, 0] and g.state["phase"] == "end" and kt.totals(g.state) == [10, 9])

d = new(a=1, b=1)
for tp in (1, 2, 3, 4):
    begin(d, tp % 2); fight(d)
    if tp < 4: d.do(ev="next")
score(d, 0, "crit", 4); score(d, 0, "kill", 1); score(d, 1, "kill", 4); score(d, 1, "tac", 1)
d.do(ev="primary", side=0, cat="crit"); d.do(ev="primary", side=1, cat="kill"); d.do(ev="next")
check("a draw: 4 + 1 + bonus 2 = 7 against 4 + 1 + bonus 2 = 7, no winner", d.finished and d.finished["winner"] is None and d.finished["lines"][0] == "A draw, 7 to 7" and d.state["bonus"] == [2, 2], d.finished)
check("command points with the initiative swapping: Trevor, Ethan, Trevor, Ethan: 2+1+1+2+1 = 7 and 2+1+2+1+2 = 8", d.state["cp"] == [7, 8], d.state["cp"])

t = new(length="Tutorial", tac="Off", a=1, b=1)
begin(t); fight(t)
said = t.do(ev="next")
check("tutorial: turning point 2 is the last, and she says so", t.state["tp"] == 2 and said == ["The last turning point. Score what can be scored; mourn the rest later."] and kt.strip(t) == ("Turning point 2 of 2", "Strategy"), said)
begin(t, 1); fight(t)
check("tutorial: the last End phase asks for the primary ops", t.log[-1]["ev"] == "next" and kt.prompt(t.state) == ("End of turning point 2.", "Score what the mission card says. Each op stops at 6. Then reveal your primary ops."), kt.prompt(t.state))
score(t, 0, "crit", 2); score(t, 1, "crit", 1)
t.do(ev="primary", side=0, cat="crit"); t.do(ev="primary", side=1, cat="kill"); t.do(ev="next")
check("tutorial: over after 2 turning points; 2 + half of 2 = 3 against 1 + half of 0 = 1", t.finished and t.finished["winner"] == "Ethan" and t.finished["lines"] == ["3 to 1", "Ethan: Crit 2, Kill 0, primary +1", "Trevor: Crit 1, Kill 0, primary +0"], t.finished)

e = new(a=1, b=1); begin(e); fight(e); score(e, 1, "kill", 1)
check("the leader is whoever has more points; nobody when level", kt.leader(e.state) == 1 and kt.leader(new().state) is None)
e.finish()
check("stopped early: the leader is named, with the score and where it stopped", e.finished["winner"] == "Trevor" and e.finished["lines"] == ["Victory points: Ethan 0, Trevor 1", "Stopped in turning point 1 of 4"], e.finished)
e = new(); e.finish()
check("stopped during set-up: no winner", e.finished["winner"] is None and e.finished["lines"][1] == "Stopped before the first turning point", e.finished)

# ---- modes
q = new("Silent", a=1, b=2)
said = [q.do(ev="next"), q.do(ev="init", side=0), q.do(ev="next"), q.do(ev="next"), q.do(ev="down", side=0, ready=False), q.do(ev="next"), q.do(ev="next"), q.do(ev="next")]
check("Silent: she says nothing at all through a whole turning point", all(x == [] for x in said) and q.state["tp"] == 2 and q.state["taught"] == [], said)
check("Silent: a broken rule is still refused", q.do(ev="next") != [] and q.do(ev="score", side=0, cat="kill", delta=7) != [])
r = new("Reminder", a=1, b=1); begin(r)
check("Reminder: the rule buttons teach nothing and say nothing", r.do(ev="did", what="shoot") == [] and r.state["taught"] == [])
check("Reminder: the firefight prompt is short", kt.prompt(r.state) == ("Ethan, pick an operative.", "Order? Action?"))
fight(r)
check("Reminder: no rule card is ever due", r.state["taught"] == [])
h = new("Teach", length="Tutorial", tac="Off", a=1, b=2)
check("Teach: Begin makes the Strategy card due and says nothing over it", h.do(ev="next") == [] and h.state["taught"] == ["strategy1"])
h.do(ev="init", side=0)
check("Teach: into the Firefight phase, the activation cards", h.do(ev="next") == [] and h.state["taught"] == ["strategy1", "firefight1"])
check("Teach: rule buttons only work in the Firefight phase, and only for known actions", "do not know" in h.do(ev="did", what="dance")[0])
check("Teach: the first shot makes the shooting card due", h.do(ev="did", what="shoot") == [] and h.state["taught"][-1] == "shoot")
check("Teach: the second shot gets one line, not the card again", "Shooting:" in h.do(ev="did", what="shoot")[0] and h.state["taught"].count("shoot") == 1)
for what in ("charge", "fight", "injury"): h.do(ev="did", what=what)
check("Teach: charge, fight and injury each fire once", h.state["taught"][-3:] == ["charge", "fight", "injury"] and "Charging:" in h.do(ev="did", what="charge")[0] and "Fighting:" in h.do(ev="did", what="fight")[0] and "Injured:" in h.do(ev="did", what="injury")[0] and len(h.state["taught"]) == 6)
check("Teach: out of activations fires the counteract card, once", h.do(ev="next") == [] and h.state["taught"][-1] == "counteract" and h.state["out"] == 0)
h.do(ev="next")
check("Teach: end of turning point 1 has its card", h.do(ev="next") == [] and h.state["taught"][-1] == "end1" and h.state["phase"] == "end")
check("Teach: turning point 2 strategy has its card", h.do(ev="next") == [] and h.state["taught"][-1] == "strategy2")
h.do(ev="init", side=1)
check("Teach: nothing new entering the second Firefight phase, so she speaks instead", h.do(ev="next") == ["Firefight. Trevor activates first."])
h.do(ev="next"); said = h.do(ev="next")
check("Teach: counteract the second time is a line, not the card", "may counteract" in said[0] and h.state["taught"].count("counteract") == 1, said)
h.do(ev="next")
check("Teach: the last End phase has the scoring and ending cards", h.state["phase"] == "end" and h.state["taught"][-2:] == ["scoring", "ending"])
check("Teach: the prompt asks what the operative does", kt.prompt(new("Teach", a=1, b=1).state)[0] == "How many operatives each?" and "Tell me what it does." in (lambda z: (begin(z), kt.prompt(z.state)[1])[1])(new("Teach")))
check("after the Firefight phase a rule button is refused", "Firefight phase" in h.do(ev="did", what="shoot")[0])

# ---- phones, the shared scoreboard, saving, reminders
p = new(a=2, b=2); begin(p, 1)
ph0, ph1 = kt.phone(p, 0), kt.phone(p, 1)
labels = lambda ph: [a["label"] for a in ph["actions"]]
check("phone: only the player whose activation it is can press it done", "Activation done" in labels(ph1) and "Activation done" not in labels(ph0))
check("phone: every action is for that player's own side", all(a["ev"].get("side", 1) == 1 for a in ph1["actions"]) and all(a["ev"].get("side", 0) == 0 for a in ph0["actions"]))
check("phone: no scoring buttons in the Firefight phase", not any("+1" in x for x in labels(ph0)))
check("phone: a player can spend their own command point", p.do(**next(a["ev"] for a in ph0["actions"] if a["label"] == "Spend 1 command point")) == [] and p.state["cp"] == [2, 3])
p.do(**next(a["ev"] for a in kt.phone(p, 0)["actions"] if a["label"] == "Primary op: Kill Op"))
check("phone: a player names their primary op in private", p.state["primary"] == ["kill", None] and "Your primary op: Kill Op" in kt.phone(p, 0)["lines"] and not any("rimary" in x for x in labels(kt.phone(p, 0))))
check("phone: the other player's phone does not show it", not any("Kill Op" in l and "rimary" in l for l in kt.phone(p, 1)["lines"]) and "Primary op: Crit Op" in labels(kt.phone(p, 1)))
check("the shared scoreboard never shows a primary op", "primary" not in json.dumps(kt.scoreboard(p)).lower())
fight(p)
check("phone, End of turning point 1: Tac and Kill can be scored, Crit cannot", labels(kt.phone(p, 1))[:3] == ["Spend 1 command point", "Tac Op +1", "Kill Op +1"], labels(kt.phone(p, 1)))
p.do(**next(a["ev"] for a in kt.phone(p, 1)["actions"] if a["label"] == "Kill Op +1"))
check("phone: a player scores their own point", p.state["vp"][1]["kill"] == 1 and p.state["vp"][0]["kill"] == 0)
sb = kt.scoreboard(p)
check("scoreboard: both players, totals, the detail and where the game is",
      [(r["name"], r["value"]) for r in sb["rows"]] == [("Ethan", 0), ("Trevor", 1)] and sb["rows"][1]["detail"] == "Crit Op 0 / 6, Tac Op 0 / 6, Kill Op 1 / 6, CP 3, Lost 0 of 2, Tac Op: not chosen" and sb["note"] == "Turning point 1 of 4, End", sb)
check("phone lines: where the game is, the points with their caps, command points, losses",
      kt.phone(p, 1)["lines"] == ["Turning point 1 of 4, End", "Victory points 1: Crit Op 0 / 6, Tac Op 0 / 6, Kill Op 1 / 6", "Command points 3", "Operatives lost 0 of 2", "Your Tac Op: not recorded yet", "Ethan's Tac Op: not chosen"], kt.phone(p, 1)["lines"])
check("phone: a seat that is not playing can do nothing", kt.phone(p, 5)["actions"] == [])
check("phases a reminder can hang on", kt.phases() == [("strategy", "Strategy"), ("firefight", "Firefight"), ("end", "End")] and kt.phase(p.state) == "end" and kt.press(p.state) == {"ev": "next"})
folder = paths.data("sessions")
sv = new(a=2, b=2, folder=folder); begin(sv, 1); sv.do(ev="next"); sv.do(ev="down", side=0, ready=True)
back = engine.Session.load(sv.path, plugins, clock)
check("a saved game loads back exactly", back.state == sv.state and back.log == sv.log and json.loads(json.dumps(sv.state)) == sv.state)
sv.add_reminder(1, "firefight", "use the plasma"); sv.add_reminder(None, "end", "count the objectives")
sv.add_reminder(1, "strategy", "pick a ploy"); sv.add_reminder(0, "end", "check the objective")
said = sv.do(ev="next")
check("a Firefight reminder is not said again at every activation", kt.remind_each_turn is False and not any("Reminder" in x for x in said), said)
heard = []
while sv.state["phase"] == "firefight": heard += sv.do(ev="next")
check("reminders for the End phase are said when it starts: everyone's, and a player's own with the name",
      "Reminder: count the objectives" in heard and "Reminder for Ethan: check the objective" in heard, heard)
said = sv.do(ev="next")
check("a player's own Strategy reminder is said when the Strategy phase starts, though nobody is active",
      sv.state["phase"] == "strategy" and "Reminder for Trevor: pick a ploy" in said, said)
heard = sv.do(ev="init", side=0) + sv.do(ev="next")
first = sum("use the plasma" in x for x in heard)
while sv.state["phase"] == "firefight": heard += sv.do(ev="next")
check("a player's Firefight reminder is said once, with the name, when the Firefight phase starts",
      first == 1 and sum("use the plasma" in x for x in heard) == 1 and "Reminder for Trevor: use the plasma" in heard, heard)
os.remove(sv.path)

# ---- the words
steps = kt.teach()
text = json.dumps(steps, ensure_ascii=False) + open(os.path.join(kt.folder, "plugin.py"), encoding="utf-8").read()
check("teach.json: every step has a title, text, an id and a trigger", len(steps) >= 15 and all(x.get("title") and x.get("text") and x.get("id") and "when" in x for x in steps) and len({x["id"] for x in steps}) == len(steps))
check("every card the plugin can make due has at least one step", all(kt.cards(k) for k in ("start", "strategy1", "firefight1", "shoot", "charge", "fight", "injury", "counteract", "end1", "strategy2", "scoring", "ending")))
check("the first-game steps before play are the seven from the script", [x["id"] for x in kt.cards("start")] == ["welcome", "card", "terrain", "objectives", "dropzones", "deploy", "primary"])
check("her voice: no exclamation marks, no 'awesome', no 'let's go'", not any(w in text.lower() for w in ("awesome", "let's go")) and "!" not in json.dumps(steps) and not any("!" in v for v in __import__("deepthought.games.killteam.plugin", fromlist=["AGAIN"]).AGAIN.values()))

# ---------------------------------------------------------------- screens
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens import common, extras
from deepthought.screens.home import Home
from deepthought.games.killteam.plugin import Card, KTAdjust, KTDown, KTPlay, KTReveal, KTScore, KTSheet, card_pages

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
    if sum(1 for w in screen.widgets if getattr(w, "style", "") == "primary") != 1: out.append(("primary buttons", [w.label for w in screen.widgets if getattr(w, "style", "") == "primary"]))
    app.render()
    return out
def tap(label, n=0):
    """Tap the n-th tappable thing whose label starts with this."""
    w = [w for w in app.screen.widgets if w.action and w.label.startswith(label)][n]
    app.toast = None
    w.action()
def has(label):
    return any(w.action and w.label.startswith(label) for w in app.screen.widgets)
def press():
    app.toast = None
    app.gesture("press")
def double():
    """A double press as the button sends it: the press first, then the double."""
    app.toast = None
    app.gesture("press"); app.gesture("double")
bad = []                                     # every screen_ok problem met on the way, with where
def ok(where):
    p = screen_ok()
    if p: bad.append((where, p))
    return not p
def cards(where):
    """Press through any rule cards on top. Returns their headings."""
    seen = []
    while isinstance(app.screen, Card):
        ok(where + " card"); seen.append(app.screen.pages[app.screen.i][0]); press()
    return seen

check("each teaching step fits on one card", all(len(card_pages([(x["title"], x["text"])])) == 1 for x in steps), [x["id"] for x in steps if len(card_pages([(x["title"], x["text"])])) != 1])
check("no line of a card is wider than the screen", all(T.font("text", 24).size(l)[0] <= T.W - 48 for x in steps for _, ls in card_pages([(x["title"], x["text"])]) for l in ls))

def setup(mode, length, tac):
    app.go_home(); app.push(common.Setup(app, kt))
    su = app.screen
    su.names[0], su.names[1] = "Ethan", "Trevor"; su.refresh()
    for key, want, label in (("mode", mode, "Mode"), ("length", length, "Length"), ("tacops", tac, "Tac Ops")):
        for _ in range(4):
            if not su.opts[key].startswith(want): tap(label)
    return su

# ---- Teach mode, the tutorial game, tapped all the way through
su = setup("Teach", "Tutorial", "Off")
check("Set up: two players, three options, and it fits", su.n == 2 and not has("+") and su.opts == {"mode": "Teach", "length": "Tutorial, 2 rounds", "tacops": "Off"} and screen_ok() == [], (su.opts, screen_ok()))
tap("How to play")
check("How to play opens the steps in order", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "The whole rhythm" and screen_ok() == [], screen_ok())
tap("Back"); tap("Start game")
s = app.session; st = s.state
check("Teach: the game starts on the first of seven first-game cards", isinstance(app.screen, Card) and app.screen.title == "Step 1 of 7" and app.screen.left == "Kill Team · Teach" and len(app.screen.pages) == 7 and ok("teach start"), app.screen.title)
check("a card's buttons: Back and one main button", [w.label for w in app.screen.widgets] == ["Back", "Next"])
press(); tap("Back")
check("Back steps back a card", app.screen.i == 0)
app.screen.i = 6; app.screen.refresh()
check("the last card's main button says Got it", [w.label for w in app.screen.widgets] == ["Back", "Got it"] and ok("teach last card"))
app.screen.i = 0; app.screen.refresh()
seen = cards("teach start")
play = app.screen
check("pressing through all seven leaves the play screen, in set-up", len(seen) == 7 and seen[-1] == "Your primary op" and isinstance(play, KTPlay) and st["phase"] == "setup" and len(s.log) == 0, seen)
check("set-up play screen: two steppers, Begin, and it fits", [w.label for w in play.widgets] == ["−", "+", "−", "+", "Begin", "Undo", "Menu"] and play.pill is None and ok("teach operatives"), [w.label for w in play.widgets])
for _ in range(3): tap("−")
for _ in range(4): tap("−", 1)
check("the steppers set 3 operatives against 2", st["start"] == [3, 2])
tap("+", 1); press()
check("a press begins the game and a card comes up", s.state["phase"] == "strategy" and isinstance(app.screen, Card) and len(s.log) == 9)
app.gesture("double")
check("double press, even with a card up: takes back its own press and undoes one more", app.screen is play and s.state["phase"] == "setup" and s.state["start"] == [3, 2] and len(s.log) == 7, (s.state["start"], len(s.log)))
st = s.state
press()
check("the button begins the game and the Strategy card comes up", st["phase"] == "strategy" and cards("teach strategy") == ["The Strategy phase"] and app.screen is play)
check("Strategy screen: two initiative buttons, and it fits", has("Ethan won the roll") and has("Trevor won the roll") and (play.left, play.title) == ("Turning point 1 of 2", "Strategy") and ok("teach strategy"))
press()
check("the button will not move on without the initiative", st["phase"] == "strategy" and "initiative" in app.toast, app.toast)
tap("Ethan won the roll")
check("tapping the winner: 3 command points each, the button says who has it", st["cp"] == [3, 3] and has("Ethan has initiative") and "One command point each" in app.toast and ok("teach strategy chosen"), app.toast)
press()
check("into the Firefight phase: the activation and moving cards", cards("teach firefight") == ["Your first activation", "Moving"] and st["phase"] == "firefight" and app.screen is play)
check("Teach firefight screen: the four rule buttons, whose turn, and it fits", all(has(x) for x in ("Shoot", "Charge", "Fight", "Injured", "Next", "Score", "Operative down", "Undo", "Menu")) and play.pill == ("Ethan's turn", T.player_colour(0)) and ok("teach firefight"), [w.label for w in play.widgets])
check("the ring is in the active player's colour", app.hw._ring.now == ("turn", {"colour": T.player_colour(0)}), app.hw._ring.now)
tap("Shoot")
check("first shot: the shooting and blocking cards", cards("teach shoot") == ["Shooting", "Blocking"] and app.screen is play)
tap("Shoot")
check("second shot: a line, no card", app.screen is play and "Shooting:" in app.toast, app.toast)
tap("Charge"); c1 = cards("teach charge"); tap("Fight"); c2 = cards("teach fight"); tap("Injured"); c3 = cards("teach injury")
check("first charge, fight and injury each bring their card", (c1, c2, c3) == (["Charging"], ["Fighting"], ["Injured"]), (c1, c2, c3))
tap("Spend CP: Ethan")
check("tapping your command points spends one", st["cp"] == [2, 3] and app.toast is None)
tap("Operative down"); dn = app.screen
check("Operative down: asks whether it had activated, and fits", isinstance(dn, KTDown) and [w.label for w in dn.widgets if w.label.startswith(("Not", "Already", "Put"))] == ["Not yet activated", "Already activated", "Put one back"] * 2 and ok("teach down"), [w.label for w in dn.widgets])
tap("Not yet activated", 1)
check("Trevor loses one that had not activated: 1 of 2 lost, 1 activation left", st["lost"] == [0, 1] and st["left"] == [3, 1] and "kill grade" in app.toast and ok("teach down after"), (st["lost"], st["left"], app.toast))
tap("Put one back", 1); tap("Undo")
check("Undo on that screen takes the put-back away again", s.state["lost"] == [0, 1])
st = s.state
press()
check("the button on Operative down goes back to the game", app.screen is play)
press(); press()
check("Ethan, Trevor, then Trevor is out: the counteract card", st["left"] == [2, 0] and st["active"] == 0 and cards("teach counteract") == ["Out of activations"])
check("the play screen now tells Ethan to keep activating", kt.prompt(st)[0] == "Ethan, keep activating." and ok("teach counteract"))
press(); press()
check("end of turning point 1: its card, then the End screen with Score sheet as the main button", cards("teach end1") == ["End of turning point one"] and st["phase"] == "end" and [w.label for w in play.widgets if w.action][2:] == ["Score sheet", "Operative down", "Undo", "Menu"] and play.pill is None and ok("teach end"), [w.label for w in play.widgets])
press(); sheet = app.screen
check("in the End phase the button opens the score sheet", isinstance(sheet, KTSheet) and (sheet.left, sheet.title) == ("End of turning point 1", "Score this round") and len(s.log) and st["phase"] == "end" and ok("teach sheet 1"))
check("Tac Ops off: the sheet has Crit and Kill rows only", [w.label for w in sheet.widgets] == ["−", "+"] * 4 + ["Back", "Done"])
tap("+")
check("the sheet refuses a Crit Op point in turning point 1, and says why", st["vp"][0]["crit"] == 0 and "first turning point" in app.toast, app.toast)
tap("+", 2)
check("a Kill Op point for Ethan goes on", st["vp"][0]["kill"] == 1 and app.toast is None)
n_log = len(s.log)
press()
check("the button on the sheet is Done: turning point 2 begins and its card comes up", s.state["tp"] == 2 and isinstance(app.screen, Card) and len(s.log) == n_log + 1)
app.gesture("double")
check("double press after the sheet's Done: that Done is taken back, and nothing else", s.state["tp"] == 1 and s.state["phase"] == "end" and s.state["vp"][0]["kill"] == 1
      and len(s.log) == n_log and app.screen is play and "strategy2" not in s.state["taught"], (s.state["tp"], s.state["phase"], len(s.log)))
st = s.state
press(); sheet = app.screen
check("the button opens the sheet again, the point still on it", isinstance(sheet, KTSheet) and st["vp"][0]["kill"] == 1)
press()
check("the button is Done: turning point 2, the Strategy card", st["tp"] == 2 and st["phase"] == "strategy" and cards("teach strategy2") == ["Strategy, again"] and app.screen is play)
tap("Trevor won the roll")
check("turning point 2: Trevor gains 1 (4), Ethan gains 2 (2 + 2 = 4)", st["cp"] == [4, 4] and "Trevor gains one" in app.toast, (st["cp"], app.toast))
press()
check("no card this time; Trevor activates first with his one operative", app.screen is play and st["active"] == 1 and st["left"] == [3, 1] and play.pill[0] == "Trevor's turn")
press(); press(); press(); press()
got = cards("teach last end")
check("the last End phase: scoring, the ending and what to learn next", got == ["Scoring", "The last turning point", "What to learn next"] and st["phase"] == "end", got)
tap("Score sheet"); sheet = app.screen
check("the last sheet's main button leads to the primary ops", has("Done: primary ops") and ok("teach sheet 2"))
tap("+"); tap("+"); tap("+", 3)
check("scored: Ethan Crit 2 and Kill 1, Trevor Kill 1", st["vp"] == [{"crit": 2, "tac": 0, "kill": 1}, {"crit": 0, "tac": 0, "kill": 1}], st["vp"])
tap("Done"); rv = app.screen
check("Primary ops screen: Crit or Kill for each side, and it fits", isinstance(rv, KTReveal) and [w.label for w in rv.widgets] == ["Crit Op", "Kill Op", "Crit Op", "Kill Op", "Back", "Finish the game"] and ok("teach reveal"), [w.label for w in rv.widgets])
tap("Finish")
check("the game will not finish until both have revealed", app.screen is rv and s.finished is None and "reveal your primary op" in app.toast, app.toast)
tap("Crit Op"); tap("Kill Op", 1)
check("the chosen op shows its points and bonus: Crit 2 gives +1, Kill 1 gives +1", [w.label for w in rv.widgets][:4] == ["Crit Op: 2, bonus +1", "Kill Op", "Crit Op", "Kill Op: 1, bonus +1"] and [w.selected for w in rv.widgets][:4] == [True, False, False, True] and ok("teach reveal chosen"), [w.label for w in rv.widgets])
press()
over = app.screen
check("the button finishes the game: Game over, Ethan 3 + 1 = 4 to Trevor 1 + 1 = 2", isinstance(over, common.GameOver) and s.finished["winner"] == "Ethan" and s.finished["lines"][0] == "4 to 2" and app.session is None and screen_ok() == [], (s.finished, screen_ok()))
app.gesture("press")
check("then Home, with the result as the last game", isinstance(app.screen, Home) and app.last_game == "Last game: Kill Team, Ethan won", app.last_game)

# ---- Reminder and Silent: a full game each, every screen checked on the way
def play_through(mode, tac):
    setup(mode, "Full", tac); tap("Start game")
    s, where = app.session, mode
    first = app.screen
    ok(where + " operatives")
    for _ in range(4): tap("−"); tap("−", 1)                  # two operatives each
    press()
    for tp in (1, 2, 3, 4):
        play = app.screen
        ok("%s strategy %d" % (where, tp)); tap("Trevor won the roll" if tp % 2 else "Ethan won the roll"); ok("%s strategy chosen %d" % (where, tp))
        press(); ok("%s firefight %d" % (where, tp))
        if tp == 1:
            tap("Score"); board = app.screen; ok(where + " scoreboard")
            tap("Ethan Kill Op"); ok(where + " adjust"); tap("+ 1"); ok(where + " adjust stepped"); tap("Set to 1")
            tap("Trevor CP"); tap("+ 1"); tap("+ 1"); press()
            tap("Ethan Lost"); ok(where + " down"); tap("Already activated"); press()
            tap("Back to the game")
            tap("Operative down"); tap("Put one back"); tap("Back to the game")
        for _ in range(4): press()
        ok("%s end %d" % (where, tp)); press(); ok("%s sheet %d" % (where, tp))
        tap("+", 1 if tp > 1 else 0)                                # Trevor's Crit Op from turning point 2; refused for Ethan in 1
        press()
    ok(where + " reveal"); tap("Kill Op"); tap("Crit Op", 1); ok(where + " reveal chosen"); tap("Finish")
    return s, first

s, first = play_through("Reminder", "On")
check("Reminder: no cards at the start, straight to the play screen", isinstance(first, KTPlay))
check("Reminder: a whole game by taps: Ethan Kill 1 + bonus 1 = 2, Trevor Crit 3 + bonus 2 = 5", s.finished and s.finished["winner"] == "Trevor" and s.finished["lines"] == ["2 to 5", "Ethan: Crit 0, Tac 0, Kill 1, primary +1", "Trevor: Crit 3, Tac 0, Kill 0, primary +2"], s.finished)
check("Reminder: command points, initiative Trevor, Ethan, Trevor, Ethan: Ethan 2+1+1+2+1 = 7; Trevor 2+1+2+1+2 = 8, corrected by +2 = 10", s.state["cp"] == [7, 10], s.state["cp"])
check("Reminder: nothing was taught", s.state["taught"] == [] and isinstance(app.screen, common.GameOver) and screen_ok() == [])
s, first = play_through("Silent", "Off")
check("Silent: a whole game by taps ends the same way", isinstance(first, KTPlay) and s.finished and s.finished["winner"] == "Trevor" and s.finished["lines"][0] == "2 to 5", s.finished)
check("every Kill Team screen met in all three modes passes screen_ok", bad == [], bad)

# ---- the pieces not met on the way
setup("Silent", "Full", "Off"); tap("Start game"); play = app.screen; s = app.session
check("Silent: the set-up screen has no sentences to wrap, and still fits", ok("silent setup"))
press(); tap("Ethan won the roll")
check("Silent: no line from her when the initiative is given", app.toast is None and s.state["cp"] == [3, 3])
press()
check("Silent: no rule buttons in the Firefight phase", not has("Shoot") and has("Spend CP: Ethan") and ok("silent firefight"))
tap("Score"); board = app.screen
check("scoreboard, Tac Ops off: the Tac row cannot be tapped", isinstance(board, KTScore) and not has("Ethan Tac Op") and has("Ethan Crit Op") and ok("silent scoreboard"))
tap("Ethan Crit Op"); adj = app.screen
tap("− 1")
check("Correct a number: cannot step below nothing", isinstance(adj, KTAdjust) and adj.delta == 0 and "Less than nothing" in app.toast)
for _ in range(7): tap("+ 1")
check("Correct a number: cannot step past 6", adj.delta == 6 and "stops at 6" in app.toast and has("Set to 6"))
tap("Set to 6")
check("Correct a number: a Crit Op point in turning point 1 is refused on confirming, and the screen stays", app.screen is adj and s.state["vp"][0]["crit"] == 0 and "first turning point" in app.toast, app.toast)
n_log = len(s.log)
double()
check("double press on a refused correction leaves Correct a number without changing anything", app.screen is board and s.state["vp"][0]["crit"] == 0 and len(s.log) == n_log)
tap("Trevor CP"); tap("− 1"); tap("− 1"); press()
check("Correct a number: the button confirms: Trevor's command points 3 - 2 = 1", app.screen is board and s.state["cp"] == [3, 1])
app.gesture("double")
check("a double press whose press confirmed the correction: the screen has closed, and nothing more happens",
      app.screen is board and s.state["cp"] == [3, 1] and len(s.log) == n_log + 1, (type(app.screen).__name__, s.state["cp"]))
tap("Trevor CP"); press()
check("confirming no change is not an event", app.screen is board and s.log[-1]["ev"] == "cp" and len([e for e in s.log if e["ev"] == "cp"]) == 1)
press()
check("the button leaves the scoreboard", app.screen is play)
for _ in range(12): press()
tap("Score sheet"); sheet = app.screen; tap("+", 2); tap("Back")
check("Back leaves the sheet without ending the turning point", app.screen is play and s.state["phase"] == "end" and s.state["vp"][0]["kill"] == 1)
tap("Score sheet"); n_log = len(s.log); double()
check("double press on the sheet: its press was Done, so that is taken back, and one more (the point)",
      app.screen is play and s.state["tp"] == 1 and s.state["phase"] == "end" and s.state["vp"][0]["kill"] == 0 and len(s.log) == n_log - 1, (s.state["tp"], s.state["phase"], len(s.log)))
double()
check("double press in the End phase: the sheet its press opened is put away, and one event is undone",
      app.screen is play and s.state["phase"] == "firefight" and len(s.log) == n_log - 2, s.state["phase"])
press(); tap("Operative down"); dn = app.screen
check("Operative down outside the Firefight phase: just Lost one and Put one back", [w.label for w in dn.widgets][:4] == ["Lost one", "Put one back"] * 2 and ok("down in end"), [w.label for w in dn.widgets])
tap("Lost one"); n_log = len(s.log); double()
check("double press on Operative down: its press closed the screen, so nothing is undone behind the player's back",
      s.state["lost"] == [1, 0] and app.screen is play and s.state["phase"] == "end" and len(s.log) == n_log)
tap("Operative down"); tap("Undo")
check("Undo on Operative down takes the loss back", s.state["lost"] == [0, 0] and app.screen is not play)
press(); tap("Menu")
check("the shared More menu opens from Kill Team", isinstance(app.screen, extras.GameMenu) and screen_ok() == [])
tap("Rules")
check("Rules shows the same steps", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "The whole rhythm")
tap("Back"); tap("Home")
path, d = engine.unfinished(paths.data("sessions"))
app.resume_game(path)
check("a game left for Home resumes where it was, with no first-game cards", isinstance(app.screen, KTPlay) and app.session.state == s.state and app.session.state["phase"] == "end")
tap("Menu"); tap("End game"); tap("End it")
check("ending early from the menu: no winner at nil all", isinstance(app.screen, common.GameOver) and app.screen.session.finished["winner"] is None and app.screen.session.finished["lines"][0] == "Victory points: Ethan 0, Trevor 0")

class Voice:
    def __init__(self): self.said = []
    def say(self, text, show=True): self.said.append(text)
    def hold(self, on): pass
app.voice = Voice()
setup("Teach", "Full", "On"); tap("Start game")
read = lambda start: sum(1 for x in app.voice.said if x.startswith(start))
check("with a voice: a card is read aloud once as it appears, and gains Say again", read("Two squads.") == 1 and [w.label for w in app.screen.widgets] == ["Back", "Say again", "Next"] and ok("card with voice"), app.voice.said)
tap("Say again"); press()
check("Say again reads it again; the next card is read in its turn", read("Two squads.") == 2 and read("Pick up one") == 1, app.voice.said)
double()
check("double press on the first-game cards puts them away; there is no event to undo", isinstance(app.screen, KTPlay) and len(app.session.log) == 0)
app.voice = None

# ---------------------------------------------------------------- the slow-play clock: the sums
from deepthought import persona
from deepthought.games.killteam import plugin as PKT
pc = rules.Pace()
check("pace: nothing before the limit, once at the limit, never again for that activation",
      [pc.due("a", t0, 90) for t0 in (1000, 1050, 1089.9, 1090, 1091, 5000)] == [False, False, False, True, False, False])
check("pace: a new activation starts the clock again", [pc.due("b", t0, 90) for t0 in (5001, 5090.9, 5091, 5300)] == [False, False, True, False])
check("pace: back to an activation that has had its line (undo): nothing more, however long", [pc.due("a", t0, 90) for t0 in (5301, 9999)] == [False, False])
check("pace: forward again to the other one: nothing more either", pc.due("b", 20000, 90) is False)
check("pace: off means off, and nothing to time means nothing", [rules.Pace().due("a", t0, 0) for t0 in (0, 99999)] == [False, False] and [pc.due(None, t0, 90) for t0 in (30000, 99999)] == [False, False])
pc2 = rules.Pace(); pc2.due("a", 0, 90); pc2.restart()
check("pace: restart begins the count from the next look", [pc2.due("a", t0, 90) for t0 in (500, 589, 590)] == [False, False, True])
check("the choices: 90 seconds by default, 3 minutes, or off", [(l, v) for l, v, _ in rules.NUDGES] == [("90 s", 90), ("3 min", 180), ("Off", 0)])
check("her nudge lines: four, in her voice, no exclamation marks, nothing about the player", len(PKT.NUDGE_LINES) == 4 and all(persona.in_voice(l % "Ninety seconds" if "%s" in l else l) for l in PKT.NUDGE_LINES)
      and not any(x in " ".join(PKT.NUDGE_LINES).lower() for x in ("you are", "slow", "hurry up", "your fault")))
pk = new()
keys = [kt.pace_key(pk.state)]
pk.do(ev="next"); keys.append(kt.pace_key(pk.state)); pk.do(ev="init", side=0); keys.append(kt.pace_key(pk.state))
check("nothing is timed while setting up or in the Strategy phase", keys == [None, None, None])
pk.do(ev="next"); k1 = kt.pace_key(pk.state)
pk.do(ev="down", side=1, ready=True); pk.do(ev="cp", side=0, delta=-1)
check("the clock times one activation; a kill or a spent point in the middle of it is still the same activation", k1 == (1, 0) and kt.pace_key(pk.state) == k1)
pk.do(ev="next"); k2 = kt.pace_key(pk.state)
check("the next activation is a new one; undo goes back to the same one as before", k2 == (1, 1) and pk.undo() and kt.pace_key(pk.state) == k1)
fight(pk)
check("nothing is timed in the End phase", pk.state["phase"] == "end" and kt.pace_key(pk.state) is None)
pk.do(ev="next"); pk.do(ev="init", side=1); pk.do(ev="next")
check("turning point 2 carries the count on, so no two activations share a name", kt.pace_key(pk.state) == (2, pk.state["acts"]) and pk.state["acts"] >= 10)

# ---------------------------------------------------------------- the slow-play clock: on the play screen
sess = paths.data("sessions")
def play_on(s):
    app.go_home(); app.toast = None
    app.session = s
    scr = kt.play_screen(app, s); app.push(scr)
    return scr
def acts(): return [w.label for w in app.screen.widgets if w.action]
turn_ring = lambda i: ("turn", {"colour": T.player_colour(i)})
nudge_lines = [l % "Ninety seconds" if "%s" in l else l for l in PKT.NUDGE_LINES]
tk = new(folder=sess); begin(tk)
scr = play_on(tk)
check("a play screen has a tick for the app to call; 90 seconds is the default", callable(getattr(scr, "tick", None)) and PKT.nudge_secs(tk) == 90 and "nudge" not in tk.d["options"])
fired = [scr.tick(t0) for t0 in (100.0, 150.0, 189.9)]
check("under 90 seconds in an activation: silence, and the ring stays the turn colour", fired == [False] * 3 and app.toast is None and app.hw._ring.now == turn_ring(0), (fired, app.toast))
check("at 90 seconds: one line from her and the amber warning on the ring", scr.tick(190.0) is True and app.toast in nudge_lines and app.hw._ring.now[0] == "warn", app.toast)
first_line = app.toast
check("the warning is still blinking a moment later", scr.tick(192.0) is False and app.hw._ring.now[0] == "warn")
check("then the ring goes back to the turn colour", scr.tick(190.0 + PKT.WARN_SECS) is False and app.hw._ring.now == turn_ring(0))
app.toast = None
scr.do(ev="down", side=1, ready=True); app.toast = None
check("nothing further in that activation, however long it runs and whoever falls in it", [scr.tick(t0) for t0 in (250.0, 370.0, 4000.0)] == [False] * 3 and app.toast is None and app.hw._ring.now == turn_ring(0))
scr.do(ev="next"); app.toast = None
check("the next activation starts its own clock: quiet for 90 more seconds", tk.state["active"] == 1 and [scr.tick(t0) for t0 in (4001.0, 4090.0)] == [False, False] and app.toast is None)
check("and then one line, a different one", scr.tick(4091.0) is True and app.toast in nudge_lines and app.toast != first_line and app.hw._ring.now[0] == "warn", app.toast)
scr.tick(4100.0); app.toast = None
check("after the blink the ring shows whose activation it is", app.hw._ring.now == turn_ring(1))
scr.do(ev="next"); scr.tick(4101.0)
tk.undo(); scr.refresh()
check("undo back into an activation that has had its line: no second line", kt.pace_key(tk.state) == (1, 1) and [scr.tick(t0) for t0 in (4102.0, 4300.0, 9000.0)] == [False] * 3 and app.toast is None)
scr.tick(9001.0); app.gesture("press"); scr.tick(9002.0); app.gesture("double"); app.toast = None
check("the button's double press (undo) does not fire it again either", kt.pace_key(tk.state) == (1, 0) and [scr.tick(t0) for t0 in (9003.0, 9999.0)] == [False, False] and app.toast is None, kt.pace_key(tk.state))
# a game left for hours and resumed
app.go_home()
app.resume_game(tk.path)
res = app.screen
check("resume makes a new play screen with a new clock", isinstance(res, KTPlay) and res is not scr and app.session.state == tk.state)
check("a game resumed after hours does not fire at once", res.tick(500000.0) is False and res.tick(500089.0) is False and app.toast is None and app.hw._ring.now[0] == "turn")
check("it fires 90 seconds after the resume", res.tick(500090.0) is True and app.toast in nudge_lines)
app.toast = None
# the setting, from the game's menu
tap("Menu"); menu = app.screen
check("More opens the game menu with the nudge setting added, and it fits", isinstance(menu, extras.GameMenu) and acts()[-4:] == ["Back to the game", "Lookup", "Dice", "Nudge: 90 s"] and screen_ok() == [], (acts(), screen_ok()))
check("the menu's labels fit their buttons", all(T.font("bold", 22).size(w.label)[0] <= w.rect.w - 24 for w in menu.widgets if w.rect.y >= common.BOTTOM_Y), [(w.label, w.rect.w) for w in menu.widgets if w.rect.y >= common.BOTTOM_Y])
tap("Nudge")
check("a tap: 3 minutes, she says so, and it is saved with the game", acts()[-1] == "Nudge: 3 min" and "Three minutes an activation" in app.toast and json.load(open(tk.path, encoding="utf-8"))["options"]["nudge"] == 180 and screen_ok() == [], app.toast)
tap("Back to the game"); res.do(ev="next"); app.toast = None
res.tick(600000.0)
tap("Menu"); tap("Nudge"); tap("Nudge"); tap("Nudge"); tap("Back to the game"); app.toast = None
check("changing the limit starts the count again from then, not from the start of the activation", PKT.nudge_secs(app.session) == 180
      and [res.tick(t0) for t0 in (600100.0, 600279.0)] == [False, False] and res.tick(600280.0) is True)
app.toast = None
again = engine.Session.load(tk.path, plugins, clock)
check("a resumed game keeps its limit", PKT.nudge_secs(again) == 180)
tap("Menu"); tap("Nudge")
check("another tap: off", acts()[-1] == "Nudge: Off" and PKT.nudge_secs(app.session) == 0 and "keep the time to myself" in app.toast and screen_ok() == [])
tap("Back to the game"); res.do(ev="next"); app.toast = None
check("off means off: a whole day on one operative and not a word", [res.tick(t0) for t0 in (700000.0, 700090.0, 786400.0)] == [False] * 3 and app.toast is None and app.hw._ring.now[0] == "turn")
tap("Menu"); tap("Nudge"); tap("Back to the game")
check("a third tap comes round to 90 seconds again", PKT.nudge_secs(app.session) == 90)
app.session.d["options"]["nudge"] = "soon"
check("a setting that makes no sense reads as the default", PKT.nudge_secs(app.session) == 90)
# modes and phases
sl = new(mode="Silent"); begin(sl); scr = play_on(sl)
scr.tick(0.0)
check("Silent mode: the ring warns, she says nothing", scr.tick(90.0) is True and app.toast is None and app.hw._ring.now[0] == "warn")
tc = new(mode="Teach"); scr = play_on(tc)
while isinstance(app.screen, Card): app.pop()
scr.do(ev="next")
while isinstance(app.screen, Card): app.pop()
scr.do(ev="init", side=0); scr.do(ev="next")
while isinstance(app.screen, Card): app.pop()
app.toast = None
check("Teach mode: off unless a player turns it on", tc.state["phase"] == "firefight" and PKT.nudge_secs(tc) == 0 and [scr.tick(t0) for t0 in (0.0, 5000.0)] == [False, False] and app.toast is None)
tap("Menu")
check("Teach mode: the menu shows it off; one tap turns it on at 90 seconds", acts()[-1] == "Nudge: Off" and screen_ok() == [] and (tap("Nudge") or acts()[-1] == "Nudge: 90 s") and PKT.nudge_secs(tc) == 90)
tap("Back to the game")
st2 = new(); st2.do(ev="next"); scr = play_on(st2)
check("the Strategy phase is not timed", [scr.tick(t0) for t0 in (0.0, 9999.0)] == [False, False] and app.toast is None)
en = new(); begin(en); fight(en); scr = play_on(en)
check("the End phase is not timed", en.state["phase"] == "end" and [scr.tick(t0) for t0 in (0.0, 9999.0)] == [False, False] and app.toast is None)
# an old saved game: no count of activations, no nudge setting
old = new(folder=sess); begin(old); old.do(ev="next")
d = json.load(open(old.path, encoding="utf-8"))
for x in [d["state"]] + d["undo"]:
    del x["acts"]; x.pop("pending", None)
old_path = os.path.join(sess, "old-killteam.json")
json.dump(d, open(old_path, "w", encoding="utf-8"))
og = engine.Session.load(old_path, plugins, clock)
check("an old save loads, and its activation can be timed", og is not None and "acts" not in og.state and kt.pace_key(og.state) == (1, 0) and PKT.nudge_secs(og) == 90)
scr = play_on(og); scr.tick(0.0)
check("an old save: the clock fires once at 90 seconds", scr.tick(90.0) is True and scr.tick(200.0) is False)
app.toast = None
check("an old save: the next activation counts from there, and undo steps back", og.do(ev="next") == [] and kt.pace_key(og.state) == (1, 1) and og.undo() and kt.pace_key(og.state) == (1, 0))
app.go_home(); app.toast = None

# ---- the slow-play clock stands still while another screen covers the play screen
def frame(t):
    """What the app's loop does with the screens each frame."""
    return [x.tick(t) for x in list(app.stack) if getattr(x, "tick", None)]
cv = new(folder=sess); begin(cv)
scr = play_on(cv); frame(0.0); frame(30.0)
tap("Menu"); tap("End game")
check("under the menu and the End-game question: 90 seconds pass and she says nothing, the ring does not warn",
      isinstance(app.screen, common.Choice) and frame(31.0) == [False] and frame(500.0) == [False] and app.toast is None and app.hw._ring.now[0] != "warn", (app.toast, app.hw._ring.now))
tap("Keep playing"); app.gesture("press")
check("back on the play screen the count carries on from where it stopped: 30 seconds used, 60 to go",
      app.screen is scr and frame(501.0) == [False] and frame(559.0) == [False] and frame(561.5) == [True] and app.toast in nudge_lines, app.toast)
app.toast = None; tap("Menu"); tap("Who first")
ring_then = app.hw._ring.now[0]
frame(561.5 + PKT.WARN_SECS + 1)
check("the spinner's ring is left alone when the warning runs out underneath it", ring_then == "spin" and app.hw._ring.now[0] == "spin", (ring_then, app.hw._ring.now))
app.go_home(); app.toast = None
cv = new(folder=sess); begin(cv); scr = play_on(cv); frame(0.0); frame(90.0)
tap("Menu"); frame(91.0)
check("a warning that started before the menu was opened still ends: the ring goes back to the turn colour",
      app.hw._ring.now[0] == "warn" and frame(91.0 + PKT.WARN_SECS) == [False] and app.hw._ring.now == turn_ring(0), app.hw._ring.now)
app.go_home(); app.toast = None

# ---- a rule card and the double press: only the event that brought the card goes
tc = new("Teach", folder=sess)
scr = play_on(tc); cards("dbl")
tap("Begin"); cards("dbl"); tap("Ethan won the roll"); press(); cards("dbl"); press(); cards("dbl")
n_log, left = len(tc.log), list(tc.state["left"])
tap("Shoot")
check("a tap on Shoot brings a two-page card", isinstance(app.screen, Card) and len(app.screen.pages) == 2 and len(tc.log) == n_log + 1)
double()
check("double press while reading it: the card goes and Shoot is undone; the activation before it is not",
      app.screen is scr and len(tc.log) == n_log and tc.state["left"] == left and "shoot" not in tc.state["taught"], (len(tc.log), n_log, tc.state["left"]))
tap("Shoot"); press(); n2 = len(tc.log); double()
check("double press whose press closed the card on its last page: nothing is undone", app.screen is scr and len(tc.log) == n2 and "shoot" in tc.state["taught"])
tap("Fight"); tc.do(ev="cp", side=0, delta=-1); n2 = len(tc.log); double()
check("a card with a newer event behind it (a phone's): double press puts the card away and undoes nothing", app.screen is scr and len(tc.log) == n2)
n2 = len(tc.log); double()
check("on the play screen itself: double press takes back its own press and one more", len(tc.log) == n2 - 1 and app.screen is scr, (len(tc.log), n2))
app.go_home(); app.toast = None

# ---- every other screen: a double press after earlier taps never undoes what the player did before
sw = new(folder=sess); scr = play_on(sw)
tap("Begin"); tap("Ethan won the roll"); tap("Next"); tap("Next")
for opener, inside in ((lambda: tap("Score"), None), (lambda: tap("Menu"), None), (lambda: tap("Operative down"), "Already activated"),
                       (lambda: (tap("Score"), tap("Ethan Lost")), "Not yet activated")):
    opener(); top = app.screen
    if inside: tap(inside)
    before = (len(sw.log), json.dumps(sw.state, sort_keys=True)); double()
    if type(top).__name__ == "KTDown" and app.screen is not scr: double()      # opened from the scoreboard: close that too
    check("double press on %s after earlier taps: it closes, and nothing is undone" % type(top).__name__,
          app.screen is scr and (len(sw.log), json.dumps(sw.state, sort_keys=True)) == before, (type(app.screen).__name__, len(sw.log), before[0]))
app.go_home(); app.toast = None

# ---- a rule card that was up when the power went comes back on resume
pw = new("Teach", folder=sess)
scr = play_on(pw); cards("power")
tap("Begin")
check("the Strategy card is up, and the saved game knows it is owed", isinstance(app.screen, Card) and pw.state["pending"] == ["strategy1"]
      and json.load(open(pw.path, encoding="utf-8"))["state"]["pending"] == ["strategy1"])
app.resume_game(pw.path)
check("resumed with that card unread: it is shown again", isinstance(app.screen, Card) and app.screen.pages[0][0] == "The Strategy phase", type(app.screen).__name__)
press()
check("read to the end, it is not owed any more", isinstance(app.screen, KTPlay) and json.load(open(app.session.path, encoding="utf-8")).get("cards_seen") == 1)
app.resume_game(app.session.path)
check("resumed again: straight to the play screen, no card", isinstance(app.screen, KTPlay))
tap("Ethan won the roll"); press(); double()
check("a card taken back by a double press is not owed on resume either", app.session.state["phase"] == "strategy" and (app.resume_game(app.session.path), isinstance(app.screen, KTPlay))[1], app.session.state["phase"])
app.go_home(); app.toast = None

# ---- Operative down: the kill grade is not pushed off by a long name
import deepthought.theme as theme_mod
ln = engine.Session(kt, ["Bartholomew Xy", "Samantha-Jane"], {"mode": "Reminder"}, sess, clock); begin(ln)
for _ in range(3): ln.do(ev="down", side=0, ready=True)
scr = play_on(ln); tap("Operative down")
seen_text, real = [], theme_mod.draw_text
def spy(surf, text, *a, **k):
    if k.get("max_w") is not None and len(a) >= 2:
        seen_text.append(theme_mod.fit(text, a[0], a[1], k["max_w"])[0])
    return real(surf, text, *a, **k)
theme_mod.draw_text = spy
app.render()
theme_mod.draw_text = real
grade = kt.grades(ln.state)[1]
check("Operative down with long names: each kill grade number is on the screen", grade >= 1 and any(x.startswith("Kill grade %d" % grade) for x in seen_text) and any(x.startswith("Kill grade 0") for x in seen_text) and ok("down, long names"), seen_text)
app.go_home(); app.toast = None

# ---------------------------------------------------------------- the secret Tac Op
SECRET = "Zzyzx Gambit"                       # a made-up name: the box holds no list of real ones
def acts_of(s, seat): return {a["label"]: a for a in kt.phone(s, seat)["actions"]}
def public(s, owner=0):
    """Everything the table can see or hear about a game, as one string."""
    return json.dumps([kt.scoreboard(s), kt.phone(s, 1 - owner), kt.phone(s, 5), kt.strip(s), kt.prompt(s.state), kt.where(s.state),
                       kt.standings(s.state, s.players), kt.over(s.state)])
ts = new(folder=sess)
a0 = acts_of(ts, 0)
check("Tac Op: a player's phone offers to record it, by typing; there is nothing to reveal yet",
      a0["Record my Tac Op"]["ask"] and "choices" not in a0["Record my Tac Op"] and a0["Record my Tac Op"]["ev"] == {"ev": "tacop", "side": 0}
      and "Reveal my Tac Op" not in a0 and "Your Tac Op: not recorded yet" in kt.phone(ts, 0)["lines"], list(a0))
said = ts.do(text="  zzyzx   gambit ", **a0["Record my Tac Op"]["ev"])
check("Tac Op: recorded from the phone, tidied; she says it is chosen and does not say what",
      ts.state["tacop"] == [SECRET, None] and ts.state["tac_shown"] == [False, False] and said == ["Ethan has chosen a Tac Op. I shall keep it to myself."], (ts.state["tacop"], said))
check("Tac Op: the owner's phone shows it; the scoreboard, the other phone, a spectator and every line for the table do not",
      "Your Tac Op: %s (secret until you reveal it)" % SECRET in kt.phone(ts, 0)["lines"] and "zzyzx" not in public(ts).lower()
      and "Ethan's Tac Op: chosen" in kt.phone(ts, 1)["lines"] and kt.scoreboard(ts)["rows"][0]["tacop"] == "chosen" and kt.scoreboard(ts)["rows"][1]["tacop"] == "not chosen", public(ts))
check("Tac Op: every action on a phone is for that seat's own side", all(a["ev"].get("side", 1) == 1 for a in kt.phone(ts, 1)["actions"]) and "Reveal my Tac Op" not in acts_of(ts, 1))
check("Tac Op: a name of nothing is refused", "needs a name" in ts.do(ev="tacop", side=1, text="   ")[0] and ts.state["tacop"] == [SECRET, None])
said = ts.do(text="other zzyzx", **acts_of(ts, 0)["Change my Tac Op"]["ev"])
check("Tac Op: before the first Firefight it can be changed, and she still does not say what", ts.state["tacop"][0] == "Other Zzyzx" and "zzyzx" not in " ".join(said).lower() and "different" in said[0], said)
check("Tac Op: undo takes the change back", ts.undo() and ts.state["tacop"] == [SECRET, None])
begin(ts)
a0 = acts_of(ts, 0)
said = ts.do(ev="tacop", side=0, text="late change")
check("Tac Op: once the Firefight has begun it cannot be changed; the phone no longer offers it; the refusal does not name it",
      "Change my Tac Op" not in a0 and "Reveal my Tac Op" in a0 and ts.state["tacop"][0] == SECRET and "stays until it is revealed" in said[0] and "zzyzx" not in said[0].lower(), (list(a0), said))
check("Tac Op: the other player can still record theirs late", "Record my Tac Op" in acts_of(ts, 1))
back = engine.Session.load(ts.path, plugins, clock)
check("Tac Op: it survives save and resume, still secret", back.state["tacop"] == [SECRET, None] and back.state["tac_shown"] == [False, False] and "zzyzx" not in public(back).lower()
      and "zzyzx" in json.dumps(kt.phone(back, 0)).lower())
# on the box: every screen, drawn, with the secret recorded
import deepthought.theme as theme_mod
def drawn_on(screen_maker):
    """All the text one screen draws, and any toast."""
    out, real = [], theme_mod.draw_text
    def spy(surf, text, *a, **k):
        out.append(text); return real(surf, text, *a, **k)
    theme_mod.draw_text = spy
    try:
        screen_maker(); app.render()
    finally:
        theme_mod.draw_text = real
    return " | ".join(out + [w.label for w in app.screen.widgets] + [getattr(w, "text", "") or "" for w in app.screen.widgets] + [app.toast or ""])
scr = play_on(ts)
seen_all = [drawn_on(lambda: None), drawn_on(lambda: tap("Score")), drawn_on(lambda: tap("Ethan Lost")), drawn_on(lambda: (app.pop(), app.pop(), tap("Menu")))]
app.pop()
check("Tac Op: no screen on the box shows the name; the scoreboard there says chosen and not chosen", not any("zzyzx" in x.lower() for x in seen_all)
      and "Tac Op: chosen" in seen_all[1] and "Tac Op: not chosen" in seen_all[1], seen_all[1])
app.game_event(dict(acts_of(ts, 1)["Record my Tac Op"]["ev"], text="qqfoo plan"))
check("Tac Op: recorded from a phone during play: the box says it is chosen, not what", ts.state["tacop"][1] == "Qqfoo Plan" and "Trevor has chosen a Tac Op" in app.toast and "qqfoo" not in app.toast.lower(), app.toast)
app.toast = None
app.game_event(acts_of(ts, 0)["Reveal my Tac Op"]["ev"])
check("Tac Op: revealed from the owner's phone: she says it, and from then on everyone can see it",
      app.toast == "Ethan's Tac Op: %s." % SECRET and ts.state["tac_shown"] == [True, False] and kt.scoreboard(ts)["rows"][0]["tacop"] == SECRET
      and "Ethan's Tac Op: %s" % SECRET in kt.phone(ts, 1)["lines"] and "Your Tac Op: %s (revealed)" % SECRET in kt.phone(ts, 0)["lines"], app.toast)
check("Tac Op: the other one is still secret", "qqfoo" not in public(ts, 1).lower() and "qqfoo" not in drawn_on(lambda: tap("Score")).lower())
app.pop(); app.toast = None
a0 = acts_of(ts, 0)
check("Tac Op: once revealed it cannot be changed or revealed again", "Reveal my Tac Op" not in a0 and "Change my Tac Op" not in a0 and "Record my Tac Op" not in a0
      and "already revealed" in ts.do(ev="reveal", side=0)[0] and "stays as it is" in ts.do(ev="tacop", side=0, text="x")[0])
check("Tac Op: undo hides it again", ts.undo() and ts.state["tac_shown"] == [False, False] and "zzyzx" not in public(ts).lower() and "Reveal my Tac Op" in acts_of(ts, 0))
# the end of the game on the box: Done on the last score sheet shows both
while not (ts.state["tp"] == ts.state["tp_max"] and ts.state["phase"] == "end"):
    if ts.state["phase"] == "strategy" and ts.state["init"] is None: ts.do(ev="init", side=0)
    ts.do(ev="next")
scr = play_on(ts); app.toast = None
check("Tac Op: still secret in the last End phase, until the scoring is done", "zzyzx" not in public(ts).lower() and "qqfoo" not in public(ts, 1).lower())
press(); n_log = len(ts.log); press()
rv = app.screen
check("Tac Op: Done on the last score sheet reveals both, with the primary ops; she says them; the screen fits",
      isinstance(rv, KTReveal) and ts.state["tac_shown"] == [True, True] and len(ts.log) == n_log + 1 and SECRET in app.toast and "Qqfoo Plan" in app.toast and ok("reveal with tac ops"), app.toast)
app.toast = None
text = drawn_on(lambda: None)
check("Tac Op: the reveal screen shows each side's by name", "Tac Op: %s" % SECRET in text and "Tac Op: Qqfoo Plan" in text, text)
app.gesture("double")
check("Tac Op: the double of that press takes the reveal back, and nothing else", ts.state["tac_shown"] == [False, False] and len(ts.log) == n_log and ts.state["phase"] == "end", (len(ts.log), n_log))
ts.do(ev="primary", side=0, cat="kill"); ts.do(ev="primary", side=1, cat="tac"); ts.do(ev="next")
check("Tac Op: when the game ends nothing is secret any more", ts.finished and ts.state["tac_shown"] == [True, True] and kt.scoreboard(ts)["rows"][1]["tacop"] == "Qqfoo Plan")
app.go_home(); app.toast = None
# only one recorded, none recorded, and Tac Ops off
one = new(a=1, b=1, folder=sess); one.do(ev="tacop", side=1, text="solo zzyzx"); begin(one)
check("Tac Op: revealing when there is none is refused", "no Tac Op to reveal" in one.do(ev="reveal", side=0)[0] and one.do(ev="reveal", side="all") == ["Trevor's Tac Op: Solo Zzyzx."]
      and one.state["tac_shown"] == [False, True] and "no Tac Op to reveal" in one.do(ev="reveal", side="all")[0])
off = new(tac="Off", folder=sess)
check("Tac Ops off: nothing about a Tac Op on a phone or the scoreboard, and recording one is refused",
      not any("Tac Op" in x for x in kt.phone(off, 0)["lines"] + list(acts_of(off, 0))) and "Tac Op:" not in kt.scoreboard(off)["rows"][0]["detail"] and kt.scoreboard(off)["rows"][0]["tacop"] == ""
      and "off for this game" in off.do(ev="tacop", side=0, text="x")[0] and "off for this game" in off.do(ev="reveal", side=0)[0] and off.state["tacop"] == [None, None])
scr = play_on(off)
check("Tac Ops off: the set-up screen says nothing about them", "Tac Op" not in drawn_on(lambda: None) and ok("setup, tac ops off"))
on = new(folder=sess); scr = play_on(on); on.do(ev="tacop", side=1, text="zzyzx"); scr.refresh()
text = drawn_on(lambda: None)
check("Tac Ops on: the set-up screen says chosen or not chosen for each side, never which", "Tac Op: not chosen" in text and "Tac Op: chosen" in text and "zzyzx" not in text.lower() and ok("setup, tac ops on"), text)
d = json.load(open(on.path, encoding="utf-8"))
for x in [d["state"]] + d["undo"]:
    x.pop("tacop", None); x.pop("tac_shown", None)
old_tac = os.path.join(sess, "old-tacop.json"); json.dump(d, open(old_tac, "w", encoding="utf-8"))
og = engine.Session.load(old_tac, plugins, clock)
check("Tac Op: a game saved before this existed loads, reads as not chosen, and can record one",
      kt.scoreboard(og)["rows"][0]["tacop"] == "not chosen" and "Record my Tac Op" in acts_of(og, 0) and og.do(ev="tacop", side=0, text="late") != [] and og.state["tacop"] == ["Late", None])
app.go_home(); app.toast = None

# ---- the screenshot run
from deepthought.games.killteam import shots as kt_shots
folder, made = tempfile.mkdtemp(), []
def snap(name, screen=None):
    if screen is not None:
        app.stack = [app.stack[0]]; app.toast = None; app.push(screen)
    made.append(app.shot(os.path.join(folder, name + ".png")))
    return screen
kt_shots.shots(app, snap)
check("%d Kill Team screenshots drawn, all 800x480, all named kt-" % len(made), len(made) >= 30 and {pygame.image.load(p).get_size() for p in made} == {(800, 480)} and all(os.path.basename(p).startswith("kt-") for p in made) and len(set(made)) == len(made))
shutil.rmtree(folder)


# ---------------------------------------------------------------- Tac Op names: what a hostile phone could send
check("Tac Op name: characters with no shape are dropped; anything that is not text is no name",
      rules.tac_clean("zz\x00yzx\x1b gam\ud800bit") == "Zz Yzx Gam Bit" and rules.tac_clean(None) == "" and rules.tac_clean(12345) == ""
      and rules.tac_clean({"a": 1}) == "" and rules.tac_clean("\x00\x01") == "", rules.tac_clean("zz\x00yzx\x1b gam\ud800bit"))
_t = new(folder=sess)
_t.do(ev="tacop", side=0, text="A\x00B\ud800C")
with open(_t.path, encoding="utf-8") as _f: _saved = json.load(_f)
check("Tac Op name: what is kept can be saved and drawn", _t.state["tacop"][0] == "A B C" and _saved["state"]["tacop"][0] == "A B C")
_n = len(_t.log)
_said = _t.do(ev="tacop", side=0, text="a b c")
check("Tac Op: 'changing' it to the name it already has is refused, logs nothing, and the refusal does not say the name",
      len(_t.log) == _n and "unchanged" in _said[0] and "a b c" not in _said[0].lower(), _said)
check("Kill Team scoreboard rows carry no line of their own for the page; the page falls back to the detail, which has only the public Tac Op",
      "sub" not in kt.scoreboard(_t)["rows"][0] and "Tac Op: chosen" in kt.scoreboard(_t)["rows"][0]["detail"] and "A B C" not in json.dumps(kt.scoreboard(_t)))

print("\n%d checks" % count[0])
print("%d failed" % len(fails)); sys.exit(1 if fails else 0)
