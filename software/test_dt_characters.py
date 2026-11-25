"""Tests for dt_characters.py. Expected numbers are worked by hand from the rules."""
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dt_characters as ch
fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)
def raises(fn, exc):
    try: fn()
    except exc: return True
    except Exception as e: return "wrong error %r" % e
    return False

for score, mod in ((1,-5),(3,-4),(8,-1),(9,-1),(10,0),(11,0),(12,1),(15,2),(18,4),(20,5),(30,10)):
    check("modifier of %d is %+d" % (score, mod), ch.ability_mod(score) == mod, ch.ability_mod(score))
check("proficiency bonus by level", [ch.proficiency_bonus(l) for l in (1,4,5,8,9,12,13,16,17,20)] == [2,2,3,3,4,4,5,5,6,6])

AB = {"str":16,"dex":12,"con":14,"int":10,"wis":12,"cha":8}
b = ch.new_character("Brakka", "Ethan", "Fighter", AB, species="Dwarf", skill_profs=["Athletics","Perception"])
check("fighter level 1 hp = 10 + 2", b["hp"]["max"] == 12 and b["hp"]["current"] == 12, b["hp"])
d = ch.derived(b)
check("derived: saves, skills, passive perception", d["saves"]["str"] == 5 and d["saves"]["dex"] == 1 and d["skills"]["athletics"] == 5 and d["skills"]["stealth"] == 1 and d["passive_perception"] == 13 and d["initiative"] == 1, d)
t = ch.level_up(b)                      # level 2, average d10 = 6, +2 Con
check("level 2 average: +8 -> 20", b["hp"]["max"] == 20, b["hp"])
t = ch.level_up(b, roll=1)              # level 3, rolled 1, +2
check("level 3 rolled 1: +3 -> 23", b["hp"]["max"] == 23, b["hp"])
check("fighter is asked for a subclass at 3", any("subclass" in x for x in t), t)
t = ch.level_up(b)                      # level 4
check("level 4: ASI prompt, no proficiency change", any("Ability Score" in x for x in t) and not any("Proficiency" in x for x in t), t)
check("level 4 hp 31", b["hp"]["max"] == 31, b["hp"])
msg = ch.set_ability(b, "con", 16)
check("Con 14 -> 16 at level 4 adds 4 hp", b["hp"]["max"] == 35 and "+4" in msg, (b["hp"], msg))
t = ch.level_up(b)                      # level 5
check("level 5: proficiency +3 announced", any("+3" in x and "Proficiency" in x for x in t), t)
check("level 5 hp 35 + 6 + 3 = 44", b["hp"]["max"] == 44, b["hp"])
t6 = ch.level_up(b)
check("fighter gets an extra ASI at 6", any("Ability Score" in x for x in t6), t6)
check("history records every change", len(b["history"]) == 7 and b["history"][-1]["level"] == 6, len(b["history"]))
check("bad roll rejected", raises(lambda: ch.level_up(b, roll=11), ValueError) is True)
check("fighter has no spell slots", ch.derived(b)["spell_slots"] == [])
lo, hi = ch.hp_range(b)
check("hp range brackets real hp", lo <= b["hp"]["max"] <= hi and (lo, hi) == (13 + 5*4, 13 + 5*13), (lo, hi))

low = ch.new_character("Frail", "x", "Wizard", dict(AB, con=3))
check("level 1 hp never below 1", low["hp"]["max"] == 2, low["hp"])   # 6 - 4
ch.level_up(low, roll=1)
check("a level always gives at least 1 hp", low["hp"]["max"] == 3, low["hp"])

def caster(cls, lvl, edition="2014", sub=None):
    c = ch.new_character("T", "x", cls, AB, edition=edition)
    c["classes"][0]["level"] = lvl; c["classes"][0]["subclass"] = sub
    return c
S = lambda *a, **k: ch.spell_slots(caster(*a, **k))
check("wizard 1, 3, 5, 9, 20", (S("Wizard",1), S("Wizard",3), S("Wizard",5), S("Wizard",9), S("Wizard",20)) == ([2],[4,2],[4,3,2],[4,3,3,3,1],[4,3,3,3,3,2,2,1,1]))
check("2014 paladin 1 has none, 2 has two", (S("Paladin",1), S("Paladin",2), S("Paladin",5), S("Paladin",17)) == ([],[2],[4,2],[4,3,3,3,1]))
check("2024 paladin 1 has two", S("Paladin",1,"2024") == [2])
check("eldritch knight 3, 7, 19", (S("Fighter",3,sub="Eldritch Knight"), S("Fighter",7,sub="Eldritch Knight"), S("Fighter",19,sub="Eldritch Knight")) == ([2],[4,2],[4,3,3,1]))
check("eldritch knight 2 has none", S("Fighter",2,sub="Eldritch Knight") == [])
check("warlock pact slots", [ch.pact_slots(l) for l in (1,2,3,5,9,11,17)] == [(1,1),(2,1),(2,2),(2,3),(2,5),(3,5),(4,5)])
m = caster("Wizard", 3); m["classes"].append({"name":"Paladin","subclass":None,"level":3,"hit_die":10})
check("multiclass wizard 3 / paladin 3 (2014) = caster level 4", ch.spell_slots(m) == [4,3], ch.spell_slots(m))
m["edition"] = "2024"
check("same character under 2024 rounds up = caster level 5", ch.spell_slots(m) == [4,3,2], ch.spell_slots(m))
w = ch.new_character("Wren", "Sam", "Wizard", AB)
t = ch.level_up(w)
check("wizard 2 (2014): slots change and subclass prompt", any("3 x 1st" in x for x in t) and any("subclass" in x for x in t), t)
w24 = ch.new_character("Wren", "Sam", "Wizard", AB, edition="2024")
check("wizard 2 (2024): no subclass prompt until 3", not any("subclass" in x for x in ch.level_up(w24)) and any("subclass" in x for x in ch.level_up(w24)))
check("cleric (2014) creation asks for subclass and spells", any("subclass" in x for x in ch.creation_todo(ch.new_character("C","x","Cleric",AB))) and any("spells" in x for x in ch.creation_todo(ch.new_character("C","x","Cleric",AB))))
check("unknown class needs a hit die", raises(lambda: ch.new_character("X","x","Blood Hunter",AB), ValueError) is True and ch.new_character("X","x","Blood Hunter",AB,hit_die=10)["hp"]["max"] == 12)
mc = ch.new_character("Sel", "Jo", "Rogue", AB)
t = ch.level_up(mc, "Fighter")
check("multiclass level uses the new class's die and warns", mc["hp"]["max"] == 10 + 8 and any("multiclass" in x.lower() for x in t) and ch.derived(mc)["class_line"] == "Rogue 1 / Fighter 1", (mc["hp"], t))

# gear, coins, attunement
ch.add_item(b, "Torch", 5); ch.add_item(b, "Torch", 5); ch.add_item(b, "Longsword")
check("items stack", ch.find_item(b, "torch")["qty"] == 10)
ch.remove_item(b, "Torch", 4)
check("items remove", ch.find_item(b, "Torch")["qty"] == 6)
check("cannot remove more than held", raises(lambda: ch.remove_item(b, "Torch", 7), ValueError) is True and ch.find_item(b, "Torch")["qty"] == 6)
ch.remove_item(b, "Torch", 6)
check("item at zero is dropped from the list", ch.find_item(b, "Torch") is None)
for n in ("Ring A", "Cloak B", "Wand C", "Amulet D"): ch.add_item(b, n, needs_attunement=True)
for n in ("Ring A", "Cloak B", "Wand C"): ch.attune(b, n)
check("fourth attunement refused", raises(lambda: ch.attune(b, "Amulet D"), ValueError) is True and len(ch.derived(b)["attuned"]) == 3)
ch.attune(b, "Ring A", False); ch.attune(b, "Amulet D")
check("swap attunement works", ch.derived(b)["attuned"] == ["Cloak B", "Wand C", "Amulet D"], ch.derived(b)["attuned"])
ch.add_coins(b, gp=25, sp=4)
check("coins add", b["coins"]["gp"] == 25 and b["coins"]["sp"] == 4)
check("coins cannot go negative, and nothing changes", raises(lambda: ch.add_coins(b, gp=-5, sp=-9), ValueError) is True and b["coins"]["gp"] == 25 and b["coins"]["sp"] == 4)

# hit points
b["hp"]["temp"] = 5
check("temp hp absorbs first", ch.damage(b, 8) == "ok" and b["hp"]["temp"] == 0 and b["hp"]["current"] == b["hp"]["max"] - 3)
check("heal caps at max", ch.heal(b, 999) == b["hp"]["max"])
check("dropping to 0 is down", ch.damage(b, b["hp"]["max"] + 3) == "down" and b["hp"]["current"] == 0)
ch.heal(b, 5)
check("massive damage is dead", ch.damage(b, 5 + b["hp"]["max"]) == "dead")
b["slots_used"] = [1]; ch.long_rest(b)
check("long rest restores", b["hp"]["current"] == b["hp"]["max"] and b["slots_used"] == [])

# save / load / check
T = tempfile.mkdtemp()
p = ch.save(b, T)
check("save and load round trip", os.path.basename(p) == "brakka.json" and ch.load(p) == b)
b["ac"] = 18
check("a legal character has no problems", ch.check(b) == [], ch.check(b))
bad = json.loads(json.dumps(b)); bad["hp"]["max"] = 400; bad["abilities"]["str"] = 45; bad["ac"] = None
pr = ch.check(bad)
check("check flags impossible hp, score and missing AC", len(pr) == 3 and any("400" in x for x in pr) and any("45" in x for x in pr), pr)

# class/level text
P = ch.parse_class_level
check("parse 'Fighter 3'", [(k["name"], k["level"]) for k in P("Fighter 3")] == [("Fighter", 3)])
check("parse multiclass", [(k["name"], k["level"]) for k in P("Fighter 3 / Rogue 2")] == [("Fighter", 3), ("Rogue", 2)])
check("parse subclass in brackets", P("Wizard (Evoker) 5")[0]["subclass"] == "Evoker" and P("Wizard (Evoker) 5")[0]["level"] == 5 and P("Wizard (Evoker) 5")[0]["name"] == "Wizard")
check("parse 'Level 3 Fighter' and '3rd level fighter'", [(k["name"], k["level"]) for k in P("Level 3 Fighter") + P("3rd level fighter")] == [("Fighter", 3), ("Fighter", 3)], P("3rd level fighter"))

# PDF import, with a fillable sheet built here (field names as on the common sheets)
from reportlab.pdfgen import canvas
def make_sheet(path, values):
    c = canvas.Canvas(path); y = 800
    for name, val in values.items():
        c.acroForm.textfield(name=name, value=val, x=72, y=y, width=300, height=14, fieldFlags="multiline" if "\n" in val else ""); y -= 18
    c.showPage(); c.save()
sheet = {"CharacterName": "Brakka", "PlayerName": "Ethan", "ClassLevel": "Fighter 3", "Race ": "Dwarf", "Background": "Soldier",
         "STR": "16", "STRmod": "+3", "DEX": "12", "DEXmod ": "+1", "CON": "14", "CONmod": "+2", "INT": "10", "INTmod": "+0",
         "WIS": "12", "WISmod": "+1", "CHA": "8", "CHamod": "-1", "AC": "18", "HPMax": "28", "HPCurrent": "19", "Speed": "25 ft.",
         "GP": "40", "Equipment": "Chain mail\nShield\n2 handaxes\nTorch x5\n50 feet of rope\nPotion of healing (2)", "Wpn Name": "Longsword"}
sp = os.path.join(T, "sheet.pdf"); make_sheet(sp, sheet)
c, warn, unused = ch.import_pdf_fields(sp)
check("import: identity", (c["name"], c["player"], c["species"], c["background"]) == ("Brakka", "Ethan", "Dwarf", "Soldier"), c["name"])
check("import: class and level", ch.derived(c)["class_line"] == "Fighter 3")
check("import: abilities", c["abilities"] == AB, c["abilities"])
check("import: hp, ac, speed, coins", (c["hp"]["max"], c["hp"]["current"], c["ac"], c["speed"], c["coins"]["gp"]) == (28, 19, 18, 25, 40), (c["hp"], c["ac"], c["speed"]))
eq = {i["name"]: i["qty"] for i in c["equipment"]}
check("import: equipment lines and quantities", eq == {"Chain mail": 1, "Shield": 1, "handaxes": 2, "Torch": 5, "50 feet of rope": 1, "Potion of healing": 2}, eq)
check("import: unknown fields reported, not lost silently", unused == ["Wpn Name"], unused)
check("import: only the standing proficiency reminder for a clean sheet", len(warn) == 1 and "proficienc" in warn[0], warn)
swapped = dict(sheet, STR="+3", STRmod="16", CON="14", CONmod="+3", HPMax="90")
make_sheet(sp, swapped); c2, warn2, _ = ch.import_pdf_fields(sp)
check("import: swapped score/modifier boxes fixed and flagged", c2["abilities"]["str"] == 16 and any("swapped" in x for x in warn2), warn2)
check("import: wrong modifier flagged", any("Constitution 14 should give" in x for x in warn2), warn2)
check("import: impossible hp flagged", any("90" in x and "between" in x for x in warn2), warn2)
make_sheet(sp, {"CharacterName": "Half", "ClassLevel": "Bard 2", "STR": "10"}); c3, warn3, _ = ch.import_pdf_fields(sp)
check("import: half-filled sheet loads and lists what is missing", c3["name"] == "Half" and sum("missing" in x for x in warn3) >= 6, warn3)
cv = canvas.Canvas(sp); cv.drawString(72, 700, "printed sheet, no fields"); cv.save()
check("import: flat PDF refused with a clear message", raises(lambda: ch.import_pdf_fields(sp), ValueError) is True)

# ---- faults found in review, each kept fixed
import time
silly = {"CharacterName": "Zed", "ClassLevel": "Fighter", "Level": "2000000000", "STR": "10", "DEX": "10", "CON": "10", "INT": "10", "WIS": "10", "CHA": "10"}
t0 = time.time(); cz, wz, _ = ch.from_fields(silly)
check("a sheet with a level of two thousand million is read at once, as level 20, and says so", time.time() - t0 < 1 and cz["classes"][0]["level"] == 20 and any("levels run from 1 to 20" in x for x in wz), (time.time() - t0, wz))
cz, wz, _ = ch.from_fields(dict(silly, Level="-3"))
check("a level below 1 is read as level 1, and says so", cz["classes"][0]["level"] == 1 and any("levels run from 1 to 20" in x for x in wz), wz)
cz, wz, _ = ch.from_fields(dict(silly, ClassLevel="Fighter 3 / Rogue 400", Level=""))
check("each class of a multiclass sheet is held to 1 to 20", [k["level"] for k in cz["classes"]] == [3, 20], cz["classes"])
g = ch.new_character("Gear", "A", "Fighter", AB)
ch.add_item(g, "Arrows (20)"); ch.attune(g, "Arrows (20)"); ch.add_item(g, "Potion x2", notes="from the hag"); ch.add_item(g, "Dagger", 2)
g["hp"]["max"] = 12; g["ac"] = 15
g2, _ = ch.from_form(ch.to_form(g), g)
gear = lambda c: [(i["name"], i["qty"], i["attuned"], i["notes"]) for i in c["equipment"]]
check("opening a sheet on the phone and saving it unchanged leaves the gear as it was", gear(g2) == gear(g) == [("Arrows (20)", 1, True, ""), ("Potion x2", 1, False, "from the hag"), ("Dagger", 2, False, "")], gear(g2))
form = ch.to_form(g); form["equipment"] = "3 x Arrows (20)\nPotion x2\nTorch (5)\n2 x Dagger"
g3, _ = ch.from_form(form, g)
check("a count typed in front of gear already on the sheet changes the count; new lines are still read as counts", gear(g3) == [("Arrows (20)", 3, True, ""), ("Potion x2", 1, False, "from the hag"), ("Torch", 5, False, ""), ("Dagger", 2, False, "")], gear(g3))
g["reviewed"], g["benched"], g["id"] = True, True, "abc123"
g4, _ = ch.from_form(dict(ch.to_form(g), hp_current=3), g)
check("an edit from the phone keeps what the box decided: still checked, still benched, the same id",
      (g4.get("reviewed"), g4.get("benched"), g4.get("id"), "needs_review" in g4, g4["hp"]["current"]) == (True, True, "abc123", False, 3), g4)
check("a sheet typed in new carries none of those", not any(k in ch.from_form(ch.to_form(g))[0] for k in ("reviewed", "benched", "id")))
check("with no saved sheet, counts are read as before",[(i["name"], i["qty"]) for i in ch.parse_equipment("Arrows (20)\nPotion x2")] == [("Arrows", 20), ("Potion", 2)])
import pypdf
real_reader, given = pypdf.PdfReader, []
def spy(source, *a, **k):
    given.append(source); return real_reader(source, *a, **k)
pypdf.PdfReader = spy
make_sheet(sp, sheet); c5, _, _ = ch.import_pdf_fields(sp)
pypdf.PdfReader = real_reader
check("a PDF sheet is handed to the reader as an open file, and the file is closed afterwards", c5["name"] == "Brakka" and len(given) == 1 and not isinstance(given[0], str) and given[0].closed, given)
real_pypdf = sys.modules["pypdf"]; sys.modules["pypdf"] = None
check("with pypdf missing a PDF sheet is refused in words, not by ending the program", raises(lambda: ch.import_pdf_fields(sp), ValueError) is True)
sys.modules["pypdf"] = real_pypdf
shutil.rmtree(T)
print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
