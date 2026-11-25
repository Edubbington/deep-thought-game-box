import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils
from shapely.geometry import Polygon, Point
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
H=bpy.data.objects["P_HeadBell"]; CORE=bpy.data.objects["P_Core"]; OLD=bpy.data.objects["P_Chin"]
def loops_at(o,z):
    bm=bmesh.new(); bm.from_mesh(o.data)
    res=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,z),plane_no=(0,0,1))
    cut=[e for e in res['geom_cut'] if isinstance(e,bmesh.types.BMEdge)]; adj={}
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
    bm.free(); return [Polygon(l).buffer(0) for l in loops if len(l)>12]
def big(p):
    return p if p.geom_type=='Polygon' else max(p.geoms,key=lambda q:q.area)
def prism(name,poly,z0,z1):
    poly=big(poly); bm=bmesh.new(); pts=list(poly.exterior.coords)[:-1]
    bot=[bm.verts.new((x,y,z0)) for x,y in pts]; top=[bm.verts.new((x,y,z1)) for x,y in pts]
    bm.faces.new(bot[::-1]); bm.faces.new(top); n=len(pts)
    for i in range(n): bm.faces.new((bot[i],bot[(i+1)%n],top[(i+1)%n],top[i]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); return link(name,bm)
def ring(name,outer,inner,z0,z1):
    o=prism(name,outer,z0,z1); i=prism(name+"i",inner,z0-1,z1+1); boolean(o,i,'DIFFERENCE'); rm(i); return o
# outline of the plate = the old chin's outer loop at z=97 (flush with the bell)
outline=Polygon(section_loop(bpy.data.objects["DT"],98.5)).buffer(0); print("outline area",round(outline.area),"bounds",[round(v,1) for v in outline.bounds])
# core lip at z 98.5: outer and inner loops
cl=sorted(loops_at(CORE,98.5),key=lambda p:-p.area); lip_out,lip_in=cl[0],cl[1]
print("core lip loops:",[round(p.area) for p in cl], "lip width ~",round((lip_out.area-lip_in.area)/lip_out.length,2))
mags=[(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]
for m in mags:
    d_out=lip_out.exterior.distance(Point(m)); print("magnet",m,"inside lip ring:",lip_out.contains(Point(m)) and not lip_in.contains(Point(m)),"inside lip outline:",lip_out.contains(Point(m)),"dist to lip outer edge",round(d_out,1))
# ---- build
plate=prism("P_Chin41",outline,96,100.5)                              # skin + floor, 4.5 thick, flush with the bell
# floor above the bell's bottom edge + the lip, LOFTED to follow the bell's inner wall (0.4 mm clearance), 0.5 mm slices
from shapely.geometry import LineString
def wall_at(z):
    lp=sorted(loops_at(H,z),key=lambda p:-p.area); return big(lp[1])
def resample(poly,N=400):
    ext=LineString(poly.exterior.coords); L=ext.length
    pts=[ext.interpolate(L*j/N) for j in range(N)]
    k=min(range(N),key=lambda j:(pts[j].x)**2+(pts[j].y+200)**2)   # start at the front-centre so slices correspond
    pts=pts[k:]+pts[:k]
    # consistent winding (counter-clockwise)
    area=sum(pts[j].x*pts[(j+1)%N].y-pts[(j+1)%N].x*pts[j].y for j in range(N))
    if area<0: pts=[pts[0]]+pts[1:][::-1]
    return [(p.x,p.y) for p in pts]
def loft(name,zs,offset):
    rows=[]; bm=bmesh.new(); cache={}
    def pts_at(zw):
        if zw not in cache: cache[zw]=resample(big(wall_at(zw).buffer(offset,join_style=1)))
        return cache[zw]
    for z in zs:
        zw=max(z,100.6)
        if 103.0<zw<106.0:
            t=(zw-103.0)/3.0; a=pts_at(103.0); b=pts_at(106.0); pts=[(ax+(bx-ax)*t,ay+(by-ay)*t) for (ax,ay),(bx,by) in zip(a,b)]   # blend across the pilot-hole band
        else: pts=pts_at(zw)
        rows.append([bm.verts.new((x,y,z)) for x,y in pts])
    N=len(rows[0])
    for r0,r1 in zip(rows,rows[1:]):
        for j in range(N): bm.faces.new((r0[j],r0[(j+1)%N],r1[(j+1)%N],r1[j]))
    bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1]); bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); return link(name,bm)
zs=[100.0+0.5*i for i in range(0,18)]           # 100.0 .. 108.5
fl=loft("fl",[z for z in zs if z<=104.5]+[104.6],-0.4); boolean(plate,fl,'UNION'); rm(fl)
lo=loft("lo",[103.5]+[z for z in zs if z>=104.0],-0.4); li=loft("li",[103.0]+[z for z in zs if z>=104.0]+[109.0],-3.4)
boolean(lo,li,'DIFFERENCE'); rm(li); boolean(plate,lo,'UNION'); rm(lo)
# clearance pockets for the three core magnet bosses (top at z 100.0): r+0.4, blind to 100.4
ko=multi("ko",[("cyl",{"loc":Vector((x,y,97.7)),"r":8.4,"h":5.4,"seg":48}) for x,y in mags]); boolean(plate,ko,'DIFFERENCE'); rm(ko)
wire=cyl("wire",Vector((0,12,99)),14,20); boolean(plate,wire,'DIFFERENCE'); rm(wire)              # wire hole over the neck channel exit
# magnet pockets from the underside
for x,y in mags:
    mp=cyl("mp",Vector((x,y,100.4+1.7-0.5)),3.2,4.4,32); boolean(plate,mp,'DIFFERENCE'); rm(mp)   # magnet pockets in the roof of each clearance pocket: z 100.4..103.8
# screw pilots, same as v4: z 104.5 at 90/225/315 deg from (0,-10), r1.05, 8 mm deep from the outer surface
dg=bpy.context.evaluated_depsgraph_get(); hs=dup(bpy.data.objects["DT"],"hs2"); bb=box("s",Vector((0,0,198)),(400,400,204)); boolean(hs,bb,'INTERSECT'); rm(bb)
bvh=mathutils.bvhtree.BVHTree.FromObject(hs,dg); pil=[]
for ang in (90,225,315):
    d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); o=Vector((0,-10,104.5))
    h=bvh.ray_cast(o+d*200,-d,300); R=d.to_track_quat('Z','Y').to_matrix().to_4x4()
    pil.append(("cyl",{"loc":h[0]-d*4.0,"r":1.05,"h":12,"seg":16,"rot":R}))
P=multi("pil",pil); boolean(plate,P,'DIFFERENCE'); rm(P); rm(hs)
print("chin v4.1",stats(plate))
# ---- verify against the core and the bell
dg=bpy.context.evaluated_depsgraph_get()
pb=mathutils.bvhtree.BVHTree.FromObject(plate,dg); cb=mathutils.bvhtree.BVHTree.FromObject(CORE,dg); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def inside(b,p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(60):
        h=b.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
# sample the core lip volume: any point also inside the plate = collision
import random; random.seed(1); coll=0; tot=0
for mx,my in mags:
    for ang in range(0,360,20):
        for rr in (2,5,7.5):
            for z in (96.5,98,99.5,99.9):
                p=Vector((mx+rr*math.cos(math.radians(ang)),my+rr*math.sin(math.radians(ang)),z)); tot+=1; coll+= inside(pb,p) and inside(cb,p)
print("core-lip vs plate collision samples:",coll,"of",tot)
# plate vs bell: sample the plate lip
coll=0; tot=0
for zz in (101,103,105,107,108):
    lp=sorted(loops_at(plate,zz),key=lambda p:-p.area); c=0; t=0
    for poly in lp:
        for x,y in list(poly.exterior.coords)[::4]:
            t+=1; c+= inside(hb,Vector((x,y,zz)))
    print("plate vs bell at z",zz,":",c,"of",t,"samples inside the bell")
for x,y in [(m[0]+1.5,m[1]) for m in mags]+[(x+9,y) for x,y in mags]+[(0,-60),(0,40),(-60,0),(60,0)]:
    h=[]; p=Vector((x,y,90)); d=Vector((0,0,1))
    for _ in range(6):
        r=pb.ray_cast(p,d,30)
        if r[0] is None: break
        h.append(round(r[0].z,1)); p=r[0]+d*0.02
    print("point",(x,y),"plate z-crossings",h)
OLD.name="P_Chin_v4"; plate.name="P_Chin"
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s6b.blend")
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
cp=place_on_bed(plate,False); export(cp,"/home/claude/out/DeepThought_1b_HeadChin_v4.1.stl")
bm=bmesh.new(); bm.from_mesh(cp.data)
print("print dims",[round(v,1) for v in cp.dimensions],"bed contact",round(sum(f.calc_area() for f in bm.faces if f.normal.z<-0.95 and f.calc_center_median().z<0.1)),"overhang>45",round(sum(f.calc_area() for f in bm.faces if f.normal.z<-0.707 and f.calc_center_median().z>0.3)))
