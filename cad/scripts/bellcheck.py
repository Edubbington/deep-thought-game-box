import bpy, bmesh, collections, sys
from mathutils import Vector
f=sys.argv[-1]; TOP=float(sys.argv[-2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=f); o=bpy.context.selected_objects[0]
bm=bmesh.new(); bm.from_mesh(o.data)
for thr,label in ((-0.707,">45"),(-0.74,">47.7"),(-0.8,">53")):
    print(label,"deg overhang total:",round(sum(f.calc_area() for f in bm.faces if f.normal.z<thr and f.calc_center_median().z>0.3)))
cnt=collections.Counter()
for f in bm.faces:
    c=f.calc_center_median()
    if c.z<0.3 or f.normal.z>=-0.74: continue
    mz=TOP-c.z; my=-c.y; x=c.x
    cnt[(int(mz//10)*10, int(my//20)*20, int(x//20)*20)]+=f.calc_area()
print("overhang>47.7deg by (model z, y, x bands):")
for k,v in cnt.most_common(16): print(f"  z{k[0]:>3}..{k[0]+10:<3} y{k[1]:>4}..{k[1]+20:<4} x{k[2]:>4}..{k[2]+20:<4}: {v:.0f}")
