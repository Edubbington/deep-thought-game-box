import bpy, bmesh, mathutils, random
from mathutils import Vector
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
bpy.ops.wm.read_factory_settings(use_empty=True)
# verify the EXPORTED STLs against each other, in the printed-core STL frame
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_2_Core_legs_dome.stl"); C=bpy.context.selected_objects[0]; C.name="core"
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1b_HeadChin_v4.2.stl"); P=bpy.context.selected_objects[0]; P.name="chin"
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1b_HeadChin_v4.stl"); P4=bpy.context.selected_objects[0]; P4.name="chin4"
# core STL: plate top at 72.6, strips to 76.6. Chin STLs: printed flat-top-down? v4 chin was exported with place_on_bed(flip=False) -> underside at z=0 (model 96).
# Put the chin into the core frame: model z = stl z + 96 ; core model z = stl z + 23.4 ; xy: both were centred on their own bbox centre -> re-centre using model data below.
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
Cm=bpy.data.objects["P_Core"]; Pm=bpy.data.objects["P_Chin42"]
def bbc(o):
    import numpy as np; v=np.array([(o.matrix_world@w.co)[:] for w in o.data.vertices]); return (v.min(0)+v.max(0))/2, v.min(0)
cc,cmin=bbc(Cm); pc,pmin=bbc(Pm)
print("core model bbox centre",cc.round(2),"min z",round(cmin[2],2)," chin42 model centre",pc.round(2),"min z",round(pmin[2],2))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_2_Core_legs_dome.stl"); C=bpy.context.selected_objects[0]
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1b_HeadChin_v4.2.stl"); P=bpy.context.selected_objects[0]
# move both into model frame
def shift(o,v):
    b=bmesh.new(); b.from_mesh(o.data); b.transform(mathutils.Matrix.Translation(Vector(v))); b.to_mesh(o.data); b.free()
import numpy as np
def bb(o):
    v=np.array([w.co[:] for w in o.data.vertices]); return (v.min(0)+v.max(0))/2, v.min(0), v.max(0)-v.min(0)
for o,c,mn in ((C,cc,cmin),(P,pc,pmin)):
    sc,smin,sdim=bb(o); print(o.name,"stl bbox centre",sc.round(2),"min",smin.round(2),"dims",sdim.round(2))
    shift(o,(c[0]-sc[0],c[1]-sc[1],mn[2]-smin[2]))
    print("  after shift bbox centre",bb(o)[0].round(2),"min z",round(bb(o)[1][2],2))
bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
cb=mathutils.bvhtree.BVHTree.FromObject(C,dg); pb=mathutils.bvhtree.BVHTree.FromObject(P,dg)
def cross(b,x,y,z0=90,z1=112):
    out=[]; p=Vector((x,y,z0)); d=Vector((0,0,1))
    for _ in range(12):
        h=b.ray_cast(p,d,z1-z0)
        if h[0] is None: break
        out.append(h[0].z); p=h[0]+d*0.01
    return out
# 1) grid over the whole footprint: wherever the core has material above 96 (the strips), the chin must start >= core top + 0.3
bad=[]; n=0; gaps=[]
for xi in range(-90,90):
    for yi in range(-80,70):
        x,y=xi+0.5,yi+0.5
        cz=cross(cb,x,y,z0=95.9,z1=101)
        if not cz: continue
        top=max(cz)
        if top<96.3: continue           # bare plate at 96
        n+=1; pz=cross(pb,x,y,z0=95.5,z1=112)
        if pz:
            gap=min(pz)-top; gaps.append(gap)
            if gap<0.3: bad.append((x,y,round(top,2),round(min(pz),2)))
print(f"strip columns sampled on a 1 mm grid: {n}; chin material too close/colliding: {len(bad)}; vertical gap over the strips min {min(gaps):.2f} max {max(gaps):.2f} mm")
print(bad[:10])
# 2) side clearance: channel wall to strip wall, sampled at z=98 along each strip edge
bm=bmesh.new(); bm.from_mesh(C.data); bm.transform(C.matrix_world)
strips=list(unary_union([Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in bm.faces if f.normal.z>0.9 and f.calc_center_median().z>99.7]).buffer(0.01).buffer(-0.01).geoms)
side=[]
for s in strips:
    ext=s.exterior
    for k in range(0,200):
        p=ext.interpolate(ext.length*k/200)
        # outward normal: step away from the strip until out of it, then ray horizontally to the chin channel wall
        c=s.centroid; 
        for ang in range(0,360,45):
            import math; d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0))
            q=Vector((p.x,p.y,98.0))+d*0.05
            if s.contains(Point(q.x,q.y)): continue
            h=pb.ray_cast(q,d,3.0)
            if h[0]: side.append((h[0]-q).length+0.05)
print(f"horizontal clearance strip wall -> channel wall at z=98: min {min(side):.2f}  median {sorted(side)[len(side)//2]:.2f} mm ({len(side)} rays)")
# 3) chin rests on the plate top: lowest chin z and area of chin faces at 96 that sit over core material at 96
bm2=bmesh.new(); bm2.from_mesh(P.data); bm2.transform(P.matrix_world)
low=min(v.co.z for v in bm2.verts); print("chin lowest point z =",round(low,2),"(core plate top = 96.0)")
# 4) magnet pockets: core pocket positions from the core STL (down-facing faces just below 96)
import collections
pk=collections.defaultdict(list)
for f in bm.faces:
    c=f.calc_center_median()
    if f.normal.z>0.9 and 91.0<c.z<95.9: pk[(round(c.x/4)*4,round(c.y/4)*4)].append((c.x,c.y,c.z))
cores=[(round(sum(a[0] for a in v)/len(v),1),round(sum(a[1] for a in v)/len(v),1),round(v[0][2],2)) for k,v in pk.items() if len(v)>4]
print("core magnet pocket floors (x,y,z):",cores)
for x,y,z in cores:
    pz=cross(pb,x,y,z0=95.5,z1=110); print("  chin above pocket",(x,y),"chin z-crossings",[round(v,2) for v in pz])
    # pocket diameter in chin: ray horizontally at z=97.5 from the centre
    import math; rs=[]
    for ang in range(0,360,30):
        d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); h=pb.ray_cast(Vector((x,y,97.5)),d,10); rs.append((h[0]-Vector((x,y,97.5))).length if h[0] else None)
    print("    chin pocket diameter at that spot:",round(2*sum(rs)/len(rs),2) if all(rs) else rs)
    rs=[]
    for ang in range(0,360,30):
        d=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0)); h=cb.ray_cast(Vector((x,y,94.5)),d,10); rs.append((h[0]-Vector((x,y,94.5))).length if h[0] else None)
    print("    core pocket diameter:",round(2*sum(rs)/len(rs),2) if all(rs) else rs)
