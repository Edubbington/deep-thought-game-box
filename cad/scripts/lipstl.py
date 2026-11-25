import bpy, bmesh, math, pickle, collections
from mathutils import Vector
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.stl_import(filepath=path); o=bpy.context.selected_objects[0]
    bm=bmesh.new(); bm.from_mesh(o.data); return bm
core=load("/home/claude/out/DeepThought_2_Core_legs_dome.stl")
zs=[v.co.z for v in core.verts]; top=max(zs); print("core STL z 0..",round(top,2))
lev=collections.Counter(round(f.calc_center_median().z,1) for f in core.faces if f.normal.z>0.9)
print("up-face levels near the top:",[(z,n) for z,n in sorted(lev.items()) if z>top-6])
tris=[Polygon([(v.co.x,v.co.y) for v in f.verts]) for f in core.faces if f.normal.z>0.9 and f.calc_center_median().z>top-0.3]
lip=unary_union(tris).buffer(0.01).buffer(-0.01)
print("lip at the top: type",lip.geom_type,"area",round(lip.area))
if lip.geom_type=='MultiPolygon':
    print("  pieces (area, bbox):",[(round(p.area),[round(v,1) for v in p.bounds]) for p in lip.geoms])
    main=max(lip.geoms,key=lambda p:p.area)
else: main=lip
print("main piece bbox",[round(v,1) for v in main.bounds],"interiors",[round(Polygon(i).area) for i in main.interiors])
ext=main.exterior
if main.interiors:
    inn=max(main.interiors,key=lambda i:Polygon(i).area)
    print("lip width samples:",[round(Point(ext.interpolate(ext.length*k/12)).distance(inn),2) for k in range(12)])
# the top plate level (where the chin underside should rest)
plate_lev=[(z,n) for z,n in sorted(lev.items()) if z<top-1]; plate_z=max(plate_lev,key=lambda zn:zn[1])[0]; print("top plate z",plate_z,"-> lip height",round(top-plate_z,2))
# core outline at the top plate: section just below plate_z
b=core.copy(); res=bmesh.ops.bisect_plane(b,geom=b.verts[:]+b.edges[:]+b.faces[:],plane_co=(0,0,plate_z-0.4),plane_no=(0,0,1))
pts=[(v.co.x,v.co.y) for v in res['geom_cut'] if isinstance(v,bmesh.types.BMVert)]
xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; print("core top-plate outline bbox",round(min(xs),1),round(max(xs),1),round(min(ys),1),round(max(ys),1))
# magnet pockets in the core top: down-facing faces (pocket floors) within the top plate
pf=[(f.calc_center_median(),f.calc_area()) for f in core.faces if f.normal.z>0.9 and plate_z-4.6<f.calc_center_median().z<plate_z-1 and f.calc_area()<40]
cl=[]
for c,a in pf:
    for k in cl:
        if (k[0][0]-c).length<5: k.append((c,a)); break
    else: cl.append([(c,a)])
for k in cl:
    A=sum(a for c,a in k)
    if A>15: cx=sum(c.x*a for c,a in k)/A; cy=sum(c.y*a for c,a in k)/A; print(f"  core magnet pocket floor at ({cx:.1f},{cy:.1f}) z={k[0][0].z:.1f} area {A:.0f} -> dia {2*math.sqrt(A/math.pi):.1f}")
pickle.dump({"ext":list(ext.coords),"inn":list(inn.coords) if main.interiors else None,"top":top,"plate_z":plate_z,"outline":pts},open("/home/claude/build/corelip_stl.pkl","wb"))
