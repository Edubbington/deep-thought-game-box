import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import mathutils, bmesh, random, math
from mathutils import Matrix
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s6c.blend")
H=bpy.data.objects["P_HeadBell"]
Z0,Z1=150.2,181.45; Y0,Y1=-45.9,25.9; X0=62.8; XP=64.2; XE=XP+6.2; XF=79.7; YC=-10.0; ZC=165.55
def bx(n,x0,x1,y0,y1,z0=Z0,z1=Z1): return box(n,Vector(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)),(x1-x0,y1-y0,z1-z0))
b=bx("Basket",X0,XP,Y0,Y1)
for n,(x0,x1,y0,y1) in {"sl":(XP,XE,Y0,YC-14.75),"sr":(XP,XE,YC+14.75,Y1),"pl":(XP,XF,Y0,YC-22.0),"pr":(XP,XF,YC+22.0,Y1)}.items():
    p=bx(n,x0-0.3,x1,y0,y1); boolean(b,p,'UNION'); rm(p)
rotY=Matrix.Rotation(math.radians(90),4,'Y')
for yy in (YC-17.5,YC+17.5):
    h=cyl("h",Vector(((X0+XE)/2,yy,ZC)),1.1,20,24,rot=rotY); boolean(b,h,'DIFFERENCE'); rm(h)
for yy in (-37.5,17.5):
    h=cyl("h2",Vector((XF-4.0,yy,165.0)),1.1,10,24,rot=rotY); boolean(b,h,'DIFFERENCE'); rm(h)   # x 70.7..80.7: 9 mm deep from the front of each end pillar, under grille holes
print("basket",stats(b))
# speaker stand-in for the check and the render
sp=bx("Speaker",XP,XP+15.5,YC-14.25,YC+14.25,ZC-15.25,ZC+15.25)
for yy in (YC-17.75,YC+17.75):
    e=bx("e",XP+6.25,XP+9.25,yy-3.5,yy+3.5,ZC-4,ZC+4); boolean(sp,e,'UNION'); rm(e)
dg=bpy.context.evaluated_depsgraph_get()
T={o.name:mathutils.bvhtree.BVHTree.FromObject(o,dg) for o in (H,b,sp)}
def inside(t,p):
    n=0; q=Vector(p); d=Vector((0.37,0.41,0.83)).normalized()
    for _ in range(200):
        h=t.ray_cast(q,d,1000)
        if h[0] is None: break
        n+=1; q=h[0]+d*0.01
    return n%2==1
random.seed(1); nb=ns=cb=cs=bs=0; bad=[]
for _ in range(40000):
    p=(random.uniform(61,81),random.uniform(-48,28),random.uniform(148,183))
    ib=inside(T["Basket"],p); isp=inside(T["Speaker"],p)
    if ib or isp:
        ih=inside(T["P_HeadBell"],p); nb+=ib; ns+=isp; cb+= ib and ih; cs+= isp and ih; bs+= ib and isp
        if ih: bad.append(tuple(round(v,1) for v in p))
print(f"samples in basket {nb}, in speaker {ns}; basket-in-bell {cb}, speaker-in-bell {cs}, basket-in-speaker {bs}")
print("in-bell points:",bad[:25])
print("clearances: basket to slot: x",X0-62.5,80-XF,"y",Y0+46.25,26.25-Y1,"top",181.75-Z1,"| speaker front to outer wall",round(80-(XP+15.5),2),"speaker top to slot top",round(181.75-(ZC+15.25),2),"speaker bottom z",ZC-15.25,"(zip tie band 146-150)")
print("ear back sits at x",XP+6.25,"block top at",XE,"; ear tips y",YC-21.25,YC+21.25,"pillars start",YC-22,YC+22,"; pilot depth",round(XE-X0,2))
print("grille centre (y -10, z 165); speaker centre",YC,ZC)
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/build/s7.blend")
# export: plate on the bed. (x,y,z)->(y,z,x)
e=dup(b,"Basket_print"); bm=bmesh.new(); bm.from_mesh(e.data)
for v in bm.verts: v.co=Vector((v.co.y-Y0,v.co.z-Z0,v.co.x-X0))
bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); bm.to_mesh(e.data)
vol=sum(f.calc_area()*f.calc_center_median().dot(f.normal)/3 for f in bm.faces)
print("print dims",[round(x,2) for x in e.dimensions],"volume cm3",round(vol/1000,1),"non-manifold",sum(1 for ed in bm.edges if not ed.is_manifold),"down-facing above bed:",round(sum(f.calc_area() for f in bm.faces if f.normal.z<-0.5 and f.calc_center_median().z>0.1),1))
export(e,"/home/claude/out/DeepThought_6_SpeakerBasket_v2.stl")
# render
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.world=bpy.data.worlds.new("w"); sc.world.color=(0.18,0.18,0.2)
cam=bpy.data.cameras.new("c"); cam.type='ORTHO'; co=bpy.data.objects.new("cam",cam); bpy.context.collection.objects.link(co); sc.camera=co
b.color=(0.25,0.45,0.85,1); sp.color=(0.12,0.12,0.12,1)
def shot(name,objs,d,scale):
    for o in bpy.data.objects: o.hide_render=o.name not in objs
    d=Vector(d).normalized(); ctr=Vector(((X0+XF)/2,YC,(Z0+Z1)/2)); co.location=ctr+d*600; co.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler(); cam.ortho_scale=scale
    sc.render.resolution_x=1100; sc.render.resolution_y=700; sc.render.filepath="/home/claude/guide/"+name+".png"; bpy.ops.render.render(write_still=True)
shot("B2_empty",["Basket"],(1,-0.5,0.45),105); shot("B2_loaded",["Basket","Speaker"],(1,-0.5,0.45),105)
