import bpy, mathutils, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5c.blend")
pl=bpy.data.objects["P_Plinth"]; dg=bpy.context.evaluated_depsgraph_get()
bvh=mathutils.bvhtree.BVHTree.FromObject(pl,dg)
zs=[]
for x in range(-90,91,5):
    for y in range(-105,55,5):
        h=bvh.ray_cast(Vector((x,y,60)),Vector((0,0,-1)),100)
        if h[0] is not None and h[0].z>15: zs.append((round(h[0].z,2),x,y))
zs.sort(); print("n",len(zs),"min",zs[0],"max",zs[-1])
import collections
c=collections.Counter(round(z,1) for z,_,_ in zs); print(sorted(c.items()))
