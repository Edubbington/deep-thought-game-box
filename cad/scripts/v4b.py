import bpy, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
dg=bpy.context.evaluated_depsgraph_get(); B=bpy.data.objects["P_HeadBell"]; bb=mathutils.bvhtree.BVHTree.FromObject(B,dg)
def hits(o,d,maxd=400):
    out=[]; p=Vector(o); d=Vector(d).normalized()
    for _ in range(12):
        h=bb.ray_cast(p,d,maxd)
        if h[0] is None: break
        out.append(h[0]); p=h[0]+d*0.02
    return out
print("ray +y at (71,*,165): y crossings",[round(p.y,1) for p in hits((71,-80,165),(0,1,0),200)])
print("ray +y at (71,*,140): y crossings",[round(p.y,1) for p in hits((71,-80,140),(0,1,0),200)])
print("ray +x at (*, -30,165): x crossings",[round(p.x,1) for p in hits((0,-30,165),(1,0,0),200)])
print("ray +x at (*, -30,172): x crossings",[round(p.x,1) for p in hits((0,-30,172),(1,0,0),200)])
print("ray +z at (71,-10,*): z crossings",[round(p.z,1) for p in hits((71,-10,120),(0,0,1),120)])
print("ray +z at (71,-48.5,*): z crossings (y-wall)",[round(p.z,1) for p in hits((71,-48.5,120),(0,0,1),120)])
print("ray +z at (60,-10,*): z crossings (front wall of frame)",[round(p.z,1) for p in hits((60,-10,120),(0,0,1),120)])
