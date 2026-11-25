import bpy, mathutils
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
H=bpy.data.objects["P_HeadBell"]; dg=bpy.context.evaluated_depsgraph_get(); hb=mathutils.bvhtree.BVHTree.FromObject(H,dg)
def thru(y,z):
    h=hb.ray_cast(Vector((110,y,z)),Vector((-1,0,0)),45)   # from outside toward the slot; stops at x=65
    return None if h[0] is None else round(h[0].x,2)
for yc in (-37.5,17.5):
    open_=[(round(yc+dy*0.1,1),round(165+dz*0.1,1)) for dy in range(-25,26) for dz in range(-25,26) if thru(yc+dy*0.1,165+dz*0.1) is None or thru(yc+dy*0.1,165+dz*0.1)<66]
    ys=[p[0] for p in open_]; zs=[p[1] for p in open_]
    print("hole near y",yc,": centre",round((min(ys)+max(ys))/2,2),round((min(zs)+max(zs))/2,2),"dia",round(max(ys)-min(ys)+0.1,2),round(max(zs)-min(zs)+0.1,2))
    print("   outer wall surface x beside it:",thru(yc+2.75,165+2.4),thru(yc-2.75,165-2.4)," inner face x=80")
