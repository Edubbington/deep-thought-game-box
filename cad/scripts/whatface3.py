import bpy, bmesh, collections, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
o=bpy.data.objects["P_HeadBell"]; bm=bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm,faces=bm.faces[:])
sel=[f for f in bm.faces if f.normal.z>0.9 and 224<f.calc_center_median().z<236]
print("flat up-facing faces z224..236: area",round(sum(f.calc_area() for f in sel)))
c=collections.Counter()
for f in sel:
    m=f.calc_center_median(); c[(round(m.y/4)*4,round(m.z))]+=f.calc_area()
for k,v in sorted(c.items()): 
    if v>20: print("  y,z",k,round(v))
a,b_,cc=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-cc)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+cc*176.0,176.0))
dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(o,dg)
def inside(p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(50):
        h=bvh.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
for d_,v_ in ((7,53),(7,56),(7,62),(12,56),(2,56),(7,70)):
    p=C+d_*D+v_*U; print(f"point d={d_} v={v_} -> model (y={p.y:.1f}, z={p.z:.1f}) inside solid: {inside(p)}")
