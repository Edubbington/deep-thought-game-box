import bpy, bmesh, math
from mathutils import Vector
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6b.blend")
C=bpy.data.objects["P_Core"]; bm=bmesh.new(); bm.from_mesh(C.data)
zs=[v.co.z for v in bm.verts]; print("core z",round(min(zs),2),round(max(zs),2))
top=max(zs)
tris=[]
for f in bm.faces:
    c=f.calc_center_median()
    if f.normal.z>0.9 and c.z>top-0.3: tris.append(Polygon([(v.co.x,v.co.y) for v in f.verts]))
lip=unary_union(tris); print("lip top faces:",len(tris),"union type",lip.geom_type,"area",round(lip.area))
if lip.geom_type=='MultiPolygon': print("  pieces:",[round(p.area) for p in lip.geoms]); lip=max(lip.geoms,key=lambda p:p.area)
print("lip exterior bbox",[round(v,1) for v in lip.bounds],"interiors",len(lip.interiors),[round(Polygon(i).area) for i in lip.interiors])
# lip width: distance from exterior to interior along a few points
ext=lip.exterior; inn=max(lip.interiors,key=lambda i:Polygon(i).area)
print("lip width samples:",[round(Point(ext.interpolate(ext.length*k/8)).distance(inn),2) for k in range(8)])
# magnet pockets vs lip
for m in [(-55.8,-68.1),(56.7,-70.2),(-62.1,48.6)]:
    p=Point(m); print("magnet",m,"inside lip ring:",lip.contains(p),"inside hole:",Polygon(inn).contains(p),"dist to lip exterior",round(ext.distance(p),1),"dist to lip interior",round(inn.distance(p),1))
# top plate level and core outline at the top plate
plate=[f.calc_center_median().z for f in bm.faces if f.normal.z>0.9 and f.calc_area()>2 and f.calc_center_median().z<top-1]
import collections; print("core up-face levels below the lip:",sorted(collections.Counter(round(z,1) for z in plate).items())[-4:])
import pickle; pickle.dump({"ext":list(ext.coords),"inn":list(inn.coords),"top":top},open("/home/claude/build/corelip.pkl","wb"))
