import bpy, bmesh, math, pickle, mathutils
from mathutils import Vector
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6b.blend")
C=bpy.data.objects["P_Core"]; P4=bpy.data.objects["P_Chin_v4"]; H=bpy.data.objects["P_HeadBell"]
bm=bmesh.new(); bm.from_mesh(C.data)
tris=[Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in bm.faces if f.normal.z>0.9 and f.calc_center_median().z>99.7]
strips=list(unary_union(tris).buffer(0.01).buffer(-0.01).geoms)
print("core top strips (model frame):")
for s in strips: print("  area",round(s.area),"bbox",[round(v,1) for v in s.bounds],"length~",round(s.length/2),"width~",round(2*s.area/s.length,2))
# strip height: section of the core at z=98 should show the same strips; and the top plate z
dg=bpy.context.evaluated_depsgraph_get(); cb=mathutils.bvhtree.BVHTree.FromObject(C,dg); pb=mathutils.bvhtree.BVHTree.FromObject(P4,dg); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def down(b,x,y,z0=130):
    h=b.ray_cast(Vector((x,y,z0)),Vector((0,0,-1)),200); return round(h[0].z,2) if h[0] else None
def up(b,x,y,z0=90):
    out=[]; p=Vector((x,y,z0)); d=Vector((0,0,1))
    for _ in range(8):
        h=b.ray_cast(p,d,40)
        if h[0] is None: break
        out.append(round(h[0].z,2)); p=h[0]+d*0.02
    return out
# sample along each strip's centreline: core top z there, and the chin v4's z-crossings there
print("\nalong each strip: core top z | chin v4 material z-ranges (chin underside should be 96.0)")
for si,s in enumerate(strips):
    ext=s.exterior; L=ext.length; worst=[]
    for k in range(0,40):
        p=ext.interpolate(L*k/40); q=Point(p.x,p.y)
        # move the point to the strip's centre: average with nearest point on the opposite side
        c=s.centroid
        pts=[ext.interpolate(L*k/40) for k in range(40)]
        x,y=p.x,p.y
        cz=down(cb,x,y); ch=up(pb,x,y)
        if cz and cz>99.5 and ch: worst.append((round(x,1),round(y,1),cz,ch))
    print(f" strip {si}: {len(worst)} samples on the strip top; examples:",worst[::max(1,len(worst)//6)][:6])
# where does the chin v4 touch the core strips? count points on strip tops with chin material below 100
coll=0; tot=0; where=[]
for s in strips:
    xs,ys=s.exterior.xy
    for x,y in zip(xs[::2],ys[::2]):
        cz=down(cb,x,y)
        if cz is None or cz<99.5: continue
        tot+=1; ch=up(pb,x,y,z0=95.5)
        # chin material between 96 and 100 at this xy?
        inside=False; zz=[v for v in ch if v<=100.0]
        if len(ch)>=1 and ch[0]<100.0: coll+=1; where.append((round(x),round(y),ch[:2]))
print(f"\nchin v4 vs strips: {coll} of {tot} strip-top samples have chin material below z=100 (= collision):")
print(where[::max(1,len(where)//10)])
pickle.dump([list(s.exterior.coords) for s in strips],open("/home/claude/build/strips.pkl","wb"))
