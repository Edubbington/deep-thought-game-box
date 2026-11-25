"""Tests for the D&D plugin: the initiative tracker's rules, the character
screens, DM mode, and what the scoreboard and the phones are allowed to see.
Expected numbers are worked by hand. Every character and enemy here is made up."""
import json, os, shutil, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
SOFT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOFT)
import dt_content
import dt_characters as ch
from deepthought import engine, paths, settings, theme as T
from deepthought.games import load_games
from deepthought.games.dnd import dm, party, rules

fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

games, problems = load_games()
plugins = {g["id"]: g["plugin"] for g in games if g["plugin"]}
dnd = plugins.get("dnd")
check("the D&D plugin loads, with no problems reported for it", dnd is not None and not any("dnd" in p for p in problems), problems)
shipped = os.path.join(SOFT, "campaigns", "dragon-of-icespire-peak.json")
shipped_before = open(shipped, "rb").read()

# ---------------------------------------------------------------- the sums
check("concentration: 1 damage is DC 10", rules.conc_dc(1) == 10)
check("concentration: 19 damage is DC 10 (half is 9)", rules.conc_dc(19) == 10)
check("concentration: 20 damage is DC 10", rules.conc_dc(20) == 10)
check("concentration: 21 damage is DC 10 (half, rounded down, is 10)", rules.conc_dc(21) == 10)
check("concentration: 22 damage is DC 11", rules.conc_dc(22) == 11)
check("concentration: 45 damage is DC 22", rules.conc_dc(45) == 22)
check("concentration: 80 damage is DC 40 under 2014, stopped at 30 under 2024", (rules.conc_dc(80, "2014"), rules.conc_dc(80, "2024")) == (40, 30))

def C(i, init, tie=0, dead=False):
    return {"id": i, "init": init, "tie": tie, "dead": dead}
ids = lambda cs: [c["id"] for c in cs]
check("order: highest initiative first", ids(rules.order([C(1, 8), C(2, 19), C(3, 14)])) == [2, 3, 1])
check("order: a tie goes to whoever joined first", ids(rules.order([C(3, 15), C(1, 15), C(2, 20)])) == [2, 1, 3])
check("order: unless someone was marked as winning ties", ids(rules.order([C(1, 15), C(2, 15, tie=1), C(3, 15)])) == [2, 1, 3])
check("order: no initiative yet goes last; a negative one still counts", ids(rules.order([C(1, None), C(2, -2), C(3, 0)])) == [3, 2, 1])
trio = [C(1, 20), C(2, 15), C(3, 10)]
check("next turn: down the order, no new round", rules.next_turn(trio, 1) == (2, False) and rules.next_turn(trio, 2) == (3, False))
check("next turn: after the last comes the first, and a new round", rules.next_turn(trio, 3) == (1, True))
check("next turn: the dead are skipped", rules.next_turn([C(1, 20), C(2, 15, dead=True), C(3, 10)], 1) == (3, False))
check("next turn: skipping a dead first combatant still counts the round", rules.next_turn([C(1, 20, dead=True), C(2, 15), C(3, 10)], 3) == (2, True))
check("next turn: the only one left goes again, each time a new round", rules.next_turn([C(1, 20), C(2, 15, dead=True)], 1) == (1, True))
check("next turn: nobody alive, nobody acts", rules.next_turn([C(1, 20, dead=True)], 1) == (None, False))
D = rules.death_save
check("death save: a pass, a fail", D(0, 0, True) == (1, 0, None) and D(1, 0, False) == (1, 1, None))
check("death save: the third pass is stable", D(2, 2, True) == (3, 2, "stable"))
check("death save: the third fail is dead", D(2, 2, False) == (2, 3, "dead"))
check("death save: a 1 is two fails", D(0, 0, False, 1) == (0, 2, None) and D(1, 1, False, 1) == (1, 3, "dead"))
check("death save: a 20 is back up, whatever the count", D(2, 2, True, 20) == (0, 0, "up"))
check("names: generic enemies are numbered", rules.numbered([], "Goblin", 3) == ["Goblin 1", "Goblin 2", "Goblin 3"])
check("names: numbering carries on from the ones already there", rules.numbered(["Goblin 1", "Goblin 4", "Wolf 9"], "Goblin", 2) == ["Goblin 5", "Goblin 6"])
check("names: a typed name stays as typed, unless taken", rules.numbered(["Wren"], "Ogre", 1, False) == ["Ogre"] and rules.numbered(["Ogre"], "Ogre", 1, False) == ["Ogre 2"])
check("fifteen condition names, no rules text with them", len(rules.CONDITIONS) == 15 and all(len(c) < 15 and " " not in c for c in rules.CONDITIONS))
check("seven prep steps", len(rules.PREP) == 7)

# ---------------------------------------------------------------- made-up characters
AB = {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 12, "cha": 8}
CHARS = paths.data("characters")
def make(name, player, cls, levels, edition, **ab):
    c = ch.new_character(name, player, cls, dict(AB, **ab), edition=edition)
    for _ in range(levels - 1): ch.level_up(c)
    c["ac"] = 15
    ch.save(c, CHARS)
    return c
make("Brakka", "Ethan", "Fighter", 3, "2024")            # 12, then 6+2 twice: 28
make("Wren", "Sam", "Wizard", 3, "2024", int=16)         # 8, then 4+2 twice: 20
make("Tam", "Priya", "Rogue", 5, "2014")                 # 10, then 5+2 four times: 38
up, _, _ = ch.from_fields({"CharacterName": "Dorn", "PlayerName": "Trevor", "ClassLevel": "Cleric 2", "Race": "Human",
                           "STR": "14", "DEX": "10", "CON": "13", "INT": "10", "WIS": "16", "CHA": "12", "HPMax": "15"})
ch.log(up, "Imported from Dorn.pdf"); ch.save(up, CHARS)
F = lambda name: ch.load(os.path.join(CHARS, name + ".json"))
check("the test party: 28, 20 and 38 hit points", (F("brakka")["hp"]["max"], F("wren")["hp"]["max"], F("tam")["hp"]["max"]) == (28, 20, 38))
check("an uploaded sheet waits to be checked; the made ones do not", [n for n, _ in party.waiting()] == ["dorn.json"] and [n for n, _ in party.party()] == ["brakka.json", "tam.json", "wren.json"])

# ---------------------------------------------------------------- the tracker's rules
class Clock:
    def __init__(self): self.t = 1_000_000.0
    def __call__(self): return self.t
clock = Clock()
folder = paths.data("sessions")
s = engine.Session(dnd, ["Ethan", "Sam", "Priya", "Trevor"], {"edition": "2024"}, folder, clock)
st = lambda: s.state
def who(name): return next(c for c in s.state["combatants"] if c["name"] == name)
def W(name): return who(name)["id"]
names = lambda: [c["name"] for c in dnd.order(s.state)]
check("a new fight has the party in it already, linked to their files and seats",
      [(c["name"], c["seat"], c["hp"], c["file"]) for c in st()["combatants"]] == [("Brakka", 0, 28, "brakka.json"), ("Tam", 2, 38, "tam.json"), ("Wren", 1, 20, "wren.json")], st()["combatants"])
check("the unchecked upload is not in it", "Dorn" not in names())
check("edition defaults to 2024 and is a setup option", st()["edition"] == "2024" and dnd.options[0]["choices"] == ["2024", "2014"])
check("before the fight: no round, nobody's turn, phase 'setup'", (st()["fight"], st()["round"], dnd.active(st()), dnd.phase(st())) == (False, 0, None, "setup") and dnd.strip(s) == ("D&D", "Before the fight"))
said = s.do(ev="next")
check("the fight cannot start until everyone has an initiative", "no initiative" in said[0] and "Brakka" in said[0] and not st()["fight"] and len(s.log) == 0, said)
s.do(ev="init", who=W("Brakka"), value=17); s.do(ev="init", who=W("Tam"), value=17); s.do(ev="init", who=W("Wren"), value=11)
s.do(ev="add", kind="enemy", base="Goblin boss", count=1, init=14, numbered=False)
s.do(ev="add", kind="enemy", base="Goblin", count=2, init=8)
check("initiative order, with the 17s tied in joining order", names() == ["Brakka", "Tam", "Goblin boss", "Wren", "Goblin 1", "Goblin 2"], names())
s.do(ev="tie", who=W("Tam"))
check("Wins ties puts Tam ahead of Brakka", names() == ["Tam", "Brakka", "Goblin boss", "Wren", "Goblin 1", "Goblin 2"], names())
check("initiative outside -10 to 50 is refused", "between" in s.do(ev="init", who=W("Wren"), value=99)[0] and who("Wren")["init"] == 11)
said = s.do(ev="next")
check("starting: round 1, Tam is up, Priya's seat is active", said == ["Round 1.", "Tam is up."] and st()["round"] == 1 and s.active_name() == "Priya" and dnd.phase(st()) == "turn", said)
check("the strip says round 1", dnd.strip(s) == ("D&D · Round 1", "Initiative"))
s.add_reminder(1, "turn", "Check concentration")
said = s.do(ev="next"); check("next turn: Brakka", said == ["Brakka is up."] and s.active_name() == "Ethan", said)
said = s.do(ev="next"); check("an enemy's turn belongs to no seat", said == ["Goblin boss is up."] and dnd.active(st()) is None, said)
said = s.do(ev="next")
check("a player's start-of-turn reminder is said when their character is up", said == ["Wren is up.", "Reminder for Sam: Check concentration"], said)
s.do(ev="next"); s.do(ev="next")
check("the last in the order: still round 1", st()["turn"] == W("Goblin 2") and st()["round"] == 1)
said = s.do(ev="next")
check("after the last turn comes round 2", said == ["Round 2.", "Tam is up."] and st()["round"] == 2, said)
check("undo steps back into round 1", s.undo() and st()["round"] == 1 and st()["turn"] == W("Goblin 2"))
s.do(ev="next")
check("phases a reminder can hang off", dnd.phases() == [("turn", "Start of turn"), ("setup", "Before the fight")])
check("the button means next", dnd.press(st()) == {"ev": "next"})
check("an unknown event is refused", "do not know" in s.do(ev="dance")[0])

# concentration
boss = W("Goblin boss")
s.do(ev="conc", who=boss, on=True)
for dmg in (1, 19, 20, 21, 22, 45):
    said = s.do(ev="damage", who=boss, amount=dmg)
check("damage to a concentrating combatant asks for a Constitution save each time: DCs 10, 10, 10, 10, 11, 22",
      [p["dc"] for p in st()["prompts"]] == [10, 10, 10, 10, 11, 22] and said == ["Goblin boss was concentrating: Constitution save, DC 22."], (st()["prompts"], said))
check("an enemy's damage is only a running total", who("Goblin boss")["hurt"] == 128 and not who("Goblin boss")["dead"])
said = s.do(ev="conc_save", who=boss, passed=True)
check("a save that holds clears one prompt and keeps the spell", len(st()["prompts"]) == 5 and who("Goblin boss")["conc"] and said == [], said)
said = s.do(ev="conc_save", who=boss, passed=False)
check("a save that fails ends concentration and the other prompts", st()["prompts"] == [] and not who("Goblin boss")["conc"] and said == ["Goblin boss loses concentration."], said)
check("no save waiting, no answer taken", "no concentration save" in s.do(ev="conc_save", who=boss, passed=True)[0])
check("damage of nothing is refused", "between 1 and 999" in s.do(ev="damage", who=boss, amount=0)[0])

# temporary hit points, write-through, undo
s.do(ev="temp", who=W("Brakka"), amount=5)
check("temporary hit points are written to the character file", F("brakka")["hp"]["temp"] == 5 and who("Brakka")["temp"] == 5)
said = s.do(ev="damage", who=W("Brakka"), amount=8)
check("8 damage with 5 temporary: temporary gone, 28 becomes 25", (who("Brakka")["hp"], who("Brakka")["temp"]) == (25, 0) and said == [], (who("Brakka"), said))
check("the damage is in the character file", (F("brakka")["hp"]["current"], F("brakka")["hp"]["temp"]) == (25, 0), F("brakka")["hp"])
check("undo puts the tracker and the file back: 28 and 5 temporary", s.undo() and (who("Brakka")["hp"], who("Brakka")["temp"]) == (28, 5) and (F("brakka")["hp"]["current"], F("brakka")["hp"]["temp"]) == (28, 5), F("brakka")["hp"])
s.do(ev="damage", who=W("Brakka"), amount=8)

# down, death saves
wren = W("Wren")
s.do(ev="conc", who=wren, on=True)
said = s.do(ev="damage", who=wren, amount=9)
check("Wren, concentrating, takes 9: 11 left, save DC 10", who("Wren")["hp"] == 11 and st()["prompts"] == [{"who": wren, "dc": 10, "damage": 9}] and said == ["Wren was concentrating: Constitution save, DC 10."], said)
check("her phone shows the save that is waiting", "Constitution save, DC 10, to keep concentrating." in dnd.phone(s, 1)["lines"])
s.do(ev="conc_save", who=wren, passed=True)
said = s.do(ev="damage", who=wren, amount=15)
check("15 more: Wren is down at 0, and concentration ends with no save asked",
      who("Wren")["hp"] == 0 and dnd.down(who("Wren")) and not who("Wren")["dead"] and not who("Wren")["conc"] and st()["prompts"] == []
      and said == ["Wren is down, at 0 hit points. Death saves start next turn.", "Concentration ends."], said)
check("down: the file says 0 and she is marked Unconscious", F("wren")["hp"]["current"] == 0 and who("Wren")["cond"] == ["Unconscious"])
ph = dnd.phone(s, 1)
check("a downed player's phone offers the death saves", "Down. Death saves: 0 passed, 0 failed." in ph["lines"] and {"Death save passed", "Death save failed"} <= {a["label"] for a in ph["actions"]}, ph)
said = s.do(ev="save", who=wren, passed=True)
check("death save passed: 1 and 0", who("Wren")["saves"] == [1, 0] and said == ["Wren: death saves, 1 passed, 0 failed."], said)
s.do(ev="save", who=wren, passed=False)
said = s.do(ev="damage", who=wren, amount=3)
check("damage at 0 hit points is a failed death save: 1 and 2", who("Wren")["saves"] == [1, 2] and "2 of 3" in said[0] and not who("Wren")["dead"], said)
said = s.do(ev="heal", who=wren, amount=4)
check("any healing wakes her: 4 hit points, saves wiped, no longer Unconscious",
      who("Wren")["hp"] == 4 and who("Wren")["saves"] == [0, 0] and who("Wren")["cond"] == [] and F("wren")["hp"]["current"] == 4 and said == ["Wren is back up, on 4 hit points."], said)
s.do(ev="damage", who=wren, amount=4)
s.do(ev="save", who=wren, passed=True); s.do(ev="save", who=wren, passed=True)
said = s.do(ev="save", who=wren, passed=True)
check("three passes: stable, still at 0", who("Wren")["stable"] and who("Wren")["hp"] == 0 and not who("Wren")["dead"] and "stable" in said[0], said)
n = len(s.log)
check("a stable character makes no more death saves", "not making death saves" in s.do(ev="save", who=wren, passed=True)[0] and len(s.log) == n)
s.do(ev="damage", who=wren, amount=1)
check("hurt while stable: dying again, a fresh count with one fail", not who("Wren")["stable"] and who("Wren")["saves"] == [0, 1], who("Wren"))
said = s.do(ev="save", who=wren, passed=False, nat=1)
check("a 1 is two fails; with the one before, that is three: dead", who("Wren")["dead"] and who("Wren")["saves"] == [0, 3] and said == ["That is three failed death saves. Wren is dead."], said)
check("the dead cannot be healed or hurt", "dead" in s.do(ev="heal", who=wren, amount=5)[0] and "past caring" in s.do(ev="damage", who=wren, amount=5)[0] and F("wren")["hp"]["current"] == 0)
s.do(ev="next"); s.do(ev="next"); s.do(ev="next")
check("the dead are skipped in the order: Tam, Brakka, the boss, then Goblin 1", st()["turn"] == W("Goblin 1") and st()["round"] == 2, st()["turn"])
s.do(ev="revive", who=wren)
said = s.do(ev="save", who=wren, passed=True, nat=20)
check("brought back by the DM, then a 20: up on 1 hit point", who("Wren")["hp"] == 1 and F("wren")["hp"]["current"] == 1 and not dnd.down(who("Wren")) and said == ["A 20. Wren is back, on 1 hit point."], said)

# instant death
tam = W("Tam")
said = s.do(ev="damage", who=tam, amount=75)
check("75 damage to 38 hit points: 37 left over, one short of the maximum, so only down", dnd.down(who("Tam")) and not who("Tam")["flag"] and not who("Tam")["dead"], said)
check("undo that: 38 again, in the file too", s.undo() and who("Tam")["hp"] == 38 and F("tam")["hp"]["current"] == 38)
said = s.do(ev="damage", who=tam, amount=76)
check("76 damage: 38 left over equals the maximum. Flagged as death outright, for the DM to confirm",
      who("Tam")["flag"] and not who("Tam")["dead"] and who("Tam")["hp"] == 0 and "death outright" in said[0] and "DM decides" in said[0], said)
said = s.do(ev="confirm", who=tam, dead=False)
check("the DM says no: Tam is only down", not who("Tam")["flag"] and not who("Tam")["dead"] and dnd.down(who("Tam")) and said == ["Tam is down, not dead."], said)
said = s.do(ev="damage", who=tam, amount=38)
check("38 damage while at 0 is the whole maximum again: flagged again, no death save counted", who("Tam")["flag"] and who("Tam")["saves"] == [0, 0] and "was at 0" in said[0], said)
s.do(ev="confirm", who=tam, dead=True)
check("the DM confirms: dead", who("Tam")["dead"] and not who("Tam")["flag"])
check("nothing left to confirm", "waiting on the DM" in s.do(ev="confirm", who=tam, dead=True)[0])
s.do(ev="revive", who=tam); s.do(ev="heal", who=tam, amount=10)
check("healing never goes over the maximum", (s.do(ev="heal", who=W("Brakka"), amount=500), who("Brakka")["hp"], F("brakka")["hp"]["current"])[1:] == (28, 28))
s.do(ev="damage", who=W("Brakka"), amount=3)

# enemies
g1 = W("Goblin 1")
s.do(ev="sethp", who=g1, max=6)
said = s.do(ev="damage", who=g1, amount=5)
check("an enemy with 6 hit points takes 5: nothing said, not defeated", said == [] and not who("Goblin 1")["dead"])
said = s.do(ev="damage", who=g1, amount=1)
check("one more: defeated", said == ["Goblin 1 is defeated."] and who("Goblin 1")["dead"], said)
s.do(ev="revive", who=g1)
check("a character's hit points cannot be set from the tracker", "sheet" in s.do(ev="sethp", who=tam, max=99)[0])
check("conditions are toggled by name; unknown ones refused", s.do(ev="cond", who=W("Brakka"), name="Poisoned") == [] and who("Brakka")["cond"] == ["Poisoned"] and "do not know that condition" in s.do(ev="cond", who=W("Brakka"), name="Sleepy")[0])
check("adding mid-fight needs an initiative", "needs an initiative" in s.do(ev="add", kind="enemy", base="Rat", count=1)[0])
check("no more than eight at once", "at a time" in s.do(ev="add", kind="enemy", base="Rat", count=9, init=3)[0])
check("a character cannot be added twice, nor an unchecked sheet at all",
      "already in the fight" in s.do(ev="add_char", file="tam.json", init=3)[0] and "not been checked" in s.do(ev="add_char", file="dorn.json", init=3)[0])

# hidden combatants, the scoreboard and the phones
s.do(ev="add", kind="enemy", base="Wolf", count=1, numbered=False, init=30, hp=437, hidden=True)
wolf = W("Wolf")
row = lambda name, value="": {"name": name, "value": value, "out": False}
board = dnd.scoreboard(s)
check("scoreboard: initiative order and whose turn, nothing else",
      board == {"rows": [row("Tam"), row("Brakka"), row("Goblin boss"), row("Wren"), row("Goblin 1", "Now"), row("Goblin 2")], "note": "Round 2, initiative order"}, board)
s.do(ev="next")
said = s.do(ev="next")
check("the hidden wolf's turn: the round is called, the wolf is not", st()["turn"] == wolf and said == ["Round 3."] and dnd.active(st()) is None, said)
board = dnd.scoreboard(s)
check("scoreboard on a hidden turn: no wolf, and nobody marked", [r["name"] for r in board["rows"]] == ["Tam", "Brakka", "Goblin boss", "Wren", "Goblin 1", "Goblin 2"] and not any(r["value"] for r in board["rows"]), board)
check("a phone on a hidden turn says the round and no name", dnd.phone(s, 0)["lines"][-1] == "Round 3.")
check("damage to a hidden combatant is not announced", s.do(ev="damage", who=wolf, amount=5) == [] and who("Wolf")["hurt"] == 5)
s.do(ev="conc", who=wolf, on=True)
check("nor is its concentration save, though the DM's prompt is kept", s.do(ev="damage", who=wolf, amount=30) == [] and st()["prompts"] == [{"who": wolf, "dc": 15, "damage": 30}] and s.do(ev="conc_save", who=wolf, passed=False) == [])
s.do(ev="next")
def public():
    return json.dumps([dnd.scoreboard(s), [dnd.phone(s, i) for i in range(-1, 5)], dnd.standings(s.state, s.players), dnd.strip(s)])
dump = public()
check("nothing public mentions the hidden wolf, its 437 hit points, the boss's 128 damage, or the prep list",
      not any(x in dump for x in ("Wolf", "437", "128", "402", "prep", "Recap", "hurt", "hidden")), dump)
ph = dnd.phone(s, 2)
check("Tam's phone, on Tam's turn: own hit points, damage, healing, end turn",
      ph["lines"] == ["Tam: 10 of 38 hit points", "Round 3. Tam's turn."] and [a["label"] for a in ph["actions"]] == ["Damage 1", "Damage 5", "Damage 10", "Heal 1", "Heal 5", "Heal 10", "End my turn"], ph)
ph0 = dnd.phone(s, 0)
check("Brakka's phone: hit points and conditions, no end-turn button on someone else's turn",
      ph0["lines"] == ["Brakka: 25 of 28 hit points", "Conditions: Poisoned", "Round 3. Tam's turn."] and "End my turn" not in [a["label"] for a in ph0["actions"]], ph0)
check("phone actions only ever touch the player's own character", all(a["ev"].get("who", W("Brakka")) == W("Brakka") for a in ph0["actions"]))
s.do(**next(a["ev"] for a in ph0["actions"] if a["label"] == "Damage 5"))
check("Damage 5 from the phone: 20 on the tracker and in the file", who("Brakka")["hp"] == 20 and F("brakka")["hp"]["current"] == 20)
check("a seat with no character sees no hit points and gets no buttons", dnd.phone(s, 3) == {"lines": ["No character of yours is in the fight.", "Round 3. Tam's turn."], "actions": []}, dnd.phone(s, 3))
s.do(**ph["actions"][-1]["ev"])
check("End my turn from Tam's phone passes to Brakka", st()["turn"] == W("Brakka"))
s.do(ev="next")
s.do(ev="remove", who=boss)
check("removing whoever's turn it is passes the turn on", "Goblin boss" not in names() and st()["turn"] == W("Wren") and st()["round"] == 3)
check("removing someone twice is refused", "left the fight" in s.do(ev="remove", who=boss)[0])

# the end of a fight, and a long rest
check("no long rest mid-fight", "End the fight first" in s.do(ev="rest")[0])
s.do(ev="add", kind="ally", base="Guide", count=1, numbered=False, init=5)
said = s.do(ev="end")
check("ending the fight: enemies go, hidden ones too; the party and allies stay, initiative wiped",
      said == ["The fight is over, after 3 rounds."] and [c["name"] for c in st()["combatants"]] == ["Brakka", "Tam", "Wren", "Guide"]
      and all(c["init"] is None for c in st()["combatants"]) and (st()["fight"], st()["round"], st()["turn"]) == (False, 0, None), (said, st()))
for name, spent, used in (("brakka", 2, [1]), ("tam", 4, []), ("wren", 0, [2, 1])):
    c = F(name); c["hit_dice_spent"], c["slots_used"] = spent, used; ch.save(c, CHARS)
s.do(ev="temp", who=W("Brakka"), amount=3)
said = s.do(ev="rest")
check("long rest: said plainly, with what each edition does to hit dice",
      said == ["A long rest. Hit points and spell slots are back.", "Hit dice: all back for Brakka and Wren (2024 rules), half back for Tam (2014 rules)."], said)
check("long rest, 2024 character: full hit points, no temporary ones, every hit die and slot back",
      (F("brakka")["hp"]["current"], F("brakka")["hp"]["temp"], F("brakka")["hit_dice_spent"], F("brakka")["slots_used"]) == (28, 0, 0, []), F("brakka")["hp"])
check("long rest, 2014 character at level 5: 4 hit dice spent, 2 come back, 2 still spent", (F("tam")["hp"]["current"], F("tam")["hit_dice_spent"]) == (38, 2), F("tam")["hit_dice_spent"])
check("long rest: the tracker's copy matches", [(c["hp"], c["temp"]) for c in st()["combatants"][:3]] == [(28, 0), (38, 0), (20, 0)] and F("wren")["slots_used"] == [])
check("long rest: the unchecked upload is left alone", not any("Long rest" in h["what"] for h in F("dorn")["history"]))
check("long rest is recorded in each character's history", F("tam")["history"][-1]["what"] == "Long rest")
check("D&D has no winner", dnd.over(st()) is None and dnd.leader(st()) is None and s.finished is None)
again = engine.Session.load(s.path, plugins, clock)
check("a saved fight loads back exactly", again.state == s.state)
s.finish()
check("ended from the menu: no winner, and the record shows only the party", s.finished["winner"] is None and s.finished["lines"] == ["Stopped between fights", "Brakka 28/28, Tam 38/38, Wren 20/20"], s.finished)

s2 = engine.Session(dnd, ["A", "B"], {"edition": "2014"}, None, clock)
check("a new session reads hit points from the files; nobody at this table owns the characters", [(c["hp"], c["seat"]) for c in s2.state["combatants"]] == [(28, None), (38, None), (20, None)])
s2.do(ev="load", enemies=[{"name": "Orc", "count": 2, "hp": 15}, {"name": "Ogre", "count": 1}], hidden=True)
loaded = s2.state["combatants"][3:]
check("the fight loader: named enemies, numbered when several, hidden, hit points kept",
      [(c["name"], c["hidden"], c["max"], c["init"]) for c in loaded] == [("Orc 1", True, 15, None), ("Orc 2", True, 15, None), ("Ogre", True, None, None)], loaded)
check("loaded enemies are on no scoreboard", [r["name"] for r in dnd.scoreboard(s2)["rows"]] == ["Brakka", "Tam", "Wren"])
said = s2.do(ev="next")
check("a hidden combatant with no initiative is not named when the start is refused", said == ["Brakka has no initiative yet. Tap the name to enter it."], said)
for c in s2.state["combatants"]: s2.do(ev="init", who=c["id"], value=10)
ogre = s2.state["combatants"][-1]["id"]
s2.do(ev="conc", who=ogre, on=True); s2.do(ev="damage", who=ogre, amount=80)
check("a 2014 table: 80 damage is DC 40", s2.state["prompts"][0]["dc"] == 40)
s2.do(ev="next")
check("no loading a second fight in the middle of one", "End this fight" in s2.do(ev="load", enemies=[{"name": "Rat"}])[0])
s2.do(ev="prep", i=2)
check("prep ticks live in the session, so a new session starts with none", s2.state["prep"][2] and not any(engine.Session(dnd, ["A", "B"], {}, None, clock).state["prep"]))
c = F("brakka"); c["hp"]["current"] = 9; ch.save(c, CHARS)
n_log, n_undo = len(s2.log), len(s2.d["undo"])
check("a sheet changed elsewhere is noticed and read again", dnd.stale(s2.state) and dnd.resync(s2) is True and s2.state["combatants"][0]["hp"] == 9 and not dnd.stale(s2.state) and dnd.resync(s2) is False)
check("reading a sheet again is not an event: nothing in the log, nothing more to undo", (len(s2.log), len(s2.d["undo"])) == (n_log, n_undo) and "do not know" in s2.do(ev="sync")[0])
c["hp"]["current"] = 28; ch.save(c, CHARS)

# ---------------------------------------------------------------- the campaign file
check("campaign files are copied into the data folder on first use", dm.files() == ["dragon-of-icespire-peak.json"] and os.path.isfile(os.path.join(paths.data("campaigns"), "dragon-of-icespire-peak.json")))
camp = dm.load(dm.current())
check("the copy reads as a campaign: people, quests, no sessions yet", len(camp["people"]) == 17 and len(camp["quests"]) == 14 and camp["sessions"] == [])
check("recap with no log says so", dm.recap(camp, "x")[0] == "No log yet" and dm.session_number(camp, "x") == 1)
camp["sessions"] = [{"n": 3, "date": "2026-11-13", "lines": ["They took the job.", "They owe the innkeeper."]}, {"n": 4, "started": "tonight", "lines": ["Tonight's line."]}]
check("recap is built from the last entry before tonight's", dm.recap(camp, "tonight") == ("Last time: session 3 (2026-11-13)", "They took the job.\nThey owe the innkeeper."), dm.recap(camp, "tonight"))
check("tonight is the session after it", dm.session_number(camp, "tonight") == 4 and dm.session_number(camp, "another night") == 5)
check("log entries typed as plain text are read too", dm.entry_lines("One line.") == ["One line."] and dm.entry_lines({"summary": "A.\nB."}) == ["A.", "B."])

# ---------------------------------------------------------------- the DM's tools: the sums and the file
import random
from deepthought import dice
from deepthought.games.dnd import dmdata, improv
class Fixed:
    """A stand-in for random: every die shows n, every choice is the first."""
    def __init__(self, n=1): self.n = n
    def randint(self, a, b): return max(a, min(b, self.n))
    def choice(self, seq): return seq[0]
ship = json.loads(shipped_before.decode("utf-8"))
check("the shipped dragon table is an empty slot: twenty rolls, no words, for the owner to fill from his own booklet",
      sorted(ship["fixed_results"]["dragon_table"]["value"], key=int) == [str(n) for n in range(1, 21)] and all(v is None for v in ship["fixed_results"]["dragon_table"]["value"].values()))
check("the shipped file has a calendar, an empty treasure list, a purse of nothing and no other tables", ship["calendar"] == {"day": 1, "date": "", "notes": []} and ship["treasure"] == [] and ship["party_coins"] == {"pp": 0, "gp": 0, "ep": 0, "sp": 0, "cp": 0} and ship["tables"] == {})
old = dmdata.tidy({"calendar": {"day": "soon", "notes": ["Rain.", {"text": " Fair. ", "day": 3}, {"text": ""}, 7]}, "treasure": ["A ring", {"name": "Rope", "holder": "Wren"}, {"holder": "x"}], "party_coins": {"gp": 12, "sp": -4, "cp": "lots"}})
check("an older or hand-edited file is tidied on loading: day 1, notes with days, items with holders, coins never negative",
      old["calendar"] == {"day": 1, "date": "", "notes": [{"day": 1, "text": "Rain."}, {"text": "Fair.", "day": 3}]} and old["treasure"] == [{"name": "A ring", "holder": None, "day": None}, {"name": "Rope", "holder": "Wren", "day": None}]
      and old["party_coins"] == {"pp": 0, "gp": 12, "ep": 0, "sp": 0, "cp": 0} and old["tables"] == {}, old)
check("a file with none of it loads with all of it", dmdata.tidy({})["calendar"] == {"day": 1, "date": "", "notes": []} and dmdata.tidy({})["treasure"] == [])
cal = dmdata.tidy({})
check("calendar: a day, a week, and never before day 1", dmdata.advance(cal, 1) == 2 and dmdata.advance(cal, 7) == 9 and dmdata.advance(cal, -30) == 1 and dmdata.day_words(cal) == "Day 1")
cal["calendar"].update(day=4, date="Market week")
dmdata.add_note(cal, " first  note "); dmdata.advance(cal, 2); dmdata.add_note(cal, "second"); dmdata.add_note(cal, "third")
check("calendar: a note is stamped with the day it was written", cal["calendar"]["notes"] == [{"day": 4, "text": "first note"}, {"day": 6, "text": "second"}, {"day": 6, "text": "third"}] and dmdata.day_words(cal) == "Day 6, Market week")
check("calendar: notes list newest first, and keep their place in the file", [(k, n["text"]) for k, n in dmdata.notes_newest(cal)] == [(2, "third"), (1, "second"), (0, "first note")])
try: dmdata.add_note(cal, "   "); empty_note = False
except ValueError: empty_note = True
check("calendar: an empty note is refused", empty_note and len(cal["calendar"]["notes"]) == 3)
check("treasure: an item is stamped with the day, held by nobody in particular", dmdata.add_item(cal, " silver  mirror ") == {"name": "silver mirror", "holder": None, "day": 6} and dmdata.holder_words(cal["treasure"][0]) == "With the party")
check("treasure: who holds it goes round the party and back to nobody", [dmdata.next_holder(x, ["Brakka", "Wren"]) for x in (None, "Brakka", "Wren", "Somebody gone")] == ["Brakka", "Wren", None, None])
check("coins: steps add up", dmdata.step_coin(cal, "gp", 10) == 10 and dmdata.step_coin(cal, "gp", 100) == 110 and dmdata.step_coin(cal, "gp", -1) == 109 and dmdata.step_coin(cal, "cp", 1) == 1 and dmdata.coins_words(cal) == "109 gold, 1 copper")
def refused(fn):
    try: fn(); return ""
    except ValueError as e: return str(e)
check("coins: never below nothing, and the purse is unchanged", refused(lambda: dmdata.step_coin(cal, "gp", -110)) == "Not enough gold: the party has 109." and cal["party_coins"]["gp"] == 109)
check("coins: an unknown coin is refused", "not a coin" in refused(lambda: dmdata.step_coin(cal, "zz", 1)))

empty_tables = dmdata.tables(dmdata.tidy(json.loads(shipped_before.decode("utf-8"))))
check("tables: the shipped file offers one table, the dragon's, a d20 with no rows, and says which field to fill",
      [(t["name"], t["die"], t["rows"], t["where"], t["dragon"]) for t in empty_tables] == [("Dragon", 20, [], "fixed_results.dragon_table.value", True)], empty_tables)
tc = dmdata.tidy({"fixed_results": {"dragon_table": {"value": {"1": "Made-up hill", "2": None, "3-5": "Made-up marsh", "20": "  "}}}, "dragon": {"last_roll": None, "current_location": None},
                  "tables": {"Weather": {"die": 8, "rows": [{"lo": 4, "hi": 8, "text": "Dry."}, {"lo": 1, "hi": 3, "text": "Rain."}, {"lo": 9, "text": ""}, "junk"]},
                             "Oddments": {"rows": [{"roll": 1, "text": "A boot."}, {"roll": 12, "text": "A bell."}]}, "Broken": 5}})
tabs = {t["name"]: t for t in dmdata.tables(tc)}
check("tables: the dragon slot's own shape is read, ranges and all; empty rows do not count", tabs["Dragon"]["rows"] == [{"lo": 1, "hi": 1, "text": "Made-up hill"}, {"lo": 3, "hi": 5, "text": "Made-up marsh"}] and tabs["Dragon"]["die"] == 20)
check("tables: any named table with a die and rows is offered, rows in order", list(tabs) == ["Dragon", "Weather", "Oddments"] and tabs["Weather"]["die"] == 8 and [r["text"] for r in tabs["Weather"]["rows"]] == ["Rain.", "Dry."] and tabs["Weather"]["where"] == "tables.Weather.rows")
check("tables: with no die given, the die is the highest row, or a d20", tabs["Oddments"]["die"] == 20 and tabs["Oddments"]["rows"][1] == {"lo": 12, "hi": 12, "text": "A bell."})
check("tables: a roll picks the row it lands in", dmdata.roll(tabs["Weather"], Fixed(3)) == (3, "Rain.") and dmdata.roll(tabs["Weather"], Fixed(4)) == (4, "Dry.") and dmdata.roll(tabs["Dragon"], Fixed(4)) == (4, "Made-up marsh"))
check("tables: a roll on a row with no words says so, and is still a roll", dmdata.roll(tabs["Dragon"], Fixed(2)) == (2, None) and dmdata.roll_line(tc, tabs["Dragon"], 2, None) == "Day 1. Dragon table, rolled 2: that row is empty in the file.")
seeded = [dmdata.roll(tabs["Dragon"], random.Random(5))[0] for _ in range(3)]
check("tables: a d20 is rolled by the shared dice module", seeded == [dice.roll(1, 20, random.Random(5))[0]] * 3 and all(1 <= dmdata.roll(tabs["Weather"], random.Random(k))[0] <= 8 for k in range(40)), seeded)
tc["calendar"]["day"] = 12
check("tables: the log line carries the in-world day", dmdata.roll_line(tc, tabs["Dragon"], 4, "Made-up marsh") == "Day 12. Dragon table, rolled 4: Made-up marsh")
dmdata.record_roll(tc, tabs["Weather"], 3, "Rain."); nothing = dict(tc["dragon"]); dmdata.record_roll(tc, tabs["Dragon"], 4, "Made-up marsh")
check("tables: only the dragon's table moves the dragon", nothing == {"last_roll": None, "current_location": None} and tc["dragon"] == {"last_roll": 4, "current_location": "Made-up marsh"})
lg = {"sessions": [{"n": 3, "lines": ["Old."]}]}
dm.log_line(lg, "tonight", "First."); dm.log_line(lg, "tonight", "Second.")
check("the log: a line is added to tonight's entry, which is made if need be", len(lg["sessions"]) == 2 and lg["sessions"][1]["n"] == 4 and lg["sessions"][1]["started"] == "tonight" and lg["sessions"][1]["lines"] == ["First.", "Second."] and lg["sessions"][0]["lines"] == ["Old."], lg)

# three numbers off a page. The creature and its numbers are made up for this test.
OLD_STYLE = "Zibblewock\nA made-up thing with too many elbows.\nArmor Class 13 (old coat)\nHit Points 27 (5d8 + 5)\nSpeed 30 ft.\nSTR DEX CON INT WIS CHA\n14 (+2) 12 (+1) 13 (+1) 6 (-2) 10 (+0) 7 (-2)\n"
NEW_STYLE = "Zibblewock\nAC 15   Initiative +3 (13)\nHP 45 (6d10 + 12)\nSpeed 40 ft.\nStr 16 +3 +3  Dex 17 +3 +3  Con 14 +2 +2"
check("a page in the older layout: Armour Class 13, 27 hit points, Dexterity 12 so +1", dmdata.stat_guess(OLD_STYLE) == {"ac": 13, "hp": 27, "dex": 12, "bonus": 1}, dmdata.stat_guess(OLD_STYLE))
check("a page in the newer layout: AC 15, 45 hit points, and the stated initiative of +3", dmdata.stat_guess(NEW_STYLE) == {"ac": 15, "hp": 45, "dex": 17, "bonus": 3}, dmdata.stat_guess(NEW_STYLE))
check("a low Dexterity is a minus", dmdata.stat_guess("Armour Class: 9\nHit points: 4\nDEX 7 (−2)")["bonus"] == -2 and dmdata.stat_guess("Initiative −1 (9)")["bonus"] == -1)
check("a page with no numbers gives none, so the DM types them", dmdata.stat_guess("The zibblewock is said to regain its temper slowly.") == {"ac": None, "hp": None, "dex": None, "bonus": None} and dmdata.stat_guess("") ["hp"] is None)
page = "Other Beast\nArmor Class 19\nHit Points 99\n\nThe zibblewock is mentioned here in passing.\n\n" + OLD_STYLE + "\nLater Beast\nArmor Class 5\n"
ex = dmdata.stat_excerpt(page, "zibblewock", span=120)
check("on a page with several creatures the excerpt starts at this one's own numbers", ex.startswith("Zibblewock A made-up thing") and dmdata.stat_guess(dmdata.stat_excerpt(page, "Zibblewock"))["ac"] == 13 and dmdata.stat_guess(dmdata.stat_excerpt(page, "Zibblewock"))["hp"] == 27, ex)
check("with the name nowhere on the page, the excerpt is the top of the page", dmdata.stat_excerpt("One  two\nthree", "Zibblewock") == "One two three")

# improvise, offline
a, b = improv.invent("name", random.Random(3)), improv.invent("name", random.Random(3))
check("an invented name: the same seed gives the same one, marked as from her own lists", a == b and a["source"] == "offline" and a["kind"] == "name" and len(a["title"].split()) == 2 and a["text"].endswith("."), a)
made = [improv.invent(k, random.Random(n)) for k in ("name", "shop", "rumour") for n in range(60)]
check("every invented thing has a title and a line that fit the screen", all(0 < len(m["title"]) <= improv.MAX_TITLE and 0 < len(m["text"]) <= improv.MAX_TEXT for m in made))
check("shops are called The Something Something; rumours are called A rumour", all(m["title"].startswith("The ") for m in made if m["kind"] == "shop") and all(m["title"] == "A rumour" for m in made if m["kind"] == "rumour"))
check("there is some variety in it", len({m["title"] for m in made if m["kind"] == "name"}) > 40 and len({m["text"] for m in made if m["kind"] == "rumour"}) > 40)
known = {w.lower() for p in ship["people"] for w in p["name"].split()} | {w.lower() for q in ship["quests"] for w in q["name"].split()}
words = {w.lower().strip(".,") for m in made for w in m["title"].split()} - {"the", "a", "of"}
check("none of the invented names is a name from the campaign file", not (words & known), words & known)
check("an unknown kind is treated as a name", improv.invent("spaceship", Fixed())["kind"] == "name")
got = improv.from_cloud("shop", "**The Tin Whistle**\n\nA pie shop kept by two brothers who disagree about salt.\n")
check("a cloud reply is read as a title and a line, and marked as the cloud's", got == {"kind": "shop", "title": "The Tin Whistle", "text": "A pie shop kept by two brothers who disagree about salt.", "source": "cloud"}, got)
check("a cloud rumour keeps only the rumour", improv.from_cloud("rumour", "A rumour\nSomeone has been feeding the crows on purpose.") == {"kind": "rumour", "title": "A rumour", "text": "Someone has been feeding the crows on purpose.", "source": "cloud"})
check("a long cloud reply is cut to fit", len(improv.from_cloud("name", "Somebody\n" + "word " * 80)["text"]) <= improv.MAX_TEXT)
check("an empty or one-line cloud reply is not used", improv.from_cloud("name", "") is None and improv.from_cloud("name", "   \n ") is None and improv.from_cloud("shop", "Only a name") is None)
check("the request to the cloud asks for invention and sends nothing from the campaign", "own invention" in improv.SYSTEM and "published" in improv.SYSTEM and not any(w in (improv.SYSTEM + " ".join(improv.ASK.values())).lower() for w in ("icespire", "phandalin", "harbin")))
kc = dmdata.tidy({"people": [], "calendar": {"day": 5}})
said = [improv.keep(kc, improv.invent("name", Fixed())), improv.keep(kc, improv.invent("shop", Fixed())), improv.keep(kc, improv.invent("rumour", Fixed()))]
check("keeping a name adds a person, marked invented in the file and in words", len(kc["people"]) == 1 and kc["people"][0]["invented"] is True and kc["people"][0]["role"].startswith("Invented. ") and kc["people"][0]["met"] is False and said[0] == "Kept in People, marked Invented.", kc["people"])
check("keeping a shop or a rumour adds a dated note that says Invented", [(n["day"], n["invented"], n["text"].split(":")[0]) for n in kc["calendar"]["notes"]] == [(5, True, "Invented shop"), (5, True, "Invented rumour")] and said[1] == "Kept as a note on day 5, marked Invented.", kc["calendar"]["notes"])

# ---------------------------------------------------------------- screens
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought.screens import common, extras
from deepthought.screens.home import Home
from deepthought.screens.lookup import Lookup
from deepthought.games.dnd import plugin as P, sheets as S, ui

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
    mine = type(screen).__module__.startswith("deepthought.games.dnd")      # one primary button on each of this plugin's screens
    if mine and sum(1 for w in screen.widgets if getattr(w, "style", "") == "primary") != 1: out.append(("primaries", [w.label for w in screen.widgets if getattr(w, "style", "") == "primary"]))
    app.render()
    return out
def tap(label):
    w = next(w for w in app.screen.widgets if w.action and w.label.startswith(label))
    app.toast = None
    w.action()
def has(label):
    return any(w.action and w.label.startswith(label) for w in app.screen.widgets)
def key(text):
    for chr_ in str(text): app.screen.type(chr_)
    app.screen.done()
seen = []
real_draw = T.draw_text
def spy(surf, text, *a, **k):
    seen.append(str(text))
    return real_draw(surf, text, *a, **k)
T.draw_text = spy
def drawn():
    """Every word the current screen puts on the glass, strip and toast included."""
    del seen[:]
    app.render()
    return " | ".join(seen)

setup = common.Setup(app, dnd); app.push(setup)
setup.n, setup.names[:4] = 4, ["Ethan", "Sam", "Priya", "Trevor"]; setup.refresh()
check("Set up fits, and offers the rules edition, 2024 first", screen_ok() == [] and setup.opts == {"edition": "2024"} and has("Rules: 2024"), screen_ok())
tap("Rules"); check("the edition button switches to 2014 and back", setup.opts["edition"] == "2014"); tap("Rules")
tap("How to play")
check("How to play: a round of combat, in her own words", isinstance(app.screen, common.Pages) and len(dnd.teach()) >= 8 and any("initiative" in x["title"].lower() for x in dnd.teach()) and screen_ok() == [])
tap("Back"); tap("Start game")
play, s = app.screen, app.session
who = lambda name: next(c for c in s.state["combatants"] if c["name"] == name)
W = lambda name: who(name)["id"]
check("Start game opens the tracker with the party in it", isinstance(play, P.Tracker) and [w.label for w in play.widgets[:3]] == ["Brakka", "Tam", "Wren"] and screen_ok() == [], screen_ok())
check("before the fight: plain strip, no turn pill, ring breathing", (play.left, play.title, play.pill) == ("D&D", "Before the fight", None) and app.hw._ring.now[0] == "breathe")
app.gesture("press")
check("the button will not start a fight with no initiative", not s.state["fight"] and "no initiative" in app.toast, app.toast)
tap("Brakka"); one = app.screen
check("tapping a name opens that combatant", isinstance(one, P.Combatant) and one.title == "Brakka, Fighter 3" and screen_ok() == [], screen_ok())
tap("Initiative"); pad = app.screen
check("the number pad fits", isinstance(pad, ui.NumberPad) and screen_ok() == [], screen_ok())
pad.type("9"); pad.type("9"); pad.done()
check("the pad refuses a number out of range and stays open", app.screen is pad and "between -10 and 50" in app.toast, app.toast)
pad.delete(); pad.delete(); pad.type("1"); pad.type("7"); app.toast = None; app.gesture("press")
check("typing 17 and pressing the button sets Brakka's initiative", who("Brakka")["init"] == 17 and app.screen is one and has("Initiative 17"))
tap("Initiative"); pad = app.screen
check("the pad opens on the number already there", pad.value() == 17)
pad.delete(); pad.delete(); pad.type("3"); tap("−")
check("the pad takes a negative initiative", app.screen.value() == -3 and screen_ok() == []); tap("Cancel")
tap("Back")
s.do(ev="init", who=W("Tam"), value=12); s.do(ev="init", who=W("Wren"), value=11)
tap("Add"); add = app.screen
check("Add fits", isinstance(add, P.AddCombatant) and screen_ok() == [], screen_ok())
tap("+"); tap("+"); tap("Goblin")
check("picking a name asks for initiative, which can wait until the fight starts", isinstance(app.screen, ui.NumberPad) and has("Enter it later") and screen_ok() == [], screen_ok())
key(8)
check("three goblins, numbered, sharing initiative 8, and back on the tracker", [c["name"] for c in s.state["combatants"][3:]] == ["Goblin 1", "Goblin 2", "Goblin 3"] and who("Goblin 3")["init"] == 8 and app.screen is play)
tap("Add"); tap("Type a name")
check("a name can be typed on the keyboard", isinstance(app.screen, common.TextEntry) and screen_ok() == [])
key("ogre"); tap("Enter it later")
check("a typed enemy keeps its name, with initiative still to come", who("Ogre")["init"] is None and app.screen is play)
tap("Add"); tap("Ally"); tap("Guide"); key(5)
check("an ally joins the same way", who("Guide 1")["kind"] == "ally" and who("Guide 1")["init"] == 5)
tap("Add"); tap("Character")
check("with the whole party in, there is no character left to add", not has("Brakka") and "already here" in drawn() and screen_ok() == [])
tap("Back")
check("eight combatants: two pages, a List button", has("List 1/2") and len([w for w in play.widgets if isinstance(w, ui.Row)]) == 4 and screen_ok() == [], screen_ok())
tap("List"); check("the second page shows the rest", [w.label for w in play.widgets if isinstance(w, ui.Row)] == ["Goblin 2", "Goblin 3", "Guide 1", "Ogre"] and screen_ok() == [])
tap("Ogre"); tap("Initiative"); key(20); tap("Back")
app.gesture("press")
check("the button starts the fight: round 1, the ogre first, its name in the pill", s.state["round"] == 1 and play.pill[0] == "Ogre's turn" and play.left == "D&D · Round 1" and "Ogre is up." in app.toast, (play.pill, app.toast))
app.toast = None; app.gesture("press")
check("the button is next turn: Brakka, with the ring in Ethan's colour", play.pill == ("Brakka's turn", T.player_colour(0)) and app.hw._ring.now == ("turn", {"colour": T.player_colour(0)}), play.pill)
app.gesture("press"); app.gesture("double")
check("double press: takes back its own press and one more turn", s.state["turn"] == W("Ogre") and s.state["round"] == 1, s.state["turn"])
app.gesture("press")
tap("Undo"); check("the Undo button steps back a turn", s.state["turn"] == W("Ogre")); app.gesture("press")
check("the current turn is the row with the thick edge", [w.label for w in play.widgets if isinstance(w, ui.Row) and w.selected] == ["Brakka"])
check("hint line names who is next", "Up next: Tam." in drawn())

def open_row(name):
    """Tap a combatant's row on the tracker, turning to its page first."""
    i = [c["name"] for c in play.shown()].index(name)
    play.page = i // 4; play.refresh(); tap(name)

open_row("Brakka"); one = app.screen
tap("Start concentrating")
check("concentration can be switched on from the combatant screen", who("Brakka")["conc"] and has("Drop concentration") and "DC 10 or half the damage" in drawn())
tap("Condition"); cond = app.screen
check("the condition picker fits: fifteen names and concentration", isinstance(cond, P.Conditions) and len(cond.widgets) == 17 and screen_ok() == [], screen_ok())
tap("Prone"); tap("Poisoned"); tap("Poisoned")
check("tapping a condition puts it on; tapping again takes it off", who("Brakka")["cond"] == ["Prone"])
tap("Done"); tap("Damage")
check("Damage opens the number pad", isinstance(app.screen, ui.NumberPad) and app.screen.title == "Damage" and screen_ok() == [])
key(22); prompt = app.screen
check("22 damage to a concentrating character: the save prompt appears with DC 11", isinstance(prompt, P.ConcPrompt) and prompt.prompt["dc"] == 11 and who("Brakka")["hp"] == 6 and "DC 11" in drawn() and screen_ok() == [], screen_ok())
tap("Lost it")
check("Lost it: concentration ends, and back on Brakka's screen", not who("Brakka")["conc"] and s.state["prompts"] == [] and app.screen is one and "loses concentration" in app.toast)
tap("Heal"); key(10)
check("Heal: 6 becomes 16, in the file too", who("Brakka")["hp"] == 16 and F("brakka")["hp"]["current"] == 16)
tap("More"); more = app.screen
check("the combatant's More menu fits", isinstance(more, P.CombatantMore) and screen_ok() == [] and not has("Set hit points") and not has("Hide"), screen_ok())
tap("Temporary HP"); key(4)
check("temporary hit points set from the pad", who("Brakka")["temp"] == 4 and F("brakka")["hp"]["temp"] == 4 and app.screen is one)
tap("More"); tap("Open sheet")
check("Open sheet goes to the character sheet", isinstance(app.screen, S.Sheet) and screen_ok() == [], screen_ok())
tap("Back"); tap("Back")
s.do(ev="conc", who=W("Brakka"), on=True); s.do(ev="damage", who=W("Brakka"), amount=2)
play.refresh()
check("a save left waiting shows on the tracker in words, with its own button", has("Save DC 10") and "Brakka: Constitution save, DC 10" in drawn() and screen_ok() == [], screen_ok())
tap("Save DC"); app.gesture("press")
check("the button's answer to the prompt is Kept it", s.state["prompts"] == [] and who("Brakka")["conc"] and app.screen is play)

open_row("Wren"); one = app.screen; tap("Damage"); key(20)
check("Wren at 0: death save boxes and buttons appear", dnd.down(who("Wren")) and all(has(x) for x in ("Pass", "Fail", "A 1", "A 20")) and "Down" in drawn() and screen_ok() == [], screen_ok())
tap("Pass"); tap("Fail")
check("Pass and Fail count the boxes", who("Wren")["saves"] == [1, 1] and "1 of 3" in drawn())
tap("A 20")
check("A 20: back on 1 hit point, and the save buttons go away", who("Wren")["hp"] == 1 and not has("Pass") and screen_ok() == [])
tap("Damage"); key(21)
check("1 hit point, 21 damage: 20 left over equals her maximum. The players' screen says the DM decides, with no button for it",
      who("Wren")["flag"] and "The DM decides." in drawn() and not has("Confirm") and screen_ok() == [], drawn())
tap("Back")
check("the tracker row says so in words", "Dead? DM decides" in drawn())
open_row("Guide 1"); tap("More"); tap("Remove from fight")
check("Remove from fight takes the guide out and returns to the tracker", app.screen is play and not any(c["name"] == "Guide 1" for c in s.state["combatants"]))

# the DM's side of the same fight
s.do(ev="add", kind="enemy", base="Wolf", count=1, numbered=False, init=13, hp=437, hidden=True)
s.do(ev="sethp", who=W("Goblin 1"), max=6); s.do(ev="damage", who=W("Goblin 1"), amount=5)
play.refresh()
def all_pages():
    out = []
    for _ in range(3):
        out.append(drawn())
        if has("List"): tap("List")
    return " | ".join(out)
text = all_pages()
play.page = None; play.refresh()                        # Brakka (17) is up; the hidden wolf (13) is next, then Tam (12)
check("the players' hint skips the hidden wolf: up next is Tam", s.state["turn"] == W("Brakka") and "Up next: Tam." in drawn(), drawn())
app.dm = True
check("the DM's hint names the wolf", "Up next: Wolf." in drawn())
app.dm = False; play.refresh()
check("players' tracker: no hidden wolf, no enemy hit points", "Wolf" not in text and "437" not in text and "1/6" not in text and "Goblin 1" in text and "DM only" not in text, text)
open_row("Goblin 1")
check("players' view of an enemy: no numbers", "The DM keeps count." in drawn() and "1 / 6" not in drawn() and screen_ok() == [])
tap("Back")
app.push(P.Combatant(app, s, W("Wolf")))
check("a hidden combatant's own screen shows the players nothing", "Wolf" not in drawn() and len(app.screen.widgets) == 1 and screen_ok() == [], drawn())
tap("Back")
tap("DM")
check("DM asks for the code", isinstance(app.screen, common.TextEntry) and app.screen.title == "DM code")
key("1234")
check("the wrong code keeps DM mode locked", app.dm is False and "not the code" in app.toast and app.screen is play, app.toast)
tap("DM"); key("0000"); desk = app.screen
check("the right code opens the DM desk, and the strip says DM only", app.dm is True and isinstance(desk, dm.Desk) and desk.left == "D&D · DM only" and screen_ok() == [], screen_ok())
check("the desk: campaign name, session 1, and the six tiles", has("Dragon of Icespire Peak") and desk.title == "Session 1" and all(has(x) for x in ("Recap", "Prep", "Fights", "People", "Quests", "Log")))
tap("Back to the fight")
text = all_pages()
check("DM's tracker: DM only in the strip, the wolf marked Hidden, enemy hit points shown", play.left == "D&D · DM only" and "Wolf" in text and "Hidden" in text and "Enemy 1/6" in text and "Enemy 437/437" in text and screen_ok() == [], text)
check("the DM is told how many are hidden", "1 hidden from the players." in text)
check("even in DM mode the scoreboard and phones show none of it", not any(x in public() for x in ("Wolf", "437", "1/6")))
play.page = None; play.refresh()
open_row("Wren"); one = app.screen
check("the DM gets the two buttons for death outright", has("Confirm: dead") and has("Not dead") and screen_ok() == [], screen_ok())
tap("Not dead")
check("Not dead: Wren is down and making death saves", not who("Wren")["flag"] and dnd.down(who("Wren")) and has("Pass") and screen_ok() == [])
tap("Back"); open_row("Goblin 1"); tap("More")
check("the DM's More menu adds Hide and Set hit points", has("Hide from players") and has("Set hit points") and screen_ok() == [], screen_ok())
tap("Set hit points"); key(9)
check("Set hit points: 9, with 5 already taken", who("Goblin 1")["max"] == 9 and "4 / 9" in drawn())
tap("More"); tap("Hide from players")
check("Hide puts a combatant out of the players' sight", who("Goblin 1")["hidden"] and "Goblin 1" not in public())
tap("More"); tap("Show to players"); tap("Back")
tap("Add")
check("the DM's Add screen can add hidden enemies", has("Hidden: no") and screen_ok() == [])
tap("Hidden"); tap("Bandit"); key(2)
check("a hidden bandit joins", who("Bandit 1")["hidden"] and who("Bandit 1")["init"] == 2)

# DM desk
tap("DM desk"); desk = app.screen
tap("Page"); key(47)
check("the page stopped on is kept in the campaign file", dm.load(dm.current())["position"]["booklet_page"] == 47 and has("Page 47") and screen_ok() == [])
tap("Dragon of Icespire Peak")
check("tapping the campaign shows its notes, marked DM only", isinstance(app.screen, common.Pages) and app.screen.note == "DM only" and screen_ok() == [])
tap("Back"); tap("Recap")
check("recap with no log yet says so, and shows tonight's outline", isinstance(app.screen, common.Pages) and app.screen.pages[0][0] == "No log yet" and "Arrival" in app.screen.pages[-1][0] and screen_ok() == [], app.screen.pages)
tap("Back"); tap("Prep"); prep = app.screen
check("Prep: seven fixed steps and the campaign's own extra, all tickable", isinstance(prep, dm.Prep) and [w.label for w in prep.widgets[:7]] == rules.PREP and prep.widgets[7].label == "Roll for the dragon" and screen_ok() == [], screen_ok())
tap("Fights loaded"); tap("People skimmed"); tap("People skimmed")
check("a tick is a tick; a second tap unticks", s.state["prep"] == [False, False, True, False, False, False, False, False] and prep.widgets[2].tick is True)
tap("Back"); check("the desk counts the ticks", "1 of 8 done" in drawn())
tap("People"); people = app.screen
check("People: four to a page, with a List button", isinstance(people, dm.People) and len([w for w in people.widgets if isinstance(w, ui.Row)]) == 4 and has("List 1/5") and screen_ok() == [], screen_ok())
tap("List"); tap("List"); check("the list pages on", has("List 3/5") and screen_ok() == [])
first = people.widgets[0].label; people.widgets[0].action(); person = app.screen
check("a person's screen fits", isinstance(person, dm.Person) and first in drawn() and screen_ok() == [], screen_ok())
tap("Met"); tap("Attitude"); tap("Change note"); key("owes the party")
saved = next(p for p in dm.load(dm.current())["people"] if p["name"] == first)
check("met, attitude and a one-line note are written to the campaign file", (saved["met"], saved["attitude"], saved["your_note"]) == (True, "friendly", "Owes the party") and "Owes the party" in drawn(), saved)
tap("Back"); check("the list shows Met and the attitude as words", "Met" in drawn() and "Friendly" in drawn())
tap("Back"); tap("Quests"); quests = app.screen
check("Quests fits", isinstance(quests, dm.Quests) and has("Dwarven Excavation") and has("Party level 1") and screen_ok() == [], screen_ok())
tap("Dwarven Excavation"); quest = app.screen
check("a quest's screen fits and shows the file's own prompts", isinstance(quest, dm.Quest) and "Watch for:" in drawn() and screen_ok() == [], screen_ok())
tap("Status"); tap("Make it tonight")
saved = dm.load(dm.current())
check("status and tonight's quest are written to the campaign file", saved["quests"][0]["status"] == "posted" and saved["position"]["quest"] == "Dwarven Excavation" and has("Tonight's quest: yes"))
tap("Back"); check("the list marks tonight's quest in words", "Tonight" in drawn() and "posted" in drawn())
tap("Party level"); check("levelling the party asks first", app.screen.title == "Level the party?" and screen_ok() == [])
tap("Level 2")
check("Level 2 is written to the campaign file", dm.load(dm.current())["levelling"]["party_level"] == 2 and has("Party level 2"))
tap("Back")
check("nobody is below level 2, so the desk offers no level-up", not has("Level up"))
tap("Log"); log = app.screen
check("Log fits, empty", isinstance(log, dm.Log) and log.title == "Log: tonight" and "Nothing logged." in drawn() and not has("Show last time") and screen_ok() == [], screen_ok())
tap("Add a line"); key("the party met the ogre")
tap("Add a line"); key("nobody enjoyed it")
saved = dm.load(dm.current())["sessions"]
check("lines typed tonight make tonight's log entry", len(saved) == 1 and saved[0]["n"] == 1 and saved[0]["started"] == s.d["started"] and saved[0]["lines"] == ["The party met the ogre", "Nobody enjoyed it"], saved)
tap("Nobody enjoyed it")
check("tapping a line asks before removing it, and shows the line", isinstance(app.screen, common.Choice) and app.screen.title == "Remove this line?" and app.screen.text == "Nobody enjoyed it" and screen_ok() == [], app.screen.title)
app.gesture("press")
check("the button's own answer keeps the line", app.screen is log and dm.load(dm.current())["sessions"][0]["lines"] == ["The party met the ogre", "Nobody enjoyed it"])
tap("Nobody enjoyed it"); tap("Remove")
check("Remove takes the line out", app.screen is log and dm.load(dm.current())["sessions"][0]["lines"] == ["The party met the ogre"] and screen_ok() == [])
camp = dm.load(dm.current()); camp["sessions"].insert(0, {"n": 3, "date": "2026-11-13", "lines": ["They took the job.", "They lost the map."]}); dm.save(camp, dm.current())
log.reload(); log.refresh(); tap("Show last time")
check("last time's entry can be shown", log.title == "Log: last time" and has("They lost the map.") and screen_ok() == [])
tap("They lost the map."); tap("Remove")
check("and corrected before it is read out", dm.load(dm.current())["sessions"][0]["lines"] == ["They took the job."])
tap("Back"); tap("Recap")
check("the recap is last time's entry, not tonight's", app.screen.pages[0] == ("Last time: session 3 (2026-11-13)", ["They took the job."]), app.screen.pages[0])
check("nothing is read aloud unless the DM presses for it", app.toast is None or "took the job" not in app.toast)
tap("Back")

# book search, with a made-up campaign page
src = tempfile.mkdtemp()
os.makedirs(os.path.join(src, "mine", "dnd", "campaigns")); os.makedirs(os.path.join(src, "free", "dnd"))
open(os.path.join(src, "mine", "dnd", "campaigns", "Secret.md"), "w", encoding="utf-8").write("# The twist\n\nThe grobnar was the innkeeper all along.\n")
open(os.path.join(src, "free", "dnd", "Made Up Rules.md"), "w", encoding="utf-8").write("# Zibbles\n\nA grobnar rolls the zibble die.\n")
con = dt_content.connect(os.environ["DT_CONTENT_DB"]); dt_content.sync(con, src, log=lambda *a: None); con.close()
app.reload_library()
tap("Book search"); look = app.screen
check("Book search is the shared Lookup, on D&D", isinstance(look, Lookup) and look.game == "dnd" and screen_ok() == [])
look.run("grobnar")
check("in DM mode it finds the campaign page as well as the rules", len(look.results) == 2 and any("Secret" in r["title"] for r in look.results), look.results)
check("which is the same search the task names", look.results == app.library.search("grobnar", "dnd", dm=True))
look.open(next(r for r in look.results if "Secret" in r["title"]))
check("a campaign page opens marked DM only", app.screen.note == "DM only" and screen_ok() == [])
tap("Back"); tap("Back")

# the fight loader needs the fight to be over
tap("Fights"); loader = app.screen
check("the fight loader fits, empty", isinstance(loader, dm.FightLoader) and "Nobody lined up." in drawn() and screen_ok() == [], screen_ok())
tap("Load"); check("it will not load nothing", "Add an enemy first" in app.toast and app.screen is loader)
tap("Add enemy"); pick = app.screen
check("its enemy picker fits: names and a count, no kinds", isinstance(pick, P.AddCombatant) and not has("Ally") and not has("Hidden") and screen_ok() == [], screen_ok())
tap("+"); tap("Orc")
check("then it asks for hit points, which the DM may leave out", isinstance(app.screen, ui.NumberPad) and app.screen.title == "Hit points each" and has("No number") and screen_ok() == [])
key(15)
tap("Add enemy"); tap("Type a name"); key("troll king"); tap("No number")
check("two lines are lined up: two orcs with 15 each, and a typed name", loader.draft == [{"name": "Orc", "count": 2, "hp": 15}, {"name": "Troll King", "count": 1, "hp": None}] and has("Load 3") and screen_ok() == [], loader.draft)
tap("Load 3")
check("no loading mid-fight", "End this fight" in app.toast and app.screen is loader)
s.do(ev="end"); app.toast = None
tap("Load 3")
check("after the fight they load: hidden, named, numbered, hit points kept, and back at the desk",
      [(c["name"], c["hidden"], c["max"]) for c in s.state["combatants"][-3:]] == [("Orc 1", True, 15), ("Orc 2", True, 15), ("Troll King", True, None)] and isinstance(app.screen, dm.Desk) and "3 loaded" in app.toast, s.state["combatants"][-3:])
app.push(dm.FightLoader(app, s)); tap("Hidden")
check("the loader can also load in plain sight", has("Hidden: no")); tap("Back")
camp = dm.load(dm.current()); camp["fights"] = [{"name": "The bridge", "enemies": [{"name": "Bandit", "count": 3, "hp": 8}]}]; dm.save(camp, dm.current())
app.push(dm.FightLoader(app, s))
check("fights written into the campaign file are offered", has("Saved 1") and screen_ok() == [], screen_ok())
tap("Saved"); check("and fill the list in one tap", app.screen.draft == [{"name": "Bandit", "count": 3, "hp": 8}])
tap("Back")

# ---- the DM's tools: Improvise, Calendar, Treasure, Tables, monsters from the loaded books
from deepthought.games.dnd import dmtools
from deepthought.library import Library
class StandIn:
    """Stands in for the voice: records what would be spoken, and answers as the cloud model."""
    def __init__(self): self.spoken, self.reply, self.on, self.asked = [], "", True, []
    def say(self, text, show=True): self.spoken.append(text)
    def _llm(self):
        def llm(system, user):
            self.asked.append((system, user))
            if isinstance(self.reply, Exception): raise self.reply
            return self.reply
        return llm if self.on else None
def later():
    for job in app.jobs(): job()
real_background = dmtools.background
dmtools.background = lambda fn: fn()                 # no threads in the tests: the answer arrives at once
cur = lambda: dm.load(dm.current())
desk = app.screen
check("the desk has a second page of tiles for the tools", isinstance(desk, dm.Desk) and has("More 1/2") and not has("Improvise"))
tap("More")
check("More shows Improvise, Calendar, Treasure and Tables, and fits", all(has(x) for x in ("Improvise", "Calendar", "Treasure", "Tables", "More 2/2", "Back to the fight", "Lock")) and not has("Recap") and screen_ok() == [], screen_ok())
check("the tool tiles say where things stand", all(x in drawn() for x in ("Day 1", "0 items", "Dragon: not copied in")), drawn())

# Improvise
tap("Improvise"); imp = app.screen
text = drawn()
check("Improvise fits and shows one invented name at once, with no cloud", isinstance(imp, dmtools.Improvise) and imp.item["kind"] == "name" and imp.item["title"] in text and screen_ok() == [] and not has("Ask the cloud"), screen_ok())
check("it is labelled as invented, in words", "INVENTED" in text and "by me, from my own word lists" in text and "Not from any book." in text, text)
imp.rng = random.Random(11); first = imp.item
app.gesture("press")
check("the button gives another", imp.item != first and imp.item["source"] == "offline" and app.screen is imp)
n_people = len(cur()["people"])
tap("Keep"); kept = cur()["people"][-1]
check("Keep writes the name into the campaign file's people, marked invented", len(cur()["people"]) == n_people + 1 and kept["name"] == imp.item["title"] and kept["invented"] is True and kept["role"] == "Invented. " + imp.item["text"] and has("Kept") and "marked Invented" in app.toast and screen_ok() == [], kept)
tap("Kept"); check("keeping twice keeps once", len(cur()["people"]) == n_people + 1 and "Already kept" in app.toast)
check("the screen promises that a double press takes the keep back", "Double press takes it back." in drawn())
shown = imp.item
app.gesture("press"); between = imp.item; app.gesture("double")       # as the button sends it: a press, then the double
check("a real double press takes the keep back, puts back the name its own press replaced, and stays on the screen",
      between != shown and imp.item == shown and len(cur()["people"]) == n_people and app.screen is imp and has("Keep") and not has("Kept") and "Undone" in app.toast, (imp.item, app.toast))
tap("Keep"); invented_name = imp.item["title"]
tap("Shop")
check("Shop invents a shop", imp.item["kind"] == "shop" and imp.item["title"].startswith("The ") and has("Keep") and "INVENTED" in drawn() and screen_ok() == [])
tap("Keep"); note = cur()["calendar"]["notes"][-1]
check("a kept shop is a note on today's day that says Invented", note["day"] == 1 and note["invented"] is True and note["text"].startswith("Invented shop: " + imp.item["title"]) and "the calendar's notes" not in drawn(), note)
tap("Rumour"); check("Rumour invents a rumour", imp.item["kind"] == "rumour" and "Keep saves it to the calendar's notes." in drawn() and screen_ok() == [])
app.voice = stand = StandIn(); imp.refresh()
check("with the cloud available there is an Ask the cloud button, and it fits", has("Ask the cloud") and has("Another") and screen_ok() == [], screen_ok())
stand.reply = "A rumour\nThe ferry has started leaving a seat empty for someone."
tap("Ask the cloud")
check("while the answer is on its way the screen says so", imp.waiting and "Asking the cloud." in drawn() and "INVENTED" in drawn() and screen_ok() == [])
tap("Keep"); check("nothing can be kept while waiting", not imp.kept)
later(); text = drawn()
check("the cloud's rumour is shown, labelled as invented by the cloud model", not imp.waiting and imp.item == {"kind": "rumour", "title": "A rumour", "text": "The ferry has started leaving a seat empty for someone.", "source": "cloud"} and "INVENTED" in text and "by the cloud model, just now" in text and "The ferry has started" in text and screen_ok() == [], text)
check("it was asked through the voice's own cloud path, with nothing from the campaign in the request", len(stand.asked) == 1 and stand.asked[0] == (improv.SYSTEM, improv.request("rumour")) and "Harbin" not in stand.asked[0][1])
tap("Keep"); check("a cloud rumour is kept the same way", cur()["calendar"]["notes"][-1]["text"] == "Invented rumour: The ferry has started leaving a seat empty for someone." and cur()["calendar"]["notes"][-1]["invented"] is True)
tap("Name"); stand.reply = RuntimeError("The network is away.")
tap("Ask the cloud"); later()
check("when the cloud fails she falls back to her own lists and says why", imp.item["source"] == "offline" and imp.item["kind"] == "name" and "The network is away. This one is from my own lists." in app.toast and "by me, from my own word lists" in drawn(), app.toast)
stand.reply = "nonsense on one line"
tap("Ask the cloud"); later()
check("a reply she cannot use is treated the same", imp.item["source"] == "offline" and "nothing I could use" in app.toast)
stand.reply = "Late Arrival\nA baker."
tap("Ask the cloud"); tap("Another"); held = imp.item; later()
check("an answer that arrives after Another was pressed is dropped", imp.item == held and held["source"] == "offline" and not imp.waiting)
stand.reply = "Off Thread\nA cooper who whistles."; went = []
dmtools.background = lambda fn: went.append(real_background(fn))
tap("Ask the cloud"); went[0].join(5); waiting_still = imp.waiting; later()
check("the real path asks on a worker thread and the answer comes back through the main loop", waiting_still and not went[0].is_alive() and imp.item["title"] == "Off Thread" and imp.item["source"] == "cloud" and not imp.waiting)
dmtools.background = lambda fn: fn()
stand.on = False; imp.refresh()
check("with the cloud switched off, capped or keyless there is no Ask the cloud button", not has("Ask the cloud") and screen_ok() == [])
check("nothing on this screen was spoken aloud", stand.spoken == [], stand.spoken)
app.gesture("press"); app.gesture("double"); left = (len(cur()["people"]), len(cur()["calendar"]["notes"])); app.gesture("press"); app.gesture("double"); app.gesture("press"); app.gesture("double")
check("each double press takes back one keep, newest first", left == (n_people + 1, 1) and app.screen is imp and len(cur()["people"]) == n_people and cur()["calendar"]["notes"] == [], cur()["calendar"]["notes"])
app.gesture("press"); app.gesture("double")
check("with nothing left to take back, a double press says so and stays put", app.screen is imp and "Nothing to undo" in app.toast and len(cur()["people"]) == n_people)
tap("Back"); check("Back is the way out", app.screen is desk)
tap("Improvise"); tap("Keep"); invented_name = app.screen.item["title"]; tap("Back")
ppl = dm.People(app, s); app.push(ppl); ppl.page = 99; ppl.refresh()
mine = [w for w in ppl.widgets if isinstance(w, ui.Row) and w.label == invented_name]
check("the People list marks a kept name as Invented, in a word", len(mine) == 1 and "Invented" in mine[0].tags and "Invented" in drawn() and screen_ok() == [])
mine[0].action(); check("and so does the person's own screen", isinstance(app.screen, dm.Person) and "Invented. " in " ".join(drawn().split(" | ")) and screen_ok() == [])
tap("Back"); tap("Back")

# Calendar
tap("Calendar"); cal = app.screen
check("Calendar fits, on day 1 with no notes", isinstance(cal, dmtools.Calendar) and "Day 1" in drawn() and "No notes yet." in drawn() and "No named date" in drawn() and screen_ok() == [], screen_ok())
app.gesture("press")
check("the button is next day, saved to the file", cur()["calendar"]["day"] == 2 and "Day 2" in drawn() and "Day 2" in app.toast)
tap("+1 week"); check("a week on", cur()["calendar"]["day"] == 9 and "Day 9" in drawn())
tap("Long rest")
check("a long rest is the next day and a dated note", cur()["calendar"]["day"] == 10 and cur()["calendar"]["notes"] == [{"day": 10, "text": "Long rest."}] and has("Long rest.") and "tracker's Long rest button" in app.toast and screen_ok() == [], cur()["calendar"])
check("the calendar says what the button does", "Press: next day. Double: undo." in drawn())
app.gesture("press"); mid = cur()["calendar"]["day"]; app.gesture("double")
check("a real double press takes back its own press (day 11) and then the last change: day 9, and the note is gone",
      mid == 11 and cur()["calendar"] == {"day": 9, "date": "", "notes": []} and app.screen is cal and "Undone" in app.toast, cur()["calendar"])
tap("Undo"); tap("Undo")
check("Undo walks back a change at a time", cur()["calendar"]["day"] == 1 and "Day 1" in drawn())
tap("Undo"); check("and then says there is nothing left to undo", "Nothing to undo" in app.toast and cur()["calendar"]["day"] == 1)
tap("Next day"); tap("Next day")
tap("Add a note"); check("a note is typed on the keyboard", isinstance(app.screen, common.TextEntry) and app.screen.title == "Note for day 3"); key("met the miller")
tap("Next day"); tap("Add a note"); key("the bridge is out")
tap("Add a note"); key("")
tap("Next day"); tap("Add a note"); key("market day")
saved = cur()["calendar"]
check("notes are dated with the day they were written, in the file", saved["day"] == 5 and saved["notes"] == [{"day": 3, "text": "Met the miller"}, {"day": 4, "text": "The bridge is out"}, {"day": 5, "text": "Market day"}], saved)
check("two notes to a page, newest first, with their days in words", [w.label for w in cal.widgets if isinstance(w, ui.Row)] == ["Market day", "The bridge is out"] and has("Notes 1/2") and "Day 5" in drawn() and "Day 4" in drawn() and screen_ok() == [], screen_ok())
tap("Notes"); check("the list pages on", [w.label for w in cal.widgets if isinstance(w, ui.Row)] == ["Met the miller"] and has("Notes 2/2") and screen_ok() == [])
tap("Name the date"); key("first frost")
check("the day can be given a name", cur()["calendar"]["date"] == "First frost" and "First frost" in drawn() and screen_ok() == [])
tap("Met the miller")
check("tapping a note shows it whole and asks before removing", isinstance(app.screen, common.Choice) and app.screen.title == "Note, day 3" and "Met the miller" in drawn() and screen_ok() == [])
app.gesture("press"); check("the button's own answer keeps it", app.screen is cal and len(cur()["calendar"]["notes"]) == 3)
tap("Met the miller"); tap("Remove")
check("Remove takes it out of the file", [n["text"] for n in cur()["calendar"]["notes"]] == ["The bridge is out", "Market day"] and app.screen is cal)
tap("Undo"); check("and that too can be undone", [n["text"] for n in cur()["calendar"]["notes"]] == ["Met the miller", "The bridge is out", "Market day"])
check("nothing on the calendar was spoken aloud", stand.spoken == [], stand.spoken)
tap("Back"); check("the desk tile shows the day", "Day 5" in drawn())

# Treasure
tap("Treasure"); tre = app.screen
check("Treasure fits, empty", isinstance(tre, dmtools.Treasure) and "No treasure yet." in drawn() and "Party coins: none." in drawn() and screen_ok() == [], screen_ok())
app.gesture("press"); check("the button adds an item, by name, on the keyboard", isinstance(app.screen, common.TextEntry) and app.screen.title == "Item found"); key("silver mirror")
for thing in ("odd key", "torn map", "brass bell", "glass eye"):
    tap("Add item"); key(thing)
tap("Add item"); key("")
saved = cur()["treasure"]
check("items go into the campaign file with the day they were found", [t["name"] for t in saved] == ["Silver mirror", "Odd key", "Torn map", "Brass bell", "Glass eye"] and all(t == {"name": t["name"], "holder": None, "day": 5} for t in saved), saved)
check("four to a page, and the new one is shown", has("List 2/2") and has("Glass eye") and screen_ok() == [], screen_ok())
tap("List"); tap("Silver mirror"); item = app.screen
check("an item's screen fits", isinstance(item, dmtools.TreasureItem) and "Silver mirror" in drawn() and "Found on day 5" in drawn() and has("Held by: the party") and screen_ok() == [], screen_ok())
tap("Held by"); check("who holds it is optional, and goes round the party", cur()["treasure"][0]["holder"] == "Brakka" and has("Held by: Brakka"))
tap("Held by"); tap("Held by"); tap("Held by"); check("and back to the party as a whole", cur()["treasure"][0]["holder"] is None and has("Held by: the party"))
tap("Held by"); tap("Remove")
check("Remove asks first", isinstance(app.screen, common.Choice) and app.screen.title == "Remove it?" and "Silver mirror" in drawn() and screen_ok() == [])
app.gesture("press"); check("the button's own answer keeps it", app.screen is item and len(cur()["treasure"]) == 5)
tap("Remove"); tap("Remove")
check("confirmed, it is off the list and the screen goes back", [t["name"] for t in cur()["treasure"]] == ["Odd key", "Torn map", "Brass bell", "Glass eye"] and app.screen is tre and "off the list" in app.toast and "With the party" in drawn() and screen_ok() == [], cur()["treasure"])
tre.reload(); tre.camp["treasure"][0]["holder"] = "Wren"; tre.store(); tre.refresh()
check("the list says who holds what, in words", "Held by Wren" in drawn())
tap("Coins"); purse = app.screen
check("Party coins fits: five kinds of coin, six steps, gold chosen", isinstance(purse, dmtools.PartyCoins) and purse.coin == "gp" and all(has(x) for x in ("Platinum", "Gold", "Electrum", "Silver", "Copper", "−100", "−10", "−1", "+1", "+10", "+100")) and "Changing gold: the party has 0." in drawn() and screen_ok() == [], screen_ok())
def step(label): app.toast = None; next(w for w in app.screen.widgets if w.label == label).action()
step("+100"); step("+10"); step("+10"); step("−1")
check("steps up and down are saved to the file", cur()["party_coins"]["gp"] == 119 and "the party has 119" in drawn())
step("−100"); step("−100")
check("the purse never goes below nothing", cur()["party_coins"]["gp"] == 19 and "Not enough gold: the party has 19." in app.toast)
tap("Silver"); step("+10"); step("+1")
check("each kind of coin is counted on its own", cur()["party_coins"] == {"pp": 0, "gp": 19, "ep": 0, "sp": 11, "cp": 0} and purse.coin == "sp")
check("the purse promises only what is true: Undo undoes, the button is Back", "Undo takes the last step back. The button is Back." in drawn() and "Double press" not in drawn())
tap("Undo"); check("Undo takes the last step back", cur()["party_coins"]["sp"] == 10 and app.screen is purse)
tap("Undo"); tap("Undo"); check("a step at a time", cur()["party_coins"] == {"pp": 0, "gp": 119, "ep": 0, "sp": 0, "cp": 0})
check("no character's own coins were touched", F("brakka")["coins"]["gp"] == 0)
app.gesture("press"); app.gesture("double")
check("the button is Back; a double press there is that press and nothing more: one screen back, nothing undone",
      app.screen is tre and "Party coins: 119 gold." in drawn() and cur()["party_coins"]["gp"] == 119 and len(cur()["treasure"]) == 4, type(app.screen).__name__)
tap("Back"); check("the desk tile counts the items", "4 items" in drawn())

# Tables: the dragon's is empty until the owner copies it in
n_log = len(dm.entry_lines(cur()["sessions"][dm.tonight_index(cur(), s.d["started"])]))
tap("Tables"); tab = app.screen
text = " ".join(drawn().split(" | "))
check("with one table in the file, Tables opens it; the dragon's has not been copied in, and the screen says so plainly",
      isinstance(tab, dmtools.RollTable) and tab.title == "Dragon table" and "Not copied in yet." in text and "The Dragon table has no rows." in text and len(tab.widgets) == 1 and has("Back") and screen_ok() == [], text)
shown_path = "".join(dmtools.hard_wrap(dmtools.file_words(dm.current()), "text", 22, 690))
check("it names the file and the field to fill in", "File:" in text and "Field:" in text and "fixed_results.dragon_table.value" in text and shown_path.endswith(os.path.join("campaigns", "dragon-of-icespire-peak.json")) and all(part in text for part in dmtools.hard_wrap(dmtools.file_words(dm.current()), "text", 22, 690)[:3]), text)
check("the path is the campaign file in use, in the data folder", os.path.samefile(os.path.join(paths.SOFTWARE, "..", dmtools.file_words(dm.current())) if not os.path.isabs(dmtools.file_words(dm.current())) else dmtools.file_words(dm.current()), os.path.join(paths.data("campaigns"), dm.current())))
app.gesture("press")
check("with nothing to roll, the button only goes back, and nothing is logged", app.screen is desk and len(dm.entry_lines(cur()["sessions"][dm.tonight_index(cur(), s.d["started"])])) == n_log and cur()["dragon"]["last_roll"] is None)
camp = cur(); camp["fixed_results"]["dragon_table"]["value"] = {str(n): "Made-up place %d" % n for n in range(1, 21)}; camp["fixed_results"]["dragon_table"]["value"]["20"] = None; dm.save(camp, dm.current())
desk.enter(); check("once it is filled in, the tile says d20", "Dragon: d20" in drawn())
tap("Tables"); tab = app.screen; tab.rng = Fixed(14)
check("a filled table fits and offers the right die", has("Roll d20") and not has("Undo roll") and "19 rows in the file." in " ".join(drawn().split(" | ")) and screen_ok() == [], screen_ok())
app.gesture("press"); text = drawn()
tonight = lambda: dm.entry_lines(cur()["sessions"][dm.tonight_index(cur(), s.d["started"])])
check("the button rolls: the number is shown large, with the row's words", tab.last == (14, "Made-up place 14", 5) and "14" in text.split(" | ") and "Made-up place 14" in text and has("Undo roll") and screen_ok() == [], text)
check("the roll is in tonight's log with the calendar day", tonight()[-1] == "Day 5. Dragon table, rolled 14: Made-up place 14" and len(tonight()) == n_log + 1, tonight())
check("and the file's dragon slot knows where the dragon is", cur()["dragon"]["last_roll"] == 14 and cur()["dragon"]["current_location"] == "Made-up place 14")
tab.rng = Fixed(20); tap("Roll d20")
check("a roll on a row left empty says so, and is logged as that", tab.last[:2] == (20, None) and "That row is empty in the file." in " ".join(drawn().split(" | ")) and tonight()[-1] == "Day 5. Dragon table, rolled 20: that row is empty in the file.")
n_before = len(tonight())
app.gesture("press"); n_mid = len(tonight()); app.gesture("double")
check("a real double press takes back the roll its own press made and the roll before it, out of the log and out of the dragon slot",
      n_mid == n_before + 1 and len(tonight()) == n_before - 1 and tonight()[-1] == "Day 5. Dragon table, rolled 14: Made-up place 14" and cur()["dragon"]["last_roll"] == 14 and app.screen is tab and tab.last is None, tonight())
tap("Undo roll")
check("Undo roll does the same", len(tonight()) == n_log and cur()["dragon"]["last_roll"] is None and not has("Undo roll") and screen_ok() == [])
tab.rng = Fixed(14); tap("Roll d20"); tap("Back")
check("a roll that stands stays in the log", tonight()[-1].startswith("Day 5. Dragon table, rolled 14"))
tab = dmtools.RollTable(app, s, "Dragon"); app.push(tab)
check("coming back, the screen shows the last roll from the file", "Last roll 14: Made-up place 14" in " ".join(drawn().split(" | ")) and screen_ok() == [])
tap("Back")
log_screen = dm.Log(app, s); app.push(log_screen); tap("Day 5. Dragon table"); tap("Remove"); tap("Back")
check("the DM can strike the line from the log by hand", len(tonight()) == n_log)
camp = cur(); camp["tables"] = {"Weather": {"die": 8, "rows": [{"lo": 1, "hi": 3, "text": "Rain."}, {"lo": 4, "hi": 8, "text": "Dry."}]}, "Empty one": {"die": 6, "rows": []}}; dm.save(camp, dm.current())
desk.enter(); check("any campaign file may define more tables: the tile counts them", "3 to roll on" in drawn())
tap("Tables"); lst = app.screen
check("with several, Tables is a list that says which are ready", isinstance(lst, dmtools.Tables) and [w.label for w in lst.widgets if isinstance(w, ui.Row)] == ["Dragon", "Weather", "Empty one"] and all(x in drawn() for x in ("d20, 19 rows", "d8, 2 rows", "not copied in yet")) and screen_ok() == [], screen_ok())
tap("Weather"); app.screen.rng = Fixed(2); tap("Roll d8")
check("a d8 table rolls a d8, and leaves the dragon where it was", app.screen.last[:2] == (2, "Rain.") and tonight()[-1] == "Day 5. Weather table, rolled 2: Rain." and cur()["dragon"]["last_roll"] == 14 and screen_ok() == [])
app.gesture("press"); app.gesture("double"); tap("Back"); tap("Empty one")
check("an empty table of the owner's own names its own field", "tables.Empty one.rows" in drawn() and "Not copied in yet." in drawn() and len(app.screen.widgets) == 1 and screen_ok() == [])
tap("Back"); tap("Back")
check("nothing rolled was spoken aloud", stand.spoken == [], stand.spoken)
app.voice = None

# monsters from the DM's own loaded books. The creature and its numbers are made up.
os.makedirs(os.path.join(src, "mine", "dnd", "Beasts"))
open(os.path.join(src, "mine", "dnd", "Beasts", "Made Up Beasts.md"), "w", encoding="utf-8").write("# Zibblewock\n\n" + OLD_STYLE)
con = dt_content.connect(os.environ["DT_CONTENT_DB"]); dt_content.sync(con, src, log=lambda *a: None); con.close()
app.reload_library()
found = dmtools.book_pages(app, "Zibblewock")
check("the library is searched for the monster's name", len(found) == 1 and "Armor Class 13" in found[0]["body"] and "Made Up Beasts" in found[0]["title"], found)
app.dm = False; hidden_from_players = [d["title"] for d in dmtools.book_pages(app, "grobnar")]; app.dm = True
check("DM-only pages are searched only with DM mode on", len(dmtools.book_pages(app, "grobnar")) == 2 and len(hidden_from_players) == 1 and "Secret" not in hidden_from_players[0], hidden_from_players)
desk.tools = False; desk.refresh()
tap("Fights"); loader = app.screen
tap("Add enemy"); tap("+"); tap("Type a name"); key("zibblewock"); book = app.screen
text = " ".join(drawn().split(" | "))
check("a name the books know opens the book's own page, and it fits", isinstance(book, dmtools.MonsterBook) and book.title == "Zibblewock: your books" and "Made Up Beasts" in text and "A made-up thing with too many elbows." in text and screen_ok() == [], screen_ok())
check("the three numbers are read off the page and shown for checking", book.vals == {"hp": 27, "ac": 13, "bonus": 1} and all(has(x) for x in ("Hit points 27", "Armour Class 13", "Initiative +1")) and "Found on this page: hit points, armour class, initiative. Check them." in text, text)
app.voice = stand; tap("Read page"); check("Read page opens the whole page, with no Read aloud even when she has a voice", isinstance(app.screen, common.Pages) and not has("Read aloud") and screen_ok() == []); tap("Back"); app.voice = None
tap("Armour Class"); check("a number can be corrected on the pad", isinstance(app.screen, ui.NumberPad) and app.screen.title == "Armour Class" and app.screen.text == "13" and screen_ok() == []); app.screen.delete(); app.screen.delete(); key(15)
check("the DM's own number replaces the one that was read", book.vals["ac"] == 15 and has("Armour Class 15"))
app.gesture("press")
check("the button adds them to the fight being lined up, numbers and all", app.screen is loader and loader.draft == [{"name": "Zibblewock", "count": 2, "hp": 27, "ac": 15, "init_bonus": 1}] and has("Load 2") and "HP 27 · AC 15 · init +1" in drawn() and screen_ok() == [], loader.draft)
tap("Add enemy"); tap("Type a name"); key("grobnar"); book = app.screen
check("a page that states no numbers leaves the boxes blank for the DM", isinstance(book, dmtools.MonsterBook) and book.vals == {"hp": None, "ac": None, "bonus": None} and has("Hit points –") and has("Next 1/2") and "I could not read the numbers off this page." in drawn() and screen_ok() == [], book.vals)
tap("Initiative"); app.screen.sign(); key(1)
tap("Next"); check("a typed number is kept when the DM turns to the next page", book.i == 1 and book.vals == {"hp": None, "ac": None, "bonus": -1} and has("Initiative −1") and has("Next 2/2") and screen_ok() == [])
tap("Back"); check("Back adds nothing", app.screen is loader and len(loader.draft) == 1)
tap("Add enemy"); tap("Wolf")
check("a name the books do not know falls back to the by-hand path, and says so", isinstance(app.screen, ui.NumberPad) and app.screen.title == "Hit points each" and "Nothing in your loaded books under Wolf. By hand, then." in app.toast and screen_ok() == [], app.toast)
tap("Cancel")
app._library = Library(os.path.join(DATA, "no-such.db"))
tap("Add enemy"); tap("Type a name"); key("zibblewock")
check("with an empty library it is by hand, and she says there are no books", app.library.counts() == (0, 0) and isinstance(app.screen, ui.NumberPad) and app.screen.title == "Hit points each" and "No books are loaded, so Zibblewock is entered by hand." in app.toast, app.toast)
key(9)
check("the by-hand path still lines them up", loader.draft[-1] == {"name": "Zibblewock", "count": 1, "hp": 9})
app.reload_library(); loader.drop(1)
n_before = len(s.state["combatants"])
tap("Load 2")
zib = who("Zibblewock 1")
check("loaded, the tracker keeps the three numbers with the enemy", len(s.state["combatants"]) == n_before + 2 and (zib["max"], zib["ac"], zib["bonus"], zib["hidden"]) == (27, 15, 1, True) and isinstance(app.screen, dm.Desk), zib)
app.push(P.Combatant(app, s, zib["id"])); text = drawn()
check("the DM sees them on the enemy's screen, marked DM only", "DM only · AC 15 · Init +1" in text and "27 / 27" in text and screen_ok() == [], text)
tap("Initiative"); check("and is reminded of the bonus when entering initiative", "Your book gave +1." in " ".join(drawn().split(" | "))); tap("Cancel")
s.do(ev="hide", who=zib["id"], on=False); app.dm = False; app.screen.refresh(); text = drawn()
check("players see none of the numbers, even once the enemy is in plain sight", "AC 15" not in text and "27" not in text and "Init +1" not in text and "The DM keeps count." in text, text)
check("nor do the scoreboard and the phones", "Zibblewock 1" in public() and not any(x in public() for x in ('"ac"', "AC 15", "bonus")), public())
app.dm = True; tap("Back")
s.undo(); s.undo()
check("the made-up enemies are taken out again", len(s.state["combatants"]) == n_before)
code = "".join(open(os.path.join(dnd.folder, n), encoding="utf-8").read() for n in ("dmdata.py", "dmtools.py", "improv.py", "dm.py"))
check("no stat block is stored in the DM code: no Armour Class or hit point number anywhere in it", not __import__("re").search(r"(Armou?r Class|Hit Points)\s+\d", code))
app.push(dm.FightLoader(app, s))
tap("Back"); tap("Lock")
check("Lock leaves DM mode and returns to the tracker", app.dm is False and app.screen is play and play.left == "D&D")
text = all_pages()
check("with DM mode off again, the loaded fight is nowhere on the players' screen", not any(x in text for x in ("Orc", "Troll", "437", "DM only")), text)
check("nor on the scoreboard or a phone", not any(x in public() for x in ("Orc", "Troll")))
for scr in (dm.Desk, dm.Prep, dm.People, dm.Quests, dm.FightLoader, dm.Log):
    app.push(scr(app, s)); text = drawn()
    check("%s without DM mode shows a locked desk and one way out" % scr.__name__, "locked" in text and not any(x in text for x in ("Dragon of Icespire", "Harbin", "Dwarven", "Recap read", "took the job")) and len(app.screen.widgets) == 1 and screen_ok() == [], text)
    tap("Back")
for scr, k in ((dm.Person, 0), (dm.Quest, 0)):
    app.push(scr(app, s, k)); text = drawn()
    check("%s without DM mode shows nothing of the file" % scr.__name__, "locked" in text and "Harbin" not in text and "Dwarven" not in text and len(app.screen.widgets) == 1, text)
    tap("Back")
secrets = ("INVENTED", "Day 5", "Odd key", "119", "Made-up place", "Zibblewock", "elbows", "Dragon of Icespire")
for make_screen in (lambda: dmtools.Improvise(app, s), lambda: dmtools.Calendar(app, s), lambda: dmtools.Treasure(app, s), lambda: dmtools.TreasureItem(app, s, 0),
                    lambda: dmtools.PartyCoins(app, s), lambda: dmtools.Tables(app, s), lambda: dmtools.RollTable(app, s, "Dragon"),
                    lambda: dmtools.MonsterBook(app, s, "Zibblewock", 1, [{"title": "Made Up Beasts", "heading": "", "body": OLD_STYLE, "dm_only": True}], lambda *a: None)):
    scr = make_screen(); app.push(scr); text = drawn(); before = open(os.path.join(paths.data("campaigns"), dm.current()), "rb").read()
    fit = len(scr.widgets) == 1 and has("Back") and screen_ok() == []
    app.gesture("press")
    check("%s without DM mode shows a locked desk and one way out, and the button only leaves" % type(scr).__name__,
          "locked" in text and not any(x in text for x in secrets) and fit and app.screen is play and open(os.path.join(paths.data("campaigns"), dm.current()), "rb").read() == before, text)
    app.stack = app.stack[:app.stack.index(play) + 1]

# ---------------------------------------------------------------- characters on the box
play.page = None; play.refresh()
check("between fights the tracker offers a long rest", has("Long rest") and has("Start fight") and screen_ok() == [])
tap("Party"); plist = app.screen
check("Party lists the checked characters and says one sheet is waiting", isinstance(plist, S.Party) and [w.label for w in plist.widgets[:3]] == ["Brakka", "Tam", "Wren"] and has("Check 1") and "1 uploaded sheet to check" in drawn() and screen_ok() == [], screen_ok())
check("a character stamped for the other edition is marked in words", "2014 rules" in drawn() and "Rogue 5" in drawn())
tap("New / upload")
check("making or uploading is handed to a phone", isinstance(app.screen, S.PhoneHandoff) and "Use a phone for this part." in drawn() and screen_ok() == [])
tap("Back"); tap("Check"); rev = app.screen
text = drawn()
check("the upload review fits and shows what was read", isinstance(rev, S.Review) and "Dorn, Cleric 2, Human" in text and "Ability scores: 14, 10, 13, 10, 16, 12" in text and screen_ok() == [], text)
check("it shows the edition stamp against the table's", "Stamped for the 2014 rules. This table plays 2024." in text and has("Rules: 2014"))
found = rev.findings()
check("dt_characters.check problems are listed: Armour Class is missing", (False, "Armour Class is missing.") in found and (True, "Hit points 15: fits Cleric 2") in found, found)
check("and the reminder that proficiencies were not read", any(not ok and "proficiencies" in w for ok, w in found))
tap("More"); check("the second page of findings draws", "Armour Class is missing." in drawn() and screen_ok() == [])
tap("Rules")
check("Rules switches the stamp to this table's edition", F("dorn")["edition"] == "2024" and has("Rules: 2024") and (True, "Rules: 2024, the same as this table") in rev.findings())
tap("Set AC"); key(16)
check("Armour Class entered on the box clears that problem", F("dorn")["ac"] == 16 and not any("Armour Class" in w for _, w in rev.findings()))
tap("Save")
check("Save marks the sheet checked and puts Dorn in the party", F("dorn")["reviewed"] is True and [n for n, _ in party.party()] == ["brakka.json", "dorn.json", "tam.json", "wren.json"] and app.screen is plist and "Dorn is in the party" in app.toast, app.toast)
check("the check is in the character's history", "Sheet checked on the box (2024 rules)" == F("dorn")["history"][-1]["what"])
bad, _, _ = ch.from_fields({"CharacterName": "Half", "ClassLevel": "Bard 2", "STR": "10"}); ch.save(bad, CHARS)
plist.refresh(); tap("Check"); rev = app.screen
check("a half-filled upload lists what is missing", sum(1 for ok, w in rev.findings() if not ok and "missing" in w) >= 6 and screen_ok() == [], rev.findings())
tap("Save")
check("and cannot be saved into the party from the box", app.screen is rev and "Fix it from a phone" in app.toast and "reviewed" not in F("half"))
tap("Back")
os.remove(os.path.join(CHARS, "half.json")); plist.refresh()
check("four characters fit on one page, with no Check button left", len([w for w in plist.widgets if isinstance(w, ui.Row)]) == 4 and not has("Check") and screen_ok() == [])

tap("Dorn"); sheet = app.screen
check("Dorn's sheet opens; he is not in the fight yet", isinstance(sheet, S.Sheet) and has("Join the fight") and screen_ok() == [], screen_ok())
tap("Join the fight")
check("Join the fight adds him to the tracker", who("Dorn")["file"] == "dorn.json" and who("Dorn")["seat"] == 3 and not has("Join the fight"))
tap("Back"); tap("Brakka"); sheet = app.screen
text = drawn()
check("the sheet shows dt_characters' numbers: modifiers, proficiency, initiative, passive Perception",
      all(x in text for x in ("+3", "−1", "Prof.", "+2", "Initiative +1", "Passive Perception 11", "Hit dice 3d10", "AC 15", "Played by Ethan")) and screen_ok() == [], text)
hp = who("Brakka")["hp"]
check("Brakka has 2 temporary hit points left from earlier", who("Brakka")["temp"] == 2 and hp == 16)
tap("−")
check("minus on the sheet is 1 damage through the tracker: temporary hit points first", who("Brakka")["temp"] == 1 and who("Brakka")["hp"] == 16 and F("brakka")["hp"]["temp"] == 1, who("Brakka"))
for _ in range(2): tap("−")
check("two more: the last temporary one, then 1 real one, on the sheet and in the file", who("Brakka")["temp"] == 0 and who("Brakka")["hp"] == hp - 1 and F("brakka")["hp"]["current"] == hp - 1 and "%d/28" % (hp - 1) in drawn())
tap("+"); check("plus heals 1", F("brakka")["hp"]["current"] == hp)
tap("AC"); key(18)
check("Armour Class is entered by hand", F("brakka")["ac"] == 18 and has("AC 18") and F("brakka")["history"][-1]["what"] == "Armour Class set to 18")
tap("In the party")
check("a character can be benched, and then is not in the next fight", F("brakka").get("benched") is True and has("In the party: no") and "Brakka" not in [c["name"] for c in dnd.new_state(["Ethan"], {})["combatants"]])
tap("In the party"); check("and unbenched", not F("brakka").get("benched"))
tap("Numbers"); check("Numbers lists saves, skills and slots", isinstance(app.screen, common.Pages) and any("Saving throws" == p[0] for p in app.screen.pages) and screen_ok() == [])
tap("Back"); tap("History"); check("History shows the dated record, newest first", "Armour Class set to 18" in " ".join(app.screen.pages[0][1]) and screen_ok() == [])
tap("Back")

# gear and coins
c = F("brakka")
for name, qty in (("Chain mail", 1), ("Torch", 5)): ch.add_item(c, name, qty)
for name in ("Ring A", "Cloak B", "Wand C", "Amulet D"): ch.add_item(c, name, needs_attunement=True)
ch.add_coins(c, gp=40, sp=12); ch.save(c, CHARS)
tap("Gear"); gear = app.screen
check("Gear fits: four items to a page, each with its own Attune button", isinstance(gear, S.Gear) and len([w for w in gear.widgets if isinstance(w, ui.Row)]) == 4 and has("More gear 1/2") and screen_ok() == [], screen_ok())
check("coins and the attunement count are written out", "Coins: 40 gold, 12 silver" in drawn() and "Attuned to 0 of 3" in drawn())
tap("Chain mail")
check("tapping an item wears it; the row says Worn", ch.find_item(F("brakka"), "Chain mail")["equipped"] and next(w for w in gear.widgets if w.label == "Chain mail").right == "Worn")
tap("Chain mail"); check("tapping again packs it", not ch.find_item(F("brakka"), "Chain mail")["equipped"])
def attune(name):
    app.toast = None
    gear.attune(name)
for name in ("Ring A", "Cloak B", "Wand C"): attune(name)
check("three items attuned", ch.derived(F("brakka"))["attuned"] == ["Ring A", "Cloak B", "Wand C"] and app.toast is None)
attune("Amulet D")
check("the fourth is refused: three is the limit, and the file is unchanged", "3 is the limit" in app.toast and ch.derived(F("brakka"))["attuned"] == ["Ring A", "Cloak B", "Wand C"], app.toast)
attune("Ring A"); attune("Amulet D")
check("end one, and the fourth can take its place", ch.derived(F("brakka"))["attuned"] == ["Cloak B", "Wand C", "Amulet D"])
tap("More gear"); check("the second page of gear fits, with Attuned shown in words", has("Attuned") and "Attuned to 3 of 3" in drawn() and screen_ok() == [], screen_ok())
tap("Add by phone"); check("typing gear is a phone job", isinstance(app.screen, S.PhoneHandoff)); tap("Back")
tap("Coins"); coins = app.screen
check("Coins fits, gold chosen", isinstance(coins, S.Coins) and coins.coin == "gp" and has("Spend gold") and screen_ok() == [], screen_ok())
tap("Spend gold"); key(50)
check("spending 50 of 40 gold is refused and nothing changes", "Not enough gold" in app.toast and F("brakka")["coins"]["gp"] == 40, app.toast)
tap("Spend gold"); key(15)
check("spending 15 leaves 25", F("brakka")["coins"]["gp"] == 25 and F("brakka")["history"][-1]["what"] == "Coins -15 gp")
tap("Silver"); tap("Gain silver"); key(8)
check("gaining 8 silver makes 20", F("brakka")["coins"]["sp"] == 20 and coins.coin == "sp" and screen_ok() == [])
tap("Spend silver"); key(21)
check("coins never go below nothing", F("brakka")["coins"]["sp"] == 20 and "Not enough silver" in app.toast)
tap("Back"); tap("Back")

# level up
tap("Level up"); lv = app.screen
text = drawn()
check("Level up fits: Fighter 4, 28 to 36 on the average", isinstance(lv, S.LevelUp) and lv.title == "Brakka: Fighter 4" and "28 to 36" in text and "Took 6 on a d10, plus 2 for Constitution." in " ".join(text.split(" | ")) and screen_ok() == [], text)
check("it lists what needs choosing at level 4, and sends the player to their book", "Ability Score" in text and "Read the level 4" in text)
tap("I rolled"); pad = app.screen
pad.type("1"); pad.type("1"); pad.done()
check("a d10 cannot roll 11", app.screen is pad and "between 1 and 10" in app.toast)
pad.delete(); app.toast = None; pad.done()
check("rolled 1: 28 to 31", lv.roll == 1 and "28 to 31" in drawn() and has("Rolled 1"))
tap("Cancel")
check("Cancel changes nothing", F("brakka")["hp"]["max"] == 28 and ch.total_level(F("brakka")) == 3 and app.screen is sheet)
tap("Level up"); lv = app.screen
tap("Class"); check("with one class, the class button offers a new one", isinstance(app.screen, common.TextEntry))
key("blood hunter"); check("a class with no known hit die is sent to the phone", "hit die for Blood Hunter" in app.toast and lv.cls() == "Fighter")
tap("Class"); key("wizard")
check("a new class can be chosen: Wizard 1, on a d6", lv.title == "Brakka: Wizard 1" and "28 to 34" in drawn() and "New class" in drawn(), drawn())
tap("Class"); check("and un-chosen", lv.title == "Brakka: Fighter 4")
n_hist = len(F("brakka")["history"])
tap("I rolled"); key(4)
app.toast = None; app.gesture("press")
b = F("brakka")
check("Done: Fighter 4, rolled 4 plus 2 is 34, written to the file with one history line",
      ch.derived(b)["class_line"] == "Fighter 4" and b["hp"]["max"] == 34 and len(b["history"]) == n_hist + 1 and b["history"][-1]["what"] == "Level up: Fighter 4. Hit points +6 (rolled 4).", b["history"][-1])
check("then it shows what to choose and which entry to read", isinstance(app.screen, common.Pages) and app.screen.left == "Brakka" and "level 4 Fighter" in " ".join(" ".join(p[1]) for p in app.screen.pages) and screen_ok() == [], app.screen.pages)
check("the tracker's copy has the new maximum", who("Brakka")["max"] == 34)
tap("Back"); check("back on the sheet, which now says Fighter 4", app.screen is sheet and sheet.title == "Brakka, Fighter 4")
top = ch.new_character("Peak", "x", "Fighter", AB); top["classes"][0]["level"] = 20; ch.save(top, CHARS)
app.push(S.LevelUp(app, s, "peak.json")); tap("Done")
check("level 20 is the top", "Already level 20" in app.toast and screen_ok() == [])
tap("Cancel"); os.remove(os.path.join(CHARS, "peak.json"))
tap("Back")

# level-up for the whole party, when the campaign file says a level is due
camp = dm.load(dm.current()); camp["levelling"]["party_level"] = 4; dm.save(camp, dm.current())
check("the file says level 4: Dorn (2) and Wren (3) are due, Brakka (4) and Tam (5) are not", [n for n, _ in dm.level_due(camp)] == ["dorn.json", "wren.json"])
app.dm = True; tap("Back"); play.dm(); desk = app.screen
check("the DM desk then offers Level up", has("Level up") and screen_ok() == [], screen_ok())
tap("Level up")
check("and takes the party in turn, starting with Dorn", isinstance(app.screen, S.LevelUp) and app.screen.title == "Dorn: Cleric 3" and screen_ok() == [])
tap("Done"); tap("Back")
check("Dorn is level 3: 15 hit points plus 5 on the average plus 1 for Constitution", F("dorn")["hp"]["max"] == 21 and app.screen is desk)
tap("Lock")

# long rest and leaving
tap("Long rest")
check("Long rest from the tracker restores the party's files", (F("brakka")["hp"]["current"], F("wren")["hp"]["current"]) == (34, 20) and "A long rest." in app.toast, app.toast)
check("and wakes whoever was down", not dnd.down(who("Wren")) and who("Wren")["cond"] == [])
app.gesture("press"); app.gesture("double")
check("double press after a long rest puts the hit points back in the files", F("wren")["hp"]["current"] == 0 and not s.state["fight"], F("wren")["hp"])
tap("Long rest")
for c in s.state["combatants"]:
    if c["init"] is None: s.do(ev="init", who=c["id"], value=10)
app.dm = True; play.refresh(); app.gesture("press")
tap("End fight")
check("End fight offers a long rest; the button's own answer is Not now", app.screen.title == "Long rest?" and screen_ok() == [])
app.dm = False
app.gesture("press"); check("Not now goes back to the tracker", app.screen is play and not s.state["fight"])
tap("Menu"); menu = app.screen
check("More is the shared menu", isinstance(menu, extras.GameMenu) and screen_ok() == [])
tap("Reminders"); check("reminders can hang off Start of turn", ("turn", "Start of turn") in app.screen.phases() and screen_ok() == [])
tap("Back"); tap("End game"); tap("End it")
over = app.screen
check("the game ends from the menu, with no winner", isinstance(over, common.GameOver) and over.session.finished["winner"] is None and "No winner" in drawn() and screen_ok() == [], over.session.finished)
check("and its record names the party only", not any(x in json.dumps(over.session.finished) for x in ("Orc", "Troll", "Goblin")), over.session.finished)

# ---------------------------------------------------------------- faults found in review, each kept as a check
# Every character, enemy and line of "book" text below is made up.
import copy
app.go_home()
for _n in list(os.listdir(CHARS)):                       # a clean party for these: three made-up characters
    os.remove(os.path.join(CHARS, _n))
make("Quill", "Ethan", "Wizard", 3, "2024", int=16)      # 20 hit points
make("Stone", "Sam", "Fighter", 3, "2024")               # 28
make("Reed", "Priya", "Rogue", 5, "2014")                # 38
def fresh(*keep):
    """A new game with only the named characters in the tracker."""
    app.go_home(); app.dm = False; app.toast = None
    app.start_game(dnd, ["Ethan", "Sam", "Priya", "Trevor"], {"edition": "2024"})
    for c in list(app.session.state["combatants"]):
        if keep and c["name"] not in keep: app.session.do(ev="remove", who=c["id"])
    app.screen.refresh()
    return app.screen, app.session
def double_press(): app.gesture("press"); app.gesture("double")      # what the one button really sends
hpf = lambda name: (F(name)["hp"]["current"], F(name)["hp"]["max"], F(name)["hp"]["temp"])

# the button, pressed twice, on the screens beside the tracker
t, ss = fresh()
X = lambda name: next(c for c in ss.state["combatants"] if c["name"] == name)
for _n, _v in (("Stone", 20), ("Quill", 15), ("Reed", 10)): ss.do(ev="init", who=X(_n)["id"], value=_v)
tap("Start fight"); tap("Next turn")
tap("Reed"); tap("Damage"); key(5)
n = len(ss.log)
check("on a combatant's screen", isinstance(app.screen, P.Combatant) and X("Reed")["hp"] == 33 and ss.state["turn"] == X("Quill")["id"])
double_press()
check("a double press on a combatant's screen is its Back and nothing more: the damage and the turn both stand",
      app.screen is t and len(ss.log) == n and X("Reed")["hp"] == 33 and hpf("reed")[0] == 33 and ss.state["turn"] == X("Quill")["id"], [e["ev"] for e in ss.log])
app.dm = True; t.dm(); double_press()
check("the same from the DM desk: back to the tracker, nothing undone", app.screen is t and len(ss.log) == n and X("Reed")["hp"] == 33)
t.party(); double_press()
check("and from the Party list", app.screen is t and len(ss.log) == n)
double_press()
check("on the tracker itself a double press still takes back its own press and one event more", len(ss.log) == n - 1 and X("Reed")["hp"] == 38 and hpf("reed")[0] == 38 and ss.state["turn"] == X("Quill")["id"], [e["ev"] for e in ss.log])
app.push(S.LevelUp(app, ss, "stone.json")); n = len(ss.log); double_press()
check("a double press on Level up is one press of Done: one level, not two, and no fight event undone",
      ch.total_level(F("stone")) == 4 and hpf("stone")[1] == 36 and isinstance(app.screen, common.Pages) and len(ss.log) == n, (ch.total_level(F("stone")), type(app.screen).__name__))
tap("Back") if has("Back") else app.pop()

# reading a sheet again is not an event
check("after the level-up the tracker has the new maximum, and nothing called sync is in the log or on the undo stack",
      (X("Stone")["hp"], X("Stone")["max"]) == (36, 36) and "sync" not in [e["ev"] for e in ss.log] and len(ss.d["undo"]) == len(ss.log), ss.log[-2:])
ss.do(ev="damage", who=X("Stone")["id"], amount=9)
_c = F("stone"); ch.level_up(_c); party.write(_c, "stone.json")       # level 5 while 9 down: 27 becomes 35 of 44
n = len(ss.log); t.enter()
check("a level gained mid-fight is read in when the tracker comes back up, as no event", (X("Stone")["hp"], X("Stone")["max"]) == (35, 44) and len(ss.log) == n and ss.log[-1]["ev"] == "damage")
t.undo()
check("Undo then takes back the 9 damage, not the reading of the sheet, and keeps the level's hit points: 44 of 44, in the file too",
      (X("Stone")["hp"], X("Stone")["max"]) == (44, 44) and hpf("stone")[:2] == (44, 44) and ch.total_level(F("stone")) == 5 and len(ss.log) == n - 1, (X("Stone")["hp"], hpf("stone")))

# undoing a long rest puts the files back whole
t, ss = fresh()
X = lambda name: next(c for c in ss.state["combatants"] if c["name"] == name)
_c = F("quill"); _c["hp"]["current"], _c["hit_dice_spent"], _c["slots_used"], _c["pact_used"] = 7, 2, [3, 1], 1; party.write(_c, "quill.json")
_c = F("reed"); _c["hp"]["current"], _c["hit_dice_spent"] = 5, 4; party.write(_c, "reed.json")
dnd.resync(ss); ss.do(ev="remove", who=X("Reed")["id"])               # Reed sits out, but still rests with the party
rest_view = lambda name: (F(name)["hp"]["current"], F(name)["hit_dice_spent"], F(name)["slots_used"], F(name)["pact_used"], len(F(name)["history"]))
before = (rest_view("quill"), rest_view("reed"))
ss.do(ev="rest")
check("the rest itself: Quill full with slots and hit dice back, Reed (not in the tracker) full with half his hit dice back",
      rest_view("quill")[:4] == (20, 0, [], 0) and rest_view("reed")[:2] == (38, 2), (rest_view("quill"), rest_view("reed")))
ss.undo()
check("undoing a long rest puts back hit points, spell slots, pact slots, hit dice and the history, for everyone who rested, in the tracker or not",
      (rest_view("quill"), rest_view("reed")) == before and before[0] == (7, 2, [3, 1], 1, before[0][4]) and X("Quill")["hp"] == 7, (rest_view("quill"), rest_view("reed"), before))
check("a saved game still loads back exactly, with the rest undone", engine.Session.load(ss.path, plugins).state == ss.state)

# character files keep their names; a renamed sheet is found again
_c = F("quill"); _c["hp"]["current"] = 20; party.write(_c, "quill.json")
os.replace(os.path.join(CHARS, "quill.json"), os.path.join(CHARS, "quill (copy).json"))
t, ss = fresh()
X = lambda name: next(c for c in ss.state["combatants"] if c["name"] == name)
Fx = lambda fname: ch.load(os.path.join(CHARS, fname))["hp"]["current"]
check("a sheet in a file not named after the character joins under that file name", X("Quill")["file"] == "quill (copy).json" and X("Quill")["hp"] == 20)
ss.do(ev="damage", who=X("Quill")["id"], amount=6)
check("damage is written to that same file; nothing is renamed", sorted(n for n in os.listdir(CHARS) if n.startswith("quill")) == ["quill (copy).json"] and Fx("quill (copy).json") == 14 and X("Quill")["file"] == "quill (copy).json", os.listdir(CHARS))
ss.undo()
check("and undo puts the file back: 20 again, on the tracker and on disk", X("Quill")["hp"] == 20 and Fx("quill (copy).json") == 20 and not dnd.stale(ss.state))
old = F("stone"); form = ch.to_form(old); form["name"] = "Stone the Bold"
new, _ = ch.from_form(form, old); ch.save(new, CHARS); os.remove(os.path.join(CHARS, "stone.json"))      # what the phone's Save does on a rename
t.enter()
bold = next(c for c in ss.state["combatants"] if c["seat"] == 1)
check("a character renamed from a phone mid-game is found again by its id: the tracker follows it to the new file and name",
      (bold["name"], bold["file"]) == ("Stone the Bold", "stone-the-bold.json") and new.get("id") == bold["sid"], (bold["name"], bold["file"]))
ss.do(ev="damage", who=bold["id"], amount=10)
check("and damage reaches the renamed file", Fx("stone-the-bold.json") == bold["hp"] == F("stone-the-bold")["hp"]["max"] - 10)
check("it cannot be added a second time under its new name", "already in the fight" in ss.do(ev="add_char", file="stone-the-bold.json")[0] and [c["name"] for c in ss.state["combatants"]].count("Stone the Bold") == 1)
legacy = dict(X("Quill")); legacy.pop("sid"); legacy["file"] = "gone.json"
check("a game saved before sheets had ids finds a moved sheet by the character's name", dnd.locate({"combatants": [legacy]}, legacy)[0] == "quill (copy).json")
os.remove(os.path.join(CHARS, "reed.json"))
reed = X("Reed"); app.push(P.Combatant(app, ss, reed["id"])); text = drawn()
check("a character whose sheet has gone altogether is kept on the tracker, and the screen says there is no file behind it", "no sheet file, kept here only" in text and screen_ok() == [], text)
was = reed["hp"]
check("its hit points still count down on the tracker", was > 2 and ss.do(ev="damage", who=reed["id"], amount=2) == [] and X("Reed")["hp"] == was - 2, was)
app.pop()
make("Reed", "Priya", "Rogue", 5, "2014")
up2, _, _ = ch.from_fields({"CharacterName": "Vex", "PlayerName": "Trevor", "ClassLevel": "Cleric 2", "STR": "14", "DEX": "10", "CON": "13", "INT": "10", "WIS": "16", "CHA": "12", "HPMax": "15", "AC": "16"})
ch.log(up2, "Imported from Vex.pdf"); up2["reviewed"], up2["benched"] = True, True
edited, _ = ch.from_form(dict(ch.to_form(up2), hp_current=9), up2)
check("an uploaded sheet that was checked stays checked, and stays benched, after an edit from a phone", not party.needs_review(edited) and edited.get("benched") is True and edited["hp"]["current"] == 9)

# what the players may see of a hidden enemy
t, ss = fresh()
X = lambda name: next(c for c in ss.state["combatants"] if c["name"] == name)
ss.do(ev="add", kind="enemy", base="Lurker", count=1, numbered=False, init=30, hp=90, hidden=True)
ss.do(ev="conc", who=X("Lurker")["id"], on=True); ss.do(ev="damage", who=X("Lurker")["id"], amount=44)      # DC 22, the DM's business
t.refresh()
check("a save waiting on a hidden enemy puts no Save button on the players' tracker", not has("Save DC") and "22" not in drawn() and "Lurker" not in drawn(), drawn())
ss.do(ev="conc", who=X("Quill")["id"], on=True); ss.do(ev="damage", who=X("Quill")["id"], amount=2); t.refresh()
check("with a visible save waiting as well, the button shows that one's number, not the hidden one's", has("Save DC 10") and not has("Save DC 22") and screen_ok() == [])
app.dm = True; t.refresh()
check("the DM's tracker shows the first save waiting, hidden or not", has("Save DC 22"))
app.dm = False
t, ss = fresh()
for c in ss.state["combatants"]: ss.do(ev="init", who=c["id"], value=10)
ss.do(ev="load", enemies=[{"name": "Orc", "count": 2}], hidden=True)
tap("Start fight")
check("players who try to start with hidden enemies still to roll are told only that the DM is not ready", app.toast == "The DM is not ready to start yet." and not ss.state["fight"], app.toast)
check("so is a phone", ss.do(ev="next") == ["The DM is not ready to start yet."])
app.dm = True; tap("Start fight")
check("the DM's own tracker names the hidden one that holds things up", app.toast.startswith("Orc 1, who is hidden, has no initiative yet.") and not ss.state["fight"], app.toast)
app.dm = False

# initiative corrected in the middle of a round costs nobody a turn
t, ss = fresh()
X = lambda name: next(c for c in ss.state["combatants"] if c["name"] == name)
up_now = lambda: dnd.get(ss.state, ss.state["turn"])["name"]
ss.do(ev="init", who=X("Quill")["id"], value=20); ss.do(ev="init", who=X("Reed")["id"], value=15)
ss.do(ev="init", who=next(c for c in ss.state["combatants"] if c["seat"] == 1)["id"], value=10)
ss.do(ev="next"); ss.do(ev="next")
check("round 1, the second in the order is up", (ss.state["round"], up_now()) == (1, "Reed"))
ss.do(ev="init", who=X("Reed")["id"], value=5)                        # it was a 5 all along
check("the hint still names who has yet to act this round", "Up next: Stone the Bold." in t.hint()[0], t.hint())
said = ss.do(ev="next")
check("correcting the initiative of whoever is acting does not skip the one who had not acted yet", said == ["Stone the Bold is up."] and ss.state["round"] == 1, said)
said = ss.do(ev="next")
check("then the round turns over, and the corrected order holds from there", said[:2] == ["Round 2.", "Quill is up."] and [c["name"] for c in dnd.order(ss.state)] == ["Quill", "Stone the Bold", "Reed"], said)
ss.do(ev="add", kind="enemy", base="Late", count=1, numbered=False, init=30)
ss.do(ev="next"); ss.do(ev="next")
said = ss.do(ev="next")
check("a newcomer whose place in the order has gone by waits for the next round, then goes first", said == ["Round 3.", "Late is up."], said)
ss.do(ev="remove", who=X("Late")["id"])
check("removing whoever is acting passes the turn to the next who has not acted", up_now() == "Quill" and ss.state["round"] == 3)
old_save = copy.deepcopy(ss.state); old_save.pop("acted")
check("a fight saved before this was kept carries on in the same place", dnd.apply(old_save, {"ev": "next"}) == ["Stone the Bold is up."] and old_save["acted"] == [X("Quill")["id"], old_save["turn"]])
check("rules.next_up: the highest who has not acted; when all have, the first, and a new round; the dead are passed over",
      rules.next_up(trio, [1]) == (2, False) and rules.next_up(trio, [1, 3]) == (2, False) and rules.next_up(trio, [1, 2, 3]) == (1, True)
      and rules.next_up([C(1, 20, dead=True), C(2, 15), C(3, 10)], [2, 3]) == (2, True) and rules.next_up([C(1, 20, dead=True)], []) == (None, False))

# the dead keep no spell going
ss.do(ev="add", kind="enemy", base="Mage", count=1, numbered=False, init=3)
mage = X("Mage")["id"]
ss.do(ev="conc", who=mage, on=True); ss.do(ev="damage", who=mage, amount=30)
check("a concentrating enemy with no maximum takes 30: a save waits", ss.state["prompts"] == [{"who": mage, "dc": 15, "damage": 30}])
ss.do(ev="sethp", who=mage, max=20)
check("setting its hit points below the damage taken defeats it, ends the spell and clears the save", X("Mage")["dead"] and not X("Mage")["conc"] and ss.state["prompts"] == [])
check("the dead cannot start concentrating", "past concentrating" in ss.do(ev="conc", who=mage, on=True)[0] and not X("Mage")["conc"])
ss.do(ev="sethp", who=mage, max=60)
check("raising the maximum again brings it back, to act when its place in the round comes", not X("Mage")["dead"] and mage not in ss.state["acted"] and [ss.do(ev="next"), ss.do(ev="next"), ss.do(ev="next")][-1] == ["Mage is up."])

# the campaign file, edited by hand, badly
app.dm = True
camp_path = os.path.join(paths.data("campaigns"), dm.current())
good_text = open(camp_path, encoding="utf-8").read()
slips = [
    ("a person typed as a bare name", lambda c: c["people"].insert(0, "Old Tom")),
    ("a person who is a number", lambda c: c["people"].insert(0, 7)),
    ("an attitude that is a number", lambda c: c["people"][0].update(attitude=3)),
    ("a quest typed as a bare name", lambda c: c["quests"].insert(0, "Rat cellar")),
    ("a quest with no status and a tier in words", lambda c: (c["quests"][0].pop("status"), c["quests"][0].update(tier="two"))),
    ("the party level in quotes", lambda c: c["levelling"].update(party_level="3")),
    ("the party level as a list", lambda c: c["levelling"].update(party_level=[3])),
    ("levelling as a number", lambda c: c.update(levelling=4)),
    ("the page as a range", lambda c: c["position"].update(booklet_page="12-14", quest=3)),
    ("the campaign's name as a number", lambda c: c.update(campaign=5)),
    ("tonight's session number in quotes", lambda c: c["sessions"].append({"n": "4", "started": ss.d["started"], "lines": ["x"]})),
    ("a session that is a number, and one whose lines are one string", lambda c: c["sessions"].extend([7, {"n": 2, "lines": "They did things"}])),
    ("an outline step with no prep, and one with prep as a sentence", lambda c: (c["session_outline"][1].update(prep=None), c["session_outline"][2].update(prep="Read the quest", n="2"))),
    ("a prep step that is a number", lambda c: c["prep_checklist"].__setitem__(7, 8)),
    ("a saved fight with its count in words", lambda c: c.update(fights=[{"name": "A", "enemies": [{"name": "Rat", "count": "three"}]}])),
    ("a saved fight with no count, and numbers for names", lambda c: c.update(fights=[{"name": 3, "enemies": [{"name": 5, "count": None, "hp": 7.5, "ac": "15"}]}])),
    ("a saved fight whose enemies are not a list", lambda c: c.update(fights=[{"name": "A", "enemies": {"Rat": 3}}, "B", {"enemies": ["Rat"]}])),
    ("a dragon table key that is not a plain number", lambda c: c["fixed_results"]["dragon_table"]["value"].update({"²": "x", "3-4": "y", "": "z"})),
    ("calendar, treasure and purse all the wrong shape", lambda c: c.update(calendar=[1], treasure={"a": 1}, party_coins=[5], tables=[1], dragon=3)),
    ("everything a list", lambda c: [c.update({k: []}) for k in list(c)]),
    ("everything a word", lambda c: [c.update({k: "x"}) for k in list(c)]),
]
def walk_the_desk():
    """Open the desk and each screen that reads the file, and draw them."""
    del app.stack[2:]; app.toast = None
    app.push(dm.Desk(app, ss)); desk = app.screen; drawn()
    tap("More"); drawn(); tap("More")
    desk.recap(); drawn(); app.pop()
    desk.campaign(); drawn(); del app.stack[3:]
    desk.prep(); drawn(); app.pop()
    desk.people(); drawn()
    if app.screen.camp["people"]: app.screen.open(0); drawn(); tap("Met"); tap("Attitude"); app.pop()
    app.pop()
    desk.quests(); drawn()
    if app.screen.camp["quests"]: app.screen.open(0); drawn(); tap("Status"); app.pop()
    app.pop()
    desk.log(); drawn(); app.pop()
    desk.fights(); drawn()
    if has("Saved"): tap("Saved"); drawn()
    app.pop()
    desk.calendar(); drawn(); app.pop()
    desk.treasure(); drawn(); app.screen.coins(); drawn(); app.pop(); app.pop()
    app.push(dmtools.Tables(app, ss)); drawn(); app.pop()
    for tb in dmdata.tables(cur()):
        app.push(dmtools.RollTable(app, ss, tb["name"])); drawn(); app.pop()
    return dm.session_number(cur(), "another night"), dm.recap(cur(), "another night")
import traceback
broke = []
for label, slip in slips:
    c = json.loads(good_text); slip(c)
    json.dump(c, open(camp_path, "w", encoding="utf-8"))
    try: walk_the_desk()
    except Exception: broke.append((label, traceback.format_exc().strip().split("\n")[-1]))
check("%d slips of the hand in the campaign file, and the DM desk opens and draws every screen after each" % len(slips), broke == [], broke)
c = json.loads(good_text); c["people"].insert(0, "Old Tom"); c["levelling"]["party_level"] = "3"
c["fights"] = [{"name": "Gate", "enemies": [{"name": "Rat", "count": "3"}, {"name": "Guard captain of the eastern gate", "count": 99, "hp": "12"}]}]
json.dump(c, open(camp_path, "w", encoding="utf-8")); tidied = cur()
check("a bare name becomes a person and a number in quotes a number, but a saved fight is left as the DM wrote it",
      tidied["people"][0]["name"] == "Old Tom" and tidied["people"][0]["attitude"] is None and tidied["levelling"]["party_level"] == 3
      and tidied["fights"][0]["enemies"] == [{"name": "Rat", "count": 3, "hp": None}, {"name": "Guard captain of the eastern gate", "count": 99, "hp": 12}], tidied["fights"])
del app.stack[2:]; app.push(dm.Desk(app, ss)); app.screen.fights(); tap("Saved")
check("the fight loader holds that saved fight to what the tracker takes, on the screen and not in the file",
      app.screen.draft == [{"name": "Rat", "count": 3, "hp": None}, {"name": "Guard captain of t", "count": 8, "hp": 12}] and screen_ok() == []
      and json.load(open(camp_path, encoding="utf-8")) == c, app.screen.draft)
del app.stack[2:]
open(camp_path, "w", encoding="utf-8").write(good_text[:-3])        # the last bracket lost
del app.stack[2:]; app.push(dm.Desk(app, ss)); text = " ".join(drawn().split(" | "))
check("a campaign file that will not parse: the desk says so in plain words and names the file, with only Back to tap",
      "I cannot read the campaign file." in text and "dragon-of-icespire-peak.json" in text.replace(" ", "") and [w.label for w in app.screen.widgets] == ["Back"] and screen_ok() == [], text)
check("and it is not written to while it is broken", open(camp_path, encoding="utf-8").read() == good_text[:-3])
app.pop()
open(camp_path, "w", encoding="utf-8").write(good_text)

# opening the desk writes nothing; a night with nothing logged leaves no entry and is not a session
c = cur(); c["sessions"] = [{"n": 6, "date": "2026-11-14", "started": "last week", "lines": ["They took the job."]}]; dm.save(c, dm.current())
check("before the desk is opened tonight, the log has only last week's entry", len(cur()["sessions"]) == 1 and dm.session_number(cur(), ss.d["started"]) == 7)
on_disk = open(camp_path, "rb").read()
app.push(dm.Desk(app, ss)); desk = app.screen
check("opening the desk says Session 7 and writes nothing to the campaign file", desk.title == "Session 7" and open(camp_path, "rb").read() == on_disk, cur()["sessions"])
desk.enter(); check("however often it is opened", open(camp_path, "rb").read() == on_disk)
check("so a night with nothing logged was not a session: the night after is still session 7", dm.session_number(cur(), "the night after") == 7)
check("and its recap is the last one with something written", dm.recap(cur(), "the night after") == ("Last time: session 6 (2026-11-14)", "They took the job."), dm.recap(cur(), "the night after"))
tap("Log"); check("the Log screen can still show that last written entry", has("Show last time") and "Nothing logged." in drawn()); tap("Back")
app.pop()

# numbers read off a page of the DM's own book are held to what could be typed
page = [{"title": "Made-up bestiary", "heading": "Zib", "body": "Zib. A made-up beast. AC 13 HP 22 Initiative +77", "dm_only": False}]
book = dmtools.MonsterBook(app, ss, "Zib", 1, page, lambda *a: None)
check("an initiative bonus of +77 on the page is taken as a misreading and not offered; the rest is", book.vals == {"hp": 22, "ac": 13, "bonus": None} and book.read == ["Hit points", "Armour Class"], book.vals)
page[0]["body"] = "Zib AC 13 HP 22 Initiative +2"
check("a sensible one is", dmtools.MonsterBook(app, ss, "Zib", 1, page, lambda *a: None).vals == {"hp": 22, "ac": 13, "bonus": 2})
app.dm = False; app.go_home()

# ---------------------------------------------------------------- the campaign file is the DM's: reading it changes nothing
import datetime, types
from deepthought import web
shipped_json = json.load(open(shipped, encoding="utf-8"))
def desk_round_trip(data):
    """Write a campaign, open the desk, look at every part of it, close it. Returns what is on disk after."""
    json.dump(data, open(camp_path, "w", encoding="utf-8"), indent=1)
    scr, ss2 = fresh(); app.dm = True
    app.push(dm.Desk(app, ss2)); desk = app.screen; drawn()
    for go in (desk.people, desk.quests, desk.prep, desk.fights, desk.log, desk.calendar, desk.treasure, desk.recap, desk.campaign):
        go(); drawn()
        if isinstance(app.screen, (dm.People, dm.Quests)) and app.screen.camp[{"People": "people", "Quests": "quests"}[type(app.screen).__name__]]:
            app.screen.open(0); drawn(); app.pop()
        del app.stack[3:]; app.screen.enter()
    app.pop(); app.pop(); app.push(dm.Desk(app, ss2)); app.pop()
    return json.load(open(camp_path, encoding="utf-8"))
check("load the shipped campaign, open the desk and every part of it, close it: the file holds exactly what it held",
      desk_round_trip(shipped_json) == shipped_json)
long_note = "First paragraph about the innkeeper.\n\nSecond paragraph.\n- a list\n- of things\n" + "He owes the party a favour. " * 20
mine = json.loads(json.dumps(shipped_json))
mine["people"][0]["your_note"] = long_note; mine["people"][0]["note"] = long_note; mine["quests"][0]["your_notes"] = long_note
mine["quests"][0]["watch_for"] = long_note; mine["people"][1]["attitude"] = "neutral"; mine["people"][2]["met"] = "no"
mine["position"]["booklet_page"] = 0; mine["note"] = long_note * 5; mine["levelling"]["method"] = long_note * 5
mine["prep_checklist"].append("Print the handout for the dwarven excavation and bring the miniatures for it")
mine["session_outline"].append("A bare line with no number"); mine["people"][3]["name"] = "A name far longer than any button: " + "x" * 80
mine["fights"] = [{"name": "The gate " * 12, "enemies": [{"name": "Guard captain of the eastern gate", "count": 12, "hp": 21, "ac": 55}]}]
after = desk_round_trip(mine)
check("the same for a long hand-edited one: long notes, paragraphs, odd values and all are left exactly as written", after == mine,
      [k for k in mine if after.get(k) != mine[k]])
scr, ss2 = fresh(); app.dm = True; app.push(dm.Desk(app, ss2)); tap("Page"); key("12")
after = json.load(open(camp_path, encoding="utf-8"))
check("and when the DM does change something, only that changes: the long notes are still whole",
      after["position"]["booklet_page"] == 12 and after["people"][0]["your_note"] == long_note and after["quests"][0]["watch_for"] == long_note
      and after["people"][1]["attitude"] == "neutral" and after["prep_checklist"] == mine["prep_checklist"] and after["note"] == mine["note"]
      and after["fights"] == mine["fights"] and after["sessions"] == [], [k for k in mine if after.get(k) != mine[k]])
app.go_home()

# ---------------------------------------------------------------- one log entry to a calendar date
class FakeDate(datetime.date):
    now = datetime.date(2026, 11, 21)
    @classmethod
    def today(cls): return cls.now
dm.datetime = types.SimpleNamespace(date=FakeDate, timedelta=datetime.timedelta)
c = {"sessions": []}
check("nothing logged yet: this is session 1, and asking leaves no entry behind", dm.session_number(c, "game A") == 1 and c["sessions"] == [])
dm.log_line(c, "game A", "The party met the innkeeper.")
dm.log_line(c, "game B", "A second game started the same evening.")
check("two games started on one evening share one entry, session 1",
      [(e["n"], e["date"], len(e["lines"])) for e in c["sessions"]] == [(1, "2026-11-21", 2)] and dm.session_number(c, "game C") == 1, c["sessions"])
FakeDate.now = datetime.date(2026, 11, 28)
check("the same game picked up again a week later is session 2, and its recap is last week's night",
      dm.session_number(c, "game A") == 2 and dm.tonight_index(c, "game A") is None and dm.recap(c, "game A")[0] == "Last time: session 1 (2026-11-21)", dm.recap(c, "game A"))
dm.log_line(c, "game A", "They fought the manticore.")
check("and what is logged that night goes in a new entry, not last week's",
      [(e["n"], e["date"], e["lines"]) for e in c["sessions"]] == [(1, "2026-11-21", ["The party met the innkeeper.", "A second game started the same evening."]),
                                                                  (2, "2026-11-28", ["They fought the manticore."])], c["sessions"])
FakeDate.now = datetime.date(2026, 12, 5)
c["sessions"] += [{"n": k, "date": "2026-12-0%d" % k, "started": "empty %d" % k, "lines": []} for k in (3, 4)]
check("entries with nothing in them are not sessions: tonight is session 3", dm.session_number(c, "game D") == 3)
dm.log_line(c, "game D", "Tonight.")
check("and they are dropped when the next line is logged", [(e["n"], e["date"]) for e in c["sessions"]] == [(1, "2026-11-21"), (2, "2026-11-28"), (3, "2026-12-05")], c["sessions"])
# a night that runs past midnight is one night
FakeDate.now = datetime.date(2026, 12, 12)
c = {"sessions": [{"n": 3, "date": "2026-12-05", "lines": ["Old night."]}]}
dm.log_line(c, "late game", "Took the job at the mine."); dm.log_line(c, "late game", "Fought the ochre thing.")
FakeDate.now = datetime.date(2026, 12, 13)                # the same game, ten minutes later
check("past midnight the same game is still tonight's session, with what was logged before midnight",
      dm.session_number(c, "late game") == 4 and dm.tonight_index(c, "late game") == 1 and len(dm.entry_lines(c["sessions"][1])) == 2, c["sessions"])
dm.log_line(c, "late game", "The wizard fell down the shaft.")
check("and a line logged after midnight goes in the same entry",
      [(e["n"], e["date"], len(e["lines"])) for e in c["sessions"]] == [(3, "2026-12-05", 1), (4, "2026-12-12", 3)], c["sessions"])
FakeDate.now = datetime.date(2026, 12, 19)
check("next week's recap is that whole night, not only the part after midnight",
      dm.session_number(c, "next game") == 5 and dm.recap(c, "next game") == ("Last time: session 4 (2026-12-12)", "Took the job at the mine.\nFought the ochre thing.\nThe wizard fell down the shaft."), dm.recap(c, "next game"))
check("and the late game itself, picked up a week later, gets a new entry", dm.tonight_index(c, "late game") is None)
# entries the DM typed in some other shape are his, and are never thrown away
c = {"sessions": [{"n": 1, "date": "2026-10-01", "lines": "We met the townmaster.\nTook the first job."},
                  {"n": 2, "date": "2026-10-08", "lines": {"1": "Fought at the mine"}},
                  {"n": 3, "date": "2026-10-15", "summary": "Reached the hill."},
                  {"n": 4, "date": "2026-10-22", "lines": []}, "A bare line somebody typed"]}
check("log lines typed as one string, or as numbered items, are read as lines",
      dm.entry_lines(c["sessions"][0]) == ["We met the townmaster.", "Took the first job."] and dm.entry_lines(c["sessions"][1]) == ["Fought at the mine"])
dm.log_line(c, "new game", "Tonight we began.")
check("logging tonight drops only the entry with nothing in it; every entry the DM typed is still in the file",
      [e if isinstance(e, str) else e.get("date") for e in c["sessions"]] == ["2026-10-01", "2026-10-08", "2026-10-15", "A bare line somebody typed", "2026-12-19"]
      and c["sessions"][0]["lines"] == "We met the townmaster.\nTook the first job." and c["sessions"][-1]["n"] == 5, c["sessions"])
dm.datetime = datetime
# numbers and nesting no file should hold
check("a number too big to be one, or not a number at all, is no number: it does not stop the file loading",
      dm._whole(float("inf")) is None and dm._whole(float("nan"), 1) == 1 and dm._whole(3.0) == 3 and dm._whole(2.5) is None and dm._whole(10 ** 40) == 10 ** 40)
_name = dm.current(); _path = os.path.join(dm.folder(), _name)
with open(_path, encoding="utf-8") as _f: _keep = _f.read()
_c = json.loads(_keep); _c["levelling"]["party_level"] = 12345678; _c["position"] = {"quest": "A\u0000B", "booklet_page": 12345678}
with open(_path, "w", encoding="utf-8") as _f: _f.write(json.dumps(_c).replace("12345678", "1e999"))
_got = dm.load(_name)
check("a campaign file with 1e999 in it loads, with those numbers left at nothing", _got is not None and _got["levelling"]["party_level"] == 1 and _got["position"]["booklet_page"] is None)
with open(_path, "w", encoding="utf-8") as _f: _f.write('{"people": ' + "[" * 100000 + "]" * 100000 + "}")
check("a campaign file nested beyond reading is 'cannot read', not a fault", dm.load(_name) is None)
_c["position"]["quest"] = "half \ud83d of a character"; _c["position"]["booklet_page"] = 3; _c["levelling"]["party_level"] = 2
with open(_path, "w", encoding="utf-8") as _f: _f.write(json.dumps(_c))
_got = dm.load(_name); dm.save(_got, _name)
check("a campaign file holding half a broken character can still be saved, and reads back the same", dm.load(_name)["position"]["quest"] == "half \ud83d of a character")
with open(_path, "w", encoding="utf-8") as _f: _f.write(_keep)

# ---------------------------------------------------------------- what is for the DM stays on the box
app.go_home()
party_was = {_n: open(os.path.join(CHARS, _n), "rb").read() for _n in os.listdir(CHARS)}      # put back below
for _n in party_was: os.remove(os.path.join(CHARS, _n))
make("Quill", "Ethan", "Wizard", 3, "2024", int=16); make("Stone", "Sam", "Fighter", 3, "2024"); make("Reed", "Priya", "Rogue", 5, "2014")
class Heard:
    def __init__(self): self.said = []
    def say(self, text, show=True): self.said.append(text)
    def hold(self, down): pass
json.dump(shipped_json, open(camp_path, "w", encoding="utf-8"), indent=1)
scr, s = fresh("Stone"); voice_was, app.voice = app.voice, Heard(); n0 = len(s.log)
s.do(ev="init", who=W("Stone"), value=10)
s.do(ev="add", kind="enemy", base="Vexmaw", count=1, hp=90, hidden=True, numbered=False)
app.dm = True; app.voice.said.clear(); app.toast = None
app.gesture("press")
check("the DM presses Start fight with a hidden enemy not ready: the box names it on its own screen",
      "Vexmaw, who is hidden" in (app.toast or "") and not s.state["fight"] and len(s.log) == n0 + 2, app.toast)
check("but the name is not spoken, and is not on the shared scoreboard page",
      app.voice.said == [] and web.state(app)["said"] == "" and "Vexmaw" not in json.dumps(web.state(app)), (app.voice.said, web.state(app)))
app.gesture("press"); app.gesture("double")
check("a double press there has no event of its own to take back, and undoes one", len(s.log) == n0 + 1)
s.do(ev="add", kind="enemy", base="Vexmaw", count=1, hp=90, hidden=True, numbered=False)
app.dm = False; app.toast = None; app.voice.said.clear(); app.gesture("press")
check("with DM mode off the players hear only that the DM is not ready", app.toast == "The DM is not ready to start yet." and web.state(app)["said"] == app.toast and app.voice.said == [app.toast])
app.dm = True; app.push(dm.Desk(app, s)); app.screen.calendar(); app.voice.said.clear(); app.gesture("press")
check("a DM tool's own line (the calendar moving on a day) is shown on the box, not spoken and not on the scoreboard page",
      (app.toast or "").startswith("Day 2") and app.voice.said == [] and web.state(app)["said"] == "", (app.toast, app.voice.said))
app.pop(); app.screen.fights(); tap("Load")
check("nor is the fight loader's", "Add an enemy first" in (app.toast or "") and app.voice.said == [] and web.state(app)["said"] == "")
del app.stack[2:]; app.dm = False; app.say("An ordinary line.")
check("an ordinary line after it is public again", web.state(app)["said"] == "An ordinary line." and app.voice.said == ["An ordinary line."])

# a hidden player character: nothing about them is said
scr, s = fresh("Stone"); app.voice.said.clear(); n0 = len(s.log)
s.do(ev="hide", who=W("Stone"), on=True)
quiet = [s.do(ev="damage", who=W("Stone"), amount=28), s.do(ev="save", who=W("Stone"), passed=False), s.do(ev="save", who=W("Stone"), passed=True, nat=20),
         s.do(ev="damage", who=W("Stone"), amount=1), s.do(ev="damage", who=W("Stone"), amount=200), s.do(ev="confirm", who=W("Stone"), dead=True)]
check("a hidden character goes down, saves, gets up, and dies: not a word is said, though all of it is counted",
      quiet == [[], [], [], [], [], []] and who("Stone")["dead"] and len(s.log) == n0 + 7, quiet)
s.undo(); s.undo(); s.undo(); s.undo(); s.undo(); s.undo()
app.voice = voice_was

# reminders: none as the enemies' turns begin
scr, s = fresh("Stone")
s.do(ev="init", who=W("Stone"), value=15); s.do(ev="add", kind="enemy", base="Goblin", count=2, init=10, hp=7)
s.add_reminder(1, "*", "Sam every phase"); s.add_reminder(1, "turn", "Sam shield"); s.add_reminder(None, "*", "Snacks")
heard = [[x for x in s.do(ev="next") if x.startswith("Reminder")] for _ in range(4)]
check("a player's reminders are said on their own turn and not when the enemies' turns begin",
      heard == [["Reminder for Sam: Sam every phase", "Reminder for Sam: Sam shield", "Reminder: Snacks"], [], [], ["Reminder for Sam: Sam every phase", "Reminder for Sam: Sam shield", "Reminder: Snacks"]]
      and dnd.phase(s.state) == "turn" and dnd.quiet_phases == ("wait",), heard)

# a fight saved before the box kept who has acted
scr, s = fresh()
for nm, v in (("Stone", 20), ("Quill", 15), ("Reed", 10)): s.do(ev="init", who=W(nm), value=v)
s.do(ev="next"); s.state.pop("acted")
s.do(ev="init", who=W("Reed"), value=25)
order = [dnd.get(s.state, s.state["turn"])["name"] for _ in range(2) if s.do(ev="next") is not None]
check("an old save with no list of who has acted: an initiative corrected before the next turn costs nobody theirs",
      order == ["Reed", "Quill"] and s.state["round"] == 1 and s.state["acted"] == [W("Stone"), W("Reed"), W("Quill")], (order, s.state["round"], s.state.get("acted")))

# ended by hand: Undo on Game over does not touch the fight or the sheets
scr, s = fresh("Stone"); n0 = len(s.log)
s.do(ev="damage", who=W("Stone"), amount=9)
scr.more(); tap("End game"); tap("End it")
check("D&D ends only by hand, and says so in the record", isinstance(app.screen, common.GameOver) and s.finished["by_hand"] is True)
tap("Undo")
check("Undo on Game over carries on where the table was: the 9 damage is still on the tracker and on the sheet",
      app.session is s and s.finished is None and len(s.log) == n0 + 1 and who("Stone")["hp"] == 19 and F("stone")["hp"]["current"] == 19, (len(s.log), who("Stone")["hp"]))
s.undo()

# a sheet renamed on a phone, and a new character made under the old name
scr, s = fresh("Stone"); sid = who("Stone")["sid"]
moved = F("stone"); moved["name"] = "Stone The Bold"; ch.save(moved, CHARS); os.remove(os.path.join(CHARS, "stone.json"))
ch.save(ch.new_character("Stone", "Trevor", "Wizard", dict(AB), edition="2024"), CHARS)
app.screen.enter(); c = s.state["combatants"][0]
check("the tracker follows its own character to the new file by its id, not the newcomer sitting at the old name",
      (c["name"], c["file"], c["hp"], c["max"], c["sid"]) == ("Stone The Bold", "stone-the-bold.json", 28, 28, sid) and "id" not in F("stone"), c)
s.do(ev="damage", who=c["id"], amount=5)
check("and damage goes to that sheet, not the newcomer's", F("stone-the-bold")["hp"]["current"] == 23 and F("stone")["hp"]["current"] == F("stone")["hp"]["max"])
s.undo()
for _n in ("stone.json", "stone-the-bold.json"): os.remove(os.path.join(CHARS, _n))
make("Stone", "Sam", "Fighter", 3, "2024")

# a long rest, a rename on a phone, then the rest undone
scr, s = fresh("Quill")
spent = F("quill"); spent["slots_used"], spent["hit_dice_spent"] = [1, 1], 2; ch.save(spent, CHARS)
n_hist = len(F("quill").get("history", []))
s.do(ev="rest")
check("the long rest gave the slots and hit dice back", F("quill")["slots_used"] == [] and F("quill")["hit_dice_spent"] == 0)
moved = F("quill"); moved["name"] = "Quill Reborn"; ch.save(moved, CHARS); os.remove(os.path.join(CHARS, "quill.json"))
s.undo(); got = F("quill-reborn")
check("undoing the rest finds the renamed sheet by its id: slots, hit dice and the history line are as they were",
      got["slots_used"] == [1, 1] and got["hit_dice_spent"] == 2 and len(got.get("history", [])) == n_hist and who("Quill Reborn")["file"] == "quill-reborn.json",
      (got.get("slots_used"), got.get("hit_dice_spent"), [h["what"] for h in got.get("history", [])][-2:]))
app.dm = False; app.go_home()
for _n in os.listdir(CHARS): os.remove(os.path.join(CHARS, _n))
for _n, _b in party_was.items(): open(os.path.join(CHARS, _n), "wb").write(_b)
open(camp_path, "w", encoding="utf-8").write(good_text)

# ---------------------------------------------------------------- housekeeping
T.draw_text = real_draw
from deepthought.games.dnd import shots as dnd_shots
shot_dir, made = tempfile.mkdtemp(), []
def snap(name, screen=None):
    if screen is not None:
        app.stack = [app.stack[0]]; app.toast = None; app.push(screen)
    made.append(app.shot(os.path.join(shot_dir, name + ".png")))
    return screen
before = sorted(os.listdir(CHARS))
dnd_shots.shots(app, snap)
check("%d D&D screenshots drawn, all 800x480" % len(made), len(made) >= 30 and {pygame.image.load(p).get_size() for p in made} == {(800, 480)})
check("the screenshot run leaves the data folder and DM mode as it found them", os.environ["DT_DATA"] == DATA and sorted(os.listdir(CHARS)) == before and app.dm is False)
check("the shipped campaign file was never written to", open(shipped, "rb").read() == shipped_before)
check("the DM code is still the shared setting", str(settings.get("dm_code")) == "0000")
info = json.load(open(os.path.join(dnd.folder, "game.json"), encoding="utf-8"))
check("game.json keeps its id, name and order, and the blurb fits a tile", (info["id"], info["name"], info["order"]) == ("dnd", "D&D", 30) and len(info["blurb"]) <= 32, info)
for x in (shot_dir, src, DATA): shutil.rmtree(x, ignore_errors=True)

# ---------------------------------------------------------------- the recap never gives a DM roll away
from deepthought.games.dnd import dm as _dm
_c = {"sessions": [{"n": 3, "date": "2026-11-01", "started": "earlier", "lines": ["The party reached the mill.", "Day 5. Dragon table, rolled 14: Made-up place 14", "They owe the miller 10 gp."]}]}
_head, _text = _dm.recap(_c, "tonight")
check("the recap read to the table leaves out where a DM table roll landed", _text == "The party reached the mill.\nThey owe the miller 10 gp." and "session 3" in _head, _text)
check("but the roll is still in the log for the DM", len(_dm.entry_lines(_c["sessions"][0])) == 3)

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
