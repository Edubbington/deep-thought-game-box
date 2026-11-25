"""Tests for the Warhammer 40,000 plugin: its sums, its events, and its screens
in all three modes."""
import json, os, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import engine, paths, theme as T
from deepthought.games import load_games
from deepthought.games.wh40k import rules

fails, count = [], [0]
def check(name, cond, detail=""):
    count[0] += 1
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)
def bad(fn):
    try: fn()
    except ValueError: return True
    return False

games, problems = load_games()
plugins = {g["id"]: g["plugin"] for g in games if g["plugin"]}
check("the game list loads wh40k as a ready plugin, with no problems of its own",
      "wh40k" in plugins and not [p for p in problems if p.startswith("wh40k")], problems)
w = plugins["wh40k"]
info = json.load(open(os.path.join(w.folder, "game.json"), encoding="utf-8"))
check("game.json keeps its id, name and order", (info["id"], info["name"], info["order"]) == ("wh40k", "Warhammer 40,000", 20), info)
check("two players, no more, no fewer", (w.min_players, w.max_players) == (2, 2))
opts = {o["key"]: o["choices"] for o in w.options}
check("options: mode, length, size, and who has the Necrons",
      opts["mode"] == ["Teach", "Reminder", "Silent"] and opts["length"] == ["Full, 5 rounds", "Tutorial, 3 rounds"]
      and len(opts["size"]) == 4 and opts["necrons"] == ["Player 1", "Player 2", "Nobody"] and len(w.options) <= 4, opts)

# ---------------------------------------------------------------- sums: turn order
S = rules.step
check("length: full is 5 battle rounds, tutorial is 3", [rules.rounds_for(x) for x in ("Full, 5 rounds", "Tutorial, 3 rounds", "Tutorial", None)] == [5, 3, 3, 5])
check("phases in order: Command, Movement, Shooting, Charge, Fight", rules.ORDER == ["command", "movement", "shooting", "charge", "fight"])
walk, at = [], ("command", 0, 1)
for _ in range(4):
    at = S(at[0], at[1], 0, at[2], 5); walk.append(at)
check("next walks the five phases of one player's turn", walk == [("movement", 0, 1), ("shooting", 0, 1), ("charge", 0, 1), ("fight", 0, 1)], walk)
check("after the first player's Fight: the other player's Command, same round", S("fight", 0, 0, 1, 5) == ("command", 1, 1))
check("after the second player's Fight: round 2, first player's Command", S("fight", 1, 0, 1, 5) == ("command", 0, 2))
check("when player 2 has the first turn the order is 2 then 1", S("fight", 1, 1, 3, 5) == ("command", 0, 3) and S("fight", 0, 1, 3, 5) == ("command", 1, 4))
check("after the last Fight of round 5: the end, not round 6", S("fight", 1, 0, 5, 5) == ("end", 1, 5))
check("a tutorial ends after round 3", S("fight", 1, 0, 3, 3) == ("end", 1, 3) and S("fight", 1, 0, 2, 3) == ("command", 0, 3))
check("the first player's Fight in the last round does not end the game", S("fight", 0, 0, 5, 5) == ("command", 1, 5))
check("there is nothing after the end", bad(lambda: S("end", 1, 0, 5, 5)))
n, at = 0, ("command", 0, 1)
while at[0] != "end":
    at = S(at[0], at[1], 0, at[2], 5); n += 1
check("a full game is 50 presses: 5 rounds x 2 turns x 5 phases", n == 50, n)

# ---------------------------------------------------------------- sums: command points
check("command points: one each per Command phase; a remark above 12, not at 12",
      rules.CP_PER_COMMAND == 1 and not rules.cp_warning(12) and rules.cp_warning(13) and not rules.cp_warning(0))

# ---------------------------------------------------------------- sums: scoring
t = rules.SCORING
check("the scoring table: primary from round 2; caps 15 a round, 50 primary, 40 secondary (defaults, marked)",
      (t["primary_from_round"], t["primary_per_round"], t["primary_max"], t["secondary_max"]) == (2, 15, 50, 40)
      and [r["name"] for r in t["secondary_rows"]] == ["Secondary 1", "Secondary 2"], t)
P = rules.add_primary
check("primary: none in battle round 1", bad(lambda: P([0] * 6, 1, 1)))
check("primary: round 2, 5 points go in round 2's slot", P([0] * 6, 2, 5) == [0, 5, 0, 0, 0, 0])
check("primary: 15 in a round is allowed, 16 is not", P([0] * 6, 2, 15) == [0, 15, 0, 0, 0, 0] and bad(lambda: P([0] * 6, 2, 16)))
check("primary: 10 already this round, 5 more fits, 6 more does not", P([0, 10, 0, 0, 0, 0], 2, 5)[1] == 15 and bad(lambda: P([0, 10, 0, 0, 0, 0], 2, 6)))
check("primary: the round cap starts afresh next round", P([0, 15, 0, 0, 0, 0], 3, 15) == [0, 15, 15, 0, 0, 0])
check("primary: 45 scored, round 5: 5 more makes 50, 6 more is refused", sum(P([0, 15, 15, 15, 0, 0], 5, 5)) == 50 and bad(lambda: P([0, 15, 15, 15, 0, 0], 5, 6)))
check("primary: end-of-game points have their own slot and no round cap", P([0, 5, 5, 5, 5, 0], 5, 20, final=True) == [0, 5, 5, 5, 5, 20])
check("primary: end-of-game points still stop at 50 in all", bad(lambda: P([0, 15, 15, 15, 0, 0], 5, 6, final=True)) and P([0, 15, 15, 15, 0, 0], 5, 5, final=True)[5] == 5)
check("primary: taking away comes off this round first, then the latest before it", P([0, 10, 3, 0, 0, 0], 3, -5) == [0, 8, 0, 0, 0, 0], P([0, 10, 3, 0, 0, 0], 3, -5))
check("primary: cannot take away more than was scored", bad(lambda: P([0, 2, 0, 0, 0, 0], 2, -3)) and P([0, 2, 0, 0, 0, 0], 2, -2) == [0] * 6)
loose = dict(t, primary_from_round=1, primary_per_round=None, primary_max=None)
check("primary: the table is what decides; edit it and round 1 and 99 points are allowed", P([0] * 6, 1, 99, table=loose) == [99, 0, 0, 0, 0, 0])
Q = rules.add_secondary
check("secondary: each row keeps its own points", Q([0, 0], 0, 5) == [5, 0] and Q([5, 0], 1, 3) == [5, 3])
check("secondary: a row cannot go below nothing", bad(lambda: Q([5, 0], 1, -1)) and Q([5, 0], 0, -5) == [0, 0])
check("secondary: 38 scored, 2 more makes 40, 3 more is refused", Q([30, 8], 1, 2) == [30, 10] and bad(lambda: Q([30, 8], 1, 3)))
check("secondary: a row's own cap, when the table gives one", bad(lambda: Q([5, 0], 0, 1, table=dict(t, secondary_rows=[{"name": "A", "max": 5}, {"name": "B", "max": None}])))
      and Q([4, 0], 0, 1, table=dict(t, secondary_rows=[{"name": "A", "max": 5}, {"name": "B", "max": None}])) == [5, 0])
check("secondary: no third row", bad(lambda: Q([0, 0], 2, 1)))
check("totals: 15 + 10 primary and 4 + 3 secondary is 25, 7, 32", rules.totals([0, 15, 10, 0, 0, 0], [4, 3]) == (25, 7, 32))
check("winner: more points wins; equal is a draw", (rules.winner(32, 30), rules.winner(30, 32), rules.winner(30, 30)) == (0, 1, None))

# ---------------------------------------------------------------- sums: units
H = rules.below_half
check("half strength, even: a unit of 20 is below half at 9, not at 10", H(20, 9) and not H(20, 10))
check("half strength, even: a unit of 10 is below half at 4, not at 5", H(10, 4) and not H(10, 5))
check("half strength, odd: a unit of 5 is below half at 2, not at 3", H(5, 2) and not H(5, 3))
check("half strength, odd: a unit of 3 is below half at 1, not at 2", H(3, 1) and not H(3, 2))
check("half strength: a unit of 2 with one left is exactly half, so not below", not H(2, 1))
check("half strength: one model counts wounds, so its player marks it", H(1, 1, hurt=True) and not H(1, 1, hurt=False))
check("half strength: a destroyed unit is not 'below half', it is gone", not H(5, 0) and not H(1, 0, hurt=True))
M = rules.step_model
check("models: remove one of 5, put it back", M(5, 5, False, -1) == (4, False) and M(5, 4, False, 1) == (5, False))
check("models: never below 0 or above the starting size", bad(lambda: M(5, 0, False, -1)) and bad(lambda: M(5, 5, False, 1)))
check("models: the last one going leaves 0", M(5, 1, False, -1) == (0, False))
check("one model: whole, then below half its wounds, then destroyed", M(1, 1, False, -1) == (1, True) and M(1, 1, True, -1) == (0, False))
check("one model: restoring goes back the same way", M(1, 0, False, 1) == (1, True) and M(1, 1, True, 1) == (1, False) and bad(lambda: M(1, 1, False, 1)))
check("models: one at a time", bad(lambda: M(5, 5, False, -2)))
u = rules.new_unit("Test", 10)
check("a new unit is at full strength and takes no test", u == {"name": "Test", "start": 10, "alive": 10, "hurt": False, "shocked": False} and not rules.needs_test(u))
check("battle-shock test: below half, or still shocked; never when destroyed",
      rules.needs_test(dict(u, alive=4)) and rules.needs_test(dict(u, shocked=True)) and not rules.needs_test(dict(u, alive=5))
      and not rules.needs_test(dict(u, alive=0, shocked=True)))

# ---------------------------------------------------------------- sums: the wound roll
W = rules.wound_roll
check("wound: Strength 8 against Toughness 4 is double: 2+", W(8, 4) == 2)
check("wound: more than double is still 2+", W(9, 4) == 2 and W(12, 4) == 2 and W(2, 1) == 2)
check("wound: Strength 7 or 5 against Toughness 4 is higher, not double: 3+", W(7, 4) == 3 and W(5, 4) == 3)
check("wound: Strength 9 against Toughness 5 is just short of double: 3+", W(9, 5) == 3 and W(10, 5) == 2)
check("wound: equal is 4+", W(4, 4) == 4 and W(1, 1) == 4 and W(10, 10) == 4)
check("wound: Strength 3 against Toughness 4 is lower: 5+", W(3, 4) == 5)
check("wound: Strength 3 against Toughness 5 is lower but more than half: 5+", W(3, 5) == 5 and W(5, 9) == 5 and W(6, 10) == 5)
check("wound: Strength 2 against Toughness 4 is half: 6+", W(2, 4) == 6 and W(5, 10) == 6 and W(1, 2) == 6)
check("wound: less than half is still 6+", W(1, 4) == 6 and W(3, 7) == 6 and W(4, 9) == 6)
check("wound: nothing below 1", bad(lambda: W(0, 4)) and bad(lambda: W(4, 0)))
check("wound: the card's five rows say the same as the sum",
      [n for _, n in rules.WOUND_ROWS] == [W(8, 4), W(5, 4), W(4, 4), W(3, 4), W(2, 4)] == [2, 3, 4, 5, 6])

# ---------------------------------------------------------------- the owner's army
with open(os.path.join(w.folder, "armies.json"), encoding="utf-8") as f:
    armies = json.load(f)
nec = armies["necrons"]["units"]
check("Necron list: names and model counts only, nothing else", all(sorted(x) == ["name", "size"] for x in nec), nec)
by = {}
for x in nec: by[x["name"].split(",")[0]] = by.get(x["name"].split(",")[0], 0) + x["size"]
check("Necron list: 20 Warriors, 5 Lychguard, 5 Praetorians, 6 Scarab bases, and one each of the four big names",
      by == {"Necron Warriors": 20, "Overlord": 1, "Royal Warden": 1, "Lychguard": 5, "Triarch Praetorians": 5,
             "Canoptek Doomstalker": 1, "Scarab Swarms": 6, "C'tan Void Dragon": 1}, by)

# ---------------------------------------------------------------- the game, event by event
class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t
clock = Clock()
folder = paths.data("sessions")
def new(mode="Reminder", length="Full, 5 rounds", necrons="Player 1", save=None):
    return engine.Session(w, ["Ethan", "Trevor"], {"mode": mode, "length": length, "size": "Combat Patrol", "necrons": necrons}, save, clock)
def nexts(s, n):
    out = []
    for _ in range(n): out = s.do(ev="next")
    return out

s = new(save=folder)
st = s.state
check("new game: round 1 of 5, Command phase, Ethan's turn, saved at once",
      (st["round"], st["rounds"], st["phase"], s.active_name()) == (1, 5, "command", "Ethan") and os.path.isfile(s.path))
check("the first Command phase has given both players 1 command point", st["cp"] == [1, 1])
check("Ethan has the Necron list, 9 units and 40 models; Trevor's list is empty",
      len(st["army"][0]) == 9 and sum(x["start"] for x in st["army"][0]) == 40 and st["army"][1] == [], st["army"])
check("strip: 40k, round 1 of 5, Command phase", w.strip(s) == ("40k · Round 1 of 5", "Command phase"), w.strip(s))
check("the five phases are offered for reminders", w.phases() == rules.PHASES and w.phase(st) == "command")
said = s.do(ev="next")
check("next: Movement phase, same player, no new command points", (st["phase"], st["active"], st["cp"]) == ("movement", 0, [1, 1]) and said == [], said)
nexts(s, 3)
check("three more: Shooting, Charge, Fight", st["phase"] == "fight" and st["active"] == 0)
said = s.do(ev="next")
check("after Fight: Trevor's Command phase, still round 1, both now on 2 command points",
      (st["phase"], st["active"], st["round"], st["cp"]) == ("command", 1, 1, [2, 2]) and "Trevor's turn. Command points: Ethan 2, Trevor 2." in said, said)
check("undo: back to Ethan's Fight phase and 1 command point each", s.undo() and (st := s.state)["phase"] == "fight" and st["active"] == 0 and st["cp"] == [1, 1])
s.do(ev="next"); st = s.state
said = nexts(s, 5)
check("after Trevor's Fight: battle round 2, Ethan again, 3 command points each",
      (st["round"], st["active"], st["phase"], st["cp"]) == (2, 0, "command", [3, 3]) and said[0] == "Battle round two.", said)
again = engine.Session.load(s.path, plugins, clock)
check("a saved game loads back exactly", again.state == s.state and again.log == s.log)

# command points
said = s.do(ev="cp", side=0, delta=-1)
check("spending a command point: Ethan 2, Trevor 3", st["cp"] == [2, 3] and said == [])
s.do(ev="cp", side=0, delta=-1); s.do(ev="cp", side=0, delta=-1)
n = len(s.log)
said = s.do(ev="cp", side=0, delta=-1)
st = s.state
check("no command points left: the spend is refused and not logged", st["cp"] == [0, 3] and "no command points" in said[0] and len(s.log) == n, said)
for _ in range(9): said = s.do(ev="cp", side=1, delta=1)
check("Trevor at 12 command points: no remark", st["cp"][1] == 12 and said == [], said)
said = s.do(ev="cp", side=1, delta=1)
check("Trevor at 13: a remark, but the points stand", st["cp"][1] == 13 and "More than twelve" in said[0] and "Trevor has 13" in said[0], said)
said = nexts(s, 5)
check("the next Command phase adds 1 to both and remarks on 14 again", st["cp"] == [1, 14] and any("Trevor has 14" in x for x in said), said)
for _ in range(5): s.undo()
st = s.state
check("five undos: back in Ethan's Command phase of round 2", (st["round"], st["active"], st["phase"], st["cp"]) == (2, 0, "command", [0, 13]))

# scoring
s1 = new()
n = len(s1.log)
said = s1.do(ev="score", side=0, cat="primary", delta=1)
check("round 1: primary points are refused, with the reason", "start in battle round 2" in said[0] and len(s1.log) == n and w.score(s1.state, 0) == (0, 0, 0), said)
s1.do(ev="score", side=0, cat="sec", row=0, delta=1)
check("round 1: a secondary may score", w.score(s1.state, 0) == (0, 1, 1))
nexts(s1, 10)
for _ in range(15): s1.do(ev="score", side=0, cat="primary", delta=1)
said = s1.do(ev="score", side=0, cat="primary", delta=1)
check("round 2: 15 primary go in, the 16th is refused", w.score(s1.state, 0) == (15, 1, 16) and "15 in one battle round" in said[0], said)
check("the other player's primary this round is counted apart", s1.do(ev="score", side=1, cat="primary", delta=1) == [] and w.score(s1.state, 1) == (1, 0, 1))
s1.do(ev="score", side=0, cat="sec", row=1, delta=1); s1.do(ev="score", side=0, cat="sec", row=1, delta=1)
check("secondary rows: row 1 has 1, row 2 has 2; total 15 + 3 = 18", [r["pts"] for r in s1.state["secs"][0]] == [1, 2] and w.score(s1.state, 0) == (15, 3, 18))
check("undo takes back one point", s1.undo() and [r["pts"] for r in s1.state["secs"][0]] == [1, 1])
s1.do(ev="score", side=0, cat="primary", delta=-1)
check("a point can be taken away again: 14 primary", w.score(s1.state, 0)[0] == 14)
check("there is no third kind of point", "no third kind" in s1.do(ev="score", side=0, cat="bonus", delta=1)[0])
for rnd in (3, 4, 5):
    nexts(s1, 10)
    for _ in range(15): s1.do(ev="score", side=0, cat="primary", delta=1)
check("rounds 2 to 5 at 14, 15, 15 and then only 6 of 15: primary stops at 50", w.score(s1.state, 0)[0] == 50 and s1.state["primary"][0] == [0, 14, 15, 15, 6, 0], s1.state["primary"][0])
check("leader: Ethan, 52 to 1", w.leader(s1.state) == 0 and w.score(s1.state, 0)[2] == 52)

# units
a = st["army"][0]
check("the first unit is 20 Necron Warriors", (a[0]["name"], a[0]["start"]) == ("Necron Warriors", 20))
for _ in range(10): said = s.do(ev="model", side=0, unit=0, delta=-1)
check("Warriors at 10 of 20: exactly half, no test, nothing said", a[0]["alive"] == 10 and w.tests(st, 0) == [] and said == [], said)
said = s.do(ev="model", side=0, unit=0, delta=-1)
check("Warriors at 9 of 20: below half, and she says so", a[0]["alive"] == 9 and w.tests(st, 0) == ["Necron Warriors"] and "below half strength" in said[0], said)
check("Lychguard is unit 4, five strong", (a[3]["name"], a[3]["start"]) == ("Lychguard", 5))
s.do(ev="model", side=0, unit=3, delta=-1); s.do(ev="model", side=0, unit=3, delta=-1)
check("Lychguard at 3 of 5: not below half", w.tests(st, 0) == ["Necron Warriors"])
said = s.do(ev="model", side=0, unit=3, delta=-1)
check("Lychguard at 2 of 5: below half", w.tests(st, 0) == ["Necron Warriors", "Lychguard"] and "below half" in said[0])
s.do(ev="shock", side=0, unit=3)
check("a unit can be marked battle-shocked", a[3]["shocked"] is True)
s.do(ev="model", side=0, unit=3, delta=-1); said = s.do(ev="model", side=0, unit=3, delta=-1)
check("Lychguard at 0: destroyed, no longer shocked, no test, 8 of 9 units left",
      a[3]["alive"] == 0 and not a[3]["shocked"] and w.tests(st, 0) == ["Necron Warriors"] and "destroyed" in said[0] and rules.units_alive(a) == 8, said)
n = len(s.log)
check("a destroyed unit loses no more models, and cannot be shocked", "already destroyed" in s.do(ev="model", side=0, unit=3, delta=-1)[0]
      and "destroyed" in s.do(ev="shock", side=0, unit=3)[0] and len(s.log) == n)
st = s.state; a = st["army"][0]
s.do(ev="model", side=0, unit=3, delta=1)
check("a model can be restored: Lychguard 1 of 5, below half", a[3]["alive"] == 1 and "Lychguard" in w.tests(st, 0))
check("undo puts the unit back to destroyed", s.undo() and s.state["army"][0][3]["alive"] == 0)
st = s.state; a = st["army"][0]
check("the Overlord is one model", (a[1]["name"], a[1]["start"]) == ("Overlord", 1))
s.do(ev="model", side=0, unit=1, delta=-1)
check("one model, first tap: still on the table, below half its wounds", a[1]["alive"] == 1 and a[1]["hurt"] and "Overlord" in w.tests(st, 0))
s.do(ev="model", side=0, unit=1, delta=-1)
check("one model, second tap: destroyed", a[1]["alive"] == 0 and "Overlord" not in w.tests(st, 0))
check("no such unit: refused", "no such unit" in s.do(ev="model", side=0, unit=99, delta=-1)[0] and "no such unit" in s.do(ev="model", side=1, unit=0, delta=-1)[0])
st = s.state
s.do(ev="shock", side=0, unit=4)
check("a shocked unit at full strength still tests", w.tests(st, 0) == ["Necron Warriors", "Triarch Praetorians"], w.tests(st, 0))
said = nexts(s, 10)
check("Ethan's next Command phase says battle-shock tests are due", s.active_name() == "Ethan" and "Battle-shock tests are due." in said, said)
said = nexts(s, 5)
check("Trevor's Command phase does not: his list has nothing below half", s.active_name() == "Trevor" and "Battle-shock tests are due." not in said, said)

# the other side's list, made with taps
e = new(necrons="Nobody")
check("Necrons: Nobody leaves both lists empty", e.state["army"] == [[], []])
e.do(ev="army", side=1, op="add", size=5); e.do(ev="army", side=1, op="add", size=5)
b = e.state["army"][1]
check("add unit twice: Unit 1 and Unit 2, five models each", [(x["name"], x["start"], x["alive"]) for x in b] == [("Unit 1", 5, 5), ("Unit 2", 5, 5)], b)
e.do(ev="army", side=1, op="size", unit=0, delta=5); e.do(ev="army", side=1, op="size", unit=1, delta=-1)
check("sizes change by taps: 10 and 4", [x["start"] for x in e.state["army"][1]] == [10, 4])
e.do(ev="model", side=1, unit=0, delta=-1); e.do(ev="army", side=1, op="size", unit=0, delta=1)
check("a new size puts the unit back to full: 11 of 11", (e.state["army"][1][0]["alive"], e.state["army"][1][0]["start"]) == (11, 11))
for _ in range(3): e.do(ev="army", side=1, op="size", unit=1, delta=-1)
check("a unit cannot be smaller than 1 model, or bigger than 30",
      e.state["army"][1][1]["start"] == 1 and "between 1 and 30" in e.do(ev="army", side=1, op="size", unit=1, delta=-1)[0]
      and "between 1 and 30" in e.do(ev="army", side=1, op="size", unit=0, delta=20)[0])
e.do(ev="army", side=1, op="remove", unit=0); e.do(ev="army", side=1, op="add", size=5)
check("remove a unit, add another: names do not repeat", [x["name"] for x in e.state["army"][1]] == ["Unit 2", "Unit 3"])
for _ in range(10): e.do(ev="army", side=1, op="add", size=5)
check("twelve units a side at most", len(e.state["army"][1]) == 12 and "12 units" in e.do(ev="army", side=1, op="add", size=5)[0])
e.do(ev="army", side=0, op="preset", name="necrons")
check("the ready-made Necron list can be loaded for either side later", len(e.state["army"][0]) == 9 and "no list called" in e.do(ev="army", side=0, op="preset", name="orks")[0])
p2 = new(necrons="Player 2")
check("Necrons: Player 2 gives Trevor the list", p2.state["army"][0] == [] and len(p2.state["army"][1]) == 9)

# who goes first
f = new()
said = f.do(ev="first", side=1)
check("swap first: Trevor takes the first turn, command points unchanged", (f.state["first"], f.active_name(), f.state["cp"]) == (1, "Trevor", [1, 1]) and "Trevor takes the first turn." in said)
nexts(f, 5)
check("then Ethan's turn in the same round", (f.active_name(), f.state["round"]) == ("Ethan", 1))
nexts(f, 5)
check("then round 2 with Trevor first again", (f.active_name(), f.state["round"]) == ("Trevor", 2))
check("too late to swap now", "too late" in f.do(ev="first", side=0)[0] and f.state["first"] == 1)
f2 = new(); f2.do(ev="next")
check("too late to swap once the first Command phase has passed", "too late" in f2.do(ev="first", side=1)[0])

# the one word a player says
d = new()
check("Advance belongs to the Movement phase", "Movement phase" in d.do(ev="did", what="advance")[0])
d.do(ev="next")
check("Reminder mode: Advance earns a line, not a card", "Advance:" in d.do(ev="did", what="advance")[0] and d.state["taught"] == [])
check("Fall Back earns its own line", "Fall Back:" in d.do(ev="did", what="fallback")[0])
check("Charge belongs to the Charge phase", "Charge phase" in d.do(ev="did", what="charge")[0])
nexts(d, 2)
check("in the Charge phase it is accepted", "Charge:" in d.do(ev="did", what="charge")[0])
check("an unknown event is refused politely", "do not know" in d.do(ev="dance")[0] and "do not know" in d.do(ev="did", what="dance")[0])

# game end
g = new(length="Tutorial, 3 rounds")
check("tutorial: 3 battle rounds", g.state["rounds"] == 3 and len(g.state["primary"][0]) == 4)
said = nexts(g, 20)
check("round 3 of 3 is announced as the final round", g.state["round"] == 3 and said[0] == "Final round.", said)
for _ in range(7): g.do(ev="score", side=0, cat="primary", delta=1)
for _ in range(4): g.do(ev="score", side=1, cat="sec", row=0, delta=1)
nexts(g, 9)
check("29 presses in: Trevor's Fight phase of round 3, not over", (g.state["phase"], g.state["active"], g.finished) == ("fight", 1, None))
said = g.do(ev="next")
check("30th press: final scores, nobody's turn, still not over", g.state["phase"] == "end" and w.active(g.state) is None and g.finished is None and "end-of-game" in said[0], said)
check("command points after a 3-round game with none spent: 6 each (2 a round)", g.state["cp"] == [6, 6])
check("strip at the end: Final scores", w.strip(g) == ("40k · Round 3 of 3", "Final scores"))
for _ in range(20): g.do(ev="score", side=1, cat="primary", delta=1)
check("end-of-game primary is not held to 15 a round: Trevor 20 + 4 = 24", w.score(g.state, 1) == (20, 4, 24) and g.state["primary"][1] == [0, 0, 0, 20])
g.do(ev="next")
check("one more press ends it: Trevor wins 24 to 7",
      g.finished and g.finished["winner"] == "Trevor" and g.finished["lines"][0] == "24 victory points to 7"
      and g.finished["lines"][1] == "Ethan: 7 primary, 0 secondary. Trevor: 20 and 4.", g.finished)
check("a finished game takes no more events", g.do(ev="next") == ["The game is over."])
check("undo reopens it at the final scores", g.undo() and g.finished is None and g.state["phase"] == "end" and not g.state["done"])
for _ in range(17): g.do(ev="score", side=0, cat="sec", row=1, delta=1)
g.do(ev="next")
check("7 + 17 = 24 against 24: a draw, no winner", g.finished["winner"] is None and g.finished["lines"][0] == "A draw: 24 to 24" and w.leader(g.state) is None, g.finished)
full = new(mode="Silent")
talk = []
for _ in range(50): talk += full.do(ev="next")
check("a full game: 50 presses reach the final scores in round 5, 10 command points each",
      (full.state["phase"], full.state["round"], full.state["cp"]) == ("end", 5, [10, 10]) and full.finished is None)
check("Silent mode says nothing through a whole game", talk == [], talk)
full.do(ev="model", side=0, unit=0, delta=-1)
check("Silent mode still refuses what is wrong", "no command points" in " ".join(full.do(ev="cp", side=0, delta=-11)))
full.do(ev="next")
check("no points at all is a draw at 0 to 0", full.finished and full.finished["winner"] is None and full.finished["lines"][0] == "A draw: 0 to 0")
early = new(); nexts(early, 10); early.do(ev="score", side=1, cat="sec", row=0, delta=3); early.finish()
check("stopped early: the leader is named with the standings",
      early.finished["winner"] == "Trevor" and early.finished["lines"] == ["Victory points: Ethan 0, Trevor 3", "Stopped in battle round 2 of 5"], early.finished)

# Teach mode: which cards are owed, once each
teach = json.load(open(os.path.join(w.folder, "teach.json"), encoding="utf-8"))
ids = [x.get("id") for x in teach]
from deepthought.games.wh40k import plugin as P40
need = set(P40.INTRO) | {c for _, c, _ in P40.DID.values()} | {k for k, _ in rules.PHASES} | {"turn2", "round2", "shock", "strat", "final"}
check("teach.json: every step has an id, a title and text, and every card the game can show is there",
      all(x.get("id") and x.get("title") and x.get("text") for x in teach) and need <= set(ids) and len(ids) == len(set(ids)), need - set(ids))
words = " ".join(x["title"] + " " + x["text"] for x in teach)
check("teach.json: her voice: no exclamation marks, no 'awesome', no \"let's go\"", "!" not in words and "awesome" not in words.lower() and "let's go" not in words.lower())
check("How to play (the shared pager) reads every step", len(w.teach()) == len(teach) and w.cards(["advance"])[0][0] == "Advancing")
tm = new(mode="Teach", length="Tutorial, 3 rounds")
t0 = list(tm.state["taught"])
check("Teach: the first-game steps count as shown from the start", t0 == P40.INTRO)
def fresh(s, fn):
    before = list(s.state["taught"]); fn()
    return [k for k in s.state["taught"] if k not in before]
check("Teach: first Movement phase owes the movement card", fresh(tm, lambda: tm.do(ev="next")) == ["movement"])
check("Teach: first Advance owes the advance card, and says nothing", fresh(tm, lambda: talk.extend(tm.do(ev="did", what="advance"))) == ["advance"] and talk == [])
check("Teach: the second Advance owes nothing and gets the short line", fresh(tm, lambda: talk.extend(tm.do(ev="did", what="advance"))) == [] and "Advance:" in talk.pop())
check("Teach: first Fall Back owes its card", fresh(tm, lambda: tm.do(ev="did", what="fallback")) == ["fallback"])
check("Teach: Shooting, then Charge, each owe their card", fresh(tm, lambda: tm.do(ev="next")) == ["shooting"] and fresh(tm, lambda: tm.do(ev="next")) == ["charge"])
check("Teach: first charge owes the first-charge card", fresh(tm, lambda: tm.do(ev="did", what="charge")) == ["charge1"])
check("Teach: Fight owes its card", fresh(tm, lambda: tm.do(ev="next")) == ["fight"])
check("Teach: the second player's first turn owes the end-of-turn card only", fresh(tm, lambda: tm.do(ev="next")) == ["turn2"])
check("Teach: his phases owe nothing new", fresh(tm, lambda: nexts(tm, 4)) == [])
check("Teach: first spend of a command point owes the stratagem card", fresh(tm, lambda: tm.do(ev="cp", side=1, delta=-1)) == ["strat"])
for _ in range(11): tm.do(ev="model", side=0, unit=0, delta=-1)
check("Teach: round 2 owes the scoring card, and battle-shock because Warriors are at 9 of 20", fresh(tm, lambda: tm.do(ev="next")) == ["round2", "shock"])
check("Teach: nothing new for the rest of round 2", fresh(tm, lambda: nexts(tm, 9)) == [])
check("Teach: round 3 of 3 owes the final-round card", fresh(tm, lambda: tm.do(ev="next")) == ["final"])
check("Teach: each card once per game: twelve keys beyond the intro, no repeats", len(tm.state["taught"]) == len(set(tm.state["taught"])) == len(P40.INTRO) + 12, tm.state["taught"])
tm.undo()
check("Teach: undo forgets the card with the event, so it will be shown again", "final" not in tm.state["taught"])
r = new(mode="Reminder", length="Tutorial, 3 rounds")
r.do(ev="cp", side=0, delta=-1); nexts(r, 30)
check("Reminder: no cards are ever owed", r.state["taught"] == [])

# phone and scoreboard
ph = new()
nexts(ph, 10); ph.do(ev="score", side=0, cat="primary", delta=3); ph.do(ev="score", side=0, cat="sec", row=1, delta=2)
ph.do(ev="model", side=0, unit=0, delta=-1)
mine, theirs = w.phone(ph, 0), w.phone(ph, 1)
labels = [x["label"] for x in mine["actions"]]
check("phone: the player whose turn it is may press Next; the other may not", labels[0] == "Next phase" and "Next phase" not in [x["label"] for x in theirs["actions"]])
check("phone: lines show the player's own points and command points", "Victory points: 5 (3 primary, 2 secondary)" in mine["lines"] and "Command points: 3" in mine["lines"]
      and "Necron Warriors: 19 of 20" in mine["lines"], mine["lines"])
check("phone: actions for scoring, spending and marking models", {"Primary +1", "Primary -1", "Secondary 1 +1", "Secondary 2 -1", "Spend 1 command point",
      "Necron Warriors: lose a model", "Necron Warriors: restore a model"} <= set(labels) and "Overlord: restore a model" not in labels, labels)
check("phone: every action touches only that player's own side", all(x["ev"].get("side", 1) == 1 for x in theirs["actions"]) and all(x["ev"].get("side", 0) == 0 for x in mine["actions"]))
check("phone: Trevor's phone does not list Ethan's units", not any("Necron" in l for l in theirs["lines"]))
act = next(x for x in mine["actions"] if x["label"] == "Spend 1 command point")
ph.do(**act["ev"])
check("phone: an action is an ordinary event", ph.state["cp"] == [2, 3])
check("phone: a spectator sees where the game is and can do nothing", w.phone(ph, None) == {"lines": ["Battle round 2 of 5, Command phase, Ethan's turn"], "actions": []})
sb = w.scoreboard(ph)
check("scoreboard: totals, the split, command points and units alive",
      sb["rows"][0] == {"name": "Ethan", "value": 5, "primary": 3, "secondary": 2, "cp": 2, "units": 9, "units_start": 9, "sub": "Secondary 2 2",
                        "secondaries": [{"name": "Secondary 2", "points": 2, "now": True}]}
      and sb["rows"][1]["value"] == 0 and sb["note"] == "Battle round 2 of 5, Command phase, Ethan's turn", sb)
json.dumps(ph.state)
check("the state is plain data", True)

# ---------------------------------------------------------------- screens
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens import common, extras
from deepthought.screens.home import Home
from deepthought.screens.pick_game import PickGame
from deepthought.games.wh40k.plugin import (TeachCard, W40kArmy, W40kArmyEdit, W40kCommand, W40kPlay, W40kRef, W40kScore)

app = App(hw.make("desktop", sound=False), games, headless=True)
app.push(Home(app))
def screen_ok(screen=None):
    screen = screen or app.screen
    ws, out = [x for x in screen.widgets if x.action], []
    for x in ws:
        if x.rect.h < T.MIN_BUTTON or x.rect.w < T.MIN_BUTTON: out.append(("small", x.label, tuple(x.rect)))
        if not pygame.Rect(0, T.STRIP, T.W, T.H - T.STRIP).contains(x.rect): out.append(("outside", x.label, tuple(x.rect)))
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if a.rect.colliderect(b.rect): out.append(("overlap", a.label, b.label))
    if sum(1 for x in screen.widgets if x.style == "primary") != 1: out.append(("primary buttons", [x.label for x in screen.widgets if x.style == "primary"]))
    app.render()
    return out
def tap(label):
    x = next(x for x in app.screen.widgets if x.action and x.label.startswith(label))
    app.toast = None
    x.action()
def labels():
    return [x.label for x in app.screen.widgets if x.action]
seen = []                                    # every screen_ok() failure on a walk
def look(what):
    r = screen_ok()
    if r: seen.append((what, r))
def cards():
    """Read any teach cards to the end with the button. Returns their headings."""
    out = []
    while isinstance(app.screen, TeachCard):
        look("teach card")
        out.append(app.screen.pages[app.screen.i][0])
        app.gesture("press")
    return out

def start(mode, length, necrons="Player 1"):
    app.go_home(); app.toast = None
    tap("Play")
    if not isinstance(app.screen, PickGame): tap("New game")
    app.screen.choose([g["id"] for g in games].index("wh40k"))
    setup = app.screen
    setup.names[0], setup.names[1] = "Ethan", "Trevor"
    for key, want in (("mode", mode), ("length", length), ("necrons", necrons)):
        o = next(o for o in w.options if o["key"] == key)
        while setup.opts[key] != want: tap(o["label"])
    setup.refresh()
    return setup

setup = start("Teach", "Tutorial, 3 rounds")
check("Pick a game opens Set up for Warhammer 40,000, and it fits", isinstance(setup, common.Setup) and setup.game is w and setup.n == 2 and screen_ok() == [], screen_ok())
check("Set up shows all four options", [l for l in labels() if ":" in l] == ["Mode: Teach", "Length: Tutorial, 3 rounds", "Size: Combat Patrol", "Necrons: Player 1"], labels())
tap("How to play")
check("How to play opens the 40k steps", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "The aim" and screen_ok() == [], screen_ok())
tap("Back")

# ---- Teach mode: the whole tutorial game, on the button
tap("Start game")
first = cards()
play = app.stack[1]
check("Teach: the game opens on the first-game steps, read with the button",
      isinstance(play, W40kPlay) and first[0] == "The aim" and [h for i, h in enumerate(first) if h not in first[:i]] ==
      ["The aim", "The datasheet", "Table and terrain", "Deploy", "Who goes first", "Command phase"], first)
check("Teach: then the play screen, Ethan's turn, ring in his colour",
      app.screen is play and play.pill[0] == "Ethan's turn" and app.hw._ring.now == ("turn", {"colour": T.player_colour(0)}) and screen_ok() == [], screen_ok())
check("strip: 40k, round 1 of 3, Command phase", (play.left, play.title) == ("40k · Round 1 of 3", "Command phase"))
check("the bottom row: Next phase is the main button; Swap first is offered before the first turn moves on",
      labels()[-6:] == ["Next phase", "Score", "Army", "Cards", "Swap first", "Menu"] and play.widgets[-6].style == "primary", labels())
tap("Swap first")
check("Swap first: Trevor's turn", app.session.active_name() == "Trevor" and play.pill[0] == "Trevor's turn" and "Trevor takes the first turn" in app.toast and screen_ok() == [], app.toast)
tap("Swap first"); app.toast = None
check("and back again", app.session.active_name() == "Ethan")
app.gesture("press")
check("Teach: the button moves to Movement and the movement card comes up", app.session.state["phase"] == "movement" and isinstance(app.screen, TeachCard) and app.screen.pages[0][0] == "Movement phase")
cards()
check("Teach: Movement offers Advance and Fall back; Undo has replaced Swap first", {"Advance", "Fall back", "Undo"} <= set(labels()) and "Swap first" not in labels() and screen_ok() == [], screen_ok())
tap("Advance")
check("Teach: the first Advance shows its card", cards() == ["Advancing"] and app.screen is play)
tap("Advance")
check("Teach: the second Advance is one line", app.screen is play and "Advance:" in app.toast, app.toast)
tap("Fall back"); check("Teach: the first Fall back shows its card", cards() == ["Falling back"])
app.gesture("press"); check("Teach: Shooting card", cards() == ["Shooting phase"] and screen_ok() == [], screen_ok())
tap("Cards")
check("Cards opens on the attack sequence while shooting", isinstance(app.screen, W40kRef) and app.screen.title == "Attack sequence" and screen_ok() == [], screen_ok())
app.gesture("press")
app.gesture("press"); check("Teach: Charge card, then a Charge button", cards() == ["Charge phase"] and "Charge" in labels() and screen_ok() == [], screen_ok())
tap("Charge"); check("Teach: the first charge shows its card", cards() == ["Your first charge"])
app.gesture("press"); check("Teach: Fight card; the main button now says End turn", cards() == ["Fight phase"] and labels()[-6] == "End turn" and screen_ok() == [], screen_ok())
app.gesture("press")
check("Teach: Trevor's turn begins with the end-of-turn card", cards() == ["The other turn"] and play.pill[0] == "Trevor's turn" and app.hw._ring.now == ("turn", {"colour": T.player_colour(1)}))
app.gesture("press"); app.gesture("double")
check("double press: takes back its own press and undoes one more", (app.session.state["phase"], app.session.active_name()) == ("fight", "Ethan"), (app.session.state["phase"], app.session.active_name()))
app.toast = None
app.gesture("press"); cards()
tap("Command points"); cp = app.screen
check("tapping the command points opens their screen, and it fits", isinstance(cp, W40kCommand) and screen_ok() == [], screen_ok())
app.tap((508, 200))
check("Teach: Trevor spends one: 1 left, and the stratagem card comes up", app.session.state["cp"] == [2, 1] and cards() == ["Stratagems"] and app.screen is cp)
tap("Done")
for _ in range(11): app.session.do(ev="model", side=0, unit=0, delta=-1)
for _ in range(5): app.gesture("press")
got = cards()
check("Teach: round 2 opens with the scoring card and the battle-shock card", got[0] == "Scoring begins" and "Battle-shock" in got and app.session.state["round"] == 2, got)
check("Teach: the play screen in round 2 fits, with the battle-shock line", screen_ok() == [] and w.tests(app.session.state, 0) == ["Necron Warriors"] and P40.prompt(app.session.state)[0] == "Ethan, score first.", screen_ok())
for _ in range(10):
    app.gesture("press"); look("teach round 2 %s" % app.session.state["phase"])
check("Teach: round 3 of 3 opens with the final-round card", cards() == ["The final round"] and app.session.state["round"] == 3)
for _ in range(10):
    app.gesture("press"); look("teach round 3 %s" % app.session.state["phase"])
check("Teach: the last Fight brings the last card, What to learn next", app.session.state["phase"] == "end" and cards() == ["What to learn next"])
check("Teach: after the last Fight, the final scores; nobody's turn; the button says Finish",
      app.screen is play and play.title == "Final scores" and play.pill is None and labels()[-6] == "Finish" and app.hw._ring.now[0] == "breathe" and screen_ok() == [], screen_ok())
tap("Score")
check("the score sheet is headed Final scores at the end", app.screen.title == "Final scores" and screen_ok() == [], screen_ok())
app.tap((748, 126)); app.tap((748, 126)); app.tap((358, 220))
check("score sheet taps: Trevor 2 primary, Ethan 1 on Secondary 1", w.score(app.session.state, 1) == (2, 0, 2) and w.score(app.session.state, 0) == (0, 1, 1))
app.gesture("press")
check("the button closes the score sheet", app.screen is play)
app.gesture("press")
over = app.screen
check("the button ends the game: Game over, Trevor wins 2 to 1", isinstance(over, common.GameOver) and over.session.finished["winner"] == "Trevor"
      and over.session.finished["lines"][0] == "2 victory points to 1" and screen_ok() == [], over.session.finished)
check("Teach: every screen on the way passed screen_ok", seen == [], seen)

# ---- Reminder and Silent: every screen, every phase
def tour(mode):
    """Open every 40k screen in this mode and walk a tutorial game to its end."""
    del seen[:]
    start(mode, "Tutorial, 3 rounds")
    tap("Start game")
    play, s = app.screen, app.session
    ok = isinstance(play, W40kPlay) and s.state["mode"] == mode.lower()
    look("play, first turn")
    ok &= "Advance" not in labels()
    # the army: Ethan's Necrons, three pages, then Trevor's empty list
    tap("Army"); army = app.screen; look("army 1")
    ok &= isinstance(army, W40kArmy) and army.side == 0 and army.pages() == 3
    app.tap((508, 100)); look("army after a tap")
    ok &= s.state["army"][0][0]["alive"] == 19
    app.tap((748, 100)); ok &= s.state["army"][0][0]["alive"] == 20
    tap("Steady"); look("army shocked"); ok &= s.state["army"][0][0]["shocked"] and "Shocked" in labels()
    tap("Shocked"); ok &= not s.state["army"][0][0]["shocked"]
    app.tap((508, 168)); look("army, one model hurt"); app.tap((508, 168)); look("army, one model destroyed")
    ok &= s.state["army"][0][1]["alive"] == 0 and len([l for l in labels() if l in ("Steady", "Shocked")]) == 3
    tap("More units"); look("army 2"); tap("More units"); look("army 3"); ok &= army.page == 2 and len(army.shown()) == 1
    tap("Trevor's army"); look("army, empty"); ok &= army.side == 1 and "Ethan's army" in labels()
    tap("Edit list"); edit = app.screen; look("edit, empty"); ok &= isinstance(edit, W40kArmyEdit) and edit.side == 1
    for _ in range(5): tap("Add unit")
    look("edit, five units, page 2"); ok &= len(s.state["army"][1]) == 5 and edit.page == 1
    tap("More units"); look("edit, page 1")
    app.tap((572, 100)); app.tap((498, 100)); app.tap((362, 168)); look("edit, sizes")
    ok &= [x["start"] for x in s.state["army"][1]] == [11, 4, 5, 5, 5]
    app.tap((700, 304)); look("edit, removed"); ok &= [x["name"] for x in s.state["army"][1]] == ["Unit 1", "Unit 2", "Unit 3", "Unit 5"]
    tap("Use Necrons"); look("edit, necrons"); ok &= len(s.state["army"][1]) == 9
    app.gesture("press"); app.gesture("double")               # the button closes the editor; its double undoes nothing
    ok &= app.screen is army and len(s.state["army"][1]) == 9
    s.undo(); army.refresh()                                  # undo: the list is back to four units
    ok &= len(s.state["army"][1]) == 4
    look("army, four units"); tap("Back"); ok &= app.screen is play
    # reference cards
    tap("Cards"); ref = app.screen; look("ref phases"); ok &= ref.title == "Phase order" and any(now for _, _, now in ref.rows())
    tap("Next card"); look("ref sequence"); ok &= ref.title == "Attack sequence"
    tap("Next card"); look("ref wound"); ok &= ref.title == "Wound roll" and [b for _, b, _ in ref.rows()] == ["2+", "3+", "4+", "5+", "6+"]
    tap("Previous card"); ok &= ref.title == "Attack sequence"; tap("Close"); ok &= app.screen is play
    # the shared menu and the score sheet
    tap("Menu"); look("more"); ok &= isinstance(app.screen, extras.GameMenu); tap("Back to the game")
    tap("Victory points"); sheet = app.screen; look("score, round 1"); ok &= isinstance(sheet, W40kScore) and sheet.title == "Score this turn"
    app.tap((358, 126)); ok &= "start in battle round 2" in (app.toast or "") and w.score(s.state, 0)[0] == 0
    app.toast = None; tap("Done")
    tap("Command points"); look("command points")
    for _ in range(12): app.tap((748, 116))
    look("command points, over 12"); ok &= s.state["cp"][0] == 13
    ok &= ("More than twelve" in (app.toast or "")) == (mode != "Silent")
    app.toast = None; tap("Done"); look("play, over 12")
    said_any = False
    for i in range(30):
        app.toast = None
        app.gesture("press")
        said_any |= bool(app.toast)
        if s.finished: break
        look("%s round %d %s" % (mode, s.state["round"], s.state["phase"]))
        ok &= app.screen is play                              # no cards outside Teach mode
        if i == 9:                                            # round 2, Ethan's Command phase: score
            tap("Score"); app.tap((358, 126)); app.tap((358, 126)); app.tap((748, 220)); look("score, round 2"); tap("Done")
            ok &= w.score(s.state, 0)[0] == 2 and w.score(s.state, 1)[1] == 1
    ok &= (s.state["phase"], s.finished) == ("end", None) and said_any == (mode != "Silent")
    look("final scores")
    app.gesture("press")
    ok &= isinstance(app.screen, common.GameOver) and app.screen.session.finished["winner"] == "Ethan"
    look("game over")
    return ok

check("Reminder: every 40k screen opens, works by taps, and a tutorial game runs to its end", tour("Reminder"))
check("Reminder: every screen passed screen_ok", seen == [], seen)
check("Silent: every 40k screen opens, works by taps, and a tutorial game runs to its end with nothing said", tour("Silent"))
check("Silent: every screen passed screen_ok", seen == [], seen)

# ---- a few screens on their own
sil = new(mode="Silent")
scr = w.play_screen(app, sil); app.push(scr)
check("Silent: the play screen draws no prompt, only the bar and two tall number panels",
      [tuple(x.rect) for x in scr.widgets[:2]] == [(20, 126, 760, 124), (20, 258, 760, 124)] and screen_ok() == [], screen_ok())
rem = new(mode="Reminder")
scr = w.play_screen(app, rem); app.push(scr)
check("Reminder: phase prompts in words", P40.prompt(rem.state)[0] == "Ethan takes the first turn." and [tuple(x.rect) for x in scr.widgets[:2]] == [(20, 310, 375, 74), (405, 310, 375, 74)])
rem.do(ev="next"); rem.do(ev="next")
check("the Shooting prompt names both players", P40.prompt(rem.state) == ("Ethan, pick a unit to shoot with.", "Roll to hit, then to wound. Trevor rolls the saves."))
ref = W40kRef(app, rem, 0)
check("the phase-order card marks the phase the game is in", [name for name, _, now in ref.rows() if now] == ["3  Shooting"])
check("reference cards can be read aloud as sentences", "Strength is higher: 3 or more." in W40kRef(app, rem, 2).words() and "!" not in W40kRef(app, rem, 1).words(), W40kRef(app, rem, 2).words())
texts = " ".join(P40.SEQUENCE[i][1] for i in range(4)) + " ".join(P40.PHASE_LINES) + " ".join(c[2] for c in P40.DID.values())
check("her lines carry no exclamation marks", "!" not in texts)

# ---------------------------------------------------------------- named secondaries: the sums
N, SC, AW = rules.sec_name, rules.sec_score, rules.sec_away
def view(rows): return sorted((r["name"], r["pts"], r["slot"]) for r in rows)
r0 = rules.new_secs()
check("secondaries: a player starts with two unnamed rows at nothing", view(r0) == [("Secondary 1", 0, 0), ("Secondary 2", 0, 1)] and not rules.sec_named(r0[0]) and rules.sec_words(r0) == "")
r1 = N(r0, 0, "assassination")
check("naming a row: the name is tidied and the other row is left alone", view(r1) == [("Assassination", 0, 0), ("Secondary 2", 0, 1)] and rules.sec_named(rules.sec_at(r1, 0)) and view(r0)[0][0] == "Secondary 1")
check("a typed name keeps its apostrophe and gains capitals", rules.sec_clean("  secure no man's   land ") == "Secure No Man's Land" and len(rules.sec_clean("x" * 60)) == rules.MAX_SEC_NAME)
r2 = SC(SC(r1, 0, 3), 1, 2)
check("scoring goes to the row in that slot: Assassination 3, the unnamed one 2", view(r2) == [("Assassination", 3, 0), ("Secondary 2", 2, 1)] and rules.sec_points(r2) == 5)
check("in words: named rows, and unnamed ones only if they have points", rules.sec_words(r2) == "Assassination 3, Secondary 2 2" and rules.sec_words(r1) == "Assassination 0")
r3 = N(r2, 1, "Cleanse")
check("naming an unnamed row that has points keeps the points with it", view(r3) == [("Assassination", 3, 0), ("Cleanse", 2, 1)])
r4 = N(r3, 0, "Sabotage")
check("a new name on a row that has scored: the old one is put away with its points, the new one starts at 0",
      view(r4) == [("Assassination", 3, None), ("Cleanse", 2, 1), ("Sabotage", 0, 0)] and rules.sec_points(r4) == 5, view(r4))
check("in words: the ones in hand, then the earlier ones", rules.sec_words(r4) == "Sabotage 0, Cleanse 2; earlier: Assassination 3")
r5 = N(r4, 0, "Area Denial")
check("a new name on a named row with no points simply replaces it", view(r5) == [("Area Denial", 0, 0), ("Assassination", 3, None), ("Cleanse", 2, 1)])
r6 = N(SC(r5, 0, 1), 0, "ASSASSINATION")
check("a name put away earlier comes back with the points it had", view(r6) == [("Area Denial", 1, None), ("Assassination", 3, 0), ("Cleanse", 2, 1)], view(r6))
check("refused: no name, the same name again, a name in the other row, and the plain row names",
      bad(lambda: N(r3, 0, "   ")) and bad(lambda: N(r3, 0, "assassination")) and bad(lambda: N(r3, 0, "Cleanse")) and bad(lambda: N(r3, 0, "secondary 2")) and bad(lambda: N(r3, 2, "X")))
check("refused: a cap that is not a whole number of points", bad(lambda: N(r0, 0, "X", cap=0)) and bad(lambda: N(r0, 0, "X", cap="5")) and N(r0, 0, "X", cap=5)[0]["cap"] == 5)
capped = SC(N(r0, 0, "Cleanse", cap=5), 0, 5)
check("a named secondary's own cap: 5 go in, the 6th is refused, and taking one away is fine", bad(lambda: SC(capped, 0, 1)) and SC(capped, 0, -1)[0]["pts"] == 4)
check("a row cannot go below nothing", bad(lambda: SC(r0, 0, -1)))
big = SC(N(SC(N(r0, 0, "A"), 0, 30), 0, "B"), 0, 8)
check("the game cap counts the ones put away too: 30 + 8, 2 more makes 40, 3 more is refused", rules.sec_points(SC(big, 1, 2)) == 40 and bad(lambda: SC(big, 1, 3)) and bad(lambda: SC(big, 0, 3)))
check("the table's own per-row cap still holds for a row with no cap of its own",
      bad(lambda: SC(SC(r0, 0, 5, table=dict(t, secondary_rows=[{"name": "Secondary 1", "max": 5}, {"name": "Secondary 2", "max": None}])), 0, 1,
                     table=dict(t, secondary_rows=[{"name": "Secondary 1", "max": 5}, {"name": "Secondary 2", "max": None}]))))
check("putting away: with points it stays on the record, with none it is forgotten; the slot is unnamed again",
      view(AW(r3, 0)) == [("Assassination", 3, None), ("Cleanse", 2, 1), ("Secondary 1", 0, 0)] and view(AW(r1, 0)) == view(r0) and bad(lambda: AW(r0, 0)))
many = r0
for k in range(rules.MAX_SEC_ROWS - 2):
    many = SC(N(many, 0, "Name %d" % k), 0, 1)
check("%d names for one player is the limit" % rules.MAX_SEC_ROWS, len(N(many, 0, "One More")) == rules.MAX_SEC_ROWS and bad(lambda: N(SC(N(many, 0, "One More"), 0, 1), 0, "Too Many")))
check("a game saved before names: two bare numbers read as two unnamed rows", view(rules.new_secs(points=[3, 1])) == [("Secondary 1", 3, 0), ("Secondary 2", 1, 1)])

# ---- the list of names in secondaries.json
raw = json.load(open(os.path.join(w.folder, "secondaries.json"), encoding="utf-8"))
table = P40.secondary_table()
check("secondaries.json says plainly that its names are from memory and unchecked", "NAMES FROM MEMORY" in raw["README"][0] and "your deck wins" in raw["README"][0] and "no card text" in " ".join(raw["README"]))
check("the list: at least ten names, none twice, none too long for a row", len(table) >= 10 and len({e["name"].lower() for e in table}) == len(table) == len(raw["secondaries"])
      and all(1 <= len(e["name"]) <= rules.MAX_SEC_NAME for e in table), [e["name"] for e in table if len(e["name"]) > rules.MAX_SEC_NAME])
check("every entry has a short label of its own and a cap that is a number or nothing; no cap is guessed",
      all(e["scores"] and len(e["scores"]) <= 34 and e["scores"].startswith("for ") for e in table) and all(e["cap"] is None for e in table), [e for e in table if len(e["scores"]) > 34])
check("every label fits under its name on the picker", all(T.font("text", 22).size(e["scores"])[0] <= 375 - 28 for e in table), [e["scores"] for e in table if T.font("text", 22).size(e["scores"])[0] > 347])
here, tmp_here = P40.HERE, tempfile.mkdtemp()
P40.HERE = tmp_here
check("no list file: the table is empty, nothing breaks", P40.secondary_table() == [])
open(os.path.join(tmp_here, "secondaries.json"), "w").write("{ this is not json")
check("a broken list file: the table is empty, nothing breaks", P40.secondary_table() == [])
json.dump({"secondaries": [{"name": "my own one", "cap": 4, "scores": "for  things"}, {"name": "My Own One"}, {"cap": 3}, "junk", {"name": "Other", "cap": "lots"}]},
          open(os.path.join(tmp_here, "secondaries.json"), "w"))
check("an edited list: names tidied, repeats and junk dropped, a bad cap read as none",
      P40.secondary_table() == [{"name": "My Own One", "cap": 4, "scores": "for things"}, {"name": "Other", "cap": None, "scores": ""}], P40.secondary_table())
P40.HERE = here
shutil.rmtree(tmp_here)

# ---- named secondaries in a game
ns = new(save=folder)
check("a new game: two unnamed secondary rows a side, and no old-style numbers", view(ns.state["secs"][0]) == view(r0) and "sec" not in ns.state)
n = len(ns.log)
check("naming is an event: logged, nothing said", ns.do(ev="sec", side=0, op="name", slot=0, name="Assassination", cap=None) == [] and len(ns.log) == n + 1)
ns.do(ev="sec", side=1, op="name", slot=1, name="no prisoners", cap=5)
for _ in range(3): ns.do(ev="score", side=0, cat="sec", row=0, delta=1)
for _ in range(5): ns.do(ev="score", side=1, cat="sec", row=1, delta=1)
said = ns.do(ev="score", side=1, cat="sec", row=1, delta=1)
check("scores are kept per named secondary, per player, and a cap is enforced by name", w.score(ns.state, 0) == (0, 3, 3) and w.score(ns.state, 1) == (0, 5, 5) and said == ["No Prisoners stops at 5."], said)
check("a refused name changes nothing and is not logged", "already" in ns.do(ev="sec", side=0, op="name", slot=0, name="Assassination")[0] and len(ns.log) == n + 10
      and "named or put away" in ns.do(ev="sec", side=0, op="rename", slot=0)[0])
ns.do(ev="sec", side=0, op="name", slot=0, name="Cleanse")
check("changing a scored secondary keeps its points in the total", view(ns.state["secs"][0]) == [("Assassination", 3, None), ("Cleanse", 0, 0), ("Secondary 2", 0, 1)] and w.score(ns.state, 0)[1] == 3)
check("undo takes the change of name back", ns.undo() and view(ns.state["secs"][0]) == [("Assassination", 3, 0), ("Secondary 2", 0, 1)])
check("undo takes a point back from the named row", ns.undo() and w.score(ns.state, 1)[1] == 4 and ns.do(ev="score", side=1, cat="sec", row=1, delta=1) == [])
ns.do(ev="sec", side=0, op="name", slot=0, name="Cleanse"); ns.do(ev="score", side=0, cat="sec", row=0, delta=2)
sb = w.scoreboard(ns)
check("scoreboard: each player's secondaries by name, and a line for the shared page",
      sb["rows"][0]["sub"] == "Cleanse 2; earlier: Assassination 3" and sb["rows"][0]["secondary"] == 5 and sb["rows"][1]["sub"] == "No Prisoners 5"
      and sb["rows"][0]["secondaries"] == [{"name": "Assassination", "points": 3, "now": False}, {"name": "Cleanse", "points": 2, "now": True}] and json.dumps(sb), sb["rows"])
mine = w.phone(ns, 0)
check("phone: the player's secondaries by name, and the buttons carry the names", "Secondaries: Cleanse 2; earlier: Assassination 3" in mine["lines"]
      and {"Cleanse +1", "Cleanse -1", "Secondary 2 +1", "Secondary 2 -1"} <= {x["label"] for x in mine["actions"]} and "No Prisoners +1" in [x["label"] for x in w.phone(ns, 1)["actions"]], mine)
ns.do(**next(x["ev"] for x in mine["actions"] if x["label"] == "Cleanse +1"))
check("phone: a named +1 scores that secondary", view(ns.state["secs"][0])[1] == ("Cleanse", 3, 0))
back = engine.Session.load(ns.path, plugins, clock)
check("save and load: the named secondaries come back exactly", back.state == ns.state and w.score(back.state, 0) == (0, 6, 6) and view(back.state["secs"][1]) == [("No Prisoners", 5, 1), ("Secondary 1", 0, 0)])
check("save and load: undo still works on the loaded game", back.undo() and view(back.state["secs"][0])[1] == ("Cleanse", 2, 0))

# an old saved game: secondary points as bare numbers, no names, no nudge setting
old = new(save=folder); nexts(old, 10)
d = json.load(open(old.path, encoding="utf-8"))
for st in [d["state"]] + d["undo"]:
    del st["secs"]; st["sec"] = [[3, 1], [0, 2]]
old_path = os.path.join(folder, "old-wh40k.json")
json.dump(d, open(old_path, "w", encoding="utf-8"))
og = engine.Session.load(old_path, plugins, clock)
check("an old save loads: its secondary points are there under plain names", og is not None and "secs" not in og.state and w.score(og.state, 0) == (0, 4, 4) and w.score(og.state, 1) == (0, 2, 2))
check("an old save: scoreboard and phone read it without changing it", w.scoreboard(og)["rows"][0]["sub"] == "Secondary 1 3, Secondary 2 1" and "Secondary 1 +1" in [x["label"] for x in w.phone(og, 0)["actions"]]
      and "secs" not in og.state and P40.nudge_secs(og) == 240)
check("an old save: the next event brings it up to date", og.do(ev="score", side=0, cat="sec", row=1, delta=1) == [] and "sec" not in og.state and view(og.state["secs"][0]) == [("Secondary 1", 3, 0), ("Secondary 2", 2, 1)])
check("an old save: a row can then be named, keeping its points", og.do(ev="sec", side=0, op="name", slot=0, name="Sabotage") == [] and view(og.state["secs"][0])[0] == ("Sabotage", 3, 0))
og.undo(); og.undo()
check("an old save: undo goes back to the old shape and it still reads", og.state["sec"] == [[3, 1], [0, 2]] and w.score(og.state, 0) == (0, 4, 4))
check("an old save: a refused event leaves the old shape alone", "start in battle round" not in og.do(ev="cp", side=0, delta=-99)[0] and og.state["sec"] == [[3, 1], [0, 2]] and "secs" not in og.state)

# ---------------------------------------------------------------- the slow-play clock: the sums
pc = rules.Pace()
check("pace: nothing before the limit, once at the limit, never again for that phase",
      [pc.due("a", t0, 240) for t0 in (1000, 1100, 1239.9, 1240, 1241, 5000)] == [False, False, False, True, False, False])
check("pace: a new phase starts the clock again", [pc.due("b", t0, 240) for t0 in (5001, 5240.9, 5241, 5300)] == [False, False, True, False])
check("pace: back to a phase that has had its line (undo): nothing more, however long", [pc.due("a", t0, 240) for t0 in (5301, 9999)] == [False, False])
check("pace: forward again to the other one: nothing more either", pc.due("b", 20000, 240) is False)
check("pace: off means off, and nothing to time means nothing", rules.Pace().due("a", 0, 0) is False and [rules.Pace().due("a", t0, 0) for t0 in (0, 99999)] == [False, False]
      and [pc.due(None, t0, 240) for t0 in (30000, 99999)] == [False, False])
pc2 = rules.Pace(); pc2.due("a", 0, 240); pc2.restart()
check("pace: restart begins the count from the next look", [pc2.due("a", t0, 240) for t0 in (500, 739, 740)] == [False, False, True])
check("the choices: 4 minutes by default, 8 minutes, or off", [(l, v) for l, v, _ in rules.NUDGES] == [("4 min", 240), ("8 min", 480), ("Off", 0)])
from deepthought import persona
check("her nudge lines: four, in her voice, no exclamation marks, nothing about the player", len(P40.NUDGE_LINES) == 4 and all(persona.in_voice(l % "Four minutes" if "%s" in l else l) for l in P40.NUDGE_LINES)
      and not any(x in " ".join(P40.NUDGE_LINES).lower() for x in ("you are", "slow", "hurry up", "your fault")))
check("the clock times one phase of one turn, and nothing at the final scores", w.pace_key(new().state) == (1, 0, "command") and w.pace_key((lambda g: (nexts(g, 50), g.state)[1])(new(mode="Silent"))) is None)

# ---------------------------------------------------------------- the slow-play clock: on the play screen
def play_on(s):
    app.go_home(); app.toast = None
    app.session = s
    scr = w.play_screen(app, s); app.push(scr)
    return scr
turn_ring = lambda i: ("turn", {"colour": T.player_colour(i)})
tk = new(save=folder)
scr = play_on(tk)
check("a play screen has a tick for the app to call", callable(getattr(scr, "tick", None)) and P40.nudge_secs(tk) == 240)
fired = [scr.tick(t0) for t0 in (100.0, 200.0, 339.9)]
check("under four minutes in a phase: silence, and the ring stays the turn colour", fired == [False, False, False] and app.toast is None and app.hw._ring.now == turn_ring(0), (fired, app.toast))
check("at four minutes: one line from her and the amber warning on the ring", scr.tick(340.0) is True and app.toast in [l % "Four minutes" if "%s" in l else l for l in P40.NUDGE_LINES] and app.hw._ring.now[0] == "warn", app.toast)
first_line = app.toast
check("the warning is still blinking a moment later", scr.tick(342.0) is False and app.hw._ring.now[0] == "warn")
check("then the ring goes back to the turn colour", scr.tick(340.0 + P40.WARN_SECS) is False and app.hw._ring.now == turn_ring(0))
app.toast = None
check("nothing further in that phase, however long it runs", [scr.tick(t0) for t0 in (400.0, 580.0, 4000.0)] == [False] * 3 and app.toast is None and app.hw._ring.now == turn_ring(0))
scr.do(ev="next"); app.toast = None
check("the next phase starts its own clock: quiet for four more minutes", [scr.tick(t0) for t0 in (4001.0, 4240.0)] == [False, False] and app.toast is None)
check("and then one line, a different one", scr.tick(4241.0) is True and app.toast and app.toast != first_line, app.toast)
scr.tick(4250.0); app.toast = None
scr.do(ev="next"); scr.tick(4251.0)
tk.undo(); scr.refresh()
check("undo back into a phase that has had its line: no second line", tk.state["phase"] == "movement" and [scr.tick(t0) for t0 in (4252.0, 4600.0, 9000.0)] == [False] * 3 and app.toast is None)
scr.tick(9001.0); app.gesture("press"); scr.tick(9002.0); app.gesture("double"); app.toast = None
check("the button's double press (undo) does not fire it again either", tk.state["phase"] == "command" and [scr.tick(t0) for t0 in (9003.0, 9999.0)] == [False, False] and app.toast is None, tk.state["phase"])
# a game left for hours and resumed
app.go_home()
app.resume_game(tk.path)
res = app.screen
check("resume makes a new play screen with a new clock", isinstance(res, W40kPlay) and res is not scr and app.session.state == tk.state)
check("a game resumed after hours does not fire at once", res.tick(500000.0) is False and res.tick(500239.0) is False and app.toast is None and app.hw._ring.now == turn_ring(0))
check("it fires four minutes after the resume", res.tick(500240.0) is True and app.toast is not None)
app.toast = None
# the setting, from the game's menu
tap("Menu"); menu = app.screen
check("More opens the game menu with the nudge setting added, and it fits", isinstance(menu, extras.GameMenu) and labels()[-4:] == ["Back to the game", "Lookup", "Dice", "Nudge: 4 min"] and screen_ok() == [], (labels(), screen_ok()))
check("the menu's labels fit their buttons", all(T.font("bold", 22).size(x.label)[0] <= x.rect.w - 24 for x in menu.widgets if x.rect.y >= common.BOTTOM_Y), [(x.label, x.rect.w) for x in menu.widgets if x.rect.y >= common.BOTTOM_Y])
tap("Nudge")
check("a tap: 8 minutes, she says so, and it is saved with the game", labels()[-1] == "Nudge: 8 min" and "Eight minutes a phase" in app.toast and json.load(open(tk.path, encoding="utf-8"))["options"]["nudge"] == 480 and screen_ok() == [], app.toast)
tap("Back to the game"); res.do(ev="next"); app.toast = None
res.tick(600000.0)
tap("Menu"); tap("Nudge"); tap("Nudge"); tap("Nudge"); tap("Back to the game"); app.toast = None
check("changing the limit starts the count again from then, not from the start of the phase", P40.nudge_secs(app.session) == 480
      and [res.tick(t0) for t0 in (600400.0, 600879.0)] == [False, False] and res.tick(600880.0) is True)
app.toast = None
again = engine.Session.load(tk.path, plugins, clock)
check("a resumed game keeps its limit", P40.nudge_secs(again) == 480)
tap("Menu"); tap("Nudge")
check("another tap: off", labels()[-1] == "Nudge: Off" and P40.nudge_secs(app.session) == 0 and "keep the time to myself" in app.toast and screen_ok() == [])
tap("Back to the game"); res.do(ev="next"); app.toast = None
check("off means off: a whole day in one phase and not a word", [res.tick(t0) for t0 in (700000.0, 700240.0, 786400.0)] == [False] * 3 and app.toast is None and app.hw._ring.now[0] == "turn")
tap("Menu"); tap("Nudge"); tap("Back to the game")
check("a third tap comes round to 4 minutes again", P40.nudge_secs(app.session) == 240)
app.session.d["options"]["nudge"] = "soon"
check("a setting that makes no sense reads as the default", P40.nudge_secs(app.session) == 240)
# modes
sl = new(mode="Silent"); scr = play_on(sl)
scr.tick(0.0)
check("Silent mode: the ring warns, she says nothing", scr.tick(240.0) is True and app.toast is None and app.hw._ring.now[0] == "warn")
tc = new(mode="Teach"); scr = play_on(tc)
while isinstance(app.screen, TeachCard): app.pop()
app.toast = None
check("Teach mode: off unless a player turns it on", P40.nudge_secs(tc) == 0 and [scr.tick(t0) for t0 in (0.0, 5000.0)] == [False, False] and app.toast is None)
tap("Menu")
check("Teach mode: the menu shows it off; one tap turns it on", labels()[-1] == "Nudge: Off" and screen_ok() == [])
tap("Nudge"); check("Teach mode: turned on, it is 4 minutes", labels()[-1] == "Nudge: 4 min" and P40.nudge_secs(tc) == 240)
tap("Back to the game")
fin = new(length="Tutorial, 3 rounds"); nexts(fin, 30); scr = play_on(fin)
check("at the final scores there is no phase to time", [scr.tick(t0) for t0 in (0.0, 9999.0)] == [False, False] and app.toast is None)
app.toast = None

# ---------------------------------------------------------------- named secondaries: the screens
from deepthought.games.wh40k.plugin import W40kSecPick
sg = new(save=folder); nexts(sg, 10)
scr = play_on(sg); app.toast = None
tap("Score"); sheet = app.screen
check("the score sheet: three rows a side, each a minus, a box and a plus; it fits", isinstance(sheet, W40kScore) and len(sheet.widgets) == 19 and screen_ok() == []
      and [x.label for x in sheet.widgets if x.action and x.label not in ("−", "+")] == ["Ethan Secondary 1", "Ethan Secondary 2", "Trevor Secondary 1", "Trevor Secondary 2", "Done"], screen_ok())
tap("Ethan Secondary 1"); pick = app.screen
check("tapping a secondary's box opens the picker for that player and row, and it fits", isinstance(pick, W40kSecPick) and (pick.side, pick.slot) == (0, 0) and pick.left == "40k · Ethan" and screen_ok() == [], screen_ok())
check("the picker: eight names a page, Type a name, More names, Back; nothing to put away yet", labels()[:8] == [e["name"] for e in table[:8]] and labels()[8:] == ["Type a name", "More names", "Back"], labels())
pages_ok = []
for _ in range(pick.pages()):
    pages_ok += screen_ok(); tap("More names")
check("every page of names fits, and More names comes round again", pages_ok == [] and pick.page == 0 and pick.pages() == -(-len(table) // 8), pages_ok)
tap(table[1]["name"])
check("a tap on a name names the row and goes back to the sheet", app.screen is sheet and view(sg.state["secs"][0])[0] == (table[1]["name"], 0, 0) and screen_ok() == [], view(sg.state["secs"][0]))
app.tap((358, 220)); app.tap((358, 220)); app.tap((748, 126))
check("the plus beside it scores it: Ethan 2 on that secondary, Trevor 1 primary", rules.sec_at(sg.state["secs"][0], 0)["pts"] == 2 and w.score(sg.state, 1) == (1, 0, 1))
app.tap((200, 314))
check("the second row's box opens the picker for the second row", isinstance(app.screen, W40kSecPick) and app.screen.slot == 1 and app.screen.side == 0)
tap("Type a name"); entry = app.screen
check("Type a name opens the keyboard, and it fits", isinstance(entry, common.TextEntry) and entry.title == "Secondary name" and screen_ok(entry) == [], screen_ok(entry))
for ch in "hold the bridge": entry.type(ch)
entry.done()
check("a typed name names the row and goes back to the sheet", app.screen is sheet and rules.sec_at(sg.state["secs"][0], 1)["name"] == "Hold The Bridge" and rules.sec_at(sg.state["secs"][0], 1)["cap"] is None and screen_ok() == [], app.screen)
tap("Ethan Secondary 2"); tap("Type a name"); app.screen.done()
check("typing nothing changes nothing", isinstance(app.screen, W40kSecPick) and rules.sec_at(sg.state["secs"][0], 1)["name"] == "Hold The Bridge")
tap(table[1]["name"])
check("a name already in the other row is refused, with the reason, and the picker stays", isinstance(app.screen, W40kSecPick) and "already in the other row" in (app.toast or ""), app.toast)
app.toast = None
check("a named row can be put away from the picker", "Put away" in labels() and screen_ok() == [])
tap("Put away")
check("Put away with no points: forgotten, the row is unnamed again", app.screen is sheet and view(sg.state["secs"][0]) == [(table[1]["name"], 2, 0), ("Secondary 2", 0, 1)])
tap("Ethan Secondary 1")
check("the picker marks the name in use and says what a change does", [x.label for x in app.screen.widgets if getattr(x, "selected", False)] == [table[1]["name"]] and screen_ok() == [])
tap(table[2]["name"])
check("changing a scored secondary: the old one stays in the total", app.screen is sheet and view(sg.state["secs"][0]) == sorted([(table[1]["name"], 2, None), (table[2]["name"], 0, 0), ("Secondary 2", 0, 1)]) and w.score(sg.state, 0)[1] == 2 and screen_ok() == [])
app.gesture("press")
check("the button closes the sheet; the play screen names the secondaries in hand", app.screen is scr and rules.sec_words(sg.state["secs"][0]).startswith(table[2]["name"] + " 0") and screen_ok() == [])
app.gesture("double")
check("the double of the press that closed the sheet undoes nothing behind the player's back", app.screen is scr and rules.sec_at(sg.state["secs"][0], 0)["name"] == table[2]["name"], view(sg.state["secs"][0]))
tap("Undo")
check("Undo on the play screen takes the change of name back", rules.sec_at(sg.state["secs"][0], 0)["name"] == table[1]["name"] and rules.sec_at(sg.state["secs"][0], 0)["pts"] == 2, view(sg.state["secs"][0]))
tap("Score"); tap("Trevor Secondary 2"); app.gesture("press")
check("the button closes the picker without choosing", isinstance(app.screen, W40kScore) and view(sg.state["secs"][1]) == view(r0))
P40.HERE = tempfile.mkdtemp()
tap("Trevor Secondary 2")
check("with no list file the picker still opens, offers typing, and fits", isinstance(app.screen, W40kSecPick) and labels() == ["Type a name", "Back"] and screen_ok() == [], labels())
P40.HERE = here
tap("Back"); tap("Done")
# long names and a capped one, drawn
for side, slot, name, cap in ((0, 1, "Deploy Teleport Homers", 5), (1, 0, "Storm Hostile Objective", None), (1, 1, "Secure No Man's Land", 8)):
    sg.do(ev="sec", side=side, op="name", slot=slot, name=name, cap=cap)
tap("Score")
check("the sheet with long names and caps still fits", screen_ok() == [])
tap("Done")
json.dump(d, open(old_path, "w", encoding="utf-8"))
og2 = engine.Session.load(old_path, plugins, clock); scr = play_on(og2); tap("Score")
check("an old save: the score sheet opens and a tap scores", screen_ok() == [] and (app.tap((358, 220)) is not None) and w.score(og2.state, 0)[1] == 5)
tap("Done"); app.toast = None

# ---------------------------------------------------------------- the double press, as the button sends it
def double():
    app.toast = None
    app.gesture("press"); app.gesture("double")
def at(s): return (s.state["round"], s.state["active"], s.state["phase"], len(s.log))
td = new(mode="Teach", length="Tutorial, 3 rounds", save=folder)
scr = play_on(td); cards()
td.do(ev="cp", side=0, delta=1); scr.refresh()
app.gesture("press")
check("Teach: a press that moves to a new phase brings its card", isinstance(app.screen, TeachCard) and at(td) == (1, 0, "movement", 2))
app.gesture("double")
check("Teach: the double of that press puts the card away, takes the press back and undoes one more",
      app.screen is scr and at(td) == (1, 0, "command", 0) and td.state["cp"] == [1, 1] and "movement" not in td.state["taught"], (at(td), td.state["cp"]))
nexts(td, 9)
for _ in range(11): td.do(ev="model", side=0, unit=0, delta=-1)
scr.refresh(); n_log = len(td.log)
tap("End turn")
check("Teach: a tap into round 2 brings more than one card", isinstance(app.screen, TeachCard) and len(app.screen.pages) >= 2 and td.state["round"] == 2 and len(td.log) == n_log + 1, len(td.log))
double()
check("double press while reading them: the cards go and the tap that brought them is undone, nothing before it",
      app.screen is scr and len(td.log) == n_log and td.state["round"] == 1 and td.state["phase"] == "fight" and "round2" not in td.state["taught"], at(td))
tap("End turn"); cards(); n_log = len(td.log); double()
check("on the play screen: double press takes back its own press and one more", app.screen is scr and len(td.log) == n_log - 1, (len(td.log), n_log))
app.go_home(); app.toast = None

rd = new(save=folder); scr = play_on(rd)
tap("Next phase"); tap("Next phase"); tap("Score"); sheet = app.screen
sheet.do(ev="score", side=0, cat="sec", row=0, delta=1)
before = at(rd); double()
check("double press on the score sheet after earlier taps: the sheet closes and nothing is undone",
      app.screen is scr and at(rd) == before and rd.state["secs"][0][0]["pts"] == 1, (at(rd), before))
for label in ("Menu", "Army", "Cards", "Command points"):
    tap(label); top = app.screen; double()
    check("double press on %s: it closes and nothing is undone" % type(top).__name__, app.screen is scr and at(rd) == before, (type(app.screen).__name__, at(rd)))
tap("Score"); tap("Ethan Secondary 2"); double(); double()
check("double press on the picker, then on the sheet under it: both close, nothing is undone", app.screen is scr and at(rd) == before)
tap("Army"); tap("Edit list"); tap("Add unit"); before = at(rd); double()
check("double press on Edit list: back to the army, the new unit stays", isinstance(app.screen, W40kArmy) and at(rd) == before and len(rd.state["army"][0]) == 10)
app.go_home(); app.toast = None

# ---------------------------------------------------------------- the slow-play clock stands still under another screen
def frame(t):
    """What the app's loop does with the screens each frame."""
    return [x.tick(t) for x in list(app.stack) if getattr(x, "tick", None)]
cv = new(save=folder); scr = play_on(cv); frame(0.0); frame(100.0)
tap("Menu"); tap("Rules")
check("under the menu and the rules: four minutes pass, she says nothing and the ring does not warn",
      isinstance(app.screen, common.Pages) and frame(101.0) == [False] and frame(900.0) == [False] and app.toast is None and app.hw._ring.now[0] != "warn", (app.toast, app.hw._ring.now))
tap("Back"); tap("Back to the game")
check("back on the play screen the count carries on: 100 seconds used, 140 to go",
      app.screen is scr and frame(901.0) == [False] and frame(1039.0) == [False] and frame(1041.5) == [True] and app.toast is not None, app.toast)
app.toast = None; tap("Menu"); tap("Who first")
ring_then = app.hw._ring.now[0]
frame(1041.5 + P40.WARN_SECS + 1)
check("the spinner's ring is left alone when the warning runs out underneath it", ring_then == "spin" and app.hw._ring.now[0] == "spin", (ring_then, app.hw._ring.now))
app.go_home(); app.toast = None
cv = new(save=folder); scr = play_on(cv); frame(0.0); frame(240.0)
tap("Menu"); frame(241.0)
check("a warning that began before the menu was opened still ends: the ring goes back to the turn colour",
      app.hw._ring.now[0] == "warn" and frame(241.0 + P40.WARN_SECS) == [False] and app.hw._ring.now == turn_ring(0), app.hw._ring.now)
app.go_home(); app.toast = None

# ---------------------------------------------------------------- a cap is not slipped past by naming a row late
cap_rows = SC(rules.new_secs(), 0, 8)
check("naming a row that already holds more than the name's cap is refused, and says why",
      bad(lambda: N(cap_rows, 0, "Assassination", 5)) and view(N(cap_rows, 0, "Assassination", 8))[0] == ("Assassination", 8, 0) and view(N(cap_rows, 0, "Assassination"))[0] == ("Assassination", 8, 0))
real_table = P40.secondary_table
P40.secondary_table = lambda: [{"name": "Assassination", "cap": 5, "scores": "for destroying characters"}]
cg = new(save=folder); scr = play_on(cg); tap("Score")
for _ in range(8): app.tap((358, 220))
tap("Ethan Secondary 1"); tap("Assassination")
check("on the screen: 8 points on an unnamed row, then a name capped at 5: refused, the picker stays, the row is as it was",
      isinstance(app.screen, W40kSecPick) and "stops at 5" in (app.toast or "") and view(cg.state["secs"][0])[0] == ("Secondary 1", 8, 0), (app.toast, view(cg.state["secs"][0])))
P40.secondary_table = real_table
app.go_home(); app.toast = None

# ---------------------------------------------------------------- a teach card that was up when the power went
pw = new(mode="Teach", necrons="Nobody", save=folder); scr = play_on(pw); cards()
app.gesture("press")
check("the Movement card is up, and the saved game knows it is owed", isinstance(app.screen, TeachCard) and pw.state["pending"] == ["movement"]
      and json.load(open(pw.path, encoding="utf-8"))["state"]["pending"] == ["movement"])
app.resume_game(pw.path)
check("resumed with that card unread: it is shown again", isinstance(app.screen, TeachCard) and app.screen.pages[0][0] == "Movement phase", type(app.screen).__name__)
cards()
check("read to the end, it is not owed any more", isinstance(app.screen, W40kPlay) and json.load(open(app.session.path, encoding="utf-8")).get("cards_seen") == 1)
app.resume_game(app.session.path)
check("resumed again: straight to the play screen, no card", isinstance(app.screen, W40kPlay))
app.gesture("press"); cards(); app.gesture("press"); cards(); app.gesture("press"); app.gesture("double")
check("a card taken back by a double press is not owed on resume either", app.session.state["phase"] == "shooting" and (app.resume_game(app.session.path), isinstance(app.screen, W40kPlay))[1], app.session.state["phase"])
app.go_home(); app.toast = None

# ---------------------------------------------------------------- the strip: no turn pill where both players act
ps = new(save=folder); scr = play_on(ps)
tap("Score"); a_pill = app.screen.pill; tap("Done"); tap("Command points"); b_pill = app.screen.pill; tap("Done")
check("the score sheet and the command points screen carry no turn pill; the play screen does", a_pill is None and b_pill is None and scr.pill[0] == "Ethan's turn")
app.go_home(); app.toast = None

# ---------------------------------------------------------------- naming a secondary from the player's own phone
def acts_of(s, seat): return {a["label"]: a for a in w.phone(s, seat)["actions"]}
pn = new(save=folder); nexts(pn, 10)
a0 = acts_of(pn, 0)
check("phone: each unnamed row offers Name it, asking for a name and listing the ones in secondaries.json",
      a0["Name Secondary 1"]["ev"] == {"ev": "sec", "side": 0, "op": "name", "slot": 0} and a0["Name Secondary 2"]["ev"]["slot"] == 1
      and a0["Name Secondary 1"]["choices"] == [e["name"] for e in P40.secondary_table()] and a0["Name Secondary 1"]["ask"] and a0["Name Secondary 1"]["max"] == rules.MAX_SEC_NAME
      and not any(x.startswith("Put away") for x in a0), list(a0))
check("phone: a picked name names that player's own row", pn.do(text="Assassination", **a0["Name Secondary 1"]["ev"]) == [] and view(pn.state["secs"][0]) == [("Assassination", 0, 0), ("Secondary 2", 0, 1)]
      and view(pn.state["secs"][1]) == view(r0))
a0 = acts_of(pn, 0)
check("phone: a named row then offers Change and Put away, by name", "Change Assassination" in a0 and "Put away Assassination" in a0 and "Name Secondary 2" in a0 and "Name Secondary 1" not in a0, list(a0))
check("phone: the same name in the other row is refused, as on the box", "already in the other row" in pn.do(text="assassination", **a0["Name Secondary 2"]["ev"])[0] and view(pn.state["secs"][0])[1] == ("Secondary 2", 0, 1))
check("phone: no name, and my own word for an unnamed row, are refused", "needs a name" in pn.do(text="  ", **a0["Name Secondary 2"]["ev"])[0] and "needs a name" in pn.do(**a0["Name Secondary 2"]["ev"])[0]
      and "no name" in pn.do(text="secondary 2", **a0["Name Secondary 2"]["ev"])[0])
check("phone: a name typed that is not on the list is taken, tidied, with no cap", pn.do(text="hold  the bridge", **a0["Name Secondary 2"]["ev"]) == []
      and rules.sec_at(pn.state["secs"][0], 1)["name"] == "Hold The Bridge" and rules.sec_at(pn.state["secs"][0], 1)["cap"] is None)
check("phone: every naming action is for that seat's own side, so the other seat cannot name these rows",
      all(a["ev"].get("side", 1) == 1 for a in w.phone(pn, 1)["actions"]) and set(acts_of(pn, 1)) & {"Change Assassination", "Put away Assassination"} == set()
      and "Name Secondary 1" in acts_of(pn, 1) and "Assassination" not in " ".join(x for x in acts_of(pn, 1) if "Name" not in x))
pn.do(ev="score", side=0, cat="sec", row=0, delta=3)
pn.do(text="Cleanse", **acts_of(pn, 0)["Change Assassination"]["ev"])
check("phone: changing a scored secondary puts the old one away with its points, as on the box", view(pn.state["secs"][0]) == sorted([("Assassination", 3, None), ("Cleanse", 0, 0), ("Hold The Bridge", 0, 1)]) and w.score(pn.state, 0)[1] == 3)
check("phone: Put away from the phone", pn.do(**acts_of(pn, 0)["Put away Hold The Bridge"]["ev"]) == [] and rules.sec_at(pn.state["secs"][0], 1)["name"] == "Secondary 2")
check("phone: undo takes a phone's naming back like any other event", pn.undo() and pn.undo() and view(pn.state["secs"][0]) == sorted([("Assassination", 3, 0), ("Hold The Bridge", 0, 1)]))
back = engine.Session.load(pn.path, plugins, clock)
check("phone: names given from a phone survive save and resume", back.state == pn.state and "Change Assassination" in acts_of(back, 0))
real_table = P40.secondary_table
P40.secondary_table = lambda: [{"name": "Sabotage", "cap": 2, "scores": "for an action in terrain"}]
pn.do(ev="score", side=1, cat="sec", row=0, delta=5)
said = pn.do(text="sabotage", **acts_of(pn, 1)["Name Secondary 1"]["ev"])
check("phone: a name whose cap is below the points already on the row is refused; the cap comes from the list", "stops at 2" in said[0] and view(pn.state["secs"][1])[0] == ("Secondary 1", 5, 0), said)
check("phone: on an empty row the listed cap is applied", pn.do(text="sabotage", **acts_of(pn, 1)["Name Secondary 2"]["ev"]) == [] and rules.sec_at(pn.state["secs"][1], 1)["cap"] == 2)
P40.secondary_table = real_table
P40.HERE = tempfile.mkdtemp()
check("phone: with no list file the phone still offers naming, by typing only", acts_of(pn, 0)["Change Hold The Bridge"]["choices"] == [] and acts_of(pn, 0)["Change Hold The Bridge"]["ask"])
P40.HERE = here

from deepthought.games.wh40k import shots as shots_mod
out_dir, made = tempfile.mkdtemp(), []
def snap(name, screen=None):
    if screen is not None:
        app.stack = [app.stack[0]]
        app.toast = None
        app.push(screen)
    made.append(app.shot(os.path.join(out_dir, name + ".png")))
    return screen
shots_mod.shots(app, snap)
check("%d screenshots drawn, all 800x480, all named wh40k-" % len(made),
      len(made) >= 25 and {pygame.image.load(p).get_size() for p in made} == {(800, 480)} and all(os.path.basename(p).startswith("wh40k-") for p in made))
shutil.rmtree(out_dir)
check("nothing was written outside the temp data folder", paths.data("sessions").startswith(DATA))


# ---------------------------------------------------------------- secondary names: what a hostile phone could send
check("secondary name: characters with no shape are dropped; anything that is not text is no name",
      rules.sec_clean("grob\x00nar\x1b hu\ud800nt") == "Grob Nar Hu Nt" and rules.sec_clean(None) == "" and rules.sec_clean(7) == "" and rules.sec_clean(["x"]) == "",
      rules.sec_clean("grob\x00nar\x1b hu\ud800nt"))

print("\n%d checks, %d failed" % (count[0], len(fails))); sys.exit(1 if fails else 0)
