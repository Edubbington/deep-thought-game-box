import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s3.blend")
t0=time.time()
DT=bpy.data.objects["DT"]; head=bpy.data.objects["P_Head"]; core=bpy.data.objects["P_Core"]
pl=bpy.data.objects["P_Plinth"]; rs=bpy.data.objects["P_Riser"]
hs=dup(DT,"hs"); b=box("s",Vector((0,0,198)),(400,400,204)); boolean(hs,b,'INTERSECT'); rm(b)
def clip_union(target,obj):
    boolean(obj,hs,'INTERSECT'); boolean(target,obj,'UNION'); rm(obj)
def bridge_items(cx,cy,cz,axis_normal):
    pass
# ---------- HEAD ----------
a,b_,c=-60.77,-0.0130,-0.2046
D=Vector((-b_,1,-c)).normalized(); X=Vector((1,b_,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
C=Vector((-3.0,a+b_*-3.0+c*176.0,176.0))
# speaker cradle for a 3070 oval speaker (70x31x17) on the right wall
fr=box("fr",Vector((77,-10,165)),(20,82,44)); clip_union(head,fr)
op=box("op",Vector((70,-10,165)),(20,72.5,33.5)); boolean(head,op,'DIFFERENCE'); rm(op)
zs=multi("zs",[("box",{"loc":Vector((72,-10,165+dz)),"size":(8,5,3)}) for dz in (-19.6,19.6)]); boolean(head,zs,'DIFFERENCE'); rm(zs)
rotY=Matrix.Rotation(math.radians(90),4,'Y'); holes=[]; sp=5.5
for i in range(-7,8):
    for j in range(-4,5):
        yy=-10+i*sp+(j%2)*sp/2; zz=165+j*sp*0.866
        if ((yy+10)/31.0)**2+((zz-165)/12.5)**2<=1.0: holes.append(("cyl",{"loc":Vector((82,yy,zz)),"r":1.5,"h":16,"seg":12,"rot":rotY}))
G=multi("gr",holes); boolean(head,G,'DIFFERENCE'); rm(G)
print("speaker cradle + grille",len(holes),stats(head))
pad=box("pad",Vector((-3,64,160)),(90,8,60)); clip_union(head,pad)   # y 60..68, clipped to head solid
# measure pad front face
from mathutils.bvhtree import BVHTree
bvh=BVHTree.FromPolygons([v.co for v in head.data.vertices],[tuple(p.vertices) for p in head.data.polygons])
loc,_,_,_=bvh.ray_cast(Vector((-3,0,160)),Vector((0,1,0))); pf=loc.y; print("pad face y",round(pf,2))
br=[];tn=[]
for x in (-35,29):
    for z in (140,180):
        br.append(("box",{"loc":Vector((x,pf-3+0.5,z)),"size":(12,7,7)}))
        tn.append(("box",{"loc":Vector((x,pf-1.3+0.05,z)),"size":(16,2.6,4.6)}))
B=multi("br",br); boolean(head,B,'UNION'); rm(B)
T=multi("tn",tn); boolean(head,T,'DIFFERENCE'); rm(T)
print("wiring pad",stats(head))
# crown magnets on the flat top: thicken ceiling locally, then 3 pockets
disc=cyl("disc",Vector((0,-10,245.5)),45,5,96); clip_union(head,disc)
cm=multi("cm",[("cyl",{"loc":Vector((0+30*math.cos(t),-10+30*math.sin(t),250-1.7+0.5)),"r":3.2,"h":4.4,"seg":32}) for t in (math.radians(90),math.radians(210),math.radians(330))])
boolean(head,cm,'DIFFERENCE'); rm(cm)
print("crown magnets",stats(head))
# ---------- CORE: locating lip ----------
cav=dup(hs,"cav"); erode(cav,3.0,1.0)
pts=section_loop(cav,101); rm(cav)
op=prism("op",pts,80,110)
cs=dup(bpy.data.objects["DT"],"cs"); b=box("s",Vector((0,0,(23.4+96)/2)),(400,400,96-23.4)); boolean(cs,b,'INTERSECT'); rm(b)
cs.location.z=8; sel(cs); bpy.ops.object.transform_apply(location=True)
# opening footprint where chin exists; make it tall for clean erosion
opz=prism("opz",pts,88,102); boolean(opz,cs,'INTERSECT'); rm(cs)
sec=section_loop(opz,95); rm(opz); rm(op)
tall=prism("tall",sec,60,140)
lo=dup(tall,"lo"); erode(lo,0.4,0.4); li=dup(tall,"li"); erode(li,2.4,0.4); rm(tall)
boolean(lo,li,'DIFFERENCE'); rm(li)
sl=box("sl",Vector((0,0,97.95)),(400,400,4.1)); boolean(lo,sl,'INTERSECT'); rm(sl)   # z 95.9..100
bosses=[(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]
kb=multi("kb",[("cyl",{"loc":Vector((x,y,100)),"r":7.8,"h":20,"seg":48}) for x,y in bosses]); boolean(lo,kb,'DIFFERENCE'); rm(kb)
boolean(core,lo,'UNION'); rm(lo)
print("core lip",stats(core))
# ---------- BASE PLATE: LED ring seat ----------
dk=cyl("dk",Vector((0,1.7,19.5)),30,7,96); boolean(pl,dk,'UNION'); rm(dk)          # z 16..23 thickening under top
gr=cyl("gro",Vector((0,1.7,22.0)),24.6,2.2,96); gi=cyl("gri",Vector((0,1.7,22.0)),15.0,3,96)
boolean(gr,gi,'DIFFERENCE'); rm(gi); boolean(pl,gr,'DIFFERENCE'); rm(gr)              # 2mm deep annular seat
wh=cyl("wh",Vector((0,1.7,19)),15,12,64); boolean(pl,wh,'DIFFERENCE'); rm(wh)         # re-open wire hole
print("base plate",stats(pl))
# ---------- RISER: weight trays + zip anchors ----------
items=[]
for sx in (-1,1):
    cx,cy=sx*50,26
    items.append(("box",{"loc":Vector((cx,cy,-37.5+6-0.5)),"size":(60,36,13)}))
T=multi("trays",items)
inner=multi("trin",[("box",{"loc":Vector((sx*50,26,-37.5+6+1)),"size":(56,32,14)}) for sx in (-1,1)])
boolean(T,inner,'DIFFERENCE'); rm(inner); boolean(rs,T,'UNION'); rm(T)
an=multi("an",[("box",{"loc":Vector((x,-20,-37.5+3-0.5)),"size":(12,10,7)}) for x in (-30,30)])
boolean(rs,an,'UNION'); rm(an)
tu=multi("tu",[("box",{"loc":Vector((x,-20,-37.5+1.25)),"size":(16,5,2.6)}) for x in (-30,30)])
boolean(rs,tu,'DIFFERENCE'); rm(tu)
print("riser",stats(rs))
rm(hs)
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s5.blend")
print("t %.0fs"%(time.time()-t0))
