import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from mathutils.bvhtree import BVHTree
for f in ["s3.blend","s5.blend"]:
    bpy.ops.wm.open_mainfile(filepath="/home/claude/build/"+f)
    o=bpy.data.objects["P_Riser"]
    bvh=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
    for x,y in [(0,0),(50,26),(-30,-20),(0,-79)]:
        hits=[]; p=Vector((x,y,50))
        for i in range(8):
            loc,_,_,_=bvh.ray_cast(p,Vector((0,0,-1)))
            if loc is None: break
            hits.append(round(loc.z,1)); p=loc+Vector((0,0,-0.01))
        print(f,(x,y),hits)
