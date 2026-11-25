import sys; sys.path.insert(0,'/home/claude/build')
exec(open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0])
def load_stl(path,name):
    bpy.ops.wm.stl_import(filepath=path); o=bpy.context.selected_objects[0]; o.name=name; o.hide_render=True; o.color=(0.8,0.5,0.3,1); return o
o=load_stl("/home/claude/out/DeepThought_3_BasePlate_v3.2.stl","STL_P32")
shot("bed_BasePlate_v32",[o.name],(0.7,-1,0.9),W=900,H=700,zoom=1.5,extra=["bed"],center=Vector((0,0,o.dimensions.z/2)),labels=[("Locating ring: drops 5 mm inside the riser wall",(0,-105.5,27)),("Flat top (on the bed) - no recess",(60,-60,0.5))])
