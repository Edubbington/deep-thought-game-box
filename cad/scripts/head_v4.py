import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils
from shapely.geometry import Polygon, LineString
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5d.blend")
t0=time.time()
DT=bpy.data.objects["DT"]; head=bpy.data.objects["P_Head"]
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
cx,cz=-3.0,176.0; C=Vector((cx,a+b_*cx+c*cz,cz))
def hull(name,pts):
    bm=bmesh.new()
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm,input=bm.verts); bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); return link(name,bm)
hs=dup(DT,"hs"); bb=box("s",Vector((0,0,198)),(400,400,204)); boolean(hs,bb,'INTERSECT'); rm(bb)   # solid head z 96..300
TOP=239.0
# ---- A. speaker: refill old cradle; new taller frame with a 45deg top; vertical slot open from below; side zip slots; grille recut
fr=box("fr",Vector((72.5,-10,176.5)),(29,82,67)); boolean(fr,hs,'INTERSECT')          # x 58..87, z 143..210
wedge=hull("wg",[Vector((x,y,z)) for y in (-60,40) for x,z in ((58,181),(87,210),(58,220),(87,220))])
boolean(fr,wedge,'DIFFERENCE'); rm(wedge); boolean(head,fr,'UNION'); rm(fr)
slot=box("slot",Vector((71.25,-10,158)),(17.5,72.5,47.5)); boolean(head,slot,'DIFFERENCE'); rm(slot)   # x 62.5..80, z 134.25..181.75
zs=box("zs",Vector((70,-10,148)),(14,100,4)); boolean(head,zs,'DIFFERENCE'); rm(zs)                    # through both y-walls, z 146..150
rotY=Matrix.Rotation(math.radians(90),4,'Y'); holes=[]; sp=5.5
for i in range(-7,8):
    for j in range(-4,5):
        yy=-10+i*sp+(j%2)*sp/2; zz=165+j*sp*0.866
        if ((yy+10)/31.0)**2+((zz-165)/12.5)**2<=1.0: holes.append(("cyl",{"loc":Vector((82,yy,zz)),"r":1.5,"h":16,"seg":12,"rot":rotY}))
G=multi("gr",holes); boolean(head,G,'DIFFERENCE'); rm(G); print("A speaker",stats(head),round(time.time()-t0))
# ---- B. display: 56.5deg (=45deg to the bed) chamfers under the pocket floor and the window's bottom edge; gusset over the seat top
S=1.7  # ~47 deg to the bed once the 11.5 deg screen tilt is accounted for
w1=hull("w1",[C+x*X+d*D+v*U for x in (-61.6,61.6) for d,v in ((5.9,-39.0),(14.3,-39.0),(14.3,-39.75-8.4*S))]); boolean(head,w1,'DIFFERENCE'); rm(w1)
# window: outward sill bevel on the bottom edge (49 deg to the bed), back-face opening unchanged so the display still has its stop
w2=hull("w2",[C+x*X+d*D+v*U for x in (-55.4,55.4) for d,v in ((6.3,-32.5),(-3,-33.25-5.5-7.05*0.78),(-3,-32.5))]); boolean(head,w2,'DIFFERENCE'); rm(w2)
g=hull("g",[C+x*X+d*D+v*U for x in (-82,82) for d,v in ((-2,53.5),(14.5,53.5),(-2,54+27))]); boolean(g,hs,'INTERSECT'); boolean(head,g,'UNION'); rm(g)
print("B display",stats(head),round(time.time()-t0))
# ---- C. wiring pad: 45deg chamfer on its top
pw=hull("pw",[Vector((x,y,z)) for x in (-50,44) for y,z in ((59.5,181.5),(68,190),(59.5,196),(68,196))]); boolean(head,pw,'DIFFERENCE'); rm(pw)
# ---- D. flat top + 6 mm ceiling plate + crown pockets
k=box("k",Vector((0,0,(TOP-100)/2)),(500,500,TOP+100)); boolean(head,k,'INTERSECT'); rm(k)
pl=dup(hs,"plate"); s=box("s2",Vector((0,0,TOP-3)),(500,500,6)); boolean(pl,s,'INTERSECT'); rm(s); boolean(head,pl,'UNION'); rm(pl)
cm=multi("cm",[("cyl",{"loc":Vector((30*math.cos(t),-10+30*math.sin(t),TOP-1.7+0.5)),"r":3.2,"h":4.4,"seg":32}) for t in (math.radians(90),math.radians(210),math.radians(330))])
boolean(head,cm,'DIFFERENCE'); rm(cm); print("D top",stats(head),round(time.time()-t0))
# ---- E. 45deg bevel on the top rim (replaces the rounded shoulder that would overhang when printed top-down)
Z0=TOP-6.0
ring=Polygon(section_loop(hs,Z0)).buffer(0)
if ring.geom_type!='Polygon': ring=max(ring.geoms,key=lambda p:p.area)
N=480; levels=[]
for i in range(0,int((TOP+1-Z0)/0.5)+1):
    k=i*0.5; z=Z0+k; p=ring.buffer(-k,join_style=2)
    if p.geom_type!='Polygon': p=max(p.geoms,key=lambda q:q.area)
    ext=LineString(p.exterior.coords); L=ext.length
    levels.append([(ext.interpolate(L*j/N).x,ext.interpolate(L*j/N).y,z) for j in range(N)])
bm=bmesh.new(); rows=[]
base=[bm.verts.new((x,y,Z0-40)) for x,y,z in levels[0]]; rows.append(base)
for lv in levels: rows.append([bm.verts.new(v) for v in lv])
for r0,r1 in zip(rows,rows[1:]):
    for j in range(N): bm.faces.new((r0[j],r0[(j+1)%N],r1[(j+1)%N],r1[j]))
bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1])
bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); env=link("env",bm)
top_part=dup(head,"top_part"); boolean(top_part,env,'INTERSECT'); rm(env)
kb=box("kb",Vector((0,0,(Z0+0.5-100)/2)),(500,500,Z0+0.5+100)); boolean(head,kb,'INTERSECT'); rm(kb)
boolean(head,top_part,'UNION'); rm(top_part); print("E bevel",stats(head),round(time.time()-t0))
# ---- F. split: chin plate (z<=100.5) with lip; bell (z>=100.5) minus old boss stubs; 3 horizontal screw pilots
ZC=100.5
plate=dup(head,"P_Chin"); k=box("k1",Vector((0,0,(ZC-100)/2)),(500,500,ZC+100)); boolean(plate,k,'INTERSECT'); rm(k)
k=box("k2",Vector((0,0,(ZC+400)/2)),(500,500,400-ZC)); boolean(head,k,'INTERSECT'); rm(k)
cav=dup(hs,"cav"); erode(cav,3.0,0.8)
stubs=multi("stubs",[("cyl",{"loc":Vector((x,y,106)),"r":7.6,"h":12,"seg":32}) for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]])
boolean(stubs,cav,'INTERSECT'); boolean(head,stubs,'DIFFERENCE'); rm(stubs); rm(cav)
# tapered lip in three slabs, each sized from the BELL's own inner outline at the slab's bottom (0.3 mm clearance), 2.7 mm thick
def loops_at(o,z):
    bm=bmesh.new(); bm.from_mesh(o.data)
    res=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,z),plane_no=(0,0,1))
    cut=[e for e in res['geom_cut'] if isinstance(e,bmesh.types.BMEdge)]
    adj={}
    for e in cut:
        a_,b2=e.verts; adj.setdefault(a_,[]).append(b2); adj.setdefault(b2,[]).append(a_)
    loops=[]; seen=set()
    for s0 in adj:
        if s0 in seen: continue
        loop=[s0]; seen.add(s0); prev=None; cur=s0
        while True:
            nx=[v for v in adj[cur] if v is not prev and (v not in seen or v is s0)]
            if not nx or nx[0] is s0: break
            prev,cur=cur,nx[0]; seen.add(cur); loop.append(cur)
        loops.append([(v.co.x,v.co.y) for v in loop])
    bm.free(); return loops
def shp_prism(name,poly,z0,z1):
    bm=bmesh.new(); pts=list(poly.exterior.coords)[:-1]
    bot=[bm.verts.new((x,y,z0)) for x,y in pts]; top=[bm.verts.new((x,y,z1)) for x,y in pts]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    n=len(pts)
    for i in range(n): bm.faces.new((bot[i],bot[(i+1)%n],top[(i+1)%n],top[i]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); return link(name,bm)
for zsec,z0,z1 in ((ZC+0.6,ZC-2,ZC+1.5),(ZC+1.6,ZC+1.5,ZC+5),(ZC+5.1,ZC+5,ZC+8)):
    lp=sorted([Polygon(l).buffer(0) for l in loops_at(head,zsec) if len(l)>20],key=lambda p:-p.area)
    inner=lp[1] if len(lp)>1 else lp[0]
    if inner.geom_type!='Polygon': inner=max(inner.geoms,key=lambda p:p.area)
    outer_ring=inner.buffer(-0.4,join_style=1); inner_ring=inner.buffer(-3.0,join_style=1)
    if outer_ring.geom_type!='Polygon': outer_ring=max(outer_ring.geoms,key=lambda p:p.area)
    if inner_ring.geom_type!='Polygon': inner_ring=max(inner_ring.geoms,key=lambda p:p.area)
    lo=shp_prism("lo",outer_ring,z0,z1); li=shp_prism("li",inner_ring,z0-1,z1+1)
    boolean(lo,li,'DIFFERENCE'); rm(li); boolean(plate,lo,'UNION'); rm(lo)
    print("  lip slab",z0,z1,"inner outline area",round(inner.area))
dgx=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(hs,dgx)
pil=[]
for ang in (90,225,315):
    d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); o=Vector((0,-10,104.5))
    h=bvh.ray_cast(o+d*200,-d,300); R=d.to_track_quat('Z','Y').to_matrix().to_4x4()
    pil.append(("cyl",{"loc":h[0]-d*4.0,"r":1.05,"h":12,"seg":16,"rot":R}))
P=multi("pil",pil); P2=dup(P,"pil2"); boolean(head,P,'DIFFERENCE'); rm(P); boolean(plate,P2,'DIFFERENCE'); rm(P2)
head.name="P_HeadBell"; print("F split",stats(head),stats(plate),round(time.time()-t0))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s6.blend")
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
cb=place_on_bed(head,True); export(cb,"/home/claude/out/DeepThought_1a_HeadBell_v4.stl")
cp=place_on_bed(plate,False); export(cp,"/home/claude/out/DeepThought_1b_HeadChin_v4.stl")
for o in (cb,cp):
    bm=bmesh.new(); bm.from_mesh(o.data)
    bed=sum(f.calc_area() for f in bm.faces if f.normal.z<-0.95 and f.calc_center_median().z<0.1)
    ov=sum(f.calc_area() for f in bm.faces if f.normal.z<-0.707 and f.calc_center_median().z>0.3)
    print(o.name,"dims",[round(v,1) for v in o.dimensions],"bed contact",round(bed),"mm2  overhang>45deg",round(ov),"mm2")
print("done",round(time.time()-t0),"s")
