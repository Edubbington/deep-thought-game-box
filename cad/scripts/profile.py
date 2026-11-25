import bpy, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5b.blend")
dg=bpy.context.evaluated_depsgraph_get()
def hits(name,origin,d,maxn=8):
    o=bpy.data.objects[name]; bvh=mathutils.bvhtree.BVHTree.FromObject(o,dg)
    out=[]; p=Vector(origin)
    for _ in range(maxn):
        h=bvh.ray_cast(p,Vector(d),500)
        if h[0] is None: break
        out.append(round(h[0].y,1)); p=h[0]+Vector(d)*0.05
    return out
print("ray along +y at x=0 (front wall); values = y of each surface crossing")
for z in [-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,8,10,15,20,22]:
    print(f"z={z:>3}  plate:{hits('P_Plinth',(0,-200,z),(0,1,0))[:4]}   riser:{hits('P_Riser',(0,-200,z),(0,1,0))[:4]}")
