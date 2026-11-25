import sys; sys.path.insert(0,'/home/claude/build')
from lib import *
import bmesh, math, mathutils, numpy as np
bpy.ops.wm.open_mainfile(filepath="/home/claude/build/s7.blend")
prof=[(0,0),(8,0),(8,4.7),(6.5,6.2),(1.5,6.2),(0,4.7)]; L=10.4
def block(name,ox,oy):
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    a=[bm.verts.new((ox,oy+y,z)) for y,z in prof]; b=[bm.verts.new((ox+L,oy+y,z)) for y,z in prof]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(len(prof)): j=(i+1)%len(prof); bm.faces.new((a[i],a[j],b[j],b[i]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); bm.to_mesh(me); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    for hx in (2.9,7.4):
        h=cyl("h",Vector((ox+hx,oy+4,3)),1.1,12,24); boolean(o,h,'DIFFERENCE'); rm(h)
    return o
bl=[block(f"blk{i}",(i%2)*14,(i//2)*12) for i in range(4)]
for o in bl[1:]: boolean(bl[0],o,'UNION'); rm(o)
o=bl[0]; print(stats(o)); export(o,"/home/claude/out/DeepThought_6_SpeakerEarBlocks_v3.stl")
bm=bmesh.new(); bm.from_mesh(o.data); v=np.array([w.co[:] for w in bm.verts]); print("bbox",v.min(0).round(2),v.max(0).round(2),"non-manifold",sum(1 for e in bm.edges if not e.is_manifold))
dg=bpy.context.evaluated_depsgraph_get(); t=mathutils.bvhtree.BVHTree.FromObject(o,dg)
for hx in (2.9,7.4):
    h=t.ray_cast(Vector((hx,4,20)),Vector((0,0,-1)),30); h2=t.ray_cast(Vector((hx+1.6,4,20)),Vector((0,0,-1)),30); print(" hole at X",hx,": through" if h[0] is None else f"blocked at {h[0].z:.2f}","; top surface beside it Z",round(h2[0].z,2))
# chamfer check: top surface height at Y=0.5 and Y=4
print(" top Z at Y=0.5:",round(t.ray_cast(Vector((5.2,0.5,20)),Vector((0,0,-1)),30)[0].z,2)," at Y=4:",round(t.ray_cast(Vector((5.2,4,20)),Vector((0,0,-1)),30)[0].z,2))
