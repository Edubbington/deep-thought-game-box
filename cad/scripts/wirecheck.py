import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
B={n:BVHTree.FromPolygons([v.co for v in bpy.data.objects[n].data.vertices],[tuple(p.vertices) for p in bpy.data.objects[n].data.polygons]) for n in ("P_Riser","P_Plinth","P_Core","P_Head")}
def ray(n,p,d,k=10):
    bvh=B[n]; hits=[]; p=Vector(p); d=Vector(d).normalized()
    for i in range(k):
        loc,_,_,_=bvh.ray_cast(p,d)
        if loc is None: break
        hits.append(round(loc.z,1) if abs(d.z)>0.5 else (round(loc.x,1),round(loc.y,1))); p=loc+d*0.01
    return hits
print("== vertical ray up along the wire path (x=0,y=1.7 then y=12) ==")
for n in ("P_Riser","P_Plinth","P_Core","P_Head"):
    print(n,"at (0,1.7):",ray(n,(0,1.7,-45),(0,0,1)))
for n in ("P_Core","P_Head"):
    print(n,"at (0,12):",ray(n,(0,12,-45),(0,0,1)))
print("== neck channel cross-section at z=60,75,90 (ray along +x from x=-40 at y=12) ==")
for z in (40,60,75,90,95):
    print("z=%d"%z,ray("P_Core",(-60,12,z),(1,0,0)))
print("== riser power slot: ray along +y at z=-20 ==")
print(ray("P_Riser",(0,-100,-20),(0,1,0)))
print("== dome inside radius at z=30 (ray from centre outward +x) ==")
print(ray("P_Core",(0,1.7,30),(1,0,0)))
