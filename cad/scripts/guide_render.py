import sys, json, math; sys.path.insert(0,'/home/claude/build')
from lib import *
import numpy as np
OUT="/home/claude/guide/"
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s5.blend")
sc=bpy.context.scene
for o in bpy.data.objects: o.hide_render=True
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True; sh.cavity_type='BOTH'
sc.render.film_transparent=False; sc.world=bpy.data.worlds.new("w"); sc.world.color=(0.18,0.18,0.2)
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
PARTS=("P_Riser","P_Plinth","P_Core","P_Head")
COL={"P_Riser":(0.55,0.6,0.7,1),"P_Plinth":(0.6,0.7,0.6,1),"P_Core":(0.8,0.72,0.5,1),"P_Head":(0.75,0.75,0.78,1)}
for n in PARTS: bpy.data.objects[n].color=COL[n]
def mkbed():
    bpy.ops.mesh.primitive_plane_add(size=220,location=(0,0,-0.3)); b=bpy.context.active_object; b.name="bed"; b.color=(0.25,0.27,0.32,1); b.hide_render=True; return b
bed=mkbed()
def place(objs, dirv, W=1100, H=850, zoom=1.0, up=(0,0,1), center=None):
    pts=[bpy.data.objects[n].matrix_world@Vector(c) for n in objs for c in bpy.data.objects[n].bound_box]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)])
    ctr=center if center is not None else (mn+mx)/2; d=Vector(dirv).normalized()
    co.location=ctr+d*900; q=(-d).to_track_quat('-Z','Y')
    co.rotation_euler=q.to_euler(); cam.ortho_scale=(mx-mn).length*zoom
    sc.render.resolution_x=W; sc.render.resolution_y=H
    bpy.context.view_layer.update()
def proj(p):
    W,H=sc.render.resolution_x,sc.render.resolution_y; S=cam.ortho_scale
    v=co.matrix_world.inverted()@Vector(p); k=W/S if W>=H else H/S
    return (W/2+v.x*k, H/2-v.y*k)
def shot(name, objs, dirv, labels=None, W=1100,H=850,zoom=1.0,hide_others=True,center=None,extra=()):
    for o in bpy.data.objects: o.hide_render = o.name not in list(objs)+list(extra)
    place(objs,dirv,W,H,zoom,center=center)
    sc.render.filepath=OUT+name+".png"; bpy.ops.render.render(write_still=True)
    L=[(t,proj(p)) for t,p in (labels or [])]
    json.dump({"labels":L,"W":W,"H":H},open(OUT+name+".json","w"))
    print("shot",name)
def half(n,co_,no,keep_pos=True):
    o=bpy.data.objects[n]; c=dup(o,n+"_half"); c.color=o.color; bm=bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=co_,plane_no=no,clear_outer=not keep_pos,clear_inner=keep_pos)
    bm.to_mesh(c.data); bm.free(); c.hide_render=True; return c.name
# ---------- 1. print bed, each part as exported
import importlib
def load_stl(path,name):
    bpy.ops.wm.stl_import(filepath=path); o=bpy.context.selected_objects[0]; o.name=name; o.hide_render=True; o.color=(0.8,0.5,0.3,1); return o
stls={"Riser":"DeepThought_4_Riser.stl","BasePlate":"DeepThought_3_BasePlate.stl","Core":"DeepThought_2_Core_legs_dome.stl","Head":"DeepThought_1_Head.stl"}
for k,f in stls.items():
    o=load_stl("/home/claude/out/"+f,"STL_"+k)
    shot("bed_"+k,[o.name],(0.7,-1,0.9),W=700,H=600,zoom=1.6,extra=["bed"],center=Vector((0,0,o.dimensions.z/2)))
    rm(o)
# ---------- 2. exploded, labeled
H_=bpy.data.objects["P_Head"]; C_=bpy.data.objects["P_Core"]; P_=bpy.data.objects["P_Plinth"]; R_=bpy.data.objects["P_Riser"]
H_.location.z=80; C_.location.z=40; R_.location.z=-35
shot("exploded",PARTS,(0.8,-1,0.4),labels=[("1  Head  (screen, speaker, amp)",(0,-75,80+176)),("2  Core  (legs, glowing dome, neck)",(60,-50,40+50)),("3  Base plate  (button, LED ring)",(0,-79,12)),("4  Riser  (Pi, power jack, ballast)",(0,-65,-35-20))],zoom=1.1)
H_.location.z=0; C_.location.z=0; R_.location.z=0
# ---------- 3. riser
shot("riser",["P_Riser"],(0.35,-0.9,0.75),labels=[("Power-jack slot (back wall)",(0,54,-20)),("Ballast tray",(-50,26,-30)),("Ballast tray",(50,26,-30)),("Zip-tie anchor",(-30,-20,-36)),("Zip-tie anchor",(30,-20,-36)),("Locating lip (fits inside base plate)",(-70,-60,2))],zoom=0.85)
shot("riser_back",["P_Riser"],(0.2,1,0.35),labels=[("Power-jack slot 14 x 9 mm: drill two 3 mm holes beside it for the jack's ears",(0,56,-20))],zoom=0.9)
# ---------- 4. plate
shot("plate_top",["P_Plinth"],(0.15,-0.5,1),labels=[("Button hole, 28 mm (front)",(0,-79,23)),("LED-ring seat, 49 mm recess",(24,1.7,23)),("Wire hole, 30 mm",(0,1.7,21))],zoom=0.8)
pb=half("P_Plinth",(0,0,0),(1,0,0),keep_pos=False)
shot("plate_under",[pb],(-0.5,-0.7,-0.8),labels=[("Hollow underside; riser lip fits in here",(-40,-40,0)),("Button hole",(0,-79,2))],zoom=0.85)
# ---------- 5. core
shot("core",["P_Core"],(0.6,-1,0.6),labels=[("Magnet pocket (3)",(-55.8,-68.1,96)),("Magnet pocket",(56.7,-70.2,96)),("Magnet pocket",(-62.1,48.6,96)),("Locating lip",(0,-75,98)),("Neck channel exit, 14 mm",(0,12,96)),("Glowing dome (hollow)",(45,-20,45))],zoom=0.9)
cb=half("P_Core",(0,0,0),(1,0,0),keep_pos=True)
shot("core_cut",[cb],(-1,-0.3,0.25),labels=[("Neck channel",(0,12,75)),("Dome cavity",(0,1.7,45)),("Open bottom over the plate's wire hole",(0,1.7,24))],zoom=0.9)
# ---------- 6. head
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
Cc=Vector((-3.0,a+b_*-3.0+c*176.0,176.0))
shot("head_front",["P_Head"],(0.25,-1,0.15),labels=[("Screen window 110 x 66 mm",Cc),("Display pocket rim screw hole",Cc+64.25*X+30*U),("Display pocket rim screw hole",Cc-64.25*X-30*U),("Speaker grille (right side)",(83,-10,165)),("Open bottom; sits on the core",(-30,-70,97))],zoom=0.9)
shot("head_back",["P_Head"],(-0.6,1,0.35),labels=[("Vent slots",(-3,67,225)),("Crown magnet pockets on the flat top (3)",(0,20,250))],zoom=0.9)
hr=half("P_Head",(-3,0,0),(1,0,0),keep_pos=True)   # keep x>-3, view from -x
shot("head_in_right",[hr],(-1,-0.05,0.08),labels=[("Speaker cradle 72 x 33 mm",(70,-10,165)),("Zip-tie slot",(72,-10,184.6)),("Zip-tie slot",(72,-10,145.4)),("Wiring pad (amp on foam tape)",(29,60,160)),("Zip-tie anchor",(29,57,140)),("Display pocket (from inside)",(40,-55,176)),("Magnet boss",(56.7,-70.2,100))],zoom=0.85)
hl=half("P_Head",(-3,0,0),(1,0,0),keep_pos=False)
shot("head_in_left",[hl],(1,0.05,0.08),labels=[("Display pocket, 8 mm deep",(-40,-55,176)),("Rim screw hole",Cc-64.25*X+30*U),("Wiring pad",(-35,60,160)),("Magnet boss",(-55.8,-68.1,100)),("Magnet boss",(-62.1,48.6,100))],zoom=0.85)
# ---------- 7. assembled
shot("assembled",PARTS,(0.8,-1,0.3),zoom=1.0)
print("done")
