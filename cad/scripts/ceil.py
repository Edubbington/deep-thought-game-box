import bpy, mathutils, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5d.blend")
H=bpy.data.objects["P_Head"]; dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(H,dg)
print("interior ceiling height (model z) vs radius from (0,-10); '--' = wall reached")
print("  r:  "+"  ".join(f"{r:>5}" for r in range(0,101,10)))
for a in (0,45,90,135,180,225,270,315):
    row=[]
    for r in range(0,101,10):
        x,y=r*math.cos(math.radians(a)),-10+r*math.sin(math.radians(a))
        # start low inside the cavity and shoot up
        h=bvh.ray_cast(Vector((x,y,150)),Vector((0,0,1)),120)
        row.append(f"{h[0].z:5.1f}" if h[0] is not None else "  -- ")
    print(f"{a:>3}: "+"  ".join(row))
# exterior top: where is the exterior at z=250 flat region edge?
print("exterior top height vs radius:")
for a in (0,90,180,270):
    row=[]
    for r in range(0,101,10):
        x,y=r*math.cos(math.radians(a)),-10+r*math.sin(math.radians(a))
        h=bvh.ray_cast(Vector((x,y,300)),Vector((0,0,-1)),120); row.append(f"{h[0].z:5.1f}" if h[0] is not None else "  -- ")
    print(f"{a:>3}: "+"  ".join(row))
