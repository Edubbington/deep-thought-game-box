import sys; sys.path.insert(0,'/home/claude/build')
exec(open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0].replace('s5.blend','s6.blend').replace('"P_Head")','"P_HeadBell")').replace('"P_Head":(0.75','"P_HeadBell":(0.75'))
B=bpy.data.objects["P_HeadBell"]; Ch=bpy.data.objects["P_Chin"]
Ch.location.z=-25
shot("v4_bell_chin",["P_HeadBell","P_Chin"],(0.9,-1,-0.55),W=1100,H=850,zoom=1.15,labels=[("Bell: open bottom - display and Pi go in here",(0,-10,101)),("Chin plate: lip fits inside the bell wall",(0,-60,83)),("Screw pilot (3x, M2.5)",(0,-10-93,80)),("Speaker slot (speaker drops in from below)",(71,-10,140)),("45 deg sill under the screen window",(-3,-99,138)),("Neck opening + magnet pockets to the core",(0,-10,70))])
Ch.location.z=0
bc=half("P_HeadBell",(10,0,0),(1,0,0),keep_pos=False)
shot("v4_bell_cut",[bc],(1,-0.6,0.25),W=1100,H=850,zoom=1.1,labels=[("Flat top (bed face) + 6 mm ceiling",(0,-10,239)),("45 deg top bevel",(-60,-95,236)),("Gusset over the display seat",(-40,-100,234)),("Display pocket, chamfered floor",(-40,-90,135)),("Screen window with sill",(-40,-100,150)),("Wiring pad with chamfered top",(-3,64,190))])
