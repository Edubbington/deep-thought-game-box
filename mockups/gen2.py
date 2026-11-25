import json, warnings; warnings.filterwarnings("ignore")
exec(open("gen.py").read().replace("print(flat)",""))
B3="#8FE3A0"; B4="#F29BD4"
N={}
def chiprow(items,cur):
    out='<div style="display: flex; gap: 6px">'
    for it in items:
        s=it==cur; out+=f'<div style="flex: 1; text-align: center; padding: 8px 0; border-radius: 10px; font-size: 22px; font-weight: 600; background: {TX if s else P}; color: {G if s else DIM}; border: 1px solid {TX if s else LN}">{it}</div>'
    return out+'</div>'
# ================= 40k
N["W40kPlay"]=("40k: main play screen",strip("40k · Battle round 2 of 5","Shooting phase",("Ethan&#39;s turn",B1))+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 12px">
{chiprow(["Command","Move","Shoot","Charge","Fight"],"Shoot")}
<div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 6px">
<div style="font-family: {HF}; font-size: 40px; font-weight: 700; line-height: 1.1">Ethan, pick a unit to shoot with.</div>
<div style="font-size: 24px; color: {DIM}">Roll to hit, then to wound. Trevor rolls the saves.</div>
</div>
<div style="display: flex; gap: 14px">
{num("Victory points",18,12)}
{num("Command points",2,3)}
</div>
<div style="display: flex; gap: 10px">
{btn("Next phase",primary=True,flex="1.6",fs=22)}
{btn("Score",flex="1",fs=22)}
{btn("Unit lost",flex="1.5",fs=22)}
{btn("Undo",flex="0.9",fs=22)}
{btn("Lookup",flex="1.15",fs=22)}
</div>
</div>''')
N["W40kScore"]=("40k: scoring in the Command phase",strip("40k · Battle round 3 of 5","Score this turn",("Trevor&#39;s turn",B2))+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: grid; grid-template-columns: 190px 1fr 1fr; gap: 12px; font-family: {HF}; font-size: 24px; font-weight: 700"><div></div><div style="text-align: center; color: {B1}">Ethan</div><div style="text-align: center; color: {B2}">Trevor</div></div>
<div style="display: grid; grid-template-columns: 190px 1fr 1fr; align-items: center; gap: 12px"><div style="font-size: 24px; font-weight: 600">Primary</div><div style="display: flex; justify-content: center">{stepper("15",B1)}</div><div style="display: flex; justify-content: center">{stepper("10",B2)}</div></div>
<div style="display: grid; grid-template-columns: 190px 1fr 1fr; align-items: center; gap: 12px"><div style="font-size: 24px; font-weight: 600">Secondary</div><div style="display: flex; justify-content: center">{stepper("8",B1)}</div><div style="display: flex; justify-content: center">{stepper("7",B2)}</div></div>
<div style="display: grid; grid-template-columns: 190px 1fr 1fr; align-items: center; gap: 12px"><div style="font-size: 24px; color: {DIM}">Total</div><div style="text-align: center; font-family: {HF}; font-size: 44px; font-weight: 700; color: {B1}">23</div><div style="text-align: center; font-family: {HF}; font-size: 44px; font-weight: 700; color: {B2}">17</div></div>
<div style="flex: 1"></div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 14px">
<span style="font-size: 22px; color: {DIM}">Your mission cards say what scores</span>
{btn("Done",primary=True,w="260px",h=68)}
</div>
</div>''')
def wrow(a,b,hl=False): return f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 16px; border-radius: 10px; background: {P2 if hl else "transparent"}; border: 1px solid {LN if hl else "transparent"}"><span style="font-size: 24px">{a}</span><span style="font-family: {HF}; font-size: 30px; font-weight: 700">{b}</span></div>'
N["W40kRef"]=("40k: reference card (wound roll)",strip("40k · Reference","Wound roll","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 6px">
<div style="font-size: 22px; color: {DIM}">Compare the weapon&#39;s Strength with the target&#39;s Toughness.</div>
{wrow("Strength is double the Toughness, or more","2+")}
{wrow("Strength is higher","3+")}
{wrow("Strength and Toughness are equal","4+",True)}
{wrow("Strength is lower","5+")}
{wrow("Strength is half the Toughness, or less","6+")}
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Previous card",h=64,flex="1",fs=22)}
{btn("Read aloud",h=64,flex="1",fs=22)}
{btn("Next card",h=64,flex="1",fs=22)}
{btn("Close",primary=True,h=64,w="150px")}
</div>
</div>''')
def unit(name,role,state):
    dead=state=="Destroyed"
    return f'''<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 16px; height: 64px; background: {P}; border: 1px solid {LN}; border-radius: 12px">
<div style="display: flex; flex-direction: column"><span style="font-size: 24px; font-weight: 600; color: {DIM if dead else TX}">{name}</span></div>
<span style="font-size: 22px; color: {DIM}">{role}</span>
<button type="button" style="height: 48px; padding: 0 16px; border-radius: 10px; font-size: 22px; font-weight: 600; background: {G if dead else P2}; color: {DIM if dead else TX}; border: 1px solid {LN}">{state}</button>
</div>'''
N["W40kArmy"]=("40k: your army tracker",strip("40k · Ethan&#39;s Necrons","Army","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 8px">
{unit("Warriors and Overlord","Hold the middle","18 of 20")}
{unit("Lychguard","Bodyguard","Full")}
{unit("Triarch Praetorians","In reserve","Full")}
{unit("Canoptek Doomstalker","Big gun","Destroyed")}
<div style="flex: 1"></div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 14px">
<span style="font-size: 22px; color: {DIM}">Showing 4 of 7 units</span>
{btn("More units",h=64,w="200px",fs=22)}
{btn("Back",primary=True,h=64,w="150px")}
</div>
</div>''')
# ================= D&D
def irow(init,name,note,cur=False,tag=None,dim=False):
    t=f'<span style="font-size: 22px; padding: 4px 12px; border-radius: 999px; border: 1px solid {LN}; color: {TX}">{tag}</span>' if tag else ''
    return f'''<div style="display: flex; align-items: center; gap: 14px; height: 54px; padding: 0 16px; border-radius: 12px; background: {P2 if cur else P}; border: {"3px solid "+TX if cur else "1px solid "+LN}">
<span style="font-family: {HF}; font-size: 30px; font-weight: 700; width: 44px; color: {DIM if dim else TX}">{init}</span>
<span style="font-size: 26px; font-weight: 600; flex: 1; color: {DIM if dim else TX}">{name}</span>
{t}
<span style="font-size: 22px; color: {DIM}; width: 150px; text-align: right">{note}</span>
</div>'''
N["DndInit"]=("D&D: initiative tracker",strip("D&amp;D · Round 3","Initiative",("Brakka&#39;s turn",B1))+f'''<div style="flex: 1; padding: 10px 20px; display: flex; flex-direction: column; gap: 6px">
{irow(19,"Sel","Rogue",dim=True)}
{irow(17,"Brakka","Fighter",cur=True)}
{irow(14,"Goblin boss","Enemy",tag="Poisoned")}
{irow(11,"Wren","Wizard",tag="Concentrating")}
{irow(8,"Goblins (3)","Enemy")}
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Next turn",primary=True,h=68,flex="1.5",fs=22)}
{btn("Damage",h=68,flex="1.1",fs=22)}
{btn("Condition",h=68,flex="1.5",fs=22)}
{btn("Add",h=68,flex="0.8",fs=22)}
{btn("Lookup",h=68,flex="1.1",fs=22)}
</div>
</div>''')
def box3(n,filled):
    return '<div style="display: flex; gap: 10px">'+"".join(f'<div style="width: 44px; height: 44px; border-radius: 10px; border: 2px solid {TX}; background: {TX if i<filled else "transparent"}"></div>' for i in range(n))+'</div>'
N["DndCombatant"]=("D&D: one character in a fight",strip("D&amp;D · Round 3","Wren, Wizard","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; gap: 14px">
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 6px">
<div style="font-size: 22px; color: {DIM}">Concentrating on</div>
<div style="font-family: {HF}; font-size: 30px; font-weight: 700">Web</div>
<div style="font-size: 22px">If Wren takes damage: Constitution save, DC 10 or half the damage.</div>
</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 8px">
<div style="font-size: 22px; color: {DIM}">Conditions</div>
<div style="display: flex; gap: 8px; flex-wrap: wrap"><span style="font-size: 22px; padding: 6px 14px; border-radius: 999px; border: 1px solid {TX}">Prone</span></div>
<div style="font-size: 22px">Standing up costs half her movement.</div>
</div>
</div>
<div style="background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px">
<span style="font-size: 22px; color: {DIM}">Death saves</span>
<div style="display: flex; align-items: center; gap: 12px"><span style="font-size: 22px">Passed</span>{box3(3,0)}</div>
<div style="display: flex; align-items: center; gap: 12px"><span style="font-size: 22px">Failed</span>{box3(3,0)}</div>
</div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Condition",h=64,flex="1",fs=22)}
{btn("Drop spell",h=64,flex="1",fs=22)}
{btn("Damage",h=64,flex="1",fs=22)}
{btn("Back",primary=True,h=64,w="130px")}
</div>
</div>''')
def chk(t,done=False): return f'<div style="display: flex; align-items: center; gap: 12px; font-size: 22px; color: {DIM if done else TX}"><div style="width: 28px; height: 28px; border-radius: 6px; border: 2px solid {TX}; background: {TX if done else "transparent"}; flex-shrink: 0"></div><span>{t}</span></div>'
N["DndCampaign"]=("D&D: Dungeon Master campaign screen",strip("D&amp;D · DM only","Session 4","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; gap: 14px; flex: 1">
<div style="flex: 1.2; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 8px">
<div style="font-size: 22px; color: {DIM}">Tonight: Chapter 2 [YOUR CAMPAIGN]</div>
{chk("Recap read aloud",True)}
{chk("Map and tokens out")}
{chk("Next fight loaded")}
{chk("Hand out the letter")}
</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 6px">
<div style="font-size: 22px; color: {DIM}">Your notes from last time</div>
<div style="font-size: 22px; line-height: 1.3">[YOUR NOTES] The party took the job and owes the innkeeper a favour.</div>
</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Fight",primary=True,h=68,flex="1",fs=22)}
{btn("People",h=68,flex="1",fs=22)}
{btn("Monsters",h=68,flex="1.2",fs=22)}
{btn("Rules",h=68,flex="1",fs=22)}
{btn("Log",h=68,flex="0.8",fs=22)}
</div>
</div>''')
N["DndLookup"]=("D&D: rules lookup card",strip("D&amp;D · Rules","Lookup","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; gap: 8px">{tab("Conditions",True)}{tab("Spells",False)}{tab("Monsters",False)}{tab("Items",False)}<div style="flex: 1"></div>{tab("Search",False)}</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 16px; padding: 14px 20px; display: flex; flex-direction: column; gap: 8px">
<div style="font-family: {HF}; font-size: 34px; font-weight: 700">Restrained</div>
<div style="font-size: 24px; line-height: 1.35">Speed is 0. Its attacks have Disadvantage. Attacks against it have Advantage. It has Disadvantage on Dexterity saves.</div>
<div style="flex: 1"></div>
<div style="font-size: 22px; color: {DIM}">From the free rules document, SRD 5.2.1</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Read aloud",h=64,flex="1")}
{btn("Put on a character",h=64,flex="1.5",fs=22)}
{btn("Close",h=64,w="150px")}
</div>
</div>''')
# ================= Magic
def lifecol(name,c,life,sub):
    b=f'height: 72px; width: 96px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 14px; font-size: 36px; font-weight: 600'
    return f'''<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 18px; padding: 12px 18px; display: flex; flex-direction: column; align-items: center; gap: 4px">
<div style="font-family: {HF}; font-size: 30px; font-weight: 700; color: {c}">{name}</div>
<div style="font-family: {HF}; font-size: 128px; font-weight: 700; line-height: 1; color: {c}">{life}</div>
<div style="font-size: 22px; color: {DIM}">{sub}</div>
<div style="display: flex; gap: 14px"><button type="button" aria-label="Lose 1 life" style="{b}">&minus;</button><button type="button" aria-label="Gain 1 life" style="{b}">+</button></div>
</div>'''
N["MtgLife"]=("Magic: two-player life totals",strip("Magic · Turn 6","Declare blockers",("Ethan&#39;s turn",B1))+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="flex: 1; display: flex; gap: 14px">
{lifecol("Ethan",B1,20,"No poison")}
{lifecol("Trevor",B2,14,"Poison 2")}
</div>
<div style="display: flex; gap: 10px">
{btn("Next step",primary=True,h=64,flex="1.4",fs=22)}
{btn("Counters",h=64,flex="1.1",fs=22)}
{btn("Card",h=64,flex="0.8",fs=22)}
{btn("Undo",h=64,flex="0.8",fs=22)}
{btn("Dice",h=64,flex="0.8",fs=22)}
</div>
</div>''')
def pcell(name,c,life,sub,cur=False):
    return f'''<button type="button" style="background: {P2 if cur else P}; border: {"3px solid "+TX if cur else "1px solid "+LN}; border-radius: 16px; padding: 8px 18px; display: flex; align-items: center; justify-content: space-between; color: {TX}; text-align: left">
<span style="display: flex; flex-direction: column; gap: 2px"><span style="font-family: {HF}; font-size: 28px; font-weight: 700; color: {c}">{name}</span><span style="font-size: 22px; color: {DIM}">{sub}</span></span>
<span style="font-family: {HF}; font-size: 84px; font-weight: 700; line-height: 1; color: {c}">{life}</span>
</button>'''
N["MtgCommander"]=("Magic: Commander, four players",strip("Commander · Turn 9","Main phase",("Sam&#39;s turn",B3))+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="flex: 1; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px">
{pcell("Ethan",B1,34,"Commander 9/21")}
{pcell("Trevor",B2,27,"Commander 14/21")}
{pcell("Sam",B3,40,"Monarch",True)}
{pcell("Jo",B4,19,"Poison 3")}
</div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px">
<span style="font-size: 22px; color: {DIM}">Tap a player to change life or damage</span>
{btn("Next turn",primary=True,h=64,w="220px")}
</div>
</div>''')
def cd(name,c,val,warn=False):
    b=f'height: 64px; width: 64px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-size: 30px; font-weight: 600'
    return f'''<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 68px; padding: 0 16px; background: {P}; border: 1px solid {LN}; border-radius: 12px">
<span style="font-size: 24px">From <span style="color: {c}; font-weight: 600">{name}&#39;s</span> commander</span>
<span style="font-size: 22px; color: {TX if warn else DIM}">{"7 to knockout" if warn else ""}</span>
<span style="display: flex; align-items: center; gap: 10px"><button type="button" aria-label="One less" style="{b}">&minus;</button><span style="font-family: {HF}; font-size: 38px; font-weight: 700; width: 56px; text-align: center">{val}</span><button type="button" aria-label="One more" style="{b}">+</button></span>
</div>'''
N["MtgCmdDamage"]=("Magic: commander damage for one player",strip("Commander · Turn 9","Trevor","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 8px">
<div style="display: flex; align-items: baseline; justify-content: space-between"><span style="font-size: 22px; color: {DIM}">Life</span><span style="font-family: {HF}; font-size: 64px; font-weight: 700; line-height: 1; color: {B2}">27</span><span style="font-size: 22px; color: {DIM}">21 from one commander is a knockout</span></div>
{cd("Ethan",B1,14,True)}
{cd("Sam",B3,3)}
{cd("Jo",B4,0)}
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Life",h=64,flex="1")}
{btn("Poison and counters",h=64,flex="1.6",fs=22)}
{btn("Back",primary=True,h=64,w="150px")}
</div>
</div>''')
N["MtgCard"]=("Magic: card lookup",strip("Magic · Cards","Lookup","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; gap: 10px; align-items: center">
<label for="c" style="font-size: 22px; color: {DIM}">Card name</label>
<input id="c" type="text" value="llanowar" style="flex: 1; height: 64px; box-sizing: border-box; padding: 0 18px; background: {P}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-family: inherit; font-size: 26px">
</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 16px; padding: 12px 20px; display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span style="font-family: {HF}; font-size: 32px; font-weight: 700">Llanowar Elves</span><span style="font-size: 24px">Cost: one green</span></div>
<div style="font-size: 22px; color: {DIM}">Creature: Elf Druid · 1/1</div>
<div style="font-size: 24px; line-height: 1.35">Tap: add one green mana.</div>
<div style="flex: 1"></div>
<div style="font-size: 22px; color: {DIM}">Legal in Commander · 1 ruling · Card data from Scryfall</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Rulings",h=64,flex="1",fs=22)}
{btn("Read aloud",h=64,flex="1.2",fs=22)}
{btn("Ask about it",h=64,flex="1.3",fs=22)}
{btn("Close",h=64,w="130px")}
</div>
</div>''')
rows=[("row3","Warhammer 40,000",2700,["W40kPlay","W40kScore","W40kRef","W40kArmy"]),("row4","Dungeons & Dragons",3600,["DndInit","DndCombatant","DndCampaign","DndLookup"]),("row5","Magic: The Gathering",4500,["MtgLife","MtgCommander","MtgCmdDamage","MtgCard"])]
idx=json.load(open("canvas_live.json"))
for key,title,y,names in rows:
    idx["notes"][key]={"x":0,"y":y-260,"text":title,"kind":"title1","maxW":3440}
    for c,n in enumerate(names):
        idx["boards"][f"{n}.dc.html"]={"x":c*880,"y":y,"w":800,"h":480,"title":N[n][0]}; idx["order"].append(f"{n}.dc.html")
        open(f"project/{n}.dc.html","w").write(page(N[n][0].replace("&","&amp;"),N[n][1]))
idx["notes"]["row1"]["text"]="Kill Team: during a game"
json.dump(idx,open("project/canvas.json","w"),indent=1); print(len(idx["boards"]))
