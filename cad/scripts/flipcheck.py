import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1_Head.stl")
o=bpy.context.selected_objects[0]
n=np.empty(len(o.data.polygons)*3); o.data.polygons.foreach_get("normal",n); n=n.reshape(-1,3)
a=np.empty(len(o.data.polygons)); o.data.polygons.foreach_get("area",a)
z=n[:,2]
# overhang: faces pointing down more than 50 deg from vertical => z < -cos(40deg)?? downward-facing normals with angle from -Z less than 40deg
ang=np.degrees(np.arccos(np.clip(-z,-1,1)))   # 0 = straight down
co=np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get("co",co); co=co.reshape(-1,3)
cz=np.array([co[list(p.vertices)][:,2].mean() for p in o.data.polygons])
mask=(ang<45)&(cz>1.0)
print("downward faces (overhang >45deg) area mm2: %.0f of total %.0f"%(a[mask].sum(),a.sum()))
for lo,hi in [(1,10),(10,30),(30,60),(60,100),(100,140),(140,170)]:
    m=mask&(cz>=lo)&(cz<hi); print("z %3d-%3d overhang area %.0f"%(lo,hi,a[m].sum()))
