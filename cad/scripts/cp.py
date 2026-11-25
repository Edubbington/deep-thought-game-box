import bpy, bmesh, mathutils, math, collections
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
print([ (o.name,[round(v,1) for v in o.dimensions]) for o in bpy.data.objects if o.type=='MESH'])
import numpy as np
def bb(o):
    v=np.array([(o.matrix_world@w.co)[:] for w in o.data.vertices]); return v.min(0).round(2),v.max(0).round(2)
for n in ("P_Core","P_Plinth","P_Riser"):
    if n in bpy.data.objects: print(n,bb(bpy.data.objects[n]))
C=bpy.data.objects["P_Core"]
bm=bmesh.new(); bm.from_mesh(C.data)
# core bottom faces: down-facing clusters by z
h=collections.Counter()
for f in bm.faces:
    if f.normal.z<-0.9: h[round(f.calc_center_median().z,1)]+=f.calc_area()
print("core down-facing area by z:",{k:round(v) for k,v in sorted(h.items()) if v>15})
# leg feet: faces at lowest z, cluster xy
zmin=min(v.co.z for v in bm.verts)
feet=[f.calc_center_median() for f in bm.faces if f.normal.z<-0.9 and f.calc_center_median().z<zmin+0.3]
cl=collections.defaultdict(list)
for c in feet: cl[(round(c.x/25),round(c.y/25))].append(c)
for k,v in cl.items():
    xs=[c.x for c in v]; ys=[c.y for c in v]; print(" foot cluster centre",round(sum(xs)/len(xs),1),round(sum(ys)/len(ys),1),"extent",round(max(xs)-min(xs),1),round(max(ys)-min(ys),1),"n",len(v))
