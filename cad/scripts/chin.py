import bpy, mathutils, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5d.blend")
H=bpy.data.objects["P_Head"]; dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(H,dg)
cen=Vector((0,-10,0))
print("inner / outer radius (mm) from (0,-10) vs model z, per direction")
print("z    "+"  ".join(f"{a:>3}deg(in/out)" for a in (0,45,90,135,180,225,270,315)))
for z in (96.5,98,100,102,104,106,108,110,114,118,122,126,130,140):
    row=[]
    for a in (0,45,90,135,180,225,270,315):
        d=Vector((math.cos(math.radians(a)),math.sin(math.radians(a)),0))
        p=cen+Vector((0,0,z)); hs=[]
        for _ in range(4):
            h=bvh.ray_cast(p,d,200)
            if h[0] is None: break
            hs.append((h[0]-cen-Vector((0,0,z))).length); p=h[0]+d*0.02
        row.append(f"{hs[0]:5.1f}/{hs[1]:5.1f}" if len(hs)>=2 else ("  --  /"+(f"{hs[0]:5.1f}" if hs else " -- ")))
    print(f"{z:5.1f} "+"  ".join(row))
# core top outer radius for comparison
C=bpy.data.objects["P_Core"]; cb=mathutils.bvhtree.BVHTree.FromObject(C,dg)
print("core outer radius at z=95 / z=100 per direction:")
for z in (95,100):
    row=[]
    for a in (0,45,90,135,180,225,270,315):
        d=Vector((math.cos(math.radians(a)),math.sin(math.radians(a)),0)); p=Vector((0,1.7,z)); hs=[]
        for _ in range(3):
            h=cb.ray_cast(p,d,200)
            if h[0] is None: break
            hs.append((h[0]-Vector((0,1.7,z))).length); p=h[0]+d*0.02
        row.append(f"{hs[-1]:5.1f}" if hs else " -- ")
    print(z,row)
