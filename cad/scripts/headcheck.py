import bpy, mathutils, math, bmesh, collections
from mathutils import Vector, Matrix
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5d.blend")
H=bpy.data.objects["P_Head"]; dg=bpy.context.evaluated_depsgraph_get()
bvh=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def hits(o,d,maxn=10,maxd=400):
    out=[]; p=Vector(o); d=Vector(d).normalized()
    for _ in range(maxn):
        h=bvh.ray_cast(p,d,maxd)
        if h[0] is None: break
        out.append(h[0]); p=h[0]+d*0.02
    return out
a,b,c=-60.77,-0.0130,-0.2046
D=Vector((-b,1,-c)).normalized(); X=Vector((1,b,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
cx,cz=-3.0,176.0; C=Vector((cx,a+b*cx+c*cz,cz))
def dd(p): return (p-C).dot(D)
print("== DISPLAY ==")
# window width/height: scan u at v=0, v at u=0 for rays that pass clean through the front skin
def through(u,v):
    hs=hits(C+u*X+v*U-60*D,D,maxd=70)
    return len(hs)==0 or dd(hs[0])>5   # no front-skin hit before the seat plane
us=[u/2 for u in range(-140,141)]; w=[u for u in us if through(u,0)]
vs=[v/2 for v in range(-100,101)]; h=[v for v in vs if through(0,v)]
print(f"window opening: width {max(w)-min(w)+0.25:.2f} (target 110.5)  height {max(h)-min(h)+0.25:.2f} (target 66.5)")
# pocket (seat opening) width/height: measured at the seat plane C+8D
def pocket_free(u,v):
    hs=hits(C+u*X+v*U+8*D- (0*D),X if False else D,maxd=1)  # dummy
    # test by point-in-solid: cast ray in +U from the point and count hits parity? simpler: cast along D from C+u*X+v*U+6.5D for 7mm, expect no hit if in pocket
    hs=hits(C+u*X+v*U+6.5*D,D,maxd=7); return len(hs)==0
pw=[u for u in us if pocket_free(u,0)]; ph=[v for v in vs if pocket_free(0,v)]
print(f"seat pocket:    width {max(pw)-min(pw)+0.25:.2f} (target 122.5)  height {max(ph)-min(ph)+0.25:.2f} (target 79.5)")
# seat lip: front skin thickness at pocket edge region (u=58, v=0): hits along D from outside
hs=hits(C+58*X-60*D,D,maxd=120); print("at u=58 (seat lip): surface crossings along D (mm from display plane):",[round(dd(p),2) for p in hs])
# pocket depth: from front seat face to boss tops / seat back
hs=hits(C+64.25*X+30*U-60*D,D,maxd=120); print("at boss centre: crossings:",[round(dd(p),2) for p in hs])
hs=hits(C+64.25*X+32.5*U-60*D,D,maxd=120); print("2.5mm off boss centre: crossings:",[round(dd(p),2) for p in hs])
for u,v in [(-64.25,-30),(64.25,-30),(-64.25,30),(64.25,30)]:
    hs=hits(C+u*X+v*U+40*D,-D,maxd=45); print(f"boss ({u},{v}) from inside: first hit at D={dd(hs[0]):.2f} (pilot floor), 2.5mm off: D={dd(hits(C+(u+2.5)*X+v*U+40*D,-D,maxd=45)[0]):.2f} (boss top)")
# cavity depth behind display at centre and at Pi corners
print("== CAVITY BEHIND DISPLAY ==")
for u,v in [(0,0),(-40,-25),(40,-25),(-40,25),(40,25),(0,-35),(0,35)]:
    hs=hits(C+u*X+v*U+6.5*D,D,maxd=200); print(f"  at (u={u},v={v}): free depth from seat face = {dd(hs[0])-6:.1f} mm")
# sideways room at Pi level for USB dongles: along +X / -X from centre at D=25
def room(p,d):
    hs=hits(p,d,maxd=200); return f"{(hs[0]-p).length:.1f}" if hs else "open(>200)"
for depth in (20,30,40):
    p=C+depth*D
    print(f"  at D={depth}: room +X {room(p,X)}  -X {room(p,-X)}  +U {room(p,U)}  -U {room(p,-U)}")
print("== SEAT PERIMETER (where the 8 mm lip actually exists) ==")
for u,v in [(65,0),(65,20),(65,-20),(-65,0),(-65,20),(-65,-20),(0,43),(30,43),(-30,43),(0,-43),(30,-43),(-30,-43),(58,36),(-58,36),(58,-36),(-58,-36)]:
    hs=hits(C+u*X+v*U-60*D,D,maxd=120); print(f"  ({u:>4},{v:>4}): solid from D={dd(hs[0]):.1f} to D={dd(hs[1]):.1f}" if len(hs)>=2 else f"  ({u},{v}): {len(hs)} crossings")
print("== SPEAKER ==")
hs=hits(Vector((0,-10,165)),(1,0,0),maxd=120); print("ray +x at speaker centre, x of crossings:",[round(p.x,2) for p in hs])
hs=hits(Vector((0,-10,160)),(1,0,0),maxd=120); print("ray +x at (y-10,z160) (between grille holes?):",[round(p.x,2) for p in hs])
# opening size: scan y and z at x=70 for free points
def sfree(y,z): return len(hits(Vector((62,y,z)),(1,0,0),maxd=16))==0
ys=[y/2 for y in range(-120,80)]; zs=[z/2 for z in range(280,380)]
fy=[y for y in ys if sfree(y,165)]; fz=[z for z in zs if sfree(-10,z)]
print(f"speaker pocket: {max(fy)-min(fy)+0.5:.1f} x {max(fz)-min(fz)+0.5:.1f} (target 72.5 x 33.5; speaker 70 x 31), depth from x=60 to back:", end=" ")
hs=hits(Vector((62,-30,165)),(1,0,0),maxd=40); print([round(p.x,1) for p in hs])
for dz in (-19.6,19.6):
    hs=hits(Vector((60,-10,165+dz)),(1,0,0),maxd=30); print(f"zip slot at z={165+dz}: crossings x",[round(p.x,1) for p in hs])
print("== WIRING PAD / ANCHORS ==")
hs=hits(Vector((-3,0,160)),(0,1,0),maxd=100); print("pad face y:",round(hs[0].y,2),"outer back wall y:",[round(p.y,2) for p in hs])
for x in (-35,29):
    for z in (140,180):
        hs=hits(Vector((x-30,hits(Vector((-3,0,160)),(0,1,0))[0].y-1.3,z)),(1,0,0),maxd=60); print(f"tunnel ({x},{z}) along x: crossings",[round(p.x,1) for p in hs])
print("== CROWN POCKETS (top) ==")
for t in (90,210,330):
    x,y=30*math.cos(math.radians(t)),-10+30*math.sin(math.radians(t))
    hs=hits(Vector((x,y,260)),(0,0,-1),maxd=20); hs2=hits(Vector((x+4.5,y,260)),(0,0,-1),maxd=20)
    print(f"  pocket at ({x:.1f},{y:.1f}): floor z={hs[0].z:.2f}, rim z={hs2[0].z:.2f} -> depth {hs2[0].z-hs[0].z:.2f} (magnet 3 mm)")
print("== BOTTOM MAGNET BOSSES (to core) ==")
for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]:
    hs=hits(Vector((x,y,80)),(0,0,1),maxd=30); hs2=hits(Vector((x+4.5,y,80)),(0,0,1),maxd=30)
    print(f"  boss ({x},{y}): pocket ceiling z={hs[0].z:.2f}, boss face z={hs2[0].z:.2f} -> depth {hs[0].z-hs2[0].z:.2f}")
print("== WALLS ==")
for (o,d,label) in [((0,-10,200),(1,0,0),"right wall z200"),((0,-10,200),(-1,0,0),"left wall z200"),((0,-10,200),(0,1,0),"back wall z200"),((0,-10,120),(0,-1,0),"front wall z120"),((0,-10,230),(0,0,1),"ceiling at centre")]:
    hs=hits(Vector(o),d,maxd=200); 
    if len(hs)>=2: print(f"  {label}: thickness {(hs[1]-hs[0]).length:.2f}")
    else: print(f"  {label}: crossings {len(hs)}")
print("== BOTTOM OPENING vs CORE ==")
core=bpy.data.objects["P_Core"]; cb=mathutils.bvhtree.BVHTree.FromObject(core,dg)
# head bottom opening extents at z=97 (just above head bottom 96): scan x and y for free
def hfree(x,y): return len(hits(Vector((x,y,97)),(0,0,1),maxd=3))==0 and len(hits(Vector((x,y,97)),(0,0,-1),maxd=3))==0
xs=[x for x in range(-100,101) if hfree(x,1.7)]; ys2=[y for y in range(-100,101) if hfree(0,y)]
print(f"head bottom opening at z=97: x {min(xs)}..{max(xs)}  y {min(ys2)}..{max(ys2)}")
# core top extents
cx_=[x for x in range(-100,101) if cb.ray_cast(Vector((x,1.7,120)),Vector((0,0,-1)),40)[0] is not None and cb.ray_cast(Vector((x,1.7,120)),Vector((0,0,-1)),40)[0].z>93]
print("core top (z>93) x extent:",min(cx_),max(cx_))
print("== DIMS ==", [round(v,1) for v in H.dimensions])
