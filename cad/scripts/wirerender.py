import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render=True
keep=[]
for n in ("P_Riser","P_Plinth","P_Core","P_Head"):
    o=bpy.data.objects[n]; c=dup(o,n+"_cut"); bm=bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,0),plane_no=(1,0,0),clear_outer=True)
    bm.to_mesh(c.data); bm.free(); c.hide_render=False; keep.append(c)
bpy.data.objects["P_Head_cut"].location.z=12
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='SINGLE'; sh.single_color=(0.78,0.78,0.8); sh.show_cavity=True
sc.render.resolution_x=700; sc.render.resolution_y=1000; sc.world=bpy.data.worlds.new("w")
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; cam.ortho_scale=330; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
co.location=(500,-20,110); co.rotation_euler=(math.radians(90),0,math.radians(90))
sc.render.filepath="/home/claude/out/wire_path.png"; bpy.ops.render.render(write_still=True); print("ok")
