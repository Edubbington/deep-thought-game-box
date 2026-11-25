#!/usr/bin/env python3
"""Deep Thought character sheets (D&D fifth edition, 2014 or 2024 rules).

One JSON file per character. This module does the arithmetic and the record
keeping: modifiers, proficiency bonus, hit points on level-up, spell slots,
gear, coins, attunement, and a dated history of every change. It does not
contain class features, spells or item descriptions; those are looked up in
content.db (the free rules document and your own books).

  new_character(...)            make a level 1 character
  level_up(c, cls, roll=None)   add a level; returns the list of things to do
  set_ability(c, "con", 16)     change a score (fixes hit points if Con moves)
  add_item / remove_item / equip / attune / add_coins
  damage / heal / long_rest
  derived(c)                    everything worked out, for the sheet screen
  check(c)                      list of problems, for reviewing an upload
  import_pdf_fields(path)       read a fillable PDF character sheet
  save(c, folder) / load(path)

Command line:
  python3 dt_characters.py import "Brakka.pdf" characters/
  python3 dt_characters.py show characters/brakka.json
"""
import copy, datetime, json, os, re, sys

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {"str": "Strength", "dex": "Dexterity", "con": "Constitution",
                 "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma"}
SKILLS = {
    "acrobatics": "dex", "animal handling": "wis", "arcana": "int", "athletics": "str",
    "deception": "cha", "history": "int", "insight": "wis", "intimidation": "cha",
    "investigation": "int", "medicine": "wis", "nature": "int", "perception": "wis",
    "performance": "cha", "persuasion": "cha", "religion": "int",
    "sleight of hand": "dex", "stealth": "dex", "survival": "wis"}
HIT_DIE = {"barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10, "bard": 8,
           "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
           "sorcerer": 6, "wizard": 6, "artificer": 8}
SAVES = {"barbarian": ("str", "con"), "bard": ("dex", "cha"), "cleric": ("wis", "cha"),
         "druid": ("int", "wis"), "fighter": ("str", "con"), "monk": ("str", "dex"),
         "paladin": ("wis", "cha"), "ranger": ("str", "dex"), "rogue": ("dex", "int"),
         "sorcerer": ("con", "cha"), "warlock": ("wis", "cha"), "wizard": ("int", "wis"),
         "artificer": ("con", "int")}
FULL_CASTERS = ("bard", "cleric", "druid", "sorcerer", "wizard")
HALF_CASTERS = ("paladin", "ranger")
THIRD_CASTER_SUBCLASSES = ("eldritch knight", "arcane trickster")
SUBCLASS_LEVEL_2014 = {"cleric": 1, "sorcerer": 1, "warlock": 1, "druid": 2, "wizard": 2}
EXTRA_ASI = {"fighter": (6, 14), "rogue": (10,)}
ASI_LEVELS = (4, 8, 12, 16, 19)
MAX_ATTUNED = 3
FULL_SLOTS = [
    [], [2], [3], [4, 2], [4, 3], [4, 3, 2], [4, 3, 3], [4, 3, 3, 1], [4, 3, 3, 2],
    [4, 3, 3, 3, 1], [4, 3, 3, 3, 2], [4, 3, 3, 3, 2, 1], [4, 3, 3, 3, 2, 1],
    [4, 3, 3, 3, 2, 1, 1], [4, 3, 3, 3, 2, 1, 1], [4, 3, 3, 3, 2, 1, 1, 1],
    [4, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 2, 1, 1, 1, 1], [4, 3, 3, 3, 3, 1, 1, 1, 1],
    [4, 3, 3, 3, 3, 2, 1, 1, 1], [4, 3, 3, 3, 3, 2, 2, 1, 1]]


# ---------------------------------------------------------------- arithmetic
def ability_mod(score):
    return (int(score) - 10) // 2


def proficiency_bonus(total_level):
    return 2 + (max(1, min(20, int(total_level))) - 1) // 4


def total_level(c):
    return sum(k["level"] for k in c["classes"])


def hit_die_for(c, cls):
    for k in c["classes"]:
        if k["name"].lower() == cls.lower() and k.get("hit_die"):
            return k["hit_die"]
    return HIT_DIE.get(cls.lower())


def average_roll(die):
    return die // 2 + 1


def pact_slots(warlock_level):
    """(number of slots, slot level) for a warlock."""
    if warlock_level < 1:
        return (0, 0)
    n = 1 if warlock_level == 1 else 2 if warlock_level <= 10 else 3 if warlock_level <= 16 else 4
    return (n, min(5, (warlock_level + 1) // 2))


def spell_slots(c):
    """Slots per spell level [1st, 2nd, ...], not counting warlock pact slots."""
    y2024 = str(c.get("edition", "2014")).startswith("2024")
    casters = []
    for k in c["classes"]:
        n, lv, sub = k["name"].lower(), k["level"], (k.get("subclass") or "").lower()
        if n in FULL_CASTERS:
            casters.append(("full", lv))
        elif n in HALF_CASTERS:
            casters.append(("half", lv))
        elif n == "artificer":                         # always rounds up
            casters.append(("half-up", lv))
        elif sub in THIRD_CASTER_SUBCLASSES and lv >= 3:
            casters.append(("third", lv))
    if not casters:
        return []
    if len(casters) == 1:
        kind, lv = casters[0]
        if kind == "full":
            eff = lv
        elif kind == "half":
            # 2014 paladins and rangers get no slots at level 1; 2024 ones do.
            eff = 0 if (lv == 1 and not y2024) else (lv + 1) // 2
        elif kind == "half-up":
            eff = (lv + 1) // 2
        else:
            eff = (lv + 2) // 3
    else:
        eff = 0
        for kind, lv in casters:
            if kind == "full":
                eff += lv
            elif kind == "half":
                eff += (lv + 1) // 2 if y2024 else lv // 2
            elif kind == "half-up":
                eff += (lv + 1) // 2
            else:
                eff += lv // 3
    return list(FULL_SLOTS[max(0, min(20, eff))])


# ---------------------------------------------------------------- the record
def _today():
    return datetime.date.today().isoformat()


def log(c, what, session=None):
    c.setdefault("history", []).append(
        {"date": _today(), "session": session, "level": total_level(c), "what": what})


def new_character(name, player, cls, abilities, species="", background="",
                  edition="2014", hit_die=None, save_profs=None, skill_profs=None):
    cls_l = cls.lower()
    die = hit_die or HIT_DIE.get(cls_l)
    if not die:
        raise ValueError("I don't know the hit die for %r: pass hit_die=6, 8, 10 or 12" % cls)
    ab = {a: int(abilities[a]) for a in ABILITIES}
    hp = max(1, die + ability_mod(ab["con"]))
    c = {"format": 1, "name": name, "player": player, "edition": str(edition),
         "species": species, "background": background,
         "classes": [{"name": cls, "subclass": None, "level": 1, "hit_die": die}],
         "abilities": ab,
         "save_profs": list(save_profs if save_profs is not None else SAVES.get(cls_l, ())),
         "skill_profs": [s.lower() for s in (skill_profs or [])], "expertise": [],
         "hp": {"max": hp, "current": hp, "temp": 0, "gains": [{"class": cls, "die": die, "gain": die, "how": "level 1"}]},
         "hit_dice_spent": 0,
         "ac": None, "ac_note": "", "speed": 30,
         "equipment": [], "coins": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
         "slots_used": [], "pact_used": 0, "spells": [], "features": [], "notes": "",
         "history": []}
    log(c, "Created: %s, level 1 %s" % (name, cls))
    return c


def creation_todo(c):
    """The choices a brand-new character still needs. The box asks; the
    player answers from their own book."""
    k = c["classes"][0]
    y2024 = str(c.get("edition", "2014")).startswith("2024")
    todo = ["Choose skill proficiencies for a %s and for the background." % k["name"],
            "Choose starting equipment, then enter Armour Class."]
    if not y2024 and SUBCLASS_LEVEL_2014.get(k["name"].lower()) == 1:
        todo.append("Choose a %s subclass (this class picks at level 1)." % k["name"])
    if spell_slots(c) or k["name"].lower() == "warlock":
        todo.append("Choose cantrips and starting spells.")
    if y2024:
        todo.append("Choose the origin feat from the background.")
    return todo


def set_ability(c, ability, score, session=None):
    """Change one score. If the Constitution modifier moves, hit points move
    by that much for every level, as the rules say."""
    ability = ability.lower()[:3]
    old = c["abilities"][ability]
    c["abilities"][ability] = int(score)
    msg = "%s %d -> %d" % (ABILITY_NAMES[ability], old, int(score))
    if ability == "con":
        diff = (ability_mod(score) - ability_mod(old)) * total_level(c)
        if diff:
            c["hp"]["max"] = max(total_level(c), c["hp"]["max"] + diff)
            c["hp"]["current"] = max(0, min(c["hp"]["max"], c["hp"]["current"] + diff))
            msg += " (hit point maximum %+d)" % diff
    log(c, msg, session)
    return msg


def level_up(c, cls=None, roll=None, hit_die=None, session=None):
    """Add one level in cls (default: the first class). roll=None takes the
    fixed average; otherwise pass what the player rolled on the hit die.
    Returns a list of plain-language things that changed or need choosing."""
    cls = cls or c["classes"][0]["name"]
    if total_level(c) >= 20:
        raise ValueError("already level 20")
    before_pb, before_slots = proficiency_bonus(total_level(c)), spell_slots(c)
    before_pact = pact_slots(sum(k["level"] for k in c["classes"] if k["name"].lower() == "warlock"))
    entry = next((k for k in c["classes"] if k["name"].lower() == cls.lower()), None)
    die = hit_die or (entry or {}).get("hit_die") or HIT_DIE.get(cls.lower())
    if not die:
        raise ValueError("I don't know the hit die for %r: pass hit_die=" % cls)
    if roll is not None and not 1 <= int(roll) <= die:
        raise ValueError("a d%d cannot roll %s" % (die, roll))
    todo = []
    if entry is None:
        entry = {"name": cls, "subclass": None, "level": 0, "hit_die": die}
        c["classes"].append(entry)
        todo.append("New class: %s. Check the multiclassing requirements and which proficiencies it gives." % cls)
    entry["level"] += 1
    raw = average_roll(die) if roll is None else int(roll)
    gain = max(1, raw + ability_mod(c["abilities"]["con"]))
    c["hp"]["max"] += gain
    c["hp"]["current"] = min(c["hp"]["max"], c["hp"]["current"] + gain)
    c["hp"]["gains"].append({"class": cls, "die": die, "gain": gain,
                              "how": "average" if roll is None else "rolled %d" % int(roll)})
    lv, tl = entry["level"], total_level(c)
    todo.insert(0, "%s is now a level %d %s (character level %d)." % (c["name"], lv, entry["name"], tl))
    todo.append("Hit point maximum +%d, now %d." % (gain, c["hp"]["max"]))
    if proficiency_bonus(tl) != before_pb:
        todo.append("Proficiency bonus is now +%d. Attacks, save DCs and proficient skills all go up by 1." % proficiency_bonus(tl))
    n = entry["name"].lower()
    y2024 = str(c.get("edition", "2014")).startswith("2024")
    sub_at = 3 if y2024 else SUBCLASS_LEVEL_2014.get(n, 3)
    if lv == sub_at and not entry.get("subclass"):
        todo.append("Choose a %s subclass." % entry["name"])
    if lv in ASI_LEVELS or lv in EXTRA_ASI.get(n, ()):
        todo.append("Ability Score Improvement: +2 to one score, +1 to two, or a feat.")
    after = spell_slots(c)
    if after != before_slots:
        todo.append("Spell slots are now %s." % slots_text(after))
    wl = sum(k["level"] for k in c["classes"] if k["name"].lower() == "warlock")
    if pact_slots(wl) != before_pact:
        todo.append("Pact magic: %d slot(s) of level %d." % pact_slots(wl))
    todo.append("Read the level %d %s entry in your book for new class features." % (lv, entry["name"]))
    log(c, "Level up: %s %d. Hit points +%d (%s)." % (entry["name"], lv, gain,
        "average" if roll is None else "rolled %d" % int(roll)), session)
    return todo


def slots_text(slots):
    names = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]
    return ", ".join("%d x %s" % (n, names[i]) for i, n in enumerate(slots) if n) or "none"


# ---------------------------------------------------------------- gear, coins
def find_item(c, name):
    return next((i for i in c["equipment"] if i["name"].lower() == name.lower()), None)


def add_item(c, name, qty=1, notes="", magic=False, needs_attunement=False, session=None):
    item = find_item(c, name)
    if item:
        item["qty"] += int(qty)
    else:
        item = {"name": name, "qty": int(qty), "equipped": False, "attuned": False,
                "magic": bool(magic or needs_attunement), "needs_attunement": bool(needs_attunement),
                "notes": notes}
        c["equipment"].append(item)
    log(c, "Gained %s%s" % ("%d x " % qty if qty != 1 else "", name), session)
    return item


def remove_item(c, name, qty=1, session=None):
    item = find_item(c, name)
    if not item:
        raise KeyError("%s does not have %r" % (c["name"], name))
    if qty > item["qty"]:
        raise ValueError("only %d %s to remove" % (item["qty"], name))
    item["qty"] -= int(qty)
    if item["qty"] == 0:
        c["equipment"].remove(item)
    log(c, "Lost %s%s" % ("%d x " % qty if qty != 1 else "", name), session)


def equip(c, name, on=True):
    item = find_item(c, name)
    if not item:
        raise KeyError(name)
    item["equipped"] = bool(on)


def attune(c, name, on=True, session=None):
    item = find_item(c, name)
    if not item:
        raise KeyError(name)
    if on and not item["attuned"] and sum(1 for i in c["equipment"] if i["attuned"]) >= MAX_ATTUNED:
        raise ValueError("%s is already attuned to %d items, which is the limit" % (c["name"], MAX_ATTUNED))
    item["attuned"] = bool(on)
    log(c, ("Attuned to " if on else "Ended attunement to ") + name, session)


def add_coins(c, session=None, **amounts):
    """add_coins(c, gp=25, sp=-3). Refuses to go below zero."""
    for k, v in amounts.items():
        if k not in c["coins"]:
            raise KeyError(k)
        if c["coins"][k] + int(v) < 0:
            raise ValueError("not enough %s: has %d" % (k, c["coins"][k]))
    for k, v in amounts.items():
        c["coins"][k] += int(v)
    log(c, "Coins " + ", ".join("%+d %s" % (int(v), k) for k, v in amounts.items()), session)


# ---------------------------------------------------------------- hit points
def damage(c, amount):
    """Temporary hit points go first. Returns 'ok', 'down' or 'dead'
    (dead = the leftover damage equals or exceeds the hit point maximum)."""
    amount = max(0, int(amount))
    used = min(c["hp"]["temp"], amount)
    c["hp"]["temp"] -= used
    amount -= used
    left_over = max(0, amount - c["hp"]["current"])
    c["hp"]["current"] = max(0, c["hp"]["current"] - amount)
    if c["hp"]["current"] > 0:
        return "ok"
    return "dead" if left_over >= c["hp"]["max"] else "down"


def heal(c, amount):
    c["hp"]["current"] = min(c["hp"]["max"], c["hp"]["current"] + max(0, int(amount)))
    return c["hp"]["current"]


def long_rest(c, session=None):
    c["hp"]["current"], c["hp"]["temp"] = c["hp"]["max"], 0
    c["slots_used"], c["pact_used"] = [], 0
    if str(c.get("edition", "2014")).startswith("2024"):
        c["hit_dice_spent"] = 0
    else:
        c["hit_dice_spent"] = max(0, c.get("hit_dice_spent", 0) - max(1, total_level(c) // 2))
    log(c, "Long rest", session)


# ---------------------------------------------------------------- the sheet
def derived(c):
    tl = total_level(c)
    pb = proficiency_bonus(tl)
    mods = {a: ability_mod(c["abilities"][a]) for a in ABILITIES}
    saves = {a: mods[a] + (pb if a in c.get("save_profs", ()) else 0) for a in ABILITIES}
    skills = {}
    for s, a in SKILLS.items():
        mult = 2 if s in c.get("expertise", ()) else 1 if s in c.get("skill_profs", ()) else 0
        skills[s] = mods[a] + pb * mult
    wl = sum(k["level"] for k in c["classes"] if k["name"].lower() == "warlock")
    return {"level": tl, "proficiency_bonus": pb, "mods": mods, "saves": saves, "skills": skills,
            "initiative": mods["dex"], "passive_perception": 10 + skills["perception"],
            "spell_slots": spell_slots(c), "pact_slots": pact_slots(wl),
            "carry_capacity_lb": c["abilities"]["str"] * 15,
            "attuned": [i["name"] for i in c["equipment"] if i["attuned"]],
            "class_line": " / ".join("%s %d" % (k["name"], k["level"]) for k in c["classes"]),
            "hit_dice": ", ".join("%dd%d" % (k["level"], k.get("hit_die") or HIT_DIE.get(k["name"].lower(), 8))
                                  for k in c["classes"])}


def hp_range(c):
    """Lowest and highest possible hit point maximum for these classes and
    this Constitution, used to sanity-check an uploaded sheet."""
    con, lo, hi, first = ability_mod(c["abilities"]["con"]), 0, 0, True
    for k in c["classes"]:
        die = k.get("hit_die") or HIT_DIE.get(k["name"].lower(), 8)
        for _ in range(k["level"]):
            if first:
                lo += max(1, die + con); hi += max(1, die + con); first = False
            else:
                lo += max(1, 1 + con); hi += max(1, die + con)
    return lo, hi


def check(c):
    """Problems a person should look at. Empty list = nothing odd."""
    out = []
    if not c.get("name"):
        out.append("No character name.")
    for a in ABILITIES:
        v = c["abilities"].get(a)
        if v is None:
            out.append("%s is missing." % ABILITY_NAMES[a])
        elif not 1 <= v <= 30:
            out.append("%s is %s; scores run from 1 to 30." % (ABILITY_NAMES[a], v))
    if any(c["abilities"].get(a) is None for a in ABILITIES):
        if c["hp"].get("max") is None:
            out.append("Hit point maximum is missing.")
        if c.get("ac") is None:
            out.append("Armour Class is missing.")
        return out
    tl = total_level(c)
    if not 1 <= tl <= 20:
        out.append("Total level is %d; it should be 1 to 20." % tl)
    for k in c["classes"]:
        if not (k.get("hit_die") or HIT_DIE.get(k["name"].lower())):
            out.append("I don't know the class %r, so tell me its hit die." % k["name"])
    lo, hi = hp_range(c)
    mx = c["hp"].get("max")
    if mx is None:
        out.append("Hit point maximum is missing. For this character it should be between %d and %d." % (lo, hi))
    elif not lo <= mx <= hi:
        out.append("Hit point maximum is %d, but for these classes and Constitution it should be between %d and %d. "
                   "A feat or species trait can explain a higher number." % (mx, lo, hi))
    if c.get("ac") is None:
        out.append("Armour Class is missing.")
    elif not 5 <= c["ac"] <= 30:
        out.append("Armour Class %s looks wrong." % c["ac"])
    n = sum(1 for i in c.get("equipment", ()) if i.get("attuned"))
    if n > MAX_ATTUNED:
        out.append("Attuned to %d items; the limit is %d." % (n, MAX_ATTUNED))
    for s in list(c.get("skill_profs", ())) + list(c.get("expertise", ())):
        if s not in SKILLS:
            out.append("Unknown skill %r." % s)
    return out


# ---------------------------------------------------------------- files
def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "character"


def save(c, folder):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, slug(c["name"]) + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)                                 # never leaves a half-written sheet
    return path


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- PDF import
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


FIELD_MAP = {  # normalised PDF field name -> where it goes
    "charactername": "name", "charname": "name", "name": "name",
    "playername": "player", "player": "player",
    "race": "species", "species": "species", "background": "background",
    "classlevel": "classlevel", "classandlevel": "classlevel", "class": "classlevel",
    "level": "levelonly",
    "ac": "ac", "armorclass": "ac", "armourclass": "ac",
    "hpmax": "hpmax", "maxhp": "hpmax", "hitpointmaximum": "hpmax", "hitpointsmax": "hpmax",
    "hpcurrent": "hpcur", "currenthp": "hpcur", "currenthitpoints": "hpcur",
    "hptemp": "hptemp", "temphp": "hptemp", "temporaryhitpoints": "hptemp",
    "speed": "speed", "cp": "cp", "sp": "sp", "ep": "ep", "gp": "gp", "pp": "pp",
    "equipment": "equipment", "featurestraits": "notes", "featuresandtraits": "notes"}
for _a, _full in ABILITY_NAMES.items():
    FIELD_MAP[_a] = "score:" + _a
    FIELD_MAP[_full.lower()] = "score:" + _a
    FIELD_MAP[_a + "score"] = "score:" + _a
    FIELD_MAP[_a + "mod"] = "mod:" + _a
    FIELD_MAP[_full.lower() + "mod"] = "mod:" + _a
    FIELD_MAP[_full.lower() + "modifier"] = "mod:" + _a


def _int(text):
    m = re.search(r"[-+]?\d+", str(text).replace("−", "-"))
    return int(m.group()) if m else None


def parse_class_level(text):
    """'Fighter 3', 'Fighter 3 / Rogue 2', 'Wizard (Evoker) 5', 'Level 3 Fighter'."""
    out = []
    for part in re.split(r"[/,&]| and ", str(text)):
        part = part.strip()
        if not part:
            continue
        sub = re.search(r"\(([^)]+)\)", part)
        part2 = re.sub(r"\([^)]*\)", " ", part)
        lv = _int(part2)
        name = re.sub(r"(?i)\blevel\b|\blvl\b|[-+]?\d+(st|nd|rd|th)?", " ", part2)
        name = " ".join(name.split()).title()
        if name:
            out.append({"name": name, "subclass": sub.group(1).strip() if sub else None,
                        "level": lv or 1, "hit_die": HIT_DIE.get(name.lower())})
    return out


def _lines(text):
    out = []
    for line in re.split(r"[\n;]+", str(text or "")):
        line = line.strip(" \t-•,")
        if line:
            out.append(line)
    return out


def parse_equipment(text, keep=()):
    """Gear typed one thing to a line: 'Dagger', '2 x Dagger', 'Torch (5)', 'Rations x3'.
    keep is names already on the sheet: a line that is one of them is that item,
    whatever it looks like ('Arrows (20)' stays one thing called 'Arrows (20)')."""
    out = []
    keep = {str(k).lower() for k in keep}
    for line in _lines(text):
        qty, name = 1, line
        m = re.match(r"^(\d+)\s*x?\s+(.+)$", line)
        m2 = re.match(r"^(.+?)\s+\(?x\s*(\d+)\)?$", line) or re.match(r"^(.+?)\s*\((\d+)\)$", line)
        mk = re.match(r"^(\d+)\s*x\s+(.+)$", line)
        if line.lower() in keep:
            pass
        elif mk and mk.group(2).strip().lower() in keep:
            qty, name = int(mk.group(1)), mk.group(2)
        # "50 feet of rope" is one rope, not fifty of something
        elif m and not re.match(r"(?i)(ft|feet|foot|lb|lbs|pounds?|days?|gp|sp|cp|gallons?|pints?|oz)\b", m.group(2)):
            qty, name = int(m.group(1)), m.group(2)
        elif m2:
            name, qty = m2.group(1), int(m2.group(2))
        name = name.strip()[:60]
        same = next((i for i in out if i["name"].lower() == name.lower()), None)
        if same:
            same["qty"] += qty
            continue
        out.append({"name": name, "qty": max(1, qty), "equipped": False, "attuned": False,
                    "magic": False, "needs_attunement": False, "notes": ""})
    return out


# ---------------------------------------------------------------- the typed-in sheet
def class_text(c):
    """'Fighter (Champion) 3 / Rogue 2': the form's one box for class and level."""
    return " / ".join("%s%s %d" % (k["name"], " (%s)" % k["subclass"] if k.get("subclass") else "", k["level"])
                      for k in c["classes"])


def to_form(c):
    """A character as the flat boxes of the phone form. from_form() reads it back."""
    d = {"name": c.get("name", ""), "player": c.get("player", ""), "edition": c.get("edition", "2024"),
         "species": c.get("species", ""), "background": c.get("background", ""), "classlevel": class_text(c),
         "saves": list(c.get("save_profs", ())), "skills": list(c.get("skill_profs", ())),
         "expertise": list(c.get("expertise", ())),
         "hp_max": c["hp"].get("max"), "hp_current": c["hp"].get("current"), "hp_temp": c["hp"].get("temp", 0),
         "ac": c.get("ac"), "speed": c.get("speed", 30),
         "equipment": "\n".join(("%d x %s" % (i["qty"], i["name"])) if i["qty"] != 1 else i["name"]
                                for i in c.get("equipment", ())),
         "spells": "\n".join(str(x) for x in c.get("spells", ())),
         "features": "\n".join(str(x) for x in c.get("features", ())), "notes": c.get("notes", "")}
    odd = [k["hit_die"] for k in c["classes"] if k.get("hit_die") and not HIT_DIE.get(k["name"].lower())]
    d["hit_die"] = odd[0] if odd else ""
    for a in ABILITIES:
        d[a] = c["abilities"].get(a)
    for k in ("cp", "sp", "ep", "gp", "pp"):
        d[k] = c.get("coins", {}).get(k, 0)
    return d


def from_form(d, old=None):
    """A whole sheet typed into the phone form -> (character, things to check).
    old is the saved character being edited, if any: its history, its hit point
    record and what is worn or attuned are kept. Raises ValueError with a plain
    message when there is too little to make a character."""
    name = " ".join(str(d.get("name") or "").split())[:40]
    if not name:
        raise ValueError("The character needs a name.")
    classes = parse_class_level(d.get("classlevel") or "")
    if not classes:
        raise ValueError("Give the class and level, like Fighter 3. For two classes: Fighter 3 / Rogue 2.")
    die = _int(d.get("hit_die") or "")
    for k in classes:
        k["level"] = max(1, min(20, k["level"]))
        if not k["hit_die"] and die in (6, 8, 10, 12):
            k["hit_die"] = die
    num = lambda key: _int("" if d.get(key) is None else d.get(key))
    ab = {a: num(a) for a in ABILITIES}

    def picked(key, allowed, default=()):
        got = d.get(key)
        if got is None:
            return list(default)
        got = [str(x).lower() for x in (got if isinstance(got, list) else [got])]
        return [x for x in allowed if x in got]
    text = lambda key, n=40: " ".join(str(d.get(key) or "").split())[:n]
    hp_max, hp_cur = num("hp_max"), num("hp_current")
    c = {"format": 1, "name": name, "player": text("player"),
         "edition": "2014" if str(d.get("edition")) == "2014" else "2024",
         "species": text("species"), "background": text("background"), "classes": classes, "abilities": ab,
         "save_profs": picked("saves", ABILITIES, SAVES.get(classes[0]["name"].lower(), ())),
         "skill_profs": picked("skills", sorted(SKILLS)), "expertise": picked("expertise", sorted(SKILLS)),
         "hp": {"max": hp_max, "current": hp_cur if hp_cur is not None else (hp_max or 0),
                "temp": max(0, num("hp_temp") or 0), "gains": []},
         "hit_dice_spent": 0, "ac": num("ac"), "ac_note": "typed in", "speed": num("speed") or 30,
         "equipment": parse_equipment(d.get("equipment"), [i["name"] for i in (old or {}).get("equipment", ())]),
         "coins": {k: max(0, num(k) or 0) for k in ("cp", "sp", "ep", "gp", "pp")},
         "slots_used": [], "pact_used": 0, "spells": [x[:80] for x in _lines(d.get("spells"))][:80],
         "features": [x[:120] for x in _lines(d.get("features"))][:80],
         "notes": str(d.get("notes") or "").strip()[:4000], "history": []}
    c["expertise"] = [x for x in c["expertise"] if x in c["skill_profs"]]
    if hp_max is not None and c["hp"]["current"] > hp_max:
        c["hp"]["current"] = hp_max
    if old:
        c["history"] = list(old.get("history", ()))
        c["hp"]["gains"] = list(old.get("hp", {}).get("gains", ()))
        for key in ("hit_dice_spent", "slots_used", "pact_used"):
            c[key] = old.get(key, c[key])
        for key in ("reviewed", "benched", "needs_review", "id"):    # what the box itself decided or stamped: an edit keeps it
            if key in old:
                c[key] = old[key]
        if old.get("ac") == c["ac"]:
            c["ac_note"] = old.get("ac_note", "")
        for item in c["equipment"]:
            was = find_item(old, item["name"])
            if was:
                for key in ("equipped", "attuned", "magic", "needs_attunement", "notes"):
                    item[key] = was.get(key, item[key])
        log(c, "Edited on the phone")
    else:
        log(c, "Typed in: %s, %s" % (name, class_text(c)))
    return c, check(c)


def from_fields(fields):
    """Turn {pdf field name: text} into (character, warnings, unused field names).
    Nothing is trusted: the result always goes to the review screen."""
    got, unused = {}, []
    for raw_name, value in fields.items():
        if value in (None, ""):
            continue
        key = FIELD_MAP.get(_norm(raw_name))
        if key and key not in got:
            got[key] = str(value).strip()
        elif not key:
            unused.append(raw_name)
    warn = []
    ab = {}
    for a in ABILITIES:
        score, mod = _int(got.get("score:" + a, "")), _int(got.get("mod:" + a, ""))
        # Some sheets print the modifier in the big box and the score in the
        # small one. A "score" under 6 with a "modifier" of 6 or more is swapped.
        if score is not None and mod is not None and abs(score) <= 5 and mod >= 6:
            score, mod = mod, score
            warn.append("%s: the sheet had score and modifier the other way round; I swapped them." % ABILITY_NAMES[a])
        if score is not None and mod is not None and ability_mod(score) != mod:
            warn.append("%s %d should give a modifier of %+d, but the sheet says %+d." %
                        (ABILITY_NAMES[a], score, ability_mod(score), mod))
        ab[a] = score
    classes = parse_class_level(got.get("classlevel", ""))
    if classes and "levelonly" in got and len(classes) == 1 and _int(got["levelonly"]):
        classes[0]["level"] = _int(got["levelonly"])
    if not classes:
        warn.append("I could not read the class and level.")
        classes = [{"name": "Unknown", "subclass": None, "level": 1, "hit_die": None}]
    for k in classes:
        if not 1 <= k["level"] <= 20:
            warn.append("The sheet says level %d for %s; levels run from 1 to 20, so I used %d." %
                        (k["level"], k["name"], max(1, min(20, k["level"]))))
            k["level"] = max(1, min(20, k["level"]))
    c = {"format": 1, "name": got.get("name", ""), "player": got.get("player", ""), "edition": "2014",
         "species": got.get("species", ""), "background": got.get("background", ""),
         "classes": classes, "abilities": ab,
         "save_profs": list(SAVES.get(classes[0]["name"].lower(), ())), "skill_profs": [], "expertise": [],
         "hp": {"max": _int(got.get("hpmax", "")), "current": _int(got.get("hpcur", "")),
                "temp": _int(got.get("hptemp", "")) or 0, "gains": []},
         "hit_dice_spent": 0, "ac": _int(got.get("ac", "")), "ac_note": "from the uploaded sheet",
         "speed": _int(got.get("speed", "")) or 30, "equipment": [],
         "coins": {k: _int(got.get(k, "")) or 0 for k in ("cp", "sp", "ep", "gp", "pp")},
         "slots_used": [], "pact_used": 0, "spells": [], "features": [],
         "notes": got.get("notes", ""), "history": []}
    if c["hp"]["current"] is None:
        c["hp"]["current"] = c["hp"]["max"] or 0
    c["equipment"] = parse_equipment(got.get("equipment", ""))
    warn.append("Skill and saving throw proficiencies are not read from the sheet. Tick them on the review screen.")
    warn += check(c)
    return c, warn, sorted(unused)


def import_pdf_fields(path):
    """Read a fillable PDF character sheet. A flat (printed or scanned) PDF
    has no fields and cannot be read this way."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support needs pypdf:  pip install pypdf")
    with open(path, "rb") as f:                          # an open file: pypdf reads from disk as it goes
        fields = PdfReader(f).get_fields() or {}
    flat = {name: f.get("/V") for name, f in fields.items()}
    flat = {k: (v if isinstance(v, str) else str(v)) for k, v in flat.items() if v is not None}
    if not flat:
        raise ValueError("this PDF has no filled-in form fields. Use the photo route or type the sheet in.")
    c, warn, unused = from_fields(flat)
    log(c, "Imported from %s" % os.path.basename(path))
    return c, warn, unused


def show(c):
    d = derived(c)
    lines = ["%s (%s) - %s, level %d" % (c["name"], c.get("player", ""), d["class_line"], d["level"]),
             "HP %s/%s  AC %s  Speed %s  Proficiency +%d  Initiative %+d  Passive Perception %d" % (
                 c["hp"]["current"], c["hp"]["max"], c.get("ac"), c.get("speed"),
                 d["proficiency_bonus"], d["initiative"], d["passive_perception"]),
             "  ".join("%s %d (%+d)" % (a.upper(), c["abilities"][a], d["mods"][a]) for a in ABILITIES)]
    if d["spell_slots"]:
        lines.append("Spell slots: " + slots_text(d["spell_slots"]))
    if c["equipment"]:
        lines.append("Gear: " + ", ".join(("%d x " % i["qty"] if i["qty"] != 1 else "") + i["name"] +
                                          (" [attuned]" if i["attuned"] else "") for i in c["equipment"]))
    lines.append("Coins: " + (", ".join("%d %s" % (v, k) for k, v in c["coins"].items() if v) or "none"))
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "import":
        ch, warnings, unused_fields = import_pdf_fields(a[1])
        print(show(ch) if not any(v is None for v in ch["abilities"].values()) else ch["name"])
        print("\nCheck these:")
        for w in warnings:
            print(" -", w)
        print("\nSaved to", save(ch, a[2]), "(%d sheet fields not used)" % len(unused_fields))
    elif len(a) == 2 and a[0] == "show":
        print(show(load(a[1])))
    else:
        print(__doc__)
