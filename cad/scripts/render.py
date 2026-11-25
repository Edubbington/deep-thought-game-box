import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render = o.name not in ("P_Head","P_Core","P_Plinth","P_Riser")
mode=sys.argv[-1]
if mode=="exploded":
    bpy.data.objects["P_Head"].location.z=60; bpy.data.objects["P_Core"].location.z=30; bpy.data.objects["P_Riser"].location.z=-25
sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='SINGLE'
sc.display.shading.single_color=(0.75,0.75,0.78); sc.display.shading.show_cavity=True
sc.render.resolution_x=900; sc.render.resolution_y=900; sc.render.film_transparent=False
w=bpy.data.worlds.new("w"); sc.world=w
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; cam.ortho_scale=420; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
views={"front":((0,-600,120),(90,0,0)),"q":((420,-480,330),(65,0,41)),"back":((-380,450,300),(65,0,-140)),"under":((150,-300,-350),(145,0,25))}
for name,(loc,rot) in views.items():
    co.location=loc; co.rotation_euler=[math.radians(a) for a in rot]
    sc.render.filepath="/home/claude/out/prev_%s_%s.png"%(mode,name); bpy.ops.render.render(write_still=True)
print("done")
