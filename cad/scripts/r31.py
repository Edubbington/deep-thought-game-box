import sys; sys.path.insert(0,'/home/claude/build')
exec(open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0])
def load_stl(path,name):
    bpy.ops.wm.stl_import(filepath=path); o=bpy.context.selected_objects[0]; o.name=name; o.hide_render=True; o.color=(0.8,0.5,0.3,1); return o
o=load_stl("/home/claude/out/DeepThought_3_BasePlate_v3.1.stl","STL_P31")
shot("bed_BasePlate_v31",[o.name],(0.7,-1,0.9),W=900,H=700,zoom=1.5,extra=["bed"],center=Vector((0,0,o.dimensions.z/2)))
# bottom (bed-facing) face check: lowest z faces
import bmesh
bm=bmesh.new(); bm.from_mesh(o.data)
zs=[v.co.z for v in bm.verts]; print("z range",min(zs),max(zs))
down=[f for f in bm.faces if f.normal.z<-0.7 and f.calc_center_median().z>0.5]
print("downward faces above bed (overhangs):",len(down), "area", sum(f.calc_area() for f in down))
