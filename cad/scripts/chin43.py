import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils, pickle, math
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6b.blend")
H=bpy.data.objects["P_HeadBell"]; CORE=bpy.data.objects["P_Core"]; V4=bpy.data.objects["P_Chin_v4"]
for n in ("P_Chin","P_Chin41"):
    if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
src=open("/home/claude/build/chin41.py").read()
exec(src[src.index("def loops_at"):src.index("# outline of the plate")])         # loops_at, big, prism, ring
exec(src[src.index("from shapely.geometry import LineString"):src.index("zs=[100.0+0.5*i")])   # wall_at, resample, loft
# ---- the core's wall segments, straight from the core mesh
bm=bmesh.new(); bm.from_mesh(CORE.data)
strips=list(unary_union([Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in bm.faces if f.normal.z>0.9 and f.calc_center_median().z>99.7]).buffer(0.01).buffer(-0.01).geoms)
bm.free(); print("segments:",[round(s.area) for s in strips])
plate=dup(V4,"P_Chin42")
k=box("k",Vector((0,0,(100.5-50)/2)),(500,500,150.5)); boolean(plate,k,'INTERSECT'); rm(k)   # drop the v4 lip above the bell edge; the loft below replaces it
# ---- solid fill of the old taper opening + thicker floor + lofted lip (0.4 mm to the bell wall at every height)
from shapely.geometry import LineString
from shapely.ops import polygonize
_dg=bpy.context.evaluated_depsgraph_get(); _b4=mathutils.bvhtree.BVHTree.FromObject(V4,_dg)
def outer_at(o,z,n=720):
    # outer silhouette of the v4 chin at height z, seen radially from the footprint centre;
    # rays that fall through a hole in the skin (the mouth's through-cut) are bridged from their neighbours
    rad=[]; dirs=[]
    for k in range(n):
        a=2*math.pi*k/n; d=Vector((-math.cos(a),-math.sin(a),0)); org=Vector((2+math.cos(a)*120,-9+math.sin(a)*120,z))
        h=_b4.ray_cast(org,d,200); rad.append(120-(h[0]-org).length if h[0] else 0.0); dirs.append((a,org,d))
    import statistics
    hole=[rad[k]<statistics.median([rad[(k+j)%n] for j in range(-15,16) if j!=0])-5.0 for k in range(n)]   # fell through a hole in the skin (>5 mm): the 2.3 mm mouth recess is kept
    fixed=list(rad)
    for k in range(n):
        if not hole[k]: continue
        i=k
        while hole[i%n]: i-=1
        j=k
        while hole[j%n]: j+=1
        fixed[k]=min(rad[i%n],rad[j%n])-0.5   # bridge a hole at the depth of the deeper neighbour (the mouth-slot floor), a bit deeper
    rad=fixed
    pts=[(dirs[k][1].x+dirs[k][2].x*(120-rad[k]), dirs[k][1].y+dirs[k][2].y*(120-rad[k])) for k in range(n)]
    return Polygon(pts).buffer(0)
# fill the old taper opening with 0.5 mm slabs that follow the v4 outer skin (1.2 mm inside it), so the outside is untouched
z0=96.0
while z0<100.5-1e-6:
    z1=min(z0+0.5,100.5)
    env=None   # the fill must sit inside the v4 skin at EVERY height of the slab (the mouth groove is slanted ~10 mm in x per 1 mm of z)
    for zz in [z0+0.01]+[z0+0.05+0.1*i for i in range(5)]+[z1-0.01]:
        sil_=outer_at(V4,zz); env=sil_ if env is None else env.intersection(sil_)
    ring=env.buffer(-1.2,join_style=1)
    print(f"  fill slab {z0:.1f}-{z1:.1f}: {ring.geom_type} area {ring.area:.0f}")
    for gi,g in enumerate(ring.geoms if ring.geom_type=='MultiPolygon' else [ring]):
        sl=prism(f"sl{int(z0*10)}_{gi}",g,z0-0.02,z1+0.02); boolean(plate,sl,'UNION'); rm(sl)
    z0=z1
kb=box("kb",Vector((0,0,96+100)),(500,500,200)); boolean(plate,kb,'INTERSECT'); rm(kb)   # underside dead flat at z=96
zs=[100.0+0.5*i for i in range(0,18)]
fl=loft("fl",[z for z in zs if z<=104.5]+[104.6],-0.4); boolean(plate,fl,'UNION'); rm(fl)
lo=loft("lo",[103.5]+[z for z in zs if z>=104.0],-0.4); li=loft("li",[103.0]+[z for z in zs if z>=104.0]+[109.0],-3.4)
boolean(lo,li,'DIFFERENCE'); rm(li); boolean(plate,lo,'UNION'); rm(lo)
# magnet pockets (re-cut, the fill covered them): 6.4 wide, 3.4 deep from the underside
for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]:
    mp=cyl("mp",Vector((x,y,96+1.7-0.5)),3.2,4.4,32); boolean(plate,mp,'DIFFERENCE'); rm(mp)
# ---- wire opening through the new floor (the old taper opening is below it)
w=cyl("w",Vector((0,4,100.5)),24,14); boolean(plate,w,'DIFFERENCE'); rm(w)
# ---- channel for the wall segments: segment outline + 0.4 mm, from below the plate up to 100.4 (segments top out at 100.0)
for i,s in enumerate(strips):
    ch=prism(f"ch{i}",s.buffer(0.4,join_style=1),95.0,100.4); boolean(plate,ch,'DIFFERENCE'); rm(ch)
print("chin v4.2",stats(plate))
# ---- screw pilots, same as v4: z 104.5 at 90/225/315 deg from (0,-10), r1.05, reaching 10 mm in from the head's outer surface
_hs=dup(bpy.data.objects["DT"],"hs2"); _bb=box("s",Vector((0,0,198)),(400,400,204)); boolean(_hs,_bb,'INTERSECT'); rm(_bb)
_bv=mathutils.bvhtree.BVHTree.FromObject(_hs,bpy.context.evaluated_depsgraph_get())
for ang in (90,225,315):
    d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); o=Vector((0,-10,104.5))
    h=_bv.ray_cast(o+d*200,-d,300); R=d.to_track_quat('Z','Y').to_matrix().to_4x4()
    pc_=cyl("pil",h[0]-d*4.0,1.05,12,16,rot=R); boolean(plate,pc_,'DIFFERENCE'); rm(pc_)
rm(_hs)
# ---- VERIFY against the core mesh and the bell mesh
dg=bpy.context.evaluated_depsgraph_get()
pb=mathutils.bvhtree.BVHTree.FromObject(plate,dg); cb=mathutils.bvhtree.BVHTree.FromObject(CORE,dg); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def inside(b,p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(80):
        h=b.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
coll=0; tot=0; cp_=[]
for s in strips:
    xs,ys=s.exterior.xy
    for x,y in list(zip(xs,ys))[::2]:
        for z in (96.3,97.5,98.8,99.9):
            p=Vector((x,y,z))
            if inside(cb,p):
                tot+=1
                if inside(pb,p): coll+=1; cp_.append((round(x,1),round(y,1),z))
print(f"segment volume vs plate: {coll} collisions of {tot} samples"); print("  collision points:",cp_[:12])
# plate underside: lowest plate material, and does it rest on the core top plate (z=96)?
bm=bmesh.new(); bm.from_mesh(plate.data); print("plate z range",round(min(v.co.z for v in bm.verts),2),round(max(v.co.z for v in bm.verts),2))
down=sum(f.calc_area() for f in bm.faces if f.normal.z<-0.95 and abs(f.calc_center_median().z-96.0)<0.05); print("flat underside area at z=96:",round(down),"mm2")
# any plate material inside the core (other than the segments)?
import random; random.seed(2); c2=0; t2=0
for _ in range(3000):
    x=random.uniform(-80,80); y=random.uniform(-80,65); z=random.uniform(94,100.5); p=Vector((x,y,z))
    if inside(cb,p): t2+=1; c2+= inside(pb,p)
print(f"random core-volume samples z94..100.5: {c2} inside the plate of {t2}")
# plate vs bell
for zz in (101,102.5,106.2,108.4):
    bi=big(sorted(loops_at(H,zz),key=lambda p:-p.area)[1]); pl=sorted(loops_at(plate,zz),key=lambda p:-p.area)
    if pl:
        po=pl[0]; ds=[(bi.exterior.distance(Point(c)) if bi.contains(Point(c)) else -bi.exterior.distance(Point(c))) for c in po.exterior.coords]
        print(f"plate outer edge to bell inner wall at z{zz}: min {min(ds):.2f} max {max(ds):.2f}")
# magnet pockets intact?
for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]:
    h=[]; p=Vector((x,y,90)); d=Vector((0,0,1))
    for _ in range(8):
        r=pb.ray_cast(p,d,30)
        if r[0] is None: break
        h.append(round(r[0].z,2)); p=r[0]+d*0.02
    print("magnet",(x,y),"plate z-crossings",h)
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s6c.blend")
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
tb=bmesh.new(); tb.from_mesh(plate.data); bmesh.ops.triangulate(tb,faces=tb.faces[:],quad_method='BEAUTY',ngon_method='BEAUTY'); tb.normal_update()
print("pre-export triangulated: up-facing faces at 96 =",sum(1 for f in tb.faces if f.normal.z>0.9 and abs(f.calc_center_median().z-96)<0.01)); tb.to_mesh(plate.data); tb.free()
cp=place_on_bed(plate,False)
tb=bmesh.new(); tb.from_mesh(cp.data)
bmesh.ops.dissolve_degenerate(tb,dist=1e-4,edges=tb.edges[:]); tb.faces.ensure_lookup_table()
seen=set(); kill=[]
for f in tb.faces:
    if f.index in seen: continue
    stack=[f]; comp=[]
    while stack:
        g=stack.pop()
        if g.index in seen: continue
        seen.add(g.index); comp.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: stack.append(h)
    if len(comp)<100: kill+=comp
print("removing sliver shells: faces",len(kill))
bmesh.ops.delete(tb,geom=kill,context='FACES')
flaps=[f for f in tb.faces if f.calc_area()<0.01 and any(len(e.link_faces)!=2 for e in f.edges)]
print("removing flap faces:",len(flaps)); bmesh.ops.delete(tb,geom=flaps,context='FACES')
bnd=[e for e in tb.edges if e.is_boundary]
if bnd: bmesh.ops.holes_fill(tb,edges=bnd,sides=8)
print("non-manifold edges in export mesh:",sum(1 for e in tb.edges if not e.is_manifold)); tb.to_mesh(cp.data); tb.free()
export(cp,"/home/claude/out/DeepThought_1b_HeadChin_v4.3.stl")
bm=bmesh.new(); bm.from_mesh(cp.data)
print("print dims",[round(v,1) for v in cp.dimensions],"bed contact",round(sum(f.calc_area() for f in bm.faces if f.normal.z<-0.95 and f.calc_center_median().z<0.1)))
