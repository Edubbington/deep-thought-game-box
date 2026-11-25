import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render=True
def halfcopy(name,co,no,keep_neg=True):
    o=bpy.data.objects[name]; c=dup(o,name+"_half"); bm=bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=co,plane_no=no,clear_outer=keep_neg,clear_inner=not keep_neg)
    bm.to_mesh(c.data); bm.free(); c.hide_render=False; return c
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='SINGLE'; sh.single_color=(0.78,0.78,0.8); sh.show_cavity=True; sh.show_backface_culling=False
sc.render.resolution_x=800; sc.render.resolution_y=800; sc.world=bpy.data.worlds.new("w")
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
def shot(fn,dirv,objs,zoom=1.0):
    from mathutils import Vector
    for o in bpy.data.objects: o.hide_render = o.name not in objs
    pts=[bpy.data.objects[n].matrix_world@Vector(c) for n in objs for c in bpy.data.objects[n].bound_box]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)])
    ctr=(mn+mx)/2; d=Vector(dirv).normalized()
    co.location=ctr+d*600; co.rotation_euler=(-d).to_track_quat('-Z','Z').to_euler(); cam.ortho_scale=(mx-mn).length*zoom
    sc.render.filepath="/home/claude/out/"+fn; bpy.ops.render.render(write_still=True)
def _old(fn,loc,rot,scale,objs):
    for o in bpy.data.objects: o.hide_render = o.name not in objs
    co.location=loc; co.rotation_euler=[math.radians(a) for a in rot]; cam.ortho_scale=scale
    sc.render.filepath="/home/claude/out/"+fn; bpy.ops.render.render(write_still=True)
h1=halfcopy("P_Head",(-3,0,0),(1,0,0),keep_neg=False)   # keep x>-3 : look from -x into interior
for o in bpy.data.objects: o.hide_render = o.name!=h1.name
co.location=(-400,-10,178); co.rotation_euler=(math.radians(90),0,math.radians(-90)); cam.ortho_scale=190
sc.render.filepath="/home/claude/out/in_head_right.png"; bpy.ops.render.render(write_still=True)
h2=halfcopy("P_Head",(-3,0,0),(1,0,0),keep_neg=True)
for o in bpy.data.objects: o.hide_render = o.name!=h2.name
co.location=(400,-10,178); co.rotation_euler=(math.radians(90),0,math.radians(90)); cam.ortho_scale=190
sc.render.filepath="/home/claude/out/in_head_left.png"; bpy.ops.render.render(write_still=True)
shot("in_riser.png",(0,-0.6,1),["P_Riser"],0.85)
shot("in_core_top.png",(0.4,-0.5,1),["P_Core"],0.8)
p2=halfcopy("P_Plinth",(0,1.7,0),(1,0,0),keep_neg=True)
shot("in_plate_section.png",(0.3,-0.4,1),["P_Plinth"],0.75)
print("ok")
