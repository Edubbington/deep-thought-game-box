import bpy, bmesh, collections
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
o=bpy.data.objects["P_HeadBell"]; bm=bmesh.new(); bm.from_mesh(o.data)
sel=[f for f in bm.faces if f.normal.z>0.74 and f.calc_center_median().z<238.7]
print("print-overhang faces (>47.7deg):",len(sel),"area",round(sum(f.calc_area() for f in sel)))
c=collections.Counter()
for f in sel:
    m=f.calc_center_median(); n=f.normal; c[(round(m.x/10)*10,round(m.y/10)*10,round(m.z/5)*5,round(n.z,1))]+=f.calc_area()
for k,v in c.most_common(22): print(k,round(v))
