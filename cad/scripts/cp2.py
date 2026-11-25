import bpy, bmesh, mathutils, math, collections
from mathutils import Vector
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_3_BasePlate_v3.3.stl"); P=bpy.context.selected_objects[0]
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_2_Core_legs_dome.stl"); C=bpy.context.selected_objects[0]
def sec(o,z):
    bm=bmesh.new(); bm.from_mesh(o.data)
    res=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,z),plane_no=(0,0,1))
    segs=[LineString([(e.verts[0].co.x,e.verts[0].co.y),(e.verts[1].co.x,e.verts[1].co.y)]) for e in res['geom_cut'] if isinstance(e,bmesh.types.BMEdge)]
    return sorted(polygonize(unary_union(segs)),key=lambda p:-p.area)
print("PLATE stl dims",[round(v,2) for v in P.dimensions])
bm=bmesh.new(); bm.from_mesh(P.data); h=collections.Counter()
for f in bm.faces:
    if abs(f.normal.z)>0.95: h[(round(f.calc_center_median().z,1),'up' if f.normal.z>0 else 'dn')]+=f.calc_area()
print("plate horizontal faces:",{k:round(v) for k,v in sorted(h.items()) if v>20})
for z in (0.3,2,5,10,20,27):
    ps=sec(P,z); print(" plate section z",z,[(round(p.area),[round(v,1) for v in p.bounds]) for p in ps[:5]])
print("CORE stl dims",[round(v,2) for v in C.dimensions])
for z in (0.2,1,3,8,20,40):
    ps=sec(C,z); print(" core section z",z,[(round(p.area),[round(v,1) for v in p.bounds]) for p in ps[:7]])
