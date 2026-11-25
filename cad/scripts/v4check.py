import bpy, mathutils, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
dg=bpy.context.evaluated_depsgraph_get()
B=bpy.data.objects["P_HeadBell"]; P=bpy.data.objects["P_Chin"]
bb=mathutils.bvhtree.BVHTree.FromObject(B,dg); pb=mathutils.bvhtree.BVHTree.FromObject(P,dg)
def hits(bvh,o,d,maxn=8,maxd=400):
    out=[]; p=Vector(o); d=Vector(d).normalized()
    for _ in range(maxn):
        h=bvh.ray_cast(p,d,maxd)
        if h[0] is None: break
        out.append(h[0]); p=h[0]+d*0.02
    return out
a,b,c=-60.77,-0.0130,-0.2046
D=Vector((-b,1,-c)).normalized(); X=Vector((1,b,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b*-3.0+c*176.0,176.0)); dd=lambda p:(p-C).dot(D)
print("== DISPLAY (bell) ==")
def through(u,v):
    hs=hits(bb,C+u*X+v*U-60*D,D,maxd=70); return len(hs)==0 or dd(hs[0])>5
us=[u/2 for u in range(-140,141)]; w=[u for u in us if through(u,0)]
vs=[v/2 for v in range(-100,101)]; h=[v for v in vs if through(0,v)]
print(f"window at the back face: width {max(w)-min(w)+0.5:.1f} (110.5) height {max(h)-min(h)+0.5:.1f} (66.5)  bottom edge v={min(h):.1f} top v={max(h):.1f}")
for u,v in [(65,0),(-65,0),(0,43),(0,-43),(0,-48)]:
    hs=hits(bb,C+u*X+v*U-60*D,D,maxd=120); print(f"  seat at ({u},{v}): solid D {dd(hs[0]):.1f}..{dd(hs[1]):.1f}" if len(hs)>=2 else f"  seat at ({u},{v}): {len(hs)}")
for u,v in [(-64.25,-30),(64.25,-30),(-64.25,30),(64.25,30)]:
    p=hits(bb,C+u*X+v*U+40*D,-D,maxd=45)[0]; q=hits(bb,C+(u+2.5)*X+v*U+40*D,-D,maxd=45)[0]; print(f"  boss ({u},{v}): pilot floor D={dd(p):.1f}, boss top D={dd(q):.1f}")
# pocket floor slope: at u=0, scan v below -39 for the void boundary along D
print("  pocket floor profile (d -> lowest void v):",[ (d_, round(min([v for v in [x/2 for x in range(-120,-60)] if len(hits(bb,C+d_*D+v*U-0*X,X,maxd=1))==0 and not (lambda p: False)(0)] or [0]),1)) for d_ in (7,9,11,13)])
print("  seat/ceiling slit: point (d=7,v=56) inside?", end=" ")
def inside(bvh,p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(60):
        h=bvh.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
print(inside(bb,C+7*D+56*U), "(d=7,v=60):",inside(bb,C+7*D+60*U))
print("== SPEAKER SLOT (bell) ==")
def sfree(y,z): return not inside(bb,Vector((71,y,z)))
ys=[y/2 for y in range(-120,80)]; zs=[z/2 for z in range(260,380)]
fy=[y for y in ys if sfree(y,165)]; fz=[z for z in zs if sfree(-10,z)]
print(f"  slot y-width {max(fy)-min(fy)+0.5:.1f} (72.5)  z {min(fz):.1f}..{max(fz):.1f} (open at 143 bottom, top 181.75)")
xs=[x/2 for x in range(100,180)]; fx=[x for x in xs if not inside(bb,Vector((x,-10,165)))]
print(f"  slot x-depth: free x {min(fx):.1f}..{max(fx):.1f} (62.5..80 => 17.5 for a 17 mm speaker)")
for y in (-48.5,28.5):
    hs=hits(bb,Vector((70,y,148)),(0,1,0) if y<0 else (0,-1,0),maxd=12); print(f"  zip slot through wall at y={y}: crossings",[round(p.y,1) for p in hs])
print("  grille centre ray +x from (0,-10,165):",[round(p.x,1) for p in hits(bb,Vector((0,-10,165)),(1,0,0),maxd=120)])
print("== CHIN PLATE / LIP ==")
for ang in (0,90,180,270):
    d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); o=Vector((0,-10,104))
    hp=[round((p-o).length,1) for p in hits(pb,o,d,maxd=200)]; hb=[round((p-o).length,1) for p in hits(bb,o,d,maxd=200)]
    print(f"  {ang:>3}deg z=104: plate lip r {hp}   bell wall r {hb}")
for ang in (90,225,315):
    d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); o=Vector((0,-10,104.5))
    print(f"  pilot {ang}: bell crossings {[round((p-o).length,1) for p in hits(bb,o,d,maxd=200)]}  plate crossings {[round((p-o).length,1) for p in hits(pb,o,d,maxd=200)]}")
for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]:
    p=hits(pb,Vector((x,y,80)),(0,0,1),maxd=30)[0]; q=hits(pb,Vector((x+4.5,y,80)),(0,0,1),maxd=30)[0]; print(f"  chin magnet ({x},{y}): depth {p.z-q.z:.2f}")
print("== TOP ==")
for t in (90,210,330):
    x,y=30*math.cos(math.radians(t)),-10+30*math.sin(math.radians(t))
    p=hits(bb,Vector((x,y,260)),(0,0,-1),maxd=30)[0]; q=hits(bb,Vector((x+4.5,y,260)),(0,0,-1),maxd=30)[0]; print(f"  crown pocket ({x:.0f},{y:.0f}): floor {p.z:.1f} rim {q.z:.1f} depth {q.z-p.z:.2f}")
print("  ceiling thickness at centre:",[round(p.z,1) for p in hits(bb,Vector((0,-10,200)),(0,0,1),maxd=60)])
print("  walls:",{k:round((h[1]-h[0]).length,2) for k,h in {"left":hits(bb,Vector((0,-10,200)),(-1,0,0)),"right":hits(bb,Vector((0,-10,200)),(1,0,0)),"back":hits(bb,Vector((0,-10,200)),(0,1,0))}.items() if len(h)>=2})
