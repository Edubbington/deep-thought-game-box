"""D&D screens for the screenshot run. Everything is made in a throwaway data
folder, so the real characters and campaign notes are never touched."""
import os
import random
import shutil
import tempfile

from ...engine import Session
from ...screens.common import Pages, Setup
from . import dm, dmtools, party
from .party import ch
from .plugin import AddCombatant, Combatant, CombatantMore, ConcPrompt, Conditions
from .sheets import Coins, Gear, LevelUp, Party, PhoneHandoff, Review, Sheet
from .ui import NumberPad

AB = {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 12, "cha": 8}


def demo_party():
    """Three made-up characters and one uploaded sheet waiting to be checked."""
    folder = party.folder()
    b = ch.new_character("Brakka", "Ethan", "Fighter", AB, species="Dwarf", edition="2024",
                         skill_profs=["athletics", "perception"])
    ch.level_up(b), ch.level_up(b)
    b["ac"] = 18
    for name, qty, worn in (("Chain mail", 1, True), ("Shield", 1, True), ("Longsword", 1, True), ("Torch", 5, False),
                            ("Old ring", 1, False), ("Rope", 1, False)):
        ch.add_item(b, name, qty, needs_attunement=name == "Old ring")
        ch.equip(b, name, worn)
    ch.attune(b, "Old ring")
    ch.add_coins(b, gp=40, sp=12)
    w = ch.new_character("Wren", "Sam", "Wizard", dict(AB, str=8, int=16, dex=14), species="Elf", edition="2024")
    ch.level_up(w), ch.level_up(w)
    w["ac"] = 12
    s = ch.new_character("Sel", "Priya", "Rogue", dict(AB, str=10, dex=16), species="Halfling", edition="2024")
    ch.level_up(s), ch.level_up(s)
    s["ac"] = 14
    for c in (b, w, s):
        ch.save(c, folder)
    up, _, _ = ch.from_fields({"CharacterName": "Dorn", "PlayerName": "Trevor", "ClassLevel": "Cleric 2", "Race": "Human",
                               "STR": "14", "DEX": "10", "CON": "13", "INT": "10", "WIS": "16", "CHA": "12",
                               "HPMax": "15", "HPCurrent": "15"})
    ch.log(up, "Imported from Dorn.pdf")
    ch.save(up, folder)


def shots(app, snap):
    game = app.plugins["dnd"]
    keep_env, keep_dm = os.environ.get("DT_DATA"), app.dm
    tmp = tempfile.mkdtemp()
    os.environ["DT_DATA"] = tmp
    try:
        _shots(app, snap, game)
    finally:
        app.dm = keep_dm
        if keep_env is None:
            os.environ.pop("DT_DATA", None)
        else:
            os.environ["DT_DATA"] = keep_env
        shutil.rmtree(tmp, ignore_errors=True)


def _shots(app, snap, game):
    app.dm = False
    demo_party()
    snap("dnd-setup", Setup(app, game))
    s = Session(game, ["Ethan", "Sam", "Priya", "Trevor"], {"edition": "2024"})
    ids = {c["name"]: c["id"] for c in s.state["combatants"]}
    snap("dnd-before-the-fight", game.play_screen(app, s))
    snap("dnd-add", AddCombatant(app, s))
    snap("dnd-number-pad", NumberPad(app, "Initiative", lambda n: None,
                                     "Initiative for Goblin: the d20 plus the Dexterity modifier.", low=-10, high=50,
                                     negative=True, skip=("Enter it later", lambda: None), start=14))
    for name, init in (("Sel", 19), ("Brakka", 17), ("Wren", 11)):
        s.do(ev="init", who=ids[name], value=init)
    s.do(ev="add", kind="enemy", base="Goblin boss", count=1, init=14, numbered=False, hp=18)
    s.do(ev="add", kind="enemy", base="Goblin", count=3, init=8, hp=6)
    s.do(ev="add", kind="enemy", base="Wolf", count=2, init=15, hidden=True, hp=9)
    ids.update({c["name"]: c["id"] for c in s.state["combatants"]})
    s.do(ev="cond", who=ids["Goblin boss"], name="Poisoned")
    s.do(ev="conc", who=ids["Wren"], on=True)
    s.do(ev="cond", who=ids["Wren"], name="Prone")
    for _ in range(2 * 9 + 2):                      # into round 3, Brakka's turn
        s.do(ev="next")
    s.do(ev="damage", who=ids["Goblin 1"], amount=5)
    snap("dnd-initiative", game.play_screen(app, s))
    app.screen.turn_page(0, 2)
    snap("dnd-initiative-page-2")
    snap("dnd-combatant", Combatant(app, s, ids["Wren"]))
    snap("dnd-conditions", Conditions(app, s, ids["Wren"]))
    snap("dnd-damage-pad", NumberPad(app, "Damage", lambda n: None, "How much damage does Wren take? Temporary hit "
                                     "points go first. Then I work out the concentration save.", low=1, start=22))
    s.do(ev="damage", who=ids["Wren"], amount=9)
    snap("dnd-concentration", ConcPrompt(app, s, s.state["prompts"][0]))
    snap("dnd-save-waiting", game.play_screen(app, s))
    s.do(ev="conc_save", who=ids["Wren"], passed=True)
    s.do(ev="damage", who=ids["Sel"], amount=30)
    s.do(ev="save", who=ids["Sel"], passed=True)
    s.do(ev="save", who=ids["Sel"], passed=False)
    snap("dnd-death-saves", Combatant(app, s, ids["Sel"]))
    snap("dnd-combatant-more", CombatantMore(app, s, ids["Brakka"]))
    snap("dnd-enemy-player-view", Combatant(app, s, ids["Goblin 1"]))
    snap("dnd-party", Party(app, s))
    snap("dnd-phone", PhoneHandoff(app, s))
    snap("dnd-sheet", Sheet(app, s, "brakka.json"))
    snap("dnd-gear", Gear(app, s, "brakka.json"))
    snap("dnd-coins", Coins(app, s, "brakka.json"))
    snap("dnd-level-up", LevelUp(app, s, "brakka.json"))
    snap("dnd-review", Review(app, s, "dorn.json"))
    snap("dnd-how-to-play", Pages(app, game.name, "How to play", [(x["title"], x["text"]) for x in game.teach()]))

    # ---- DM mode
    app.dm = True
    name = dm.current()
    camp = dm.load(name)
    camp["sessions"] = [{"n": 3, "date": "2026-11-13", "lines": [
        "[YOUR NOTES] The party took the job at the mine.", "They owe the innkeeper a favour.",
        "Stopped at the foot of the hill."]}]
    camp["position"] = {"quest": camp["quests"][2]["name"], "booklet_page": 12}
    camp["people"][0]["met"], camp["people"][0]["attitude"] = True, "wary"
    camp["people"][1]["met"] = True
    dm.save(camp, name)
    s.do(ev="prep", i=0)
    s.do(ev="prep", i=2)
    snap("dnd-dm-initiative", game.play_screen(app, s))
    snap("dnd-dm-combatant", Combatant(app, s, ids["Goblin 1"]))
    desk = snap("dnd-dm-desk", dm.Desk(app, s))
    desk.recap()
    snap("dnd-dm-recap")
    snap("dnd-dm-prep", dm.Prep(app, s))
    snap("dnd-dm-people", dm.People(app, s))
    snap("dnd-dm-person", dm.Person(app, s, 0))
    snap("dnd-dm-quests", dm.Quests(app, s))
    snap("dnd-dm-quest", dm.Quest(app, s, 2))
    loader = snap("dnd-dm-fights", dm.FightLoader(app, s))
    loader.draft = [{"name": "Ogre", "count": 1, "hp": 40}, {"name": "Orc", "count": 4, "hp": None}]
    loader.refresh()
    snap("dnd-dm-fights-ready")
    log = snap("dnd-dm-log", dm.Log(app, s))
    log.flip()
    snap("dnd-dm-log-last-time")
    _tool_shots(app, snap, s)
    app.toast = None


# A made-up page, standing in for one from the DM's own loaded book. The creature and
# every number are invented for these pictures.
DEMO_PAGE = {"title": "My Monster Book, p. 41", "heading": "Grobnar", "dm_only": False,
             "body": "Grobnar\nA squat, grumbling thing that lives under bridges and collects lost boots.\n"
                     "Armor Class 13\nHit Points 27\nSpeed 30 ft.\nSTR DEX CON INT WIS CHA\n"
                     "14 (+2) 12 (+1) 13 (+1) 6 (-2) 10 (+0) 7 (-2)\n"
                     "Boot Toss. The grobnar throws a boot. It is not a good boot."}


def _tool_shots(app, snap, s):
    """Improvise, the calendar, treasure, roll tables and the monster page."""
    name = dm.current()
    camp = dm.load(name)
    camp["calendar"].update(day=12, date="Third week of harvest")
    camp["calendar"]["notes"] = [{"day": 9, "text": "The bridge toll doubled."},
                                 {"day": 11, "text": "Long rest."},
                                 {"day": 12, "text": "Promised the miller an answer by market day."}]
    camp["treasure"] = [{"name": "Silver hand mirror", "holder": "Wren", "day": 4},
                        {"name": "Map with a corner missing", "holder": None, "day": 9},
                        {"name": "Three odd keys", "holder": "Sel", "day": 12}]
    camp["party_coins"].update(gp=140, sp=35, cp=8)
    camp["tables"] = {"Weather": {"die": 6, "rows": [                       # made up for the pictures
        {"lo": 1, "hi": 2, "text": "Clear and cold. Sound carries a long way tonight."},
        {"lo": 3, "hi": 4, "text": "Low cloud and a steady drizzle. Tracks are easy to follow."},
        {"lo": 5, "hi": 5, "text": "Fog until noon."}, {"lo": 6, "hi": 6, "text": "A hard wind from the hills."}]}}
    dm.save(camp, name)
    desk = dm.Desk(app, s)
    desk.tools = True
    snap("dnd-dm-desk-tools", desk)
    imp = snap("dnd-dm-improvise", dmtools.Improvise(app, s, random.Random(7)))
    imp.set_kind("shop")
    imp.keep()
    app.toast = None
    snap("dnd-dm-improvise-shop-kept")
    imp.set_kind("rumour")
    imp.item = dict(imp.item, source="cloud")                 # how a cloud answer is labelled; none was asked for
    snap("dnd-dm-improvise-rumour-cloud")
    imp.waiting = True
    snap("dnd-dm-improvise-waiting")
    cal = snap("dnd-dm-calendar", dmtools.Calendar(app, s))
    cal.open(next(k for k, n in enumerate(cal.camp["calendar"]["notes"]) if n.get("invented")))
    snap("dnd-dm-calendar-note")
    snap("dnd-dm-treasure", dmtools.Treasure(app, s))
    item = snap("dnd-dm-treasure-item", dmtools.TreasureItem(app, s, 0))
    item.remove()
    snap("dnd-dm-treasure-remove")
    snap("dnd-dm-party-coins", dmtools.PartyCoins(app, s))
    snap("dnd-dm-tables", dmtools.Tables(app, s))
    snap("dnd-dm-table-not-copied-in", dmtools.RollTable(app, s, "Dragon"))
    table = snap("dnd-dm-table-ready", dmtools.RollTable(app, s, "Weather", random.Random(3)))
    table.roll()
    app.toast = None
    snap("dnd-dm-table-rolled")
    book = snap("dnd-dm-monster-book", dmtools.MonsterBook(app, s, "Grobnar", 2, [DEMO_PAGE, dict(DEMO_PAGE, body="")],
                                                           lambda hp, ac, bonus: None))
    book.set("bonus")
    snap("dnd-dm-monster-number")
    loader = dm.FightLoader(app, s)
    loader.draft = [{"name": "Grobnar", "count": 2, "hp": 27, "ac": 13, "init_bonus": 1},
                    {"name": "Orc", "count": 4, "hp": None}]
    snap("dnd-dm-fights-from-book", loader)
