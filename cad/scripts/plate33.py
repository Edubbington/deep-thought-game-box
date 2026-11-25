import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils, bmesh, collections
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5c.blend")
pl=bpy.data.objects["P_Plinth"]
ZCUT=22.72
k=box("keep",Vector((0,0,(ZCUT-40)/2)),(500,500,ZCUT+40)); boolean(pl,k,'INTERSECT'); rm(k)
print("v3.3",stats(pl))
dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(pl,dg)
zs=[]
for x in range(-90,91,5):
    for y in range(-105,55,5):
        h=bvh.ray_cast(Vector((x,y,60)),Vector((0,0,-1)),100)
        if h[0] is not None and h[0].z>15: zs.append(round(h[0].z,3))
print("top z values:",sorted(collections.Counter(zs).items()))
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
c=place_on_bed(pl,True); export(c,"/home/claude/out/DeepThought_3_BasePlate_v3.3.stl")
bm=bmesh.new(); bm.from_mesh(c.data)
bed=[f for f in bm.faces if f.normal.z<-0.9 and f.calc_center_median().z<0.05]
hover=[f for f in bm.faces if f.normal.z<-0.7 and 0.05<=f.calc_center_median().z<1.0]
print("exported",[round(x,1) for x in c.dimensions],"bed-contact area mm2:",round(sum(f.calc_area() for f in bed)),"hovering-downward area:",round(sum(f.calc_area() for f in hover),2))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s5d.blend")
