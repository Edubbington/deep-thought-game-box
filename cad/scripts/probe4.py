import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
o=bpy.data.objects["P_Plinth"]
bvh=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
for r in (0,14,16,20,24,25,27,40):
    hits=[]; p=Vector((r,1.7,40))
    for i in range(6):
        loc,_,_,_=bvh.ray_cast(p,Vector((0,0,-1)))
        if loc is None: break
        hits.append(round(loc.z,1)); p=loc+Vector((0,0,-0.01))
    print("r=%2d z hits"%r,hits)
