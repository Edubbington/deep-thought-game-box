import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils, bmesh
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5b.blend")
pl=bpy.data.objects["P_Plinth"]; src=bpy.data.objects["DT"]
pts=section_loop(src,10)
def ring(name,eo,ei,z0,z1):
    lo=prism(name,pts,-40,60); erode(lo,eo,0.5)
    li=prism(name+"i",pts,-40,60); erode(li,ei,0.5)
    boolean(lo,li,'DIFFERENCE'); rm(li)
    sl=box(name+"s",Vector((0,0,(z0+z1)/2)),(400,400,z1-z0)); boolean(lo,sl,'INTERSECT'); rm(sl); return lo
A=ring("rA",2.8,4.8,-5,21.5)     # goes 5 mm down into the riser; reaches up through the ceiling
B=ring("rB",2.3,4.8,1,21.5)      # above the riser: fused to the skirt
boolean(A,B,'UNION'); rm(B); boolean(pl,A,'UNION'); rm(A)
print("plate v3.2",stats(pl))
dg=bpy.context.evaluated_depsgraph_get()
def hits(name,origin,d,maxn=8):
    bvh=mathutils.bvhtree.BVHTree.FromObject(bpy.data.objects[name],dg); out=[]; p=Vector(origin)
    for _ in range(maxn):
        h=bvh.ray_cast(p,Vector(d),500)
        if h[0] is None: break
        out.append(round(h[0].y,1)); p=h[0]+Vector(d)*0.05
    return out
for z in [-4.5,-3,-1,0.5,2,10,19,21]:
    print(f"z={z:>4} plate:{hits('P_Plinth',(0,-200,z),(0,1,0))[:4]}  riser:{hits('P_Riser',(0,-200,z),(0,1,0))[:2]}")
# same probe at the right side (x direction) to be sure it's a full ring
for z in [-3,2]:
    print(f"z={z:>4} +x side plate:{[round(v,1) for v in []]}", end=""); 
    bvh=mathutils.bvhtree.BVHTree.FromObject(pl,dg); out=[]; p=Vector((200,-20,z))
    for _ in range(4):
        h=bvh.ray_cast(p,Vector((-1,0,0)),500)
        if h[0] is None: break
        out.append(round(h[0].x,1)); p=h[0]+Vector((-1,0,0))*0.05
    print(out)
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
c=place_on_bed(pl,True); export(c,"/home/claude/out/DeepThought_3_BasePlate_v3.2.stl")
print("exported",[round(x,1) for x in c.dimensions])
bm=bmesh.new(); bm.from_mesh(c.data)
down=[f for f in bm.faces if f.normal.z<-0.7 and f.calc_center_median().z>0.5]
print("overhang area (mm2):",round(sum(f.calc_area() for f in down),2))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s5c.blend")
