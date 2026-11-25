import bpy, mathutils, numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1a_HeadBell_v4.stl"); o=bpy.context.selected_objects[0]
dg=bpy.context.evaluated_depsgraph_get(); t=mathutils.bvhtree.BVHTree.FromObject(o,dg)
M=bpy.data.objects["P_HeadBell"]; mv=np.array([w.co[:] for w in M.data.vertices]); cx=(mv[:,0].min()+mv[:,0].max())/2; cy=(mv[:,1].min()+mv[:,1].max())/2
def thru(y,z):
    h=t.ray_cast(Vector((110-cx,-(y-cy),239-z)),Vector((-1,0,0)),45); return None if h[0] is None else round(h[0].x+cx,2)
for yc,zc in ((-32.0,165.0),(12.0,165.0)):
    op=[(yc+a*0.1,zc+b*0.1) for a in range(-25,26) for b in range(-25,26) if (lambda v:(v is None or v<66))(thru(yc+a*0.1,zc+b*0.1))]
    ys=[p[0] for p in op]; zs=[p[1] for p in op]
    print("printed-STL grille hole: centre y %.2f z %.2f dia %.1f | outer surface x beside it: %s"%((min(ys)+max(ys))/2,(min(zs)+max(zs))/2,max(ys)-min(ys)+0.1,[thru(yc+2.75,zc+1.0),thru(yc-2.75,zc-1.0)]))
