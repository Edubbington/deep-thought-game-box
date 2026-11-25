import sys, json, math; sys.path.insert(0,'/home/claude/build')
from lib import *
OUT="/home/claude/guide/"
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render=True
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True; sh.cavity_type='BOTH'
sc.render.film_transparent=False; sc.world=bpy.data.worlds.new("w"); sc.world.color=(0.18,0.18,0.2)
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
C=bpy.data.objects["P_Core"]; P=bpy.data.objects["P_Chin42"]; H=bpy.data.objects["P_HeadBell"]; V4=bpy.data.objects["P_Chin_v4"]
C.color=(0.8,0.72,0.5,1); P.color=(0.25,0.45,0.85,1); H.color=(0.75,0.75,0.78,1); V4.color=(0.25,0.45,0.85,1)
def place(objs, dirv, W, H_, zoom=1.0, center=None):
    pts=[bpy.data.objects[n].matrix_world@Vector(c) for n in objs for c in bpy.data.objects[n].bound_box]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)])
    ctr=center if center is not None else (mn+mx)/2; d=Vector(dirv).normalized()
    co.location=ctr+d*900; co.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler(); cam.ortho_scale=(mx-mn).length*zoom
    sc.render.resolution_x=W; sc.render.resolution_y=H_; bpy.context.view_layer.update()
def shot(name, objs, dirv, W=1100,H_=850,zoom=1.0,center=None):
    for o in bpy.data.objects: o.hide_render = o.name not in objs
    place(objs,dirv,W,H_,zoom,center); sc.render.filepath=OUT+name+".png"; bpy.ops.render.render(write_still=True); print("shot",name)
def half(o,name,co_,no,keep_pos=True):
    c=dup(o,name); c.color=o.color; bm=bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=co_,plane_no=no,clear_outer=not keep_pos,clear_inner=keep_pos)
    bm.to_mesh(c.data); bm.free(); return c
# 1. underside of v4 (printed) vs v4.2
shot("C42_under_v4",["P_Chin_v4"],(0,0,-1),zoom=1.05)
shot("C42_under_v42",["P_Chin42"],(0,0,-1),zoom=1.05)
# 2. section through the front strip (y=-71.5) with the core seated: chin + core top, cut plane facing the viewer
cc=half(C,"core_cut",(0,-71.5,0),(0,-1,0),keep_pos=False)   # keep y>-71.5 ... we want to look from the front at the cut face: remove y<-71.5
pc=half(P,"chin_cut",(0,-71.5,0),(0,-1,0),keep_pos=False); hc=half(H,"bell_cut",(0,-71.5,0),(0,-1,0),keep_pos=False)
shot("C42_section_front",["core_cut","chin_cut","bell_cut"],(0,-1,0.0),zoom=0.35,center=Vector((-20,-71.5,99)),W=1400,H_=700)
# 3. section through the left strip at x=-67 looking from the left
cc2=half(C,"core_cut2",(-67,0,0),(-1,0,0),keep_pos=False); pc2=half(P,"chin_cut2",(-67,0,0),(-1,0,0),keep_pos=False); hc2=half(H,"bell_cut2",(-67,0,0),(-1,0,0),keep_pos=False)
shot("C42_section_left",["core_cut2","chin_cut2","bell_cut2"],(-1,0,0),zoom=0.35,center=Vector((-67,-10,99)),W=1400,H_=700)
# 4. front view of chin v4.2 alone (the mouth) and v4 for comparison
shot("C42_front_v42",["P_Chin42"],(0,-1,0.15),zoom=1.05,W=1100,H_=400)
shot("C42_front_v4",["P_Chin_v4"],(0,-1,0.15),zoom=1.05,W=1100,H_=400)
# 5. exploded: core + chin lifted 15 mm, from below-front angle
pl=dup(P,"chin_lift"); pl.color=P.color; pl.location.z+=14
shot("C42_exploded",["P_Core","chin_lift"],(0.6,-1,0.35),zoom=0.7,center=Vector((0,-10,90)))
