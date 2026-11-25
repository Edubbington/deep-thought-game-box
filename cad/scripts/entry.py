import bpy, bmesh, mathutils, numpy as np, pickle
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1a_HeadBell_v4.stl"); o=bpy.context.selected_objects[0]
dg=bpy.context.evaluated_depsgraph_get(); t=mathutils.bvhtree.BVHTree.FromObject(o,dg)
M=bpy.data.objects["P_HeadBell"]; mv=np.array([w.co[:] for w in M.data.vertices]); cx=(mv[:,0].min()+mv[:,0].max())/2; cy=(mv[:,1].min()+mv[:,1].max())/2
# solid mask in model x-z, union over y in the slot's length. Rays go UP in model z = DOWN in stl z.
xs=np.arange(20,90.01,0.25); zs=np.arange(98,186.01,0.25); ys=[-45.5,-40,-33,-25,-17,-10,-3,5,12,19,25.5]
mask=np.zeros((len(xs),len(zs)),bool)
for y in ys:
    for i,x in enumerate(xs):
        P=Vector((x-cx,-(y-cy),239-97.0)); D=Vector((0,0,-1)); hits=[]; p=P.copy()
        for _ in range(40):
            h=t.ray_cast(p,D,100)
            if h[0] is None: break
            hits.append(239-h[0].z); p=h[0]+D*0.005
        # model z=97 is below the bell bottom (100.5) -> outside. parity intervals
        for a,b in zip(hits[0::2],hits[1::2]):
            ia=np.searchsorted(zs,a); ib=np.searchsorted(zs,b); mask[i,ia:ib]=True
pickle.dump((xs,zs,mask),open("/home/claude/build/entry.pkl","wb"))
# print coarse picture: rows z from 184 down to 100 step 2, cols x 40..88 step 1
for z in np.arange(184,99,-2.0):
    j=np.searchsorted(zs,z); print(f"{z:5.0f} "+"".join("#" if mask[np.searchsorted(xs,x),j] else "." for x in np.arange(40,88.1,1.0)))
print("      "+"".join(str(int(x)//10%10) if int(x)%10==0 else " " for x in np.arange(40,88.1,1.0)))
