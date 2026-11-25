import bpy, bmesh, mathutils, math
import numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
for o in bpy.data.objects:
    if o.type=='MESH' and o.name.startswith("P_"):
        v=np.array([(o.matrix_world@w.co)[:] for w in o.data.vertices]); print(o.name,"min",v.min(0).round(1),"max",v.max(0).round(1))
