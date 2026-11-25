import sys; sys.path.insert(0,'/home/claude/build')
src=open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0].replace('s5.blend','s6.blend').replace('"P_Head")','"P_HeadBell")').replace('"P_Head":(0.75','"P_HeadBell":(0.75')
exec(src)
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
Cc=Vector((-3.0,a+b_*-3.0+c*176.0,176.0))
def load_stl(path,name,col):
    bpy.ops.wm.stl_import(filepath=path); o=bpy.context.selected_objects[0]; o.name=name; o.hide_render=True; o.color=col; return o
hb=load_stl("/home/claude/out/DeepThought_1a_HeadBell_v4.stl","STL_Bell",(0.75,0.75,0.78,1))
shot("bed_HeadBell_v4",[hb.name],(0.7,-1,0.6),W=900,H=700,zoom=1.2,extra=["bed"],center=Vector((0,0,hb.dimensions.z/2)),labels=[("Flat top on the bed; no supports",(0,0,0.5)),("Open bottom faces up",(0,0,138))])
hc=load_stl("/home/claude/out/DeepThought_1b_HeadChin_v4.stl","STL_Chin",(0.6,0.7,0.6,1))
shot("bed_HeadChin_v4",[hc.name],(0.7,-1,0.9),W=900,H=700,zoom=1.5,extra=["bed"],center=Vector((0,0,6)),labels=[("Lip stands up; 0.4 mm clearance to the bell",(0,-70,12)),("Tapered neck opening: 'touching build plate' supports",(0,0,1))])
for o in (hb,hc): bpy.data.objects.remove(o)
P=bpy.data.objects["P_Chin"]; B=bpy.data.objects["P_HeadBell"]
shot("head_front_v4",["P_HeadBell"],(0.25,-1,0.15),labels=[("Screen window 110 x 66 mm",Cc),("Sill bevel under the window",Cc-38*U-2*D),("Display rim screw hole (4)",Cc+64.25*X+30*U),("Speaker grille (right side)",(83,-10,165)),("Open bottom: display and Pi go in here",(-30,-70,101)),("45 deg top bevel",(-60,-90,236))],zoom=0.9)
shot("head_back_v4",["P_HeadBell"],(-0.6,1,0.35),labels=[("Vent slots",(-3,67,225)),("Crown magnet pockets (3) on the flat top",(0,20,239)),("Chin-plate screw pilot, back",(0,66,104.5))],zoom=0.9)
hr=half("P_HeadBell",(-3,0,0),(1,0,0),keep_pos=True)
shot("head_in_right_v4",[hr],(-1,-0.35,0.25),labels=[("Speaker slot: speaker pushes up from below",(71,-10,165)),("Zip-tie slot through the side wall",(70,-48,148)),("45 deg roof over the slot",(72,-10,196)),("Wiring pad (amp sticks here)",(20,60,160)),("Zip-tie tunnel",(29,58.7,140)),("Display pocket rim screw hole",Cc+64.25*X-30*U+14*D),("Chamfered pocket floor",Cc+10*D-45*U)],zoom=1.0)
hl=half("P_HeadBell",(-3,0,0),(1,0,0),keep_pos=False)
shot("head_in_left_v4",[hl],(1,-0.35,0.25),labels=[("Display pocket: 8 mm lip, display pushes in from behind",Cc-50*X+10*D),("Rim screw hole",Cc-64.25*X+30*U+14*D),("Gusset above the seat",Cc-40*X+8*D+62*U),("Zip-tie tunnel (2)",(-35,58.7,180)),("Chin-plate screw pilot, front-left",(-66,-76,104.5))],zoom=1.0)
shot("chin_top_v4",["P_Chin"],(0.3,-0.8,1),labels=[("Lip: drops inside the bell wall",(0,-62,108)),("Neck opening: wires and the core's dome nest here",(0,-5,100)),("Screw pilot (3)",(-62,-73,104.5))],zoom=1.1)
P.rotation_euler=(math.radians(180),0,0)
shot("chin_under_v4",["P_Chin"],(0.3,-0.8,1),labels=[("Magnet pocket (3) - faces the core",(-55.8,68.1,-96)),("Magnet pocket",(56.7,70.2,-96)),("Magnet pocket",(-62.1,-48.6,-96))],zoom=1.1)
P.rotation_euler=(0,0,0)
P.location.z=-30; C_=bpy.data.objects["P_Core"]; C_.location.z=-55; Pl=bpy.data.objects["P_Plinth"]; Pl.location.z=-85; R_=bpy.data.objects["P_Riser"]; R_.location.z=-125
shot("exploded_v4",["P_HeadBell","P_Chin","P_Core","P_Plinth","P_Riser"],(0.8,-1,0.4),labels=[("1a  Head bell  (screen, Pi, speaker, amp)",(0,-75,176)),("1b  Chin plate  (screws to the bell; magnets to the core)",(0,-70,98-30)),("2  Core  (legs, glowing dome, neck)",(60,-50,50-55)),("3  Base plate  (button, LED ring)",(0,-79,12-85)),("4  Riser  (power jack, ballast)",(0,-65,-20-125))],zoom=1.7)
