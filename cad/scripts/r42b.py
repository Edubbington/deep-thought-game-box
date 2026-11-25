import sys, json, math; sys.path.insert(0,'/home/claude/build')
from lib import *
OUT="/home/claude/guide/"
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render=True
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True; sh.cavity_type='BOTH'; sh.cavity_ridge_factor=2.0; sh.cavity_valley_factor=2.0
sc.render.film_transparent=False; sc.world=bpy.data.worlds.new("w"); sc.world.color=(0.18,0.18,0.2)
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
C=bpy.data.objects["P_Core"]; P=bpy.data.objects["P_Chin42"]; H=bpy.data.objects["P_HeadBell"]
C.color=(0.8,0.72,0.5,1); P.color=(0.25,0.45,0.85,1); H.color=(0.75,0.75,0.78,1)
def place(objs, dirv, W, H_, zoom=1.0, center=None, scale=None):
    pts=[bpy.data.objects[n].matrix_world@Vector(c) for n in objs for c in bpy.data.objects[n].bound_box]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)])
    ctr=center if center is not None else (mn+mx)/2; d=Vector(dirv).normalized()
    co.location=ctr+d*900; co.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler(); cam.ortho_scale=scale if scale else (mx-mn).length*zoom
    sc.render.resolution_x=W; sc.render.resolution_y=H_; bpy.context.view_layer.update()
def shot(name, objs, dirv, W=1100,H_=850,zoom=1.0,center=None,scale=None):
    for o in bpy.data.objects: o.hide_render = o.name not in objs
    place(objs,dirv,W,H_,zoom,center,scale); sc.render.filepath=OUT+name+".png"; bpy.ops.render.render(write_still=True); print("shot",name)
def slab(o,name,ymin):
    c=dup(o,name); c.color=o.color; b=box(name+"_b",Vector((0,(ymin+300)/2,60)),(400,300-ymin,300)); boolean(c,b,'INTERSECT'); rm(b); return c
# capped section at the centre of the front strip (y=-71.4), seen from the front
for o,n in ((C,"core_s"),(P,"chin_s"),(H,"bell_s")): slab(o,n,-71.4)
shot("C42_sec_front_full",["core_s","chin_s","bell_s"],(0,-1,0),W=1600,H_=500,center=Vector((0,-71.4,100)),scale=165)
shot("C42_sec_front_zoom",["core_s","chin_s","bell_s"],(0,-1,0),W=1400,H_=700,center=Vector((-58,-71.4,100)),scale=40)
# capped section at the left strip (x=-67) seen from the left
def slabx(o,name,xmin):
    c=dup(o,name); c.color=o.color; b=box(name+"_b",Vector(((xmin+300)/2,0,60)),(300-xmin,400,300)); boolean(c,b,'INTERSECT'); rm(b); return c
for o,n in ((C,"core_sx"),(P,"chin_sx"),(H,"bell_sx")): slabx(o,n,-67.0)
shot("C42_sec_left_zoom",["core_sx","chin_sx","bell_sx"],(-1,0,0),W=1400,H_=700,center=Vector((-67,-50,100)),scale=40)
# underside, angled so the channels and pockets read
shot("C42_under_angled",["P_Chin42"],(0.35,-0.45,-1),zoom=1.0,W=1100,H_=850)
# cross-cut perpendicular to the front strip at x=10 (keep x>=10), seen from -x, zoom at the front edge
def slabx2(o,name,xmin):
    c=dup(o,name); c.color=o.color; b=box(name+"_b",Vector(((xmin+300)/2,0,60)),(300-xmin,400,300)); boolean(c,b,'INTERSECT'); rm(b); return c
for o,n in ((C,"core_x10"),(P,"chin_x10"),(H,"bell_x10")): slabx2(o,n,10.0)
shot("C42_sec_x10_zoom",["core_x10","chin_x10","bell_x10"],(-1,0,0),W=1400,H_=700,center=Vector((10,-66,101)),scale=30)
shot("C42_sec_x10_full",["core_x10","chin_x10","bell_x10"],(-1,0,0),W=1600,H_=500,center=Vector((10,-8,100)),scale=160)
shot("C42_top",["P_Chin42"],(0.25,-0.6,1),zoom=1.0,W=1100,H_=800)
pl=dup(P,"chin_lift2"); pl.color=P.color; pl.location.z+=22
shot("C42_expl2",["P_Core","chin_lift2"],(0.45,-1,0.55),zoom=0.62,center=Vector((5,-10,85)),W=1100,H_=850)
