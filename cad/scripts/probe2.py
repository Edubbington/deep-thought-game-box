import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
o=bpy.data.objects["P_Head"]
bvh=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
def ray(p,d,n=6):
    hits=[]; p=Vector(p); d=Vector(d).normalized()
    for i in range(n):
        loc,_,_,_=bvh.ray_cast(p,d)
        if loc is None: break
        hits.append(tuple(round(x,1) for x in loc)); p=loc+d*0.01
    return hits
print("anchor ray", ray((-35,0,140),(0,1,0)))
print("no-anchor ray", ray((-10,0,140),(0,1,0)))
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+c*176.0,176.0))
for u,v in [(-76.25,30),(76.25,-30)]:
    p=C+u*X+v*U+40*D
    print("boss ray from inside",(u,v),ray(p,-D,3))
