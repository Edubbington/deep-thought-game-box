import sys, json; sys.path.insert(0,'/home/claude/build')
exec(open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0])
H_=bpy.data.objects["P_Head"]; C_=bpy.data.objects["P_Core"]; R_=bpy.data.objects["P_Riser"]
H_.location.z=80; C_.location.z=40; R_.location.z=-35
shot("exploded",PARTS,(0.8,-1,0.4),labels=[("1  Head  (screen, speaker, amp)",(0,-75,80+176)),("2  Core  (legs, glowing dome, neck)",(60,-50,40+50)),("3  Base plate  (button, LED ring)",(0,-79,12)),("4  Riser  (Pi, power jack, ballast)",(0,-65,-35-20))],zoom=1.55)
H_.location.z=0; C_.location.z=0; R_.location.z=0
shot("assembled",PARTS,(0.8,-1,0.3),zoom=1.4)
shot("plate_top",["P_Plinth"],(0.15,-0.5,1),labels=[("Button hole, 28 mm (front)",(0,-79,23)),("LED-ring seat, 49 mm recess",(24,1.7,23)),("Wire hole, 30 mm",(0,1.7,21))],zoom=1.0)
print("done")
