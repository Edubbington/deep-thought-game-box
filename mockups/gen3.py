import json, warnings; warnings.filterwarnings("ignore")
exec(open("gen.py").read().replace("print(flat)",""))
N={}
def prow(name,cls,hp,ac):
    return f'''<button type="button" style="height: 68px; padding: 0 18px; display: flex; align-items: center; gap: 14px; background: {P}; border: 1px solid {LN}; border-radius: 12px; color: {TX}; text-align: left">
<span style="font-size: 26px; font-weight: 600; flex: 1">{name}</span>
<span style="font-size: 22px; color: {DIM}; width: 150px">{cls}</span>
<span style="font-family: {HF}; font-size: 26px; font-weight: 700; width: 130px">HP {hp}</span>
<span style="font-family: {HF}; font-size: 26px; font-weight: 700; width: 90px">AC {ac}</span>
</button>'''
N["DndParty"]=("D&D: the party",strip("D&amp;D · Party","Characters","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
{prow("Brakka","Fighter 3","28/28",18)}
{prow("Wren","Wizard 3","11/17",12)}
{prow("Sel","Rogue 3","24/24",14)}
<div style="font-size: 22px; color: {DIM}">Tap a character to open the sheet.</div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("New character",primary=True,h=68,flex="1.3",fs=22)}
{btn("Upload a sheet",h=68,flex="1.3",fs=22)}
{btn("Back",h=68,flex="0.7",fs=22)}
</div>
</div>''')
N["DndPhone"]=("D&D: add a character from a phone",strip("D&amp;D · Party","Add a character","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="flex: 1; display: flex; gap: 20px; align-items: center">
<div style="width: 220px; height: 220px; flex-shrink: 0; border: 2px dashed {DIM}; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; color: {DIM}">[QR CODE]</div>
<div style="display: flex; flex-direction: column; gap: 10px">
<div style="font-family: {HF}; font-size: 30px; font-weight: 700; line-height: 1.15">Use a phone for this part.</div>
<div style="font-size: 22px; line-height: 1.35">1. Join the same Wi-Fi as the box.</div>
<div style="font-size: 22px; line-height: 1.35">2. Scan the code, or open [BOX ADDRESS].</div>
<div style="font-size: 22px; line-height: 1.35">3. Make a character, or upload a sheet as a PDF or a photo.</div>
</div>
</div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 14px">
<span style="font-size: 22px; color: {DIM}">New sheets appear here to be checked.</span>
{btn("Back",primary=True,h=64,w="150px")}
</div>
</div>''')
def abil(lbl,mod,score):
    return f'<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 12px; padding: 8px 0; display: flex; flex-direction: column; align-items: center"><span style="font-size: 22px; color: {DIM}">{lbl}</span><span style="font-family: {HF}; font-size: 40px; font-weight: 700; line-height: 1.1">{mod}</span><span style="font-size: 22px">{score}</span></div>'
def stat(lbl,val):
    return f'<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 12px; padding: 8px 0; display: flex; flex-direction: column; align-items: center; justify-content: center"><span style="font-size: 22px; color: {DIM}">{lbl}</span><span style="font-family: {HF}; font-size: 34px; font-weight: 700; line-height: 1.1">{val}</span></div>'
sb=f'height: 64px; width: 64px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-size: 30px; font-weight: 600'
N["DndSheet"]=("D&D: character sheet",strip("D&amp;D · Brakka","Fighter 3",("Ethan",B1))+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; gap: 8px">
{abil("STR","+3",16)}{abil("DEX","+1",12)}{abil("CON","+2",14)}{abil("INT","+0",10)}{abil("WIS","+1",12)}{abil("CHA","&minus;1",8)}
</div>
<div style="display: flex; gap: 8px">
<div style="flex: 3.6; background: {P}; border: 1px solid {LN}; border-radius: 12px; padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; gap: 8px">
<span style="font-size: 22px; color: {DIM}">Hit points</span>
<button type="button" aria-label="Lose 1 hit point" style="{sb}">&minus;</button>
<span style="font-family: {HF}; font-size: 40px; font-weight: 700">28/28</span>
<button type="button" aria-label="Gain 1 hit point" style="{sb}">+</button>
</div>
{stat("AC",18)}{stat("Prof.","+2")}{stat("Speed",25)}
</div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Gear",h=64,flex="1",fs=22)}
{btn("Spells",h=64,flex="1",fs=22)}
{btn("Level up",primary=True,h=64,flex="1.3",fs=22)}
{btn("History",h=64,flex="1.1",fs=22)}
{btn("Back",h=64,flex="0.9",fs=22)}
</div>
</div>''')
def grow(name,qty,state):
    pill=f'<span style="font-size: 22px; padding: 4px 14px; border-radius: 999px; border: 1px solid {TX if state else LN}; color: {TX if state else DIM}; width: 110px; text-align: center">{state or "Packed"}</span>'
    return f'<div style="height: 56px; padding: 0 16px; display: flex; align-items: center; gap: 14px; background: {P}; border: 1px solid {LN}; border-radius: 12px"><span style="font-size: 24px; flex: 1">{name}</span><span style="font-family: {HF}; font-size: 24px; font-weight: 700; width: 60px; text-align: right">{qty}</span>{pill}</div>'
N["DndGear"]=("D&D: gear and coins",strip("D&amp;D · Brakka","Gear","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 8px">
{grow("Chain mail","1","Worn")}
{grow("Shield","1","Worn")}
{grow("Ring of protection","1","Attuned")}
{grow("Torch","5","")}
<div style="display: flex; justify-content: space-between; font-size: 22px"><span>Coins: 40 gold, 12 silver</span><span style="color: {DIM}">Attuned to 1 of 3</span></div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Add item",primary=True,h=64,flex="1.2",fs=22)}
{btn("Coins",h=64,flex="1",fs=22)}
{btn("More gear",h=64,flex="1.2",fs=22)}
{btn("Back",h=64,flex="0.8",fs=22)}
</div>
</div>''')
def chk(t,done=False): return f'<div style="display: flex; align-items: flex-start; gap: 12px; font-size: 22px; line-height: 1.3; color: {DIM if done else TX}"><div style="width: 26px; height: 26px; margin-top: 1px; border-radius: 6px; border: 2px solid {TX}; background: {TX if done else "transparent"}; flex-shrink: 0"></div><span>{t}</span></div>'
N["DndLevelUp"]=("D&D: level up",strip("D&amp;D · Level up","Brakka: Fighter 4","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="flex: 1; display: flex; gap: 14px">
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 8px">
<div style="font-size: 22px; color: {DIM}">Hit points</div>
<div style="font-family: {HF}; font-size: 44px; font-weight: 700; line-height: 1.1">28 to 36</div>
<div style="font-size: 22px">Took 6, plus 2 for Constitution.</div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">{btn("Take 6",primary=True,h=64,flex="1",fs=22)}{btn("I rolled",h=64,flex="1",fs=22)}</div>
</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; flex-direction: column; gap: 8px">
<div style="font-size: 22px; color: {DIM}">What changes</div>
{chk("Raise ability scores, or pick a feat")}
{chk("Proficiency bonus stays +2",True)}
{chk("New features: read Fighter level 4 in your book")}
</div>
</div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px">
<span style="font-size: 22px; color: {DIM}">Done saves it to history</span>
<div style="display: flex; gap: 10px">{btn("Cancel",h=64,w="150px",fs=22)}{btn("Done",primary=True,h=64,w="170px")}</div>
</div>
</div>''')
def irow(state,text):
    ok=state=="OK"
    return f'<div style="height: 48px; display: flex; align-items: center; gap: 14px"><span style="font-size: 22px; font-weight: 600; width: 96px; text-align: center; padding: 3px 0; border-radius: 999px; background: {"transparent" if ok else TX}; color: {DIM if ok else G}; border: 1px solid {LN if ok else TX}">{state}</span><span style="font-size: 22px; color: {TX}">{text}</span></div>'
N["DndImport"]=("D&D: check an uploaded sheet",strip("D&amp;D · Upload","Check this sheet","")+f'''<div style="flex: 1; padding: 10px 20px; display: flex; flex-direction: column; gap: 6px">
{irow("OK","Brakka, Fighter 3, Dwarf")}
{irow("OK","Ability scores: 16, 12, 14, 10, 12, 8")}
{irow("OK","Hit points 28: fits a level 3 fighter")}
{irow("Check","Armour Class is missing")}
{irow("Check","Skills were not read. Tick them.")}
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">
{btn("Fix on phone",h=68,flex="1.2",fs=22)}
{btn("Fix here",h=68,flex="1",fs=22)}
{btn("Save",primary=True,h=68,flex="1")}
</div>
</div>''')
names=["DndParty","DndPhone","DndSheet","DndGear","DndLevelUp","DndImport"]
idx=json.load(open("canvas_live24.json"))
assert len(idx["boards"])==24, len(idx["boards"])
idx["notes"]["row6"]={"x":0,"y":5400-260,"text":"Dungeons & Dragons: characters","kind":"title1","maxW":5200}
for c,n in enumerate(names):
    idx["boards"][f"{n}.dc.html"]={"x":c*880,"y":5400,"w":800,"h":480,"title":N[n][0]}; idx["order"].append(f"{n}.dc.html")
    open(f"project/{n}.dc.html","w").write(page(N[n][0].replace("&","&amp;"),N[n][1]))
json.dump(idx,open("project/canvas.json","w"),indent=1); print(len(idx["boards"]))
