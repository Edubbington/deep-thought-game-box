import bpy, bmesh, mathutils
from mathutils import Vector
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
C=bpy.data.objects["P_Core"]; P=bpy.data.objects["P_Chin42"]
bm=bmesh.new(); bm.from_mesh(C.data)
strips=unary_union([Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in bm.faces if f.normal.z>0.9 and f.calc_center_median().z>99.7]).buffer(0.01).buffer(-0.01)
dg=bpy.context.evaluated_depsgraph_get(); pb=mathutils.bvhtree.BVHTree.FromObject(P,dg); cb=mathutils.bvhtree.BVHTree.FromObject(C,dg)
def cross(b,x,y):
    out=[]; p=Vector((x,y,90)); d=Vector((0,0,1))
    for _ in range(10):
        h=b.ray_cast(p,d,30)
        if h[0] is None: break
        out.append(round(h[0].z,2)); p=h[0]+d*0.02
    return out
for x,y in [(-64.5,-71.5),(-63.5,-71.5),(-48.5,-72.5),(-46.5,-71.5),(-45.5,-72.5)]:
    print((x,y),"in strip poly:",strips.contains(Point(x,y)),"dist",round(strips.distance(Point(x,y)),2),"core",cross(cb,x,y),"chin42",cross(pb,x,y))
# faces of the core near (-47,-72) above z 96.3: list their normals and z
near=[(round(f.calc_center_median().x,1),round(f.calc_center_median().y,1),round(f.calc_center_median().z,2),tuple(round(v,2) for v in f.normal)) for f in bm.faces if abs(f.calc_center_median().x+47)<2 and abs(f.calc_center_median().y+72)<1.5 and f.calc_center_median().z>96.3]
print(len(near)); print(near[:20])
