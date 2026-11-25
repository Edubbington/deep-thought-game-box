import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
from shapely.geometry import Polygon, LineString
import collections
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5d.blend")
DT=bpy.data.objects["DT"]; hs=dup(DT,"hs"); bb=box("s",Vector((0,0,198)),(400,400,204)); boolean(hs,bb,'INTERSECT'); rm(bb)
Z0=227.0; pts=section_loop(hs,Z0); print("outline pts",len(pts))
ring=Polygon(pts).buffer(0); print("ring area",round(ring.area),ring.geom_type, "bounds",[round(v,1) for v in ring.bounds])
for k in (0,2,5,10,14.5):
    p=ring.buffer(-k,join_style=1)
    print(k, p.geom_type, round(p.area), [round(v,1) for v in p.bounds])
# how does the exterior compare: exterior top profile at several angles between r 60..100
import mathutils, math
dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(hs,dg)
print("exterior height vs r (from (0,-10)) at 270deg (front) and 240/300deg:")
for a in (240,270,300):
    row=[]
    for r in range(60,101,5):
        x,y=r*math.cos(math.radians(a)),-10+r*math.sin(math.radians(a))
        h=bvh.ray_cast(Vector((x,y,300)),Vector((0,0,-1)),120); row.append(f"{r}:{h[0].z:.0f}" if h[0] else f"{r}:--")
    print(a,row)
