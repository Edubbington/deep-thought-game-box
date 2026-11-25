import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s1.blend")
t0=time.time()
head=bpy.data.objects["P_Head"]; core=bpy.data.objects["P_Core"]
cav=dup(head,"cav"); erode(cav,3.0,1.0); print(stats(cav))
pts=section_loop(cav,101)
pr=prism("open",pts,88,102)
cs=dup(core,"cs"); cs.location.z=8; sel(cs); bpy.ops.object.transform_apply(location=True)
boolean(pr,cs,'INTERSECT'); rm(cs)
boolean(cav,pr,'UNION'); rm(pr)
a,b,c=-60.77,-0.0130,-0.2046
D=Vector((-b,1,-c)).normalized(); X=Vector((1,b,0)); X=(X-X.dot(D)*D).normalized(); U=X.cross(D).normalized()
cx,cz=-3.0,176.0; C=Vector((cx,a+b*cx+c*cz,cz)); B=(X,D,U)
hs=dup(head,"hs")
seat=box("seat",C+7*D,(160,14,108),B); boolean(seat,hs,'INTERSECT'); rm(hs)
solid=dup(head,"solid")
boolean(head,cav,'DIFFERENCE'); rm(cav)
boolean(head,seat,'UNION'); rm(seat)
R=Matrix((X,-U,D)).transposed().to_4x4()
PW,PH=122.5,79.5
pos=[(u,v) for u in (-(PW/2+3.0),(PW/2+3.0)) for v in (-30,30)]
hs2=solid
bo=multi("dispboss",[("cyl",{"loc":C+u*X+v*U+9*D,"r":5.0,"h":6,"seg":32,"rot":R}) for u,v in pos])
boolean(bo,hs2,'INTERSECT'); rm(hs2); boolean(head,bo,'UNION'); rm(bo)
pk=box("pk",C+18*D,(PW,24,PH),B); boolean(head,pk,'DIFFERENCE'); rm(pk)
wn=box("wn",C-1*D,(110.5,18,66.5),B); boolean(head,wn,'DIFFERENCE'); rm(wn)
ph=multi("disppilot",[("cyl",{"loc":C+u*X+v*U+11*D,"r":1.3,"h":8,"seg":16,"rot":R}) for u,v in pos])
boolean(head,ph,'DIFFERENCE'); rm(ph)
print("after cuts",stats(head))
print("remeshed",stats(head)); bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s2a.blend")
bosses=[(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]
B1=multi("bo",[("cyl",{"loc":Vector((x,y,103)),"r":7,"h":14,"seg":48}) for x,y in bosses]); boolean(head,B1,'UNION'); rm(B1)
M1=multi("mp",[("cyl",{"loc":Vector((x,y,96+1.7-0.5)),"r":3.2,"h":4.4}) for x,y in bosses]); boolean(head,M1,'DIFFERENCE'); rm(M1)
rotY=Matrix.Rotation(math.radians(90),4,'Y'); holes=[]; sp=5.5
for i in range(-5,6):
    for j in range(-5,6):
        yy=-10+i*sp+(j%2)*sp/2; zz=165+j*sp*0.866
        if ((yy+10)/31.0)**2+((zz-165)/12.5)**2<=1.0: holes.append(("cyl",{"loc":Vector((82,yy,zz)),"r":1.5,"h":16,"seg":12,"rot":rotY}))
G=multi("gr",holes); boolean(head,G,'DIFFERENCE'); rm(G)
V=multi("vt",[("box",{"loc":Vector((-3,66,z)),"size":(44,16,3)}) for z in (214,221,228,235)]); boolean(head,V,'DIFFERENCE'); rm(V)
print("final",stats(head))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s2.blend")
print("t %.0fs"%(time.time()-t0))
