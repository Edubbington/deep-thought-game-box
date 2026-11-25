import bpy, bmesh, mathutils, numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1a_HeadBell_v4.stl"); o=bpy.context.selected_objects[0]
v=np.array([w.co[:] for w in o.data.vertices]); mn,mx=v.min(0),v.max(0); print("bell STL bbox",mn.round(2),mx.round(2))
dg=bpy.context.evaluated_depsgraph_get(); t=mathutils.bvhtree.BVHTree.FromObject(o,dg)
# model -> stl: x' = x-cx ; y' = -(y-cy) ; z' = 239-z   (flat top on the bed)
M=bpy.data.objects["P_HeadBell"]; mv=np.array([w.co[:] for w in M.data.vertices]); mmn,mmx=mv.min(0),mv.max(0); cx=(mmn[0]+mmx[0])/2; cy=(mmn[1]+mmx[1])/2
def S(p): return Vector((p[0]-cx, -(p[1]-cy), 239-p[2]))
def span(p,d,m=120):
    P=S(p); D=Vector((d[0],-d[1],-d[2]))
    a=t.ray_cast(P,D,m); b=t.ray_cast(P,-D,m)
    return (None if b[0] is None else round(-(b[0]-P).length,2), None if a[0] is None else round((a[0]-P).length,2))
print("printed-STL slot, expressed in model coordinates:")
for y in (-40,-25,-12.7,5,20):
    for z in (150,160,170,180):
        sx=span((71,y,z),(1,0,0)); print(f"  y{y} z{z}: x {[None if q is None else round(71+q,2) for q in sx]}",end=" |")
    print()
for x in (64,68,71,75,79):
    sz=[span((x,y,165),(0,0,1)) for y in (-40,-12.7,20)]; print(f"  x{x}: z-span at y -40/-12.7/20:",[[None if q is None else round(165+q,2) for q in s] for s in sz])
for z in (145,152,160,170,180):
    sy=[span((x,-12.7,z),(0,1,0)) for x in (64,71,79)]; print(f"  z{z}: y-span at x 64/71/79:",[[None if q is None else round(-12.7+q,2) for q in s] for s in sy])
