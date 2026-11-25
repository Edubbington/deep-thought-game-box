import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1_Head.stl")
o=bpy.context.selected_objects[0]
n=np.empty(len(o.data.polygons)*3); o.data.polygons.foreach_get("normal",n); n=n.reshape(-1,3)
a=np.empty(len(o.data.polygons)); o.data.polygons.foreach_get("area",a)
co=np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get("co",co); co=co.reshape(-1,3)
idx=np.array([list(p.vertices)[:3] for p in o.data.polygons]); cen=co[idx].mean(1)
ang=np.degrees(np.arccos(np.clip(-n[:,2],-1,1)))
m=(ang<45)&(cen[:,2]>1)
print("bbox",co.min(0).round(1),co.max(0).round(1))
# where are the overhangs in z 10-30 and 140-170? histogram by x,y region: distance from centre
for lo,hi in [(1,30),(140,170)]:
    mm=m&(cen[:,2]>=lo)&(cen[:,2]<hi)
    c=cen[mm]; w=a[mm]
    r=np.hypot(c[:,0]-c[:,0].mean()*0,c[:,1])
    print(lo,hi,"n",mm.sum(),"x range",c[:,0].min().round(1),c[:,0].max().round(1),"y range",c[:,1].min().round(1),c[:,1].max().round(1))
    # fraction near the outer edge (|x|>70 or |y|>65)
    edge=(np.abs(c[:,0])>65)|(np.abs(c[:,1])>60)
    print("   edge-area %.0f  interior-area %.0f"%(w[edge].sum(),w[~edge].sum()))
