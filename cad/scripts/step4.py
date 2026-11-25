import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
import os; os.makedirs("/home/claude/out",exist_ok=True)
def place_on_bed(o,flip=False):
    c=dup(o,o.name+"_print")
    if flip:
        c.rotation_euler=(math.radians(180),0,0); sel(c); bpy.ops.object.transform_apply(rotation=True)
    bb=[c.matrix_world@Vector(v) for v in c.bound_box]
    mn=Vector([min(v[i] for v in bb) for i in range(3)]); mx=Vector([max(v[i] for v in bb) for i in range(3)])
    c.location-=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z)); sel(c); bpy.ops.object.transform_apply(location=True)
    return c
names={"P_Head":("DeepThought_1_Head.stl",True),"P_Core":("DeepThought_2_Core_legs_dome.stl",False),
       "P_Plinth":("DeepThought_3_BasePlate.stl",True),"P_Riser":("DeepThought_4_Riser.stl",False)}
for n,(fn,flip) in names.items():
    c=place_on_bed(bpy.data.objects[n],flip)
    export(c,"/home/claude/out/"+fn)
    print(fn,[round(x,1) for x in c.dimensions],"fits 220x220x240:",c.dimensions.x<=220 and c.dimensions.y<=220 and c.dimensions.z<=240)
    rm(c)
