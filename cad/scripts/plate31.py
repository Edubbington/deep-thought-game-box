import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
pl=bpy.data.objects["P_Plinth"]
# find the actual top z of the plate
top=max((pl.matrix_world@Vector(v)).z for v in pl.bound_box); print("plate top z",top)
# fill the annular LED seat: solid disc from below the groove floor up to the top surface, then re-open wire hole
fill=cyl("fill",Vector((0,1.7,(20.6+top)/2)),24.8,top-20.6,96); boolean(pl,fill,'UNION'); rm(fill)
wh=cyl("wh",Vector((0,1.7,19)),15,12,64); boolean(pl,wh,'DIFFERENCE'); rm(wh)
print("plate v3.1",stats(pl))
exec(open("/home/claude/build/step4.py").read().split("names={")[0].split("import os")[1].replace("; os.makedirs(\"/home/claude/out\",exist_ok=True)",""))
c=place_on_bed(pl,True); export(c,"/home/claude/out/DeepThought_3_BasePlate_v3.1.stl")
print("exported",[round(x,1) for x in c.dimensions])
# verify: probe the top face for any surface below top-0.3 inside r26 (i.e. recess gone)
import mathutils
bvh=mathutils.bvhtree.BVHTree.FromObject(pl,bpy.context.evaluated_depsgraph_get())
bad=0
for r in (16,18,20,22,24):
    for k in range(12):
        a=k*math.pi/6; p=Vector((r*math.cos(a),1.7+r*math.sin(a),top+5))
        hit=bvh.ray_cast(p,Vector((0,0,-1)),20)
        if hit[0] is None or hit[0].z<top-0.3: bad+=1
print("recess probes below top:",bad,"of 60")
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s5b.blend")
