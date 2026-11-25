"""Tests for the Magic plugin: the sums in rules.py, every event in apply,
and the screens at two, three and four players."""
import json, os, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dt_content
from deepthought import engine, paths, theme as T
from deepthought.games import load_games
from deepthought.games.mtg import rules

fails = []
def check(name, cond, detail=""):
    line = ("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail))
    enc = sys.stdout.encoding or "utf-8"            # a Windows console cannot print every character
    print(line.encode(enc, "replace").decode(enc))
    if not cond: fails.append(name)

games, problems = load_games()
plugins = {g["id"]: g["plugin"] for g in games if g["plugin"]}
check("the game list loads Magic with no problems of its own", "mtg" in plugins and not [p for p in problems if p.startswith("mtg")], problems)
mtg = plugins["mtg"]
info = next(g for g in games if g["id"] == "mtg")
check("game.json: id mtg, name Magic, order 40, blurb fits a tile", (info["id"], info["name"], info["order"]) == ("mtg", "Magic", 40) and len(info["blurb"]) <= 28, info)
check("two to four players", (mtg.min_players, mtg.max_players) == (2, 4))
check("options: format offers Standard 20 and Commander 40", mtg.options[0]["key"] == "format" and mtg.options[0]["choices"][:2] == ["Standard 20 life", "Commander 40 life"])

STD = {"format": "Standard 20 life", "steps": "Every step", "hints": "On"}
CMD = {"format": "Commander 40 life", "steps": "Every step", "hints": "On"}
CMD_TURNS = {"format": "Commander 40 life", "steps": "Whole turn", "hints": "Off"}
def new(names, opts): return engine.Session(mtg, names, opts)

# ---------------------------------------------------------------- the sums
check("starting life: 20 standard, 40 commander", (rules.start_life("standard"), rules.start_life("commander")) == (20, 40))
check("format names: anything with Commander in it is commander", [rules.format_key(x) for x in ("Standard 20 life", "Commander 40 life", None, "")] == ["standard", "commander", "standard", "standard"])
check("out at 0 life, not at 1", rules.lost(1, 0) is None and rules.lost(0, 0) == "life" and rules.lost(-3, 0) == "life")
check("out at 10 poison, not at 9", rules.lost(20, 9) is None and rules.lost(20, 10) == "poison" and rules.lost(20, 11) == "poison")
check("out at 21 from one commander, not at 20", rules.lost(5, 0, [0, 20, 0], True) is None and rules.lost(5, 0, [0, 21, 0], True) == "commander")
check("20 from one commander and 20 from another is 40 damage but no knockout", rules.lost(1, 0, [20, 0, 20], True) is None)
check("commander damage does not count outside Commander", rules.lost(5, 0, [0, 21], False) is None)
check("life is checked before poison and commander damage", rules.lost(0, 10, [21], True) == "life" and rules.lost(3, 10, [21], True) == "poison")
check("warning at exactly 1 life", rules.warnings(1, 0) == ["life"] and rules.warnings(2, 0) == [] and rules.warnings(0, 0) == [])
check("warning at exactly 9 poison", rules.warnings(20, 9) == ["poison"] and rules.warnings(20, 8) == [] and rules.warnings(20, 10) == [])
check("warning at exactly 20 from one commander", rules.warnings(9, 0, [3, 20], True) == ["commander"] and rules.warnings(9, 0, [3, 19], True) == [] and rules.warnings(9, 0, [10, 10], True) == [])
check("no commander warning outside Commander", rules.warnings(9, 0, [20], False) == [])
check("all three warnings at once", rules.warnings(1, 9, [20, 0], True) == ["life", "poison", "commander"])
check("to go: 14 of 21 leaves 7, 9 of 10 leaves 1, never below 0", (rules.to_go(14, 21), rules.to_go(9, 10), rules.to_go(25, 21)) == (7, 1, 0))
check("the damage grid starts at nought, one row per player", rules.grid(3) == [[0, 0, 0], [0, 0, 0], [0, 0, 0]] and rules.grid(3)[0] is not rules.grid(3)[1])
ORDER = ["untap", "upkeep", "draw", "main1", "combat", "attackers", "blockers", "damage", "endcombat", "main2", "end", "cleanup"]
check("twelve steps in turn order", rules.STEP_KEYS == ORDER, rules.STEP_KEYS)
check("next step: untap to upkeep, damage to end of combat, cleanup ends the turn", (rules.next_step("untap"), rules.next_step("damage"), rules.next_step("cleanup")) == ("upkeep", "endcombat", None))
check("every step has a name and a hint", all(k in rules.STEP_NAME and rules.HINTS.get(k) for k in ORDER))
check("next alive: round the table, skipping the fallen", (rules.next_alive([False, False, False], 0), rules.next_alive([False, True, False], 0), rules.next_alive([False, True, True, False], 3), rules.next_alive([False, True, True], 0)) == (1, 2, 0, 0))
check("next alive: nobody left gives None", rules.next_alive([True, True], 0) is None)

# ---------------------------------------------------------------- new games
s = new(["Ethan", "Trevor"], STD)
check("two players, standard: 20 life each, no poison, no monarch, Ethan's untap, turn 1",
      s.state["life"] == [20, 20] and s.state["poison"] == [0, 0] and s.state["monarch"] is None and s.active_name() == "Ethan" and mtg.phase(s.state) == "untap" and s.state["turn"] == 1, s.state)
check("strip: Magic, turn 1, Untap", mtg.strip(s) == ("Magic · Turn 1", "Untap"), mtg.strip(s))
c3 = new(["A", "B", "C"], CMD)
check("three players, commander: 40 life each, a 3 by 3 grid of nought", c3.state["life"] == [40, 40, 40] and c3.state["cmd"] == [[0] * 3] * 3)
c4 = new(["A", "B", "C", "D"], CMD)
check("four players, commander: 40 life each, a 4 by 4 grid", c4.state["life"] == [40] * 4 and len(c4.state["cmd"]) == 4 and all(len(r) == 4 for r in c4.state["cmd"]))
check("strip says Commander in a Commander game", mtg.strip(c4) == ("Commander · Turn 1", "Untap"))
check("no options at all still gives a 20-life game that walks the steps", engine.Session(mtg, ["A", "B"], {}).state["life"] == [20, 20] and engine.Session(mtg, ["A", "B"], {}).state["steps"])
check("the state saves as JSON", json.loads(json.dumps(c4.state)) == c4.state)
check("phases for reminders are the twelve steps", [k for k, _ in mtg.phases()] == ORDER)
check("the button's event is next", mtg.press(s.state) == {"ev": "next"})

# ---------------------------------------------------------------- turn and step order
seen = ["untap"]
for _ in range(11):
    said = s.do(ev="next"); seen.append(mtg.phase(s.state))
    if seen[-1] == "draw": draw_said = said
check("eleven presses walk Ethan through all twelve steps in order", seen == ORDER and s.active_name() == "Ethan", seen)
check("two players, turn one: the first player is told there is no draw", any("no draw" in x for x in draw_said), draw_said)
s.do(ev="next")
check("the twelfth press passes to Trevor's untap, still turn 1", s.active_name() == "Trevor" and mtg.phase(s.state) == "untap" and s.state["turn"] == 1)
said = []
for _ in range(2): said += s.do(ev="next")
check("Trevor does draw on turn one: nothing said", mtg.phase(s.state) == "draw" and said == [] and mtg.hint(s.state) == rules.HINTS["draw"], said)
for _ in range(10): s.do(ev="next")
check("after Trevor's cleanup it is turn 2 and Ethan again", s.active_name() == "Ethan" and s.state["turn"] == 2 and mtg.phase(s.state) == "untap")
said = []
for _ in range(2): said += s.do(ev="next")
check("on turn 2 Ethan draws like anyone else", mtg.phase(s.state) == "draw" and said == [] and mtg.hint(s.state) == rules.HINTS["draw"])
check("24 + 2 events are in the log", len(s.log) == 26, len(s.log))
t = new(["A", "B", "C", "D"], CMD_TURNS)
order = []
for _ in range(9): order.append((t.active_name(), t.state["turn"])); t.do(ev="next")
check("whole-turn mode, four players: one press a turn, the turn counter goes up each time round",
      order == [("A", 1), ("B", 1), ("C", 1), ("D", 1), ("A", 2), ("B", 2), ("C", 2), ("D", 2), ("A", 3)], order)
check("whole-turn mode: strip says Main phase; no hint line", mtg.strip(t)[1] == "Main phase" and mtg.hint(t.state) is None)
t3 = new(["A", "B", "C"], CMD)
for _ in range(12): t3.do(ev="next")
check("three players: twelve presses and it is B's turn; no draw is skipped", t3.active_name() == "B" and not mtg.skips_draw(new(["A", "B", "C"], CMD).state))
h = new(["A", "B"], dict(STD, hints="Off"))
check("hints off: no hint line", mtg.hint(h.state) is None and mtg.hint(new(["A", "B"], STD).state) == rules.HINTS["untap"])
hd = new(["A", "B"], STD); hd.do(ev="next"); hd.do(ev="next")
check("the hint on the skipped draw says there is no draw", mtg.hint(hd.state) == rules.NO_DRAW)

# ---------------------------------------------------------------- life
g = new(["Ethan", "Trevor", "Sam"], STD)
check("life: minus 1 then minus 5: 20 - 1 - 5 = 14", g.do(ev="life", player=1, delta=-1) == [] and g.do(ev="life", player=1, delta=-5) == [] and g.state["life"] == [20, 14, 20])
g.do(ev="life", player=0, delta=5); g.do(ev="life", player=0, delta=1)
check("life: plus 5 then plus 1: 26, above the starting total is fine", g.state["life"] == [26, 14, 20])
check("undo takes back one life change", g.undo() and g.state["life"] == [25, 14, 20] and len(g.log) == 3)
check("life: a change of nothing, or of half a point, is refused", "whole number" in g.do(ev="life", player=0, delta=0)[0] and "whole number" in g.do(ev="life", player=0, delta=1.5)[0] and len(g.log) == 3)
check("life: an unknown player is refused", "which player" in g.do(ev="life", player=7, delta=1)[0] and "which player" in g.do(ev="life", delta=1)[0])
check("an unknown event is refused", "do not know" in g.do(ev="mill", player=0)[0] and len(g.log) == 3)
g.do(ev="life", player=1, delta=-12)
check("life 14 - 12 = 2: no warning yet", g.state["life"][1] == 2 and mtg.warnings(g.state, 1) == [])
said = g.do(ev="life", player=1, delta=-1)
check("life 1: the warning is said and shown in words", any("one life left" in x for x in said) and ("Warning: 1 life left", True) in mtg.status(g.state, 1), (said, mtg.status(g.state, 1)))
said = g.do(ev="life", player=1, delta=1)
check("back up to 2: warning gone, nothing said", said == [] and mtg.warnings(g.state, 1) == [])
g.do(ev="life", player=1, delta=-1)
said = g.do(ev="life", player=1, delta=-1)
check("life 0: Trevor is out, and it is said why", g.state["out"] == [False, True, False] and g.state["why"][1] == "life" and any("Trevor is out: no life left" in x for x in said) and g.finished is None, said)
check("a player who is out takes no more changes", "already out" in g.do(ev="life", player=1, delta=5)[0] and "already out" in g.do(ev="poison", player=1, delta=1)[0] and g.state["life"][1] == 0)
check("undo brings Trevor back on 1 life", g.undo() and g.state["out"] == [False, False, False] and g.state["life"][1] == 1 and g.state["why"][1] is None and g.state["fell"] == [])
said = g.do(ev="life", player=1, delta=-5)
check("minus 5 from 1 life: -4, out", g.state["life"][1] == -4 and g.state["out"][1])

# ---------------------------------------------------------------- skipping the fallen, last one standing
for _ in range(12): g.do(ev="next")
check("three players, Trevor out: after Ethan comes Sam, still turn 1", g.active_name() == "Sam" and g.state["turn"] == 1)
for _ in range(12): g.do(ev="next")
check("after Sam comes Ethan, turn 2", g.active_name() == "Ethan" and g.state["turn"] == 2)
check("leader: Ethan on 25 against Sam on 20; the fallen do not count", mtg.leader(g.state) == 0)
check("standings: life in order, the fallen last", mtg.standings(g.state, g.players) == ["Life: Ethan 25, Sam 20, Trevor out", "Stopped on turn 2"], mtg.standings(g.state, g.players))
g.do(ev="life", player=0, delta=-5)
check("level on 20: nobody leads", mtg.leader(g.state) is None)
said = g.do(ev="life", player=2, delta=-20)
check("Sam to 0: Ethan is the last one standing and wins", g.finished and g.finished["winner"] == "Ethan" and g.finished["lines"] == ["Sam fell last: no life left", "Ethan had 20 life left", "Turn 2"], g.finished)
check("a finished game takes no more events", g.do(ev="next") == ["The game is over."])
check("undo reopens the finished game", g.undo() and g.finished is None and g.state["life"] == [20, -4, 20])
a = new(["A", "B", "C", "D"], CMD)
a.do(ev="life", player=1, delta=-40); a.do(ev="life", player=2, delta=-40)
check("four players, B and C out: not over with two left", a.finished is None and mtg.over(a.state) is None)
for _ in range(12): a.do(ev="next")
check("four players: after A comes D, skipping two", a.active_name() == "D" and a.state["turn"] == 1)
for _ in range(12): a.do(ev="next")
check("then A again, turn 2", a.active_name() == "A" and a.state["turn"] == 2)
b = new(["A", "B", "C"], STD)
for _ in range(5): b.do(ev="next")
said = b.do(ev="life", player=0, delta=-20)
check("the player whose turn it is goes out mid-turn: the turn passes to B's untap", b.active_name() == "B" and mtg.phase(b.state) == "untap" and b.state["turn"] == 1 and any("B is up" in x for x in said), said)
b2 = new(["A", "B", "C"], STD)
for _ in range(24): b2.do(ev="next")
b2.do(ev="life", player=2, delta=-20)
check("the last seat goes out on its own turn: A is up and it is turn 2", b2.active_name() == "A" and b2.state["turn"] == 2 and mtg.phase(b2.state) == "untap")

# ---------------------------------------------------------------- poison
p = new(["Ethan", "Trevor"], STD)
check("poison cannot go below nought", "no poison counters" in p.do(ev="poison", player=0, delta=-1)[0] and p.state["poison"] == [0, 0])
for _ in range(8): p.do(ev="poison", player=1, delta=1)
check("eight poison: no warning", p.state["poison"] == [0, 8] and mtg.warnings(p.state, 1) == [] and ("Poison 8", False) in mtg.status(p.state, 1))
said = p.do(ev="poison", player=1, delta=1)
check("nine poison: warned in words, still in", any("nine poison" in x for x in said) and ("Warning: 9 poison", True) in mtg.status(p.state, 1) and not p.state["out"][1], said)
check("poison leaves life alone", p.state["life"] == [20, 20])
p.do(ev="poison", player=1, delta=-1)
check("one taken off: 8, warning gone", p.state["poison"][1] == 8 and mtg.warnings(p.state, 1) == [])
p.do(ev="poison", player=1, delta=1)
said = p.do(ev="poison", player=1, delta=1)
check("ten poison: Trevor is out on 20 life and Ethan wins", p.state["why"][1] == "poison" and p.finished and p.finished["winner"] == "Ethan" and p.finished["lines"][0] == "Trevor fell last: ten poison counters", (said, p.finished))
check("undo: nine poison, game on", p.undo() and p.state["poison"][1] == 9 and p.finished is None and not p.state["out"][1])

# ---------------------------------------------------------------- commander damage
c = new(["Ethan", "Trevor", "Sam", "Jo"], CMD)
c.do(ev="cmd", player=1, source=0, delta=14)
check("14 from Ethan's commander to Trevor: grid says so, life 40 - 14 = 26", c.state["cmd"][1] == [14, 0, 0, 0] and c.state["life"] == [40, 26, 40, 40], c.state)
c.do(ev="cmd", player=1, source=2, delta=3)
check("3 more from Sam's: counted apart, life 23", c.state["cmd"][1] == [14, 0, 3, 0] and c.state["life"][1] == 23)
check("the grid keeps who dealt it to whom: nobody else's row moved", c.state["cmd"][0] == [0] * 4 and c.state["cmd"][2] == [0] * 4 and c.state["cmd"][3] == [0] * 4)
check("status shows the worst single commander: 14 of 21", ("Commander 14/21", False) in mtg.status(c.state, 1), mtg.status(c.state, 1))
check("no damage from your own commander", "other players" in c.do(ev="cmd", player=1, source=1, delta=1)[0])
check("a commander must be named", "which commander" in c.do(ev="cmd", player=1, delta=1)[0] and "which commander" in c.do(ev="cmd", player=1, source=9, delta=1)[0])
check("damage cannot be taken back below nought", "no damage to take back" in c.do(ev="cmd", player=1, source=3, delta=-1)[0])
c.do(ev="cmd", player=1, source=2, delta=-1)
check("a correction gives the life back: Sam's 3 becomes 2, life 24", c.state["cmd"][1][2] == 2 and c.state["life"][1] == 24)
c.do(ev="life", player=1, delta=30)
said = c.do(ev="cmd", player=1, source=0, delta=5)
check("19 from Ethan: no warning yet; life 54 - 5 = 49", c.state["cmd"][1][0] == 19 and c.state["life"][1] == 49 and said == [], said)
said = c.do(ev="cmd", player=1, source=0, delta=1)
check("20 from Ethan: warned in words", any("20 from one commander" in x for x in said) and ("Warning: cmdr 20", True) in mtg.status(c.state, 1) and not c.state["out"][1], said)
c.do(ev="cmd", player=1, source=2, delta=18)
check("20 from Sam as well: 40 commander damage in all, still in on 30 life", c.state["cmd"][1] == [20, 0, 20, 0] and c.state["life"][1] == 30 and not c.state["out"][1])
said = c.do(ev="cmd", player=1, source=0, delta=1)
check("21 from Ethan: Trevor is out with 29 life left", c.state["out"][1] and c.state["why"][1] == "commander" and c.state["life"][1] == 29 and any("21 damage from one commander" in x for x in said), said)
check("undo: back to 20, in the game", c.undo() and c.state["cmd"][1][0] == 20 and not c.state["out"][1] and c.state["life"][1] == 30)
c.do(ev="cmd", player=3, source=1, delta=40)
check("40 commander damage at once: out for life, which is checked first", c.state["out"][3] and c.state["why"][3] == "life" and c.state["life"][3] == 0)
check("a commander that has left the game deals no more damage", "left the game" in c.do(ev="cmd", player=0, source=3, delta=1)[0])
n = new(["A", "B"], STD)
check("commander damage is refused in a 20-life game", "only counts in a Commander game" in n.do(ev="cmd", player=1, source=0, delta=1)[0] and n.state["life"] == [20, 20])
c2 = new(["A", "B"], CMD)
c2.do(ev="cmd", player=1, source=0, delta=20)
said = c2.do(ev="cmd", player=1, source=0, delta=1)
check("two-player Commander: 21 from A's commander beats B on 19 life", c2.finished and c2.finished["winner"] == "A" and c2.state["life"][1] == 19 and c2.finished["lines"][0] == "B fell last: 21 damage from one commander", c2.finished)

# ---------------------------------------------------------------- the monarch
m = new(["Ethan", "Trevor", "Sam", "Jo"], CMD)
check("no monarch to begin with, and none to depose", m.state["monarch"] is None and "no one to depose" in m.do(ev="monarch", player=None)[0])
said = m.do(ev="monarch", player=2)
check("Sam becomes the monarch", m.state["monarch"] == 2 and said == ["Sam is the monarch."] and ("Monarch", False) in mtg.status(m.state, 2))
check("already the monarch is refused", "already the monarch" in m.do(ev="monarch", player=2)[0])
m.do(ev="monarch", player=0)
check("the crown moves: one holder only", m.state["monarch"] == 0 and ("Monarch", False) not in mtg.status(m.state, 2))
check("undo moves it back to Sam", m.undo() and m.state["monarch"] == 2)
m.do(ev="monarch", player=None)
check("the crown can be set down: nobody holds it", m.state["monarch"] is None)
m.do(ev="monarch", player=0)
said = []
for _ in range(10): said += m.do(ev="next")
check("the monarch is reminded to draw at their own end step, once", mtg.phase(m.state) == "end" and said == ["Ethan is the monarch: draw a card."], said)
m.do(ev="next"); m.do(ev="next")
said = []
for _ in range(10): said += m.do(ev="next")
check("nobody else is reminded on their end step", m.active_name() == "Trevor" and mtg.phase(m.state) == "end" and said == [], said)
said = m.do(ev="life", player=0, delta=-40)
check("the monarch goes out on someone else's turn: the crown passes to the player whose turn it is", m.state["monarch"] == 1 and any("Trevor takes the crown" in x for x in said), (m.state["monarch"], said))
said = m.do(ev="life", player=1, delta=-40)
check("the monarch goes out on their own turn: the crown passes to the next player, who is also up", m.state["monarch"] == 2 and m.active_name() == "Sam" and any("Sam takes the crown" in x for x in said), (m.state["monarch"], said))
check("a fallen player cannot be made monarch", "cannot be the monarch" in m.do(ev="monarch", player=0)[0])
mt = new(["A", "B"], dict(STD, steps="Whole turn"))
mt.do(ev="monarch", player=0)
check("whole-turn mode: the monarch is reminded as the turn ends", mt.do(ev="next") == ["A is the monarch: draw a card as the turn ends."] and mt.do(ev="next") == [])

# ---------------------------------------------------------------- out for another reason
o = new(["A", "B", "C"], STD)
said = o.do(ev="out", player=1)
check("a player can be put out by hand, for an empty library", o.state["out"] == [False, True, False] and o.state["why"][1] == "other" and o.state["life"][1] == 20 and any("B is out" in x for x in said), said)
check("put out twice is refused", "already out" in o.do(ev="out", player=1)[0])
o.do(ev="out", player=2)
check("the last one left wins", o.finished and o.finished["winner"] == "A", o.finished)

# ---------------------------------------------------------------- saving, the scoreboard, phones
folder = paths.data("sessions")
sv = engine.Session(mtg, ["Ethan", "Trevor", "Sam", "Jo"], CMD, folder)
sv.do(ev="cmd", player=1, source=0, delta=9); sv.do(ev="poison", player=3, delta=3); sv.do(ev="monarch", player=2); sv.do(ev="next")
again = engine.Session.load(sv.path, plugins)
check("a saved game loads back exactly", again.state == sv.state and again.log == sv.log and again.players == sv.players)
board = mtg.scoreboard(sv)
check("scoreboard: a row a player with life; the step in the note", [(r["name"], r["value"], r["out"]) for r in board["rows"]] == [("Ethan", 40, False), ("Trevor", 31, False), ("Sam", 40, False), ("Jo", 40, False)] and board["note"] == "Life · Upkeep", board)
check("scoreboard: poison, commander damage and the crown are in the detail", [r["detail"] for r in board["rows"]] == ["", "Commander 9/21", "Monarch", "Poison 3"], board)
ph = mtg.phone(sv, 1)
check("phone: Trevor sees his own life, poison and commander damage", ph["lines"] == ["Life 31", "Poison 0", "9 from Ethan's commander"], ph["lines"])
labels = [x["label"] for x in ph["actions"]]
check("phone: not his turn, so life and poison but no Next", labels == ["Life +1", "Life −1", "Life +5", "Life −5", "Poison +1"], labels)
check("phone: every action is about that player's own seat", all(x["ev"]["player"] == 1 for x in ph["actions"]))
ph0 = mtg.phone(sv, 0)
check("phone: Ethan, whose turn it is, also gets Next step", ph0["actions"][-1] == {"label": "Next step", "ev": {"ev": "next"}}, ph0["actions"])
sv.do(**ph["actions"][3]["ev"]); sv.do(**ph["actions"][4]["ev"])
check("phone: Life −5 and Poison +1 do what they say: 31 - 5 = 26, poison 1", sv.state["life"][1] == 26 and sv.state["poison"][1] == 1)
check("phone: Poison −1 appears once there is poison to remove", "Poison −1" in [x["label"] for x in mtg.phone(sv, 1)["actions"]])
sv.do(**ph0["actions"][-1]["ev"])
check("phone: Next moves the step on", mtg.phase(sv.state) == "draw")
check("phone: the monarch is told", "You are the monarch" in mtg.phone(sv, 2)["lines"])
sv.do(ev="life", player=3, delta=-40)
check("phone: a fallen player is told so and can do nothing", mtg.phone(sv, 3) == {"lines": ["You are out: no life left."], "actions": []}, mtg.phone(sv, 3))
check("phone: a seat that does not exist gets nothing", mtg.phone(sv, 9) == {"lines": [], "actions": []})
sv.finish()
check("stopped early with a tie on 40: no winner, standings recorded", sv.finished["winner"] is None and sv.finished["lines"][0] == "Life: Ethan 40, Sam 40, Trevor 26, Jo out", sv.finished)

# ---------------------------------------------------------------- teaching notes
teach = mtg.teach()
check("how to play: a dozen or so short steps, each with a title and text", 8 <= len(teach) <= 16 and all(x.get("title") and x.get("text") for x in teach), len(teach))
check("how to play: no step is longer than 700 characters", max(len(x["text"]) for x in teach) <= 700, max(len(x["text"]) for x in teach))
everything = " ".join(x["title"] + " " + x["text"] for x in teach)
check("how to play: she never exclaims", "!" not in everything)
check("how to play: the three knockouts are taught: 0 life, ten poison, 21 from a commander", "reaches 0" in everything and "ten poison" in everything and "21 combat damage" in everything)

# ---------------------------------------------------------------- screens
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens import common, extras
from deepthought.screens.dice import Dice
from deepthought.screens.home import Home
from deepthought.screens.lookup import Lookup
from deepthought.screens.pick_game import PickGame
from deepthought.games.mtg.plugin import MtgCounters, MtgPlay, MtgPlayer, Panel

src = tempfile.mkdtemp()                         # a made-up card, so Lookup has something to find
json.dump([{"object": "card", "oracle_id": "id-1", "name": "Grobnar Bear", "mana_cost": "{1}{G}", "cmc": 2, "type_line": "Creature — Bear",
            "oracle_text": "Made-up test card.", "power": "2", "toughness": "2", "layout": "normal", "legalities": {}}],
          open(os.path.join(src, "cards.json"), "w"))
con = dt_content.connect(os.environ["DT_CONTENT_DB"])
dt_content.load_cards(con, os.path.join(src, "cards.json"), log=lambda *a: None); con.close()

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
def tap(label, nth=0):
    ws = [w for w in app.screen.widgets if w.action]
    w = ([w for w in ws if w.label == label] or [w for w in ws if w.label.startswith(label)])[nth]   # exact first
    app.toast = None
    w.action()
def labels(): return [w.label for w in app.screen.widgets if w.action]
def primaries(): return [w.label for w in app.screen.widgets if getattr(w, "style", "") == "primary"]

# ---- two players, from Home
tap("Play")
check("Play goes to Pick a game", isinstance(app.screen, PickGame))
app.screen.choose([g["id"] for g in games].index("mtg"))
setup = app.screen
check("choosing Magic opens Set up with two players", isinstance(setup, common.Setup) and setup.n == 2 and screen_ok() == [], screen_ok())
tap("+"); tap("+"); tap("+")
check("Set up: four players at most, all buttons fit", setup.n == 4 and screen_ok() == [], screen_ok())
tap("−"); tap("−"); tap("−")
check("Set up: two players at least", setup.n == 2)
tap("Format"); check("the Format button cycles to Commander", setup.opts["format"] == "Commander 40 life"); tap("Format")
tap("How to play")
check("How to play opens Magic's own steps", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "The aim" and screen_ok() == [], screen_ok())
n_pages, ok = len(app.screen.pages), True
for _ in range(n_pages):
    ok = ok and screen_ok() == []
    app.gesture("press")
check("pressing through all %d pages comes back to Set up, every page fitting" % n_pages, app.screen is setup and ok)
setup.names[0], setup.names[1] = "Ethan", "Trevor"
tap("Start game")
play = app.screen
check("Start game: the life screen, Ethan's turn, ring in his colour",
      isinstance(play, MtgPlay) and play.pill[0] == "Ethan's turn" and app.hw._ring.now == ("turn", {"colour": T.player_colour(0)}) and screen_ok() == [], screen_ok())
check("strip: Magic, turn 1, Untap", (play.left, play.title) == ("Magic · Turn 1", "Untap"))
check("two players: two panels, four life keys each, one primary button", labels()[:10] == ["Ethan", "−5", "−", "+", "+5", "Trevor", "−5", "−", "+", "+5"] and primaries() == ["Next step"], labels())
tap("−", 1); tap("−5", 1); tap("+", 0); tap("+5", 0)
check("the keys change life by 1 and by 5: Ethan 26, Trevor 14", app.session.state["life"] == [26, 14] and screen_ok() == [], app.session.state["life"])
tap("Undo")
check("Undo takes the last tap back: Ethan 21", app.session.state["life"] == [21, 14])
app.gesture("press")
check("the button moves to Upkeep", play.title == "Upkeep" and app.session.state["phase"] == "upkeep" and screen_ok() == [])
app.gesture("press"); app.gesture("double")
check("double press: takes back its own press and undoes one more", app.session.state["phase"] == "untap" and app.session.state["life"] == [21, 14], (app.session.state["phase"], app.session.state["life"]))
ok = True
for _ in range(12):
    app.gesture("press"); ok = ok and screen_ok() == []
check("twelve presses: every step's screen fits, then it is Trevor's turn with the ring in his colour",
      ok and play.pill[0] == "Trevor's turn" and play.title == "Untap" and app.hw._ring.now == ("turn", {"colour": T.player_colour(1)}))
tap("Counters"); cn = app.screen
check("Counters fits at two players", isinstance(cn, MtgCounters) and cn.title == "Counters" and screen_ok() == [] and primaries() == ["Back"], screen_ok())
tap("+", 1); tap("+", 1); tap("+", 0); tap("−", 0)
check("Counters: poison plus and minus per player", app.session.state["poison"] == [0, 2] and screen_ok() == [], app.session.state["poison"])
tap("Make monarch", 1)
check("Counters: Trevor is made monarch; his button says so and is marked", app.session.state["monarch"] == 1 and [w.selected for w in cn.widgets if w.label == "Is monarch"] == [True] and screen_ok() == [])
tap("Make monarch", 0)
check("Counters: the crown moves to Ethan; only one Is monarch", app.session.state["monarch"] == 0 and labels().count("Is monarch") == 1)
tap("Is monarch")
check("Counters: tapping the holder sets the crown down", app.session.state["monarch"] is None and "Is monarch" not in labels())
app.gesture("press")
check("the button leaves Counters", app.screen is play and screen_ok() == [])
tap("Trevor"); pl = app.screen
check("tapping a player's total opens their own screen: life and poison in a 20-life game",
      isinstance(pl, MtgPlayer) and pl.title == "Trevor" and pl.rows() == [("poison", None)] and screen_ok() == [] and primaries() == ["Back"], screen_ok())
tap("−5"); tap("+", 1)
check("player screen: life 14 - 5 = 9, poison 3", app.session.state["life"][1] == 9 and app.session.state["poison"][1] == 3 and screen_ok() == [])
tap("Poison and counters")
check("player screen leads to Counters", isinstance(app.screen, MtgCounters))
tap("Back"); tap("Back")
check("Back twice returns to the life screen", app.screen is play)
tap("Card"); look = app.screen
check("Card opens the shared Lookup on Magic", type(look) is Lookup and look.game == "mtg" and screen_ok() == [], screen_ok())
look.run("grobnar")
check("Lookup finds the made-up card", [r["title"] for r in look.results] == ["Grobnar Bear"] and screen_ok() == [], look.results)
look.open(look.results[0])
check("opening it shows the card as pages", isinstance(app.screen, common.Pages) and app.screen.left == "Grobnar Bear" and screen_ok() == [])
app.gesture("press"); app.gesture("double"); tap("Back")
tap("Dice")
check("Dice opens the shared dice screen", isinstance(app.screen, Dice) and screen_ok() == [], screen_ok())
tap("Back"); tap("Menu")
check("More opens the shared menu", isinstance(app.screen, extras.GameMenu) and screen_ok() == [])
tap("Reminders"); tap("When:"); tap("When:")
check("Reminders can be tied to a Magic step", "Upkeep" in " ".join(labels()), labels())
tap("Back"); tap("Back to the game")
for _ in range(8): tap("−", 1)
check("Trevor on 1 life: the screen says Warning in words, and she says it too", app.session.state["life"][1] == 1 and ("Warning: 1 life left", True) in mtg.status(app.session.state, 1) and "one life left" in (app.toast or "") and screen_ok() == [], app.toast)
tap("−", 1)
ask = app.screen
check("a tap that would end the game asks first, and changes nothing yet", isinstance(ask, common.Choice) and ask.title == "Game over?" and "Trevor" in ask.text and "Ethan wins" in ask.text and app.session.state["life"][1] == 1 and screen_ok() == [], getattr(ask, "text", ask))
app.gesture("press")
check("the button's answer is Keep playing", app.screen is play and app.session.state["life"][1] == 1 and app.session.finished is None)
tap("−5", 1); tap("End the game")
over = app.screen
check("End the game: Game over, Ethan wins, Trevor on -4", isinstance(over, common.GameOver) and over.session.finished["winner"] == "Ethan" and over.session.state["life"][1] == -4 and screen_ok() == [], over.session.finished)
app.gesture("press")
check("Home shows the last game", isinstance(app.screen, Home) and app.last_game == "Last game: Magic, Ethan won", app.last_game)

# ---- every play screen at 2, 3 and 4 players, both formats, hints on and off
def start(names, opts):
    app.go_home()
    app.start_game(mtg, names, opts)
    return app.screen
NAMES = ["Ethan", "Trevor", "Sam", "Jo"]
for n in (2, 3, 4):
    for opts in (STD, CMD, CMD_TURNS):
        tag = "%d players, %s, %s" % (n, opts["format"].split()[0], opts["steps"].lower())
        play = start(NAMES[:n], opts)
        bad = list(screen_ok())
        panels = [w for w in play.widgets if isinstance(w, Panel)]
        bad += [] if len(panels) == n else [("panels", len(panels))]
        bad += [] if primaries() == ["Next step" if opts["steps"] == "Every step" else "Next turn"] else [("primary", primaries())]
        for i in range(n):
            tap(NAMES[i]); bad += screen_ok()
            bad += [] if isinstance(app.screen, MtgPlayer) and app.screen.who == i else [("player", i)]
            want = ([("cmd", j) for j in range(n) if j != i] if opts is not STD else []) + ([("poison", None)] if n < 4 or opts is STD else [])
            bad += [] if app.screen.rows() == want else [("rows", app.screen.rows())]
            tap("Back")
        tap("Counters"); bad += screen_ok(); tap("Back")
        check("screens fit: " + tag, bad == [], bad)

# ---- four players, Commander
play = start(NAMES, CMD_TURNS)
check("four players: a grid of four tappable totals and the bottom row", labels() == ["Ethan", "Trevor", "Sam", "Jo", "Next turn", "Counters", "Card", "Undo", "Dice", "Menu"], labels())
check("strip: Commander, turn 1, Main phase", (play.left, play.title) == ("Commander · Turn 1", "Main phase"))
tap("Trevor"); pl = app.screen
check("Trevor's screen: one row for each other commander, no turn pill", pl.rows() == [("cmd", 0), ("cmd", 2), ("cmd", 3)] and pl.pill is None and (pl.left, pl.title) == ("Commander · Turn 1", "Trevor") and screen_ok() == [])
for _ in range(14): tap("+", 1)
tap("+", 2); tap("+", 2); tap("+", 2)
check("14 from Ethan's commander and 3 from Sam's: life 40 - 17 = 23", app.session.state["cmd"][1] == [14, 0, 3, 0] and app.session.state["life"][1] == 23 and screen_ok() == [], app.session.state["cmd"][1])
tap("−", 2)
check("minus on Sam's row: 2, and the life comes back: 24", app.session.state["cmd"][1][2] == 2 and app.session.state["life"][1] == 24)
tap("+5"); tap("−"); tap("−5"); tap("+")
check("the life keys on the player screen: +5, -1, -5, +1 leaves 24", app.session.state["life"][1] == 24)
tap("Undo"); check("Undo on the player screen", app.session.state["life"][1] == 23); tap("+")
for _ in range(6): tap("+", 1)
check("20 from Ethan's commander: warned in words, still in, life 24 - 6 = 18",
      app.session.state["cmd"][1][0] == 20 and app.session.state["life"][1] == 18 and not app.session.state["out"][1] and "20 from one commander" in (app.toast or "") and screen_ok() == [], app.toast)
tap("+", 1)
check("21: Trevor is out with 17 life; his screen has no keys left but Back, Undo and counters",
      app.session.state["out"][1] and app.session.state["life"][1] == 17 and labels() == ["Poison and counters", "Undo", "Back"] and screen_ok() == [], labels())
app.gesture("press")
check("the button goes back to the totals, which still fit with a player out", app.screen is play and screen_ok() == [])
app.gesture("press")
check("the button passes Ethan's turn; Trevor is skipped and Sam is up", play.pill[0] == "Sam's turn" and app.session.state["turn"] == 1)
tap("Counters"); cn = app.screen
check("Counters at four players with one out: three rows of keys, all fitting", labels().count("Out") == 3 and labels().count("Make monarch") == 3 and screen_ok() == [], labels())
for _ in range(9): tap("+", 2)
check("Jo on nine poison: warned in words", app.session.state["poison"] == [0, 0, 0, 9] and "nine poison" in (app.toast or "") and ("Warning: 9 poison", True) in mtg.status(app.session.state, 3) and screen_ok() == [], app.toast)
tap("Out", 1)
ask = app.screen
check("Out asks first", isinstance(ask, common.Choice) and ask.title == "Out of the game?" and "Sam" in ask.text and screen_ok() == [])
app.gesture("press")
check("the button's answer is Keep playing", app.screen is cn and app.session.state["out"] == [False, True, False, False])
tap("Out", 1); tap("Sam is out")
check("Sam is out; it was his turn, so Jo is up", app.session.state["out"] == [False, True, True, False] and app.session.state["why"][2] == "other" and app.session.active_name() == "Jo" and screen_ok() == [])
tap("+", 1)
check("the tenth poison counter would end the game, so she asks", isinstance(app.screen, common.Choice) and app.screen.title == "Game over?" and "Ethan wins" in app.screen.text and app.session.state["poison"][3] == 9)
tap("End the game")
check("Ethan is the last one standing", isinstance(app.screen, common.GameOver) and app.screen.session.finished["winner"] == "Ethan" and app.screen.session.finished["lines"][0] == "Jo fell last: ten poison counters" and screen_ok() == [], app.screen.session.finished)

# ---- a game stopped part-way can be picked up again
play = start(NAMES[:3], CMD)
tap("Sam"); tap("+", 1); tap("Back"); app.gesture("press")
tap("Menu"); tap("Home")
check("Home from the menu leaves the Magic game resumable", isinstance(app.screen, Home) and engine.unfinished(folder)[1]["game"] == "mtg")
tap("Play"); tap("Resume it")
check("Resume puts the game back as it was", isinstance(app.screen, MtgPlay) and app.session.state["cmd"][2] == [1, 0, 0] and app.session.state["life"] == [40, 40, 39] and app.session.state["phase"] == "upkeep" and screen_ok() == [])

# ---------------------------------------------------------------- found in review
from deepthought import guide as _guide
from deepthought.games.mtg.plugin import MtgPlay as _MP, MtgPlayer as _MPl
app.start_game(mtg, ["Ethan", "Trevor"], dict(STD, guide="Off"))
tap("Next step")
app.screen.player(1)
tap("−"); tap("−"); tap("−")
n = len(app.session.log)
app.gesture("press"); app.gesture("double")
check("a double press on a player's screen closes it and undoes nothing", isinstance(app.screen, _MP) and app.session.state["life"] == [20, 17] and len(app.session.log) == n, (app.session.state["life"], len(app.session.log), n))
tap("Menu"); app.gesture("press"); app.gesture("double")
check("a double press on the More menu undoes nothing either", isinstance(app.screen, _MP) and app.session.state["life"] == [20, 17] and app.session.state["phase"] == "upkeep" and len(app.session.log) == n)
tap("Counters"); app.gesture("press"); app.gesture("double")
check("nor on Counters", isinstance(app.screen, _MP) and len(app.session.log) == n)
app.gesture("press"); app.gesture("double")
check("on the life totals a double press takes back its own press and one more", app.session.state["life"] == [20, 18] and app.session.state["phase"] == "upkeep" and len(app.session.log) == n - 1, (app.session.state["life"], app.session.state["phase"]))

def cards_up():
    seen = []
    while isinstance(app.screen, common.Pages):
        for h, _ in app.screen.pages:
            if h not in seen: seen.append(h)
        app.render(); app.screen.close()
    return seen
check("the game says what a moment was: nothing for a plain change", mtg.marks(new(["A", "B"], STD).state, new(["A", "B"], STD).state, {"ev": "next"}) == [])
k = new(["A", "B", "C"], STD); b4 = json.loads(json.dumps(k.state)); k.do(ev="life", player=1, delta=-19)
check("down to one life is a 'warning' moment", mtg.marks(b4, k.state, {}) == ["warning"])
b4 = json.loads(json.dumps(k.state)); k.do(ev="life", player=1, delta=-1)
check("out through life is a 'knockout' moment, the same as out by hand", mtg.marks(b4, k.state, {}) == ["knockout"])
app.start_game(mtg, ["Ethan", "Trevor", "Sam"], dict(STD, steps="Whole turn", guide="As we play")); cards_up()
app.game_event({"ev": "life", "player": 1, "delta": -5})
check("Teach on: an ordinary life change brings no card", cards_up() == [])
app.game_event({"ev": "life", "player": 1, "delta": -15})
check("Teach on: a player dying through life brings up Ways to be out", cards_up() == ["Ways to be out"] and app.session.state["out"][1])
app.game_event({"ev": "out", "player": 2})
check("and it is taught once only", isinstance(app.screen, common.GameOver))
app.start_game(mtg, ["Ethan", "Trevor"], dict(STD, guide="As we play")); cards_up()
app.game_event({"ev": "poison", "player": 1, "delta": 8}); cards_up()
app.game_event({"ev": "poison", "player": 1, "delta": 1})
check("two players, Teach on: the first warning brings up Ways to be out, before the game is over", cards_up() == ["Ways to be out"] and app.session.finished is None)
app.game_event({"ev": "life", "player": 0, "delta": -19})
check("a second warning does not bring it again", cards_up() == [])

c4 = new(["Bartholomew Xy", "Trevor", "Sam", "Jo"], CMD)
c4.do(ev="cmd", player=0, source=1, delta=20); c4.do(ev="poison", player=0, delta=9); c4.do(ev="monarch", player=0); c4.do(ev="life", player=0, delta=-19)
st = mtg.status(c4.state, 0)
check("one life, nine poison, 20 from a commander and the crown: three short warnings first, then Monarch",
      st == [("Warning: 1 life left", True), ("Warning: 9 poison", True), ("Warning: cmdr 20", True), ("Monarch", False)], st)
check("each warning fits a four-player panel on one line", all(T.font("bold", 22).size(t)[0] <= 200 for t, w in st if w), [T.font("bold", 22).size(t)[0] for t, w in st])
drawn = []
_dt = T.draw_text
def _spy(surf, text, *a, **k):
    drawn.append(text); return _dt(surf, text, *a, **k)
app.start_game(mtg, ["Bartholomew Xy", "Trevor", "Sam", "Jo"], dict(CMD, guide="Off"))
for ev in (dict(ev="cmd", player=0, source=1, delta=20), dict(ev="poison", player=0, delta=9), dict(ev="monarch", player=0), dict(ev="life", player=0, delta=-19)):
    app.session.do(**ev)
app.screen.refresh(); app.toast = None
T.draw_text = _spy; app.render(); T.draw_text = _dt
check("four players: with three warnings showing, the crown moves up beside the name and no warning is cut",
      all(t in drawn for t, w in st if w) and any("monarch" in x and x.startswith("Bartholomew") for x in drawn) and "Monarch" not in drawn, drawn[:12])
app.start_game(mtg, ["Ethan", "Trevor"], dict(STD, guide="Off"))
for ev in (dict(ev="poison", player=0, delta=9), dict(ev="monarch", player=0), dict(ev="life", player=0, delta=-19), dict(ev="monarch", player=1)):
    app.session.do(**ev)
app.session.do(ev="monarch", player=0)
app.screen.refresh(); app.toast = None; drawn.clear()
T.draw_text = _spy; app.render(); T.draw_text = _dt
check("two players: two warnings and the crown: both warnings show and the crown is beside the name",
      "Warning: 1 life left" in drawn and "Warning: 9 poison" in drawn and "Ethan · monarch" in drawn, drawn[:12])
app.session.do(ev="life", player=0, delta=5); app.screen.refresh(); drawn.clear()
T.draw_text = _spy; app.render(); T.draw_text = _dt
check("with room to spare the crown has its own line, as before", "Monarch" in drawn and "Ethan" in drawn and "Ethan · monarch" not in drawn, drawn[:12])
app.start_game(mtg, ["Bartholomew Xy", "Trevor"], dict(CMD, guide="Off"))
for ev in (dict(ev="cmd", player=0, source=1, delta=20), dict(ev="poison", player=0, delta=9), dict(ev="monarch", player=0), dict(ev="life", player=0, delta=-19)):
    app.session.do(**ev)
app.screen.refresh(); app.toast = None; drawn.clear()
T.draw_text = _spy; app.render(); T.draw_text = _dt
room = next(w for w in app.screen.widgets if isinstance(w, Panel)).frame.w - 28
check("two players, Commander: three warnings at once and the crown: all three are on the big panel, in two lines, none cut",
      app.session.state["life"][0] == 1 and "Warning: 1 life left" in drawn and "Warning: 9 poison · cmdr 20" in drawn
      and any("monarch" in x and x.startswith("Bartholomew") for x in drawn)
      and T.font("bold", 22).size("Warning: 9 poison · cmdr 20")[0] <= room, (drawn[:12], room))
app.go_home()

# ---- screenshots
from deepthought.games.mtg.shots import shots
shot_dir, made = tempfile.mkdtemp(), []
def snap(name, screen=None):
    if screen is not None:
        app.stack = [app.stack[0]]
        app.toast = None
        app.push(screen)
    made.append(app.shot(os.path.join(shot_dir, name + ".png")))
    return screen
shots(app, snap)
check("%d screenshots drawn, all 800x480, all named mtg-" % len(made),
      len(made) >= 20 and {pygame.image.load(p).get_size() for p in made} == {(800, 480)} and all(os.path.basename(p).startswith("mtg-") for p in made))
shutil.rmtree(shot_dir); shutil.rmtree(src); shutil.rmtree(DATA, ignore_errors=True)

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
