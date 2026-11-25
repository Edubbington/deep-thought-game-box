import bpy, bmesh
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6.blend")
o=bpy.data.objects["P_HeadBell"]; bm=bmesh.new(); bm.from_mesh(o.data)
sel=[f for f in bm.faces if f.normal.z>0.74 and f.calc_center_median().z<238.7 and abs(f.calc_center_median().y+90)<8 and abs(f.calc_center_median().z-160)<12]
sel.sort(key=lambda f:-f.calc_area())
print("n",len(sel),"area",round(sum(f.calc_area() for f in sel)))
xs=[v.co.x for f in sel for v in f.verts]; ys=[v.co.y for f in sel for v in f.verts]; zs=[v.co.z for f in sel for v in f.verts]
print("extent x",round(min(xs),1),round(max(xs),1)," y",round(min(ys),1),round(max(ys),1)," z",round(min(zs),1),round(max(zs),1))
for f in sel[:3]: print([tuple(round(c,1) for c in v.co) for v in f.verts], [round(c,2) for c in f.normal])
