import json, datetime, os
G="#0B0F14"; P="#151C26"; P2="#1D2633"; LN="#2F3B4D"; TX="#EAF0F6"; DIM="#A9B8CA"; B1="#6CB6FF"; B2="#FFA64D"
HF="'Space Grotesk', system-ui, sans-serif"; BF="Inter, system-ui, sans-serif"
def page(title,body):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>
body{{margin:0}}
a{{color:{B1}}}a:hover{{color:#9CCEFF}}
button{{font-family:inherit;cursor:pointer}}
</style>
</helmet>
<div style="width: 800px; height: 480px; box-sizing: border-box; background: {G}; color: {TX}; font-family: {BF}; display: flex; flex-direction: column; overflow: hidden">
{body}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":800,"height":480}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
'''
def strip(left,mid="",right=""):
    r=f'<div style="font-size: 22px; font-weight: 600; color: {G}; background: {right[1]}; padding: 6px 14px; border-radius: 999px">{right[0]}</div>' if right else '<div style="width: 10px"></div>'
    m=f'<div style="font-family: {HF}; font-size: 24px; font-weight: 700; color: {TX}">{mid}</div>' if mid else ''
    return f'''<div style="height: 60px; flex-shrink: 0; box-sizing: border-box; padding: 0 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; background: {P}; border-bottom: 1px solid {LN}">
<div style="font-size: 22px; color: {DIM}">{left}</div>
{m}
{r}
</div>'''
def btn(label,primary=False,w="auto",h=72,fs=24,dim=False,flex=None):
    bg=TX if primary else P2; fg=G if primary else (DIM if dim else TX); fl=f"flex: {flex}; " if flex else ""
    return f'<button type="button" style="{fl}width: {w}; height: {h}px; box-sizing: border-box; padding: 0 20px; background: {bg}; color: {fg}; border: 1px solid {TX if primary else LN}; border-radius: 14px; font-size: {fs}px; font-weight: 600">{label}</button>'
def tile(title,sub,dim=False):
    return f'''<button type="button" style="height: 140px; box-sizing: border-box; padding: 18px 24px; background: {P}; border: 1px solid {LN}; border-radius: 18px; text-align: left; display: flex; flex-direction: column; justify-content: space-between; color: {DIM if dim else TX}">
<span style="font-family: {HF}; font-size: 36px; font-weight: 700">{title}</span>
<span style="font-size: 22px; color: {DIM}">{sub}</span>
</button>'''
F={}
# ---------- Home
F["Main"]=("Home",strip("Deep Thought","", "")+f'''<div style="flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 14px">
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px">
{tile("Play","Start or resume a game")}
{tile("Encyclopedia","Factions, kill teams, lore")}
{tile("Dice","Roll and let it judge you")}
{tile("Settings","Volume, Wi-Fi, how chatty it is")}
</div>
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 22px; color: {DIM}">
<span>Last game: Kill Team, Ethan 14, Trevor 11</span>
<span>Hold the button to ask anything</span>
</div>
</div>''')
# ---------- Pick game
F["PickGame"]=("Pick a game",strip("Play","Which game?","")+f'''<div style="flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 14px">
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px">
<button type="button" style="height: 140px; box-sizing: border-box; padding: 18px 24px; background: {P2}; border: 3px solid {TX}; border-radius: 18px; text-align: left; display: flex; flex-direction: column; justify-content: space-between; color: {TX}">
<span style="font-family: {HF}; font-size: 36px; font-weight: 700">Kill Team</span>
<span style="font-size: 22px; color: {DIM}">Two small squads, about an hour</span>
</button>
{tile("Warhammer 40,000","Full armies, five battle rounds")}
{tile("D&amp;D","Not built yet",dim=True)}
{tile("Magic","Not built yet",dim=True)}
</div>
<div style="display: flex; justify-content: space-between; align-items: center; gap: 14px">
{btn("Back",w="160px",h=64)}
<span style="font-size: 22px; color: {DIM}">Press the button to confirm Kill Team</span>
</div>
</div>''')
# ---------- Setup
def seg(opts,sel):
    out='<div style="display: flex; gap: 8px">'
    for o in opts:
        s=o==sel; out+=f'<button type="button" style="height: 64px; padding: 0 22px; background: {TX if s else P2}; color: {G if s else TX}; border: 1px solid {TX if s else LN}; border-radius: 12px; font-size: 22px; font-weight: 600">{o}</button>'
    return out+'</div>'
def row(label,ctrl): return f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px"><div style="font-size: 22px; color: {DIM}; width: 150px">{label}</div>{ctrl}</div>'
F["Setup"]=("Game setup",strip("Kill Team","Set up","")+f'''<div style="flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px">
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px">
<button type="button" style="height: 76px; background: {P}; border: 2px solid {B1}; border-radius: 14px; color: {B1}; font-family: {HF}; font-size: 30px; font-weight: 700">Ethan</button>
<button type="button" style="height: 76px; background: {P}; border: 2px solid {B2}; border-radius: 14px; color: {B2}; font-family: {HF}; font-size: 30px; font-weight: 700">Trevor</button>
</div>
{row("Mode",seg(["Teach","Reminder","Silent"],"Teach"))}
{row("Length",seg(["Tutorial: 2 rounds","Full: 4 rounds"],"Full: 4 rounds"))}
{row("Tac Ops",seg(["On","Off"],"On"))}
<div style="flex: 1"></div>
<div style="display: flex; gap: 14px">
{btn("Back",w="160px",h=68)}
{btn("Start game",primary=True,h=68,flex="1")}
</div>
</div>''')
# ---------- Play main
def num(label,a,b):
    return f'''<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between">
<span style="font-size: 22px; color: {DIM}">{label}</span>
<span style="font-family: {HF}; font-size: 44px; font-weight: 700"><span style="color: {B1}">{a}</span><span style="color: {DIM}; font-size: 28px; padding: 0 10px">to</span><span style="color: {B2}">{b}</span></span>
</div>'''
F["Play"]=("Play: main screen",strip("Kill Team · Round 2 of 4","Firefight",("Trevor&#39;s turn",B2))+f'''<div style="flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px">
<div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 8px">
<div style="font-family: {HF}; font-size: 44px; font-weight: 700; line-height: 1.1">Trevor, pick an operative.</div>
<div style="font-size: 26px; color: {DIM}">Choose its order, then spend its actions.</div>
</div>
<div style="display: flex; gap: 14px">
{num("Command points",3,4)}
{num("Activations left",3,2)}
</div>
<div style="display: flex; gap: 10px">
{btn("Next",primary=True,flex="1.6")}
{btn("Score",flex="1")}
{btn("Operative down",flex="1.9",fs=22)}
{btn("Undo",flex="1")}
{btn("Lookup",flex="1.1")}
</div>
</div>''')
# ---------- Scoreboard
def col(name,c,total,rows,cp,lost):
    r="".join(f'<div style="display: flex; justify-content: space-between; font-size: 24px"><span style="color: {DIM}">{k}</span><span style="font-weight: 600">{v}</span></div>' for k,v in rows)
    return f'''<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 18px; padding: 14px 22px; display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: baseline; justify-content: space-between">
<span style="font-family: {HF}; font-size: 32px; font-weight: 700; color: {c}">{name}</span>
<span style="font-family: {HF}; font-size: 96px; font-weight: 700; line-height: 1; color: {c}">{total}</span>
</div>
{r}
<div style="height: 1px; background: {LN}; margin: 4px 0"></div>
<div style="display: flex; justify-content: space-between; font-size: 22px; color: {DIM}"><span>Command points {cp}</span><span>Lost {lost}</span></div>
</div>'''
F["Scoreboard"]=("Play: scoreboard",strip("Kill Team · Round 2 of 4","Scoreboard","")+f'''<div style="flex: 1; padding: 14px 20px; display: flex; flex-direction: column; gap: 12px">
<div style="flex: 1; display: flex; gap: 14px">
{col("Ethan",B1,7,[("Crit Op","4 / 6"),("Tac Op","2 / 6"),("Kill Op","1 / 6")],3,"1 of 6")}
{col("Trevor",B2,5,[("Crit Op","2 / 6"),("Tac Op","2 / 6"),("Kill Op","1 / 6")],4,"2 of 6")}
</div>
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 22px; color: {DIM}">
<span>Tap a number to correct it</span>
<span>Press the button to go back</span>
</div>
</div>''')
# ---------- Score sheet
def stepper(val,c):
    b=f'height: 64px; width: 64px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-size: 30px; font-weight: 600'
    return f'<div style="display: flex; align-items: center; gap: 10px"><button type="button" aria-label="Take one away" style="{b}">&minus;</button><span style="font-family: {HF}; font-size: 34px; font-weight: 700; color: {c}; width: 86px; text-align: center">{val}</span><button type="button" aria-label="Add one" style="{b}">+</button></div>'
def srow(label,a,b): return f'<div style="display: grid; grid-template-columns: 150px 1fr 1fr; align-items: center; gap: 12px"><div style="font-size: 24px; font-weight: 600">{label}</div><div style="display: flex; justify-content: center">{stepper(a,B1)}</div><div style="display: flex; justify-content: center">{stepper(b,B2)}</div></div>'
F["ScoreSheet"]=("Play: end-of-round score sheet",strip("Kill Team · End of round 2","Score this round","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="display: grid; grid-template-columns: 150px 1fr 1fr; gap: 12px; font-family: {HF}; font-size: 24px; font-weight: 700"><div></div><div style="text-align: center; color: {B1}">Ethan</div><div style="text-align: center; color: {B2}">Trevor</div></div>
{srow("Crit Op","4 / 6","2 / 6")}
{srow("Tac Op","2 / 6","2 / 6")}
{srow("Kill Op","1 / 6","1 / 6")}
<div style="flex: 1"></div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 14px">
<span style="font-size: 22px; color: {DIM}">Each category stops at 6</span>
{btn("Done",primary=True,w="260px",h=68)}
</div>
</div>''')
# ---------- Teach step
F["TeachStep"]=("Teach mode: one step",strip("Kill Team · Teach","Shooting, step 2 of 5",("Ethan&#39;s turn",B1))+f'''<div style="flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px">
<div style="font-family: {HF}; font-size: 40px; font-weight: 700">Roll to hit</div>
<div style="display: flex; gap: 16px; flex: 1">
<div style="flex: 1.25; font-size: 24px; line-height: 1.35; display: flex; flex-direction: column; gap: 10px">
<div>Roll one die for each attack your weapon has.</div>
<div>Each die that equals or beats the weapon&#39;s Hit number is a success.</div>
<div>A six is a critical success. Keep those apart.</div>
</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 14px; padding: 14px 18px; display: flex; flex-direction: column; gap: 8px">
<div style="font-size: 22px; color: {DIM}">Example: 4 attacks, Hit 3+</div>
<div style="display: flex; gap: 8px">
{"".join(f'<div style="width: 52px; height: 52px; border-radius: 10px; background: {bg}; color: {fg}; border: 1px solid {LN}; display: flex; align-items: center; justify-content: center; font-family: {HF}; font-size: 30px; font-weight: 700">{n}</div>' for n,bg,fg in ((6,TX,G),(4,P2,TX),(3,P2,TX),(2,G,DIM)))}
</div>
<div style="font-size: 22px">1 critical, 2 hits, 1 miss</div>
</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Back",w="140px",h=68)}
{btn("Say again",w="190px",h=68)}
{btn("Next",primary=True,h=68,flex="1")}
</div>
</div>''')
# ---------- Ask
bars="".join(f'<div style="width: 18px; height: {h}px; border-radius: 9px; background: {TX}"></div>' for h in (28,64,110,150,96,132,70,118,48,84,30))
F["Ask"]=("Ask: listening",strip("Kill Team · Round 2 of 4","Ask","")+f'''<div style="flex: 1; padding: 16px 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px">
<div style="font-family: {HF}; font-size: 52px; font-weight: 700">Listening</div>
<div role="img" aria-label="Microphone level" style="height: 150px; display: flex; align-items: center; gap: 10px">{bars}</div>
<div style="font-size: 24px; color: {DIM}">Let go of the button to send</div>
{btn("Cancel",w="200px",h=64)}
</div>''')
# ---------- Lookup
chips="".join(f'<button type="button" style="height: 64px; padding: 0 18px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 999px; font-size: 22px">{c}</button>' for c in ("Cover","Obscured","Piercing","Counteract"))
F["Lookup"]=("Lookup: answer card",strip("Kill Team · Round 2 of 4","Lookup","")+f'''<div style="flex: 1; padding: 14px 20px; display: flex; flex-direction: column; gap: 12px">
<div style="display: flex; gap: 10px; align-items: center">
<label for="q" style="font-size: 22px; color: {DIM}">Search</label>
<input id="q" type="text" value="lethal" style="flex: 1; height: 64px; box-sizing: border-box; padding: 0 18px; background: {P}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-family: inherit; font-size: 26px">
</div>
<div style="display: flex; gap: 8px; align-items: center"><span style="font-size: 22px; color: {DIM}">This phase:</span>{chips}</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 16px; padding: 14px 20px; display: flex; flex-direction: column; gap: 6px">
<div style="font-family: {HF}; font-size: 34px; font-weight: 700">Lethal 5+</div>
<div style="font-size: 24px; line-height: 1.35">With this weapon, a roll of 5 or 6 is a critical success, not only a 6.</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Read aloud",h=64,flex="1")}
{btn("Ask for more",h=64,flex="1")}
{btn("Close",h=64,w="150px")}
</div>
</div>''')
# ---------- Encyclopedia
def tab(t,s): return f'<button type="button" style="height: 64px; padding: 0 22px; background: {TX if s else "transparent"}; color: {G if s else TX}; border: 1px solid {TX if s else LN}; border-radius: 12px; font-size: 22px; font-weight: 600">{t}</button>'
def li(t,s=False): return f'<button type="button" style="height: 64px; padding: 0 16px; text-align: left; background: {P2 if s else "transparent"}; color: {TX}; border: 1px solid {LN if s else "transparent"}; border-radius: 10px; font-size: 24px; font-weight: {600 if s else 400}">{t}</button>'
F["Encyclopedia"]=("Encyclopedia: a faction",strip("Encyclopedia","Xenos","")+f'''<div style="flex: 1; padding: 12px 20px; display: flex; flex-direction: column; gap: 10px; min-height: 0">
<div style="display: flex; gap: 8px">{tab("Factions",True)}{tab("Kill Teams",False)}{tab("Lore",False)}<div style="flex: 1"></div>{tab("Search",False)}</div>
<div style="flex: 1; display: flex; gap: 14px; min-height: 0">
<div style="width: 220px; display: flex; flex-direction: column; gap: 4px">{li("Aeldari")}{li("Necrons",True)}{li("Orks")}{li("T&#39;au Empire")}</div>
<div style="flex: 1; background: {P}; border: 1px solid {LN}; border-radius: 16px; padding: 14px 20px; display: flex; flex-direction: column; gap: 8px">
<div style="font-family: {HF}; font-size: 34px; font-weight: 700">Necrons</div>
<div style="font-size: 22px; line-height: 1.35">Ancient machine dynasties waking after sixty million years asleep. They are slow and very hard to kill, and fallen warriors stand back up.</div>
<div style="font-size: 22px; color: {DIM}">Good first army: forgiving, few special cases.</div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 10px">{btn("Read aloud",h=64,flex="1",fs=22)}{btn("How they play",h=64,flex="1.2",fs=22)}{btn("Units",h=64,flex="0.8",fs=22)}</div>
</div>
</div>
</div>''')
# ---------- Dice
def die(n,crit): return f'<div style="width: 84px; height: 84px; border-radius: 16px; background: {TX if crit else P2}; color: {G if crit else TX}; border: 1px solid {LN}; display: flex; align-items: center; justify-content: center; font-family: {HF}; font-size: 48px; font-weight: 700">{n}</div>'
F["Dice"]=("Dice roller",strip("Dice","6 dice","")+f'''<div style="flex: 1; padding: 14px 20px; display: flex; flex-direction: column; gap: 12px">
<div style="display: flex; gap: 12px; justify-content: center">{die(6,True)}{die(6,True)}{die(5,False)}{die(4,False)}{die(2,False)}{die(1,False)}</div>
<div style="text-align: center; font-family: {HF}; font-size: 30px; font-weight: 700">Two sixes</div>
<div style="text-align: center; font-size: 24px; color: {DIM}">&ldquo;I worked out the odds of that. You would not have liked them.&rdquo;</div>
<div style="flex: 1"></div>
<div style="display: flex; align-items: center; gap: 10px">
<span style="font-size: 22px; color: {DIM}">How many</span>
<button type="button" aria-label="One fewer die" style="height: 68px; width: 68px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-size: 30px; font-weight: 600">&minus;</button>
<span style="font-family: {HF}; font-size: 40px; font-weight: 700; width: 60px; text-align: center">6</span>
<button type="button" aria-label="One more die" style="height: 68px; width: 68px; background: {P2}; color: {TX}; border: 1px solid {LN}; border-radius: 12px; font-size: 30px; font-weight: 600">+</button>
{seg(["D6","D3","D20"],"D6")}
{btn("Roll",primary=True,h=68,flex="1")}
</div>
</div>''')
# ---------- Game over
F["GameOver"]=("Game over",strip("Kill Team · Full game","Game over","")+f'''<div style="flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px">
<div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px">
<div style="font-family: {HF}; font-size: 44px; font-weight: 700; color: {B1}">Ethan wins</div>
<div style="font-family: {HF}; font-size: 110px; font-weight: 700; line-height: 1"><span style="color: {B1}">14</span><span style="color: {DIM}; font-size: 48px; padding: 0 18px">to</span><span style="color: {B2}">11</span></div>
<div style="font-size: 22px; color: {DIM}">1 hour 52 minutes · 4 rounds</div>
<div style="font-size: 24px; text-align: center; padding-top: 6px">&ldquo;A result. I had it worked out some time ago, but do go on.&rdquo;</div>
</div>
<div style="display: flex; gap: 10px">
{btn("Score sheet",h=68,flex="1")}
{btn("New game",h=68,flex="1")}
{btn("Home",primary=True,h=68,flex="1")}
</div>
</div>''')
order=[["Main","PickGame","Setup","GameOver"],["Play","Scoreboard","ScoreSheet","TeachStep"],["Ask","Lookup","Encyclopedia","Dice"]]
titles=["Start and finish","During a game","Asking and looking things up"]
boards={}; notes={}; flat=[]
for r,rowl in enumerate(order):
    y=r*900
    notes[f"row{r}"]={"x":0,"y":y-260,"text":titles[r],"kind":"title1","maxW":4*800+3*80}
    for c,n in enumerate(rowl):
        boards[f"{n}.dc.html"]={"x":c*880,"y":y,"w":800,"h":480,"title":F[n][0]}; flat.append(f"{n}.dc.html")
        open(f"project/{n}.dc.html","w").write(page(F[n][0],F[n][1]))
idx={"v":3,"createdOnFiles":{"v":1,"at":datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},"title":"Deep Thought — Screen Mockups","launch":{"view":"canvas"},"pages":[],"boards":boards,"order":flat,"notes":notes,"designSystems":[]}
json.dump(idx,open("project/canvas.json","w"),indent=1)
print(flat)
