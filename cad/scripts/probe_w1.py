import bpy, bmesh, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
o=bpy.data.objects["P_HeadBell"]
a,b_,cc=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-cc)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+cc*176.0,176.0))
dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(o,dg)
def inside(p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(60):
        h=bvh.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
for d_,v_ in ((7,-38),(7,-41),(10,-41),(12,-45),(12,-52),(13.5,-53),(10,-50),(2,-35),(0,-36),(-2,-38),(4,-34)):
    print(f"d={d_:>5} v={v_:>4}: inside={inside(C+d_*D+v_*U)}")
