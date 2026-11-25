import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils, bmesh, random
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
H=bpy.data.objects["P_HeadBell"]; dg=bpy.context.evaluated_depsgraph_get(); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def span(p,d,maxd=150):
    a=hb.ray_cast(Vector(p),Vector(d),maxd); b=hb.ray_cast(Vector(p),-Vector(d),maxd)
    return (round((b[0]-Vector(p)).dot(Vector(d)),2) if b[0] else None, round((a[0]-Vector(p)).dot(Vector(d)),2) if a[0] else None)
c=(71,-10,165)
print("MEASURED slot from the bell mesh, about point",c)
print(" x (depth):",[c[0]+v if v is not None else None for v in span(c,(1,0,0))])
print(" y (length):",[c[1]+v if v is not None else None for v in span(c,(0,1,0))])
print(" z (height):",[c[2]+v if v is not None else None for v in span(c,(0,0,1))])
for yy in (-44,-30,-10,10,24):
    for xx in (64,71,78): 
        s=span((xx,yy,165),(0,0,1)); print("  z-span at x",xx,"y",yy,":",[165+v if v is not None else None for v in s], end=";")
    print()
print(" zip slot through end wall? ray along y at (70,*,148):",[c[1]+v if v is not None else None for v in span((70,-10,148),(0,1,0))], " at z=155:",[c[1]+v if v is not None else None for v in span((70,-10,155),(0,1,0))])
print("x-span (inner wall .. outer wall) at y=-40 and y=20 for z:")
for z in (140,142,144,146,148,150,152,160,170,180,181.5):
    print("  z",z,[ [71+v if v is not None else None for v in span((71,yy,z),(1,0,0))] for yy in (-40,-10+2.75,20)])
