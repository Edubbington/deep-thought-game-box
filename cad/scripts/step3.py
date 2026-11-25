import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s2.blend")
t0=time.time()
core=bpy.data.objects["P_Core"]; pl=bpy.data.objects["P_Plinth"]
# ---- core: hollow dome + wire channel + magnet pockets
dc=dup(core,"dc"); erode(dc,2.4,0.6)
r=cyl("r",Vector((0,1.7,46)),45,48); boolean(dc,r,'INTERSECT'); rm(r)
p=cyl("p",Vector((0,1.7,23.4)),36,10); boolean(dc,p,'UNION'); rm(p)
ch=cyl("ch",Vector((0,12,74)),7,48); boolean(dc,ch,'UNION'); rm(ch)
boolean(core,dc,'DIFFERENCE'); rm(dc)
bosses=[(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]
M=multi("mp",[("cyl",{"loc":Vector((x,y,96-1.7+0.5)),"r":3.2,"h":4.4}) for x,y in bosses]); boolean(core,M,'DIFFERENCE'); rm(M)
print(stats(core))
# ---- plinth: hollow from below, wire hole, button hole
pc=dup(pl,"pc"); erode(pc,2.5,0.5)
pc2=dup(pc,"pc2"); pc2.location.z=-3; sel(pc2); bpy.ops.object.transform_apply(location=True)
boolean(pc,pc2,'UNION'); rm(pc2)
boolean(pl,pc,'DIFFERENCE'); rm(pc)
h=multi("h",[("cyl",{"loc":Vector((0,1.7,22)),"r":15,"h":6,"seg":64}),("cyl",{"loc":Vector((0,-79,22)),"r":14,"h":6,"seg":64})]); boolean(pl,h,'DIFFERENCE'); rm(h)
print(stats(pl))
# ---- riser
pts=section_loop(pl,10) if False else None
src=bpy.data.objects["DT"]
pts=section_loop(src,10)
rs=prism("P_Riser",pts,-40,0)
rc=prism("rc",pts,-40,40); erode(rc,2.5,0.5); boolean(rs,rc,'DIFFERENCE'); rm(rc)
lo=prism("lo",pts,-60,30); erode(lo,2.8,0.5)
li=prism("li",pts,-60,30); erode(li,4.8,0.5)
boolean(lo,li,'DIFFERENCE'); rm(li)
sl=box("sl",Vector((0,0,1.75)),(400,400,4.5)); boolean(lo,sl,'INTERSECT'); rm(sl)
boolean(rs,lo,'UNION'); rm(lo)
pw=box("pw",Vector((0,54,-20)),(14,12,9)); boolean(rs,pw,'DIFFERENCE'); rm(pw)
print(stats(rs))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s3.blend")
print("t %.0fs"%(time.time()-t0))
