import bpy, bmesh, collections, sys
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=sys.argv[-1]); o=bpy.context.selected_objects[0]
bm=bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm,faces=bm.faces[:])
xs=[v.co.x for v in bm.verts]; ys=[v.co.y for v in bm.verts]; zs=[v.co.z for v in bm.verts]
print("print bbox x",round(min(xs),1),round(max(xs),1),"y",round(min(ys),1),round(max(ys),1),"z",round(min(zs),1),round(max(zs),1))
tot=0; c=collections.Counter()
for f in bm.faces:
    m=f.calc_center_median()
    if m.z<0.3 or f.normal.z>=-0.74: continue
    a=f.calc_area(); tot+=a
    c[(round(m.x/10)*10,round(m.y/10)*10,round(m.z/5)*5,round(f.normal.z,1))]+=a
print("overhang >47.7deg total",round(tot))
for k,v in c.most_common(24): print(" print(x,y,z,nz)",k,round(v))
