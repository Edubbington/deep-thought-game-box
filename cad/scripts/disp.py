import bpy, mathutils, math, collections
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
src=open("/home/claude/build/loaded.py").read()
import re
# pull the frame definition lines
for ln in src.split("\n")[:12]:
    if re.match(r"^(a|b_|c|D|C)\s*=|^a,|^D=|^C=",ln) or "b_" in ln and "=" in ln and "shot" not in ln:
        try: exec(ln)
        except Exception as e: print("skip",ln[:60],e)
H=bpy.data.objects["P_HeadBell"]; dg=bpy.context.evaluated_depsgraph_get(); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def depth(x,u):
    h=hb.ray_cast(C+x*X+u*U+45*D,-D,120)
    return round((h[0]-C).dot(D),1) if h[0] else None
print("depth along D of first surface seen from inside, U=0, x=-80..80 step 4:"); print([ (x,depth(x,0)) for x in range(-80,81,4)])
print("x=0, u=-56..56 step 4:"); print([ (u,depth(0,u)) for u in range(-56,57,4)])
# full map -> histogram of depths, and find holes in the rim
m={}
for x in range(-80,81):
    for u in range(-58,59): m[(x,u)]=depth(x,u)
hist=collections.Counter(v for v in m.values() if v is not None); print("depth histogram:",sorted(hist.items(),key=lambda kv:-kv[1])[:8])
holes=[]
for (x,u),v in m.items():
    nb=[m.get((x+dx,u+du)) for dx in (-3,3) for du in (-3,3)]
    if (v is None or v>14.6) and sum(1 for n in nb if n==14.0)>=3: holes.append((x,u,v))
print("rim hole candidates:",holes)
# fine scan around candidates
def fine(x0,u0):
    pts=[(x0+i*0.2,u0+j*0.2) for i in range(-25,26) for j in range(-25,26)]
    inh=[(x,u) for x,u in pts if (lambda d:(d is None or d>14.6))(depth(x,u))]
    if not inh: return None
    xs=[p[0] for p in inh]; us=[p[1] for p in inh]
    return round((min(xs)+max(xs))/2,1),round((min(us)+max(us))/2,1),round(max(xs)-min(xs)+0.2,1),round(max(us)-min(us)+0.2,1)
seen=[]
for x,u,v in holes:
    if any(abs(x-a)<5 and abs(u-b)<5 for a,b in seen): continue
    seen.append((x,u)); print(" hole near",(x,u),"centre/size:",fine(x,u))
# pocket edges (where depth steps 6 -> 14) along rows
row=[(x/5,depth(x/5,0)) for x in range(-340,-280)]; print("left edge:",[r for r in row if r[1]!=row[0][1]][:2], row[0])
col=[(u/5,depth(0,u/5)) for u in range(180,220)]; print("top edge:",[r for r in col if r[1]!=col[0][1]][:2], col[0])
col=[(u/5,depth(0,u/5)) for u in range(-280,-170)]; print("bottom profile:",col[::6])
print("---- blind holes in the rim (depth < 13.5 surrounded by 14.0):")
cand=[(x,u,v) for (x,u),v in m.items() if v is not None and v<13.5 and sum(1 for dx in (-4,4) for du in (-4,4) if m.get((x+dx,u+du))==14.0)>=3]
print(cand)
seen=[]
for x,u,v in cand:
    if any(abs(x-a)<5 and abs(u-b)<5 for a,b in seen): continue
    seen.append((x,u))
    pts=[(x+i*0.1,u+j*0.1) for i in range(-30,31) for j in range(-30,31)]
    inh=[(p,depth(*p)) for p in pts]; inh=[(p,d) for p,d in inh if d is not None and d<13.8]
    xs=[p[0][0] for p in inh]; us=[p[0][1] for p in inh]
    print(" hole centre",round((min(xs)+max(xs))/2,2),round((min(us)+max(us))/2,2),"dia",round(max(xs)-min(xs)+0.1,2),round(max(us)-min(us)+0.1,2),"bottom at D",min(d for p,d in inh))
print("---- fine scan of the rim band")
odd=[]
for xi in range(-800,801,5):
    for ui in range(-560,541,5):
        x,u=xi/10,ui/10
        if abs(x)<62.2 and -40.5<u<40.7: continue   # pocket itself
        if abs(x)>77 or u>48.5 or u<-40: continue     # outside the flat rim
        d=depth(x,u)
        if d is None or abs(d-14.0)>0.3: odd.append((x,u,d))
print(len(odd)); 
import itertools
cl=[]
for p in odd:
    for c in cl:
        if abs(c[0][0]-p[0])<4 and abs(c[0][1]-p[1])<4: c.append(p); break
    else: cl.append([p])
for c in cl: print(" cluster n",len(c),"x",min(p[0] for p in c),max(p[0] for p in c),"u",min(p[1] for p in c),max(p[1] for p in c),"depths",sorted(set(p[2] for p in c if p[2] is not None))[:4])
