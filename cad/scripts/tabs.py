import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import bmesh
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
objs=[]
for i in range(4):
    ox=i*16
    t=box(f"t{i}",Vector((ox,0,1.5)),(10,14,3));
    h=cyl("h",Vector((ox,-3.0,1.5)),1.7,6,32); boolean(t,h,'DIFFERENCE'); rm(h)
    objs.append(t)
for o in objs[1:]:
    boolean(objs[0],o,'UNION'); rm(o)
t=objs[0]; print(stats(t)); export(t,"/home/claude/out/DeepThought_5_DisplayTabs.stl")
