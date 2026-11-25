import sys; sys.path.insert(0,'/home/claude/build')
src=open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0].replace('s5.blend','s6.blend').replace('"P_Head")','"P_HeadBell")').replace('"P_Head":(0.75','"P_HeadBell":(0.75')
exec(src)
import mathutils
bpy.data.objects["P_Chin"].color=(0.62,0.66,0.72,1)
# ---- display frame
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+c*176.0,176.0)); B=(X,U,D)
dg=bpy.context.evaluated_depsgraph_get(); bvh=mathutils.bvhtree.BVHTree.FromObject(bpy.data.objects["P_HeadBell"],dg)
def hits(o,d,maxd=200):
    out=[]; p=Vector(o); d=Vector(d).normalized()
    for _ in range(8):
        h=bvh.ray_cast(p,d,maxd)
        if h[0] is None: break
        out.append(h[0]); p=h[0]+d*0.02
    return out
hs=hits(C+58*X-60*D,D); lipD=(hs[1]-C).dot(D); print("display front face sits at D=",round(lipD,2))
comps={}
def comp(name,o,col): o.name=name; o.color=col; o.hide_render=True; comps[name]=o; return o
GL=(0.08,0.1,0.16,1); PCB=(0.35,0.7,0.4,1); PI=(0.15,0.5,0.25,1); BLK=(0.1,0.1,0.1,1); RED=(0.8,0.2,0.15,1); BLU=(0.2,0.4,0.9,1); YEL=(0.95,0.85,0.3,1); GRY=(0.55,0.55,0.58,1); SIL=(0.8,0.8,0.85,1); WHT=(0.92,0.92,0.9,1)
# display: glass 1.6 + board 5.4 = 7 mm (assumed; measure yours)
comp("Display glass",box("g",C+(lipD+0.8)*D,(121.1,77.9,1.6),B),GL)
comp("Display board",box("pcb",C+(lipD+1.6+2.7)*D,(121.1,77.9,5.4),B),PCB)
# Pi: board underside 13 mm behind glass (standoffs), 85x56x1.5, components 15 mm high; USB stack toward -X
piD=lipD+13
comp("Pi 2 board",box("pi",C+(piD+0.75)*D-2*X,(85,56,1.5),B),PI)
comp("Pi USB/Ethernet",box("usb",C+(piD+1.5+7.5)*D-2*X-36*X-12*U,(14,32,15),B),GRY)
comp("Pi GPIO header",box("hdr",C+(piD+1.5+4.5)*D-2*X+24*U+2*X,(51,5,9),B),BLK)
comp("Pi SD/DSI side",box("dsi",C+(piD+1.5+2.5)*D-2*X+30*X,(10,22,5),B),BLK)
comp("Wi-Fi nano",box("wifi",C+(piD+1.5+4)*D-2*X-36*X-20*X-6*U,(19,14,5),B),BLU)
comp("USB mic",box("mic",C+(piD+1.5+12)*D-2*X-36*X-20*X-6*U,(22,14,7),B),WHT)
# speaker 70x31x17 oval in the slot x 62.5..79.5, centre (71,-10,165)
import bmesh
bm=bmesh.new(); M=Matrix.Translation(Vector((71,-10,165)))@Matrix.Rotation(math.radians(90),4,'Y')@Matrix.Diagonal((1,35/15.5,1,1))
bmesh.ops.create_cone(bm,cap_ends=True,segments=48,radius1=15.5,radius2=15.5,depth=17,matrix=M)
comp("Speaker",link("spk",bm),BLK)
# amp on the wiring pad (pad front face y=60), 25x18x5 standing
comp("Amp (NS4168)",box("amp",Vector((-3,57.4,160)),(25,5,18)),RED)
# base plate: ring 48/31 x 3 at z 22.72..25.7, button at (0,-79)
ptop=22.72
bm=bmesh.new(); bmesh.ops.create_cone(bm,cap_ends=True,segments=64,radius1=24,radius2=24,depth=3,matrix=Matrix.Translation(Vector((0,1.7,ptop+1.5))))
ring=link("ring",bm); hole=cyl("rh",Vector((0,1.7,ptop+1.5)),15.5,5); boolean(ring,hole,'DIFFERENCE'); rm(hole); comp("LED ring",ring,YEL)
comp("Button cap",cyl("bc",Vector((0,-79,ptop+6)),16.5,12),RED)
comp("Button body",cyl("bb",Vector((0,-79,ptop-17)),14,34),BLK)
# riser: power jack in the back-wall slot at (0,54,-20): body 12x9 inboard, 20 long
comp("Micro-USB jack",box("jack",Vector((0,46,-20)),(12,22,9)),GRY)
comp("Ballast (washers)",multi("bal",[("cyl",{"loc":Vector((sx,26,-27)),"r":12,"h":10,"seg":32}) for sx in (-50,50)]),SIL)
# magnets: core top pockets + chin pockets
comp("Magnets",multi("mag",[("cyl",{"loc":Vector((x,y,z)),"r":3,"h":3,"seg":24}) for x,y in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)] for z in (94.5,98)]),SIL)
allc=list(comps)
for n in allc: bpy.data.objects[n].hide_render=True
print("components:",allc)
# ---- renders
bell=["P_HeadBell"]; headc=["Display glass","Display board","Pi 2 board","Pi USB/Ethernet","Pi GPIO header","Pi SD/DSI side","Wi-Fi nano","USB mic","Speaker","Amp (NS4168)"]
def cutset(names,x0,keep):
    return [half(n,(x0,0,0),(1,0,0),keep_pos=keep) for n in names]
R=cutset(["P_HeadBell"]+headc,12,True)
shot("L_head_right",R,(-1,-0.45,0.3),labels=[("Speaker in its slot",(71,-10,165)),("Amp on the wiring pad",(-3,57,160)),("Display glass, against the window lip",(C+(lipD+0.8)*D+30*X)),("Display board",(C+(lipD+4.3)*D+30*X)),("Pi, 13 mm behind the glass",(C+(piD+1)*D+30*X)),("GPIO header",(C+(piD+6)*D+24*U+12*X))],zoom=1.3)
L=cutset(["P_HeadBell"]+headc,-20,False)
shot("L_head_left",L,(1,-0.45,0.3),labels=[("Wi-Fi + mic on the Pi's USB ports",(C+(piD+9)*D-58*X-6*U)),("Display board",(C+(lipD+4.3)*D-45*X)),("Pi board",(C+(piD+1)*D-30*X)),("Amp",(-3,57,160)),("Zip-tie tunnel",(-35,58.7,180))],zoom=1.3)
shot("L_head_below",bell+headc,(0.15,-0.25,-1),W=1100,H=900,labels=[("Open bottom: everything goes in here",(-3,-70,100)),("Pi, GPIO header toward the back",(C+(piD+6)*D+24*U)),("Speaker",(71,-10,160)),("Amp",(-3,57,160)),("Wi-Fi + mic on the USB ports",(C+(piD+9)*D-58*X-6*U))],zoom=1.0)
shot("L_plate",["P_Plinth","LED ring","Button cap","Button body"],(0.3,-0.9,0.7),labels=[("LED ring centred on the wire hole",(0,1.7,26)),("Arcade button through the 28 mm hole",(0,-79,30))],zoom=1.0)
shot("L_riser",["P_Riser","Micro-USB jack","Ballast (washers)"],(0.5,0.8,0.8),labels=[("Micro-USB jack in the back-wall slot",(0,52,-20)),("Ballast in the trays",(50,26,-22))],zoom=1.0)
# full cutaway: everything, bisected at x=-3 keep +x side, viewed from -x
cut=[]
for n in ["P_HeadBell","P_Chin","P_Core","P_Plinth","P_Riser"]+allc:
    cut.append(half(n,(-3,0,0),(1,0,0),keep_pos=True))
shot("L_cutaway",cut,(-1,-0.35,0.2),labels=[("Display + Pi in the head",(C+30*X+(piD+1)*D)),("Speaker",(71,-10,165)),("Amp",(-3,57,160)),("Magnets: chin plate to core",(56.7,-70.2,96)),("Wires drop through the neck",(0,12,74)),("LED ring under the dome",(10,1.7,25)),("Button",(0,-79,30)),("Power jack",(0,52,-20)),("Ballast",(50,26,-22))],zoom=1.0,W=1100,H=1000)
