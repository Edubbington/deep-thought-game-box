import bpy, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
H=bpy.data.objects["P_HeadBell"]; dg=bpy.context.evaluated_depsgraph_get(); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def hit(p,d,m=60):
    h=hb.ray_cast(Vector(p),Vector(d),m); return (h[0]-Vector(p)).dot(Vector(d)) if h[0] else None
bad=0; n=0; mn={"x-":9,"x+":9,"y-":9,"y+":9,"z+":9}
import itertools
ys=[-45.9+i*1.0 for i in range(72)]; zs=[150.3+i*1.0 for i in range(32)]; xs=[62.9+i*0.8 for i in range(22)]
for y in ys:
    for z in zs:
        n+=1; a=hit((71,y,z),(-1,0,0)); b=hit((71,y,z),(1,0,0))
        ga=(71-62.8)-(a if a is not None else 99); gb=(b if b is not None else 99)-(79.7-71)
        # ga<0 would mean wall nearer than the basket's inner face... compute clearances
        ca=(a if a is not None else 99)-(71-62.8); cb=(b if b is not None else 99)-(79.7-71)
        mn["x-"]=min(mn["x-"],ca); mn["x+"]=min(mn["x+"],cb); bad+= ca<0 or cb<0
for x in xs:
    for z in zs:
        n+=1; a=hit((x,-10,z),(0,-1,0)); b=hit((x,-10,z),(0,1,0))
        ca=(a if a is not None else 99)-(45.9-10); cb=(b if b is not None else 99)-(25.9+10)
        mn["y-"]=min(mn["y-"],ca); mn["y+"]=min(mn["y+"],cb); bad+= ca<0 or cb<0
    for y in ys:
        n+=1; b=hit((x,y,165),(0,0,1)); cb=(b if b is not None else 99)-(181.45-165); mn["z+"]=min(mn["z+"],cb); bad+= cb<0
print("axis probes",n,"violations",bad,"min clearance each side:",{k:round(v,2) for k,v in mn.items()})
