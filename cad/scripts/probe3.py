import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
o=bpy.data.objects["P_Head"]
bvh=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
def ray(p,d,n=8):
    hits=[]; p=Vector(p); d=Vector(d).normalized()
    for i in range(n):
        loc,_,_,_=bvh.ray_cast(p,d)
        if loc is None: break
        hits.append(round(loc.x,1)); p=loc+d*0.01
    return hits
print("through cradle centre (x hits):",ray((-50,-10,165),(1,0,0)))
print("through cradle frame bar (y=-48):",ray((-50,-48,165),(1,0,0)))
print("through zip slot (z=184.6):",ray((-50,-10,184.6),(1,0,0)))
print("grille hole (y=-10,z=165+5.5*.866):",ray((-50,-12.75,169.76),(1,0,0)))
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+c*176.0,176.0))
for u in (0,50,60,61,62,63,64.25,66,70):
    p=C+u*X+30*U+40*D; hits=[]
    for i in range(4):
        loc,_,_,_=bvh.ray_cast(p,-D)
        if loc is None: break
        hits.append(round((loc-C).dot(D),1)); p=loc-D*0.01
    print("u=%5.1f depth hits along D:"%u,hits)
