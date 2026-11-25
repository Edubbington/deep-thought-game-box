import bpy, bmesh, mathutils
from mathutils import Vector
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
C=bpy.data.objects["P_Core"]; P=bpy.data.objects["P_Chin42"]
bm=bmesh.new(); bm.from_mesh(C.data)
strips=unary_union([Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in bm.faces if f.normal.z>0.9 and f.calc_center_median().z>99.7]).buffer(0.01).buffer(-0.01)
# what core faces exist above z=96.2 that are NOT part of the strips (within 0.5)?
other=[]
for f in bm.faces:
    c=f.calc_center_median()
    if c.z>96.3 and c.z<99.6 and strips.distance(Point(c.x,c.y))>0.6: other.append((round(c.x,1),round(c.y,1),round(c.z,1)))
print("core faces above the plate not near the strips:",len(other),other[:10])
dg=bpy.context.evaluated_depsgraph_get(); pb=mathutils.bvhtree.BVHTree.FromObject(P,dg); cb=mathutils.bvhtree.BVHTree.FromObject(C,dg)
def cross(b,x,y):
    out=[]; p=Vector((x,y,90)); d=Vector((0,0,1))
    for _ in range(10):
        h=b.ray_cast(p,d,30)
        if h[0] is None: break
        out.append(round(h[0].z,2)); p=h[0]+d*0.02
    return out
for x,y in [(69.8,-53.1),(71.4,-53.1),(72.8,-54.4),(71.1,-68.2),(73.2,-62.3),(72.2,-56.6)]:
    print((x,y),"dist to strip",round(strips.distance(Point(x,y)),2),"core z-crossings",cross(cb,x,y),"plate z-crossings",cross(pb,x,y))
