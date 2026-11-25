import bpy, bmesh, math, time, json
SOLVER='MANIFOLD'
from mathutils import Vector, Matrix
def sel(o):
    for x in bpy.context.view_layer.objects: x.select_set(False)
    bpy.context.view_layer.objects.active=o; o.select_set(True)
def apply_mod(o,name):
    sel(o); bpy.ops.object.modifier_apply(modifier=name)
def boolean(t,c,op):
    m=t.modifiers.new("b","BOOLEAN"); m.operation=op; m.object=c; m.solver=SOLVER; apply_mod(t,"b")
def rm(o): bpy.data.objects.remove(o,do_unlink=True)
def dup(o,name):
    c=o.copy(); c.data=o.data.copy(); c.name=name; bpy.context.collection.objects.link(c); return c
def link(name,bm):
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); return o
def cyl(name,loc,r,h,seg=64,rot=None):
    bm=bmesh.new(); M=Matrix.Translation(loc)@(rot or Matrix.Identity(4))
    bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r,radius2=r,depth=h,matrix=M); return link(name,bm)
def box(name,loc,size,basis=None):
    bm=bmesh.new()
    R=Matrix.Identity(4) if basis is None else Matrix((basis[0],basis[1],basis[2])).transposed().to_4x4()
    bmesh.ops.create_cube(bm,size=1,matrix=Matrix.Translation(loc)@R@Matrix.Diagonal((*size,1))); return link(name,bm)
def multi(name,items):
    bm=bmesh.new()
    for kind,p in items:
        if kind=="cyl":
            M=Matrix.Translation(p["loc"])@p.get("rot",Matrix.Identity(4))
            bmesh.ops.create_cone(bm,cap_ends=True,segments=p.get("seg",32),radius1=p["r"],radius2=p["r"],depth=p["h"],matrix=M)
        else:
            bmesh.ops.create_cube(bm,size=1,matrix=Matrix.Translation(p["loc"])@Matrix.Diagonal((*p["size"],1)))
    return link(name,bm)
_ng=None
def erode(o,dist,vox):
    global _ng
    if _ng is None:
        ng=bpy.data.node_groups.new("erode","GeometryNodeTree")
        ng.interface.new_socket("Geometry",in_out='INPUT',socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry",in_out='OUTPUT',socket_type='NodeSocketGeometry')
        gi=ng.nodes.new("NodeGroupInput"); go=ng.nodes.new("NodeGroupOutput")
        a=ng.nodes.new("GeometryNodeMeshToSDFGrid"); a.name="sdf"; a.inputs["Band Width"].default_value=8
        b=ng.nodes.new("GeometryNodeGridToMesh"); b.name="g2m"; b.inputs["Adaptivity"].default_value=0
        ng.links.new(gi.outputs[0],a.inputs["Mesh"]); ng.links.new(a.outputs[0],b.inputs["Grid"]); ng.links.new(b.outputs[0],go.inputs[0]); _ng=ng
    _ng.nodes["sdf"].inputs["Voxel Size"].default_value=vox
    _ng.nodes["sdf"].inputs["Band Width"].default_value=int(dist/vox)+6
    _ng.nodes["g2m"].inputs["Threshold"].default_value=-dist
    m=o.modifiers.new("e","NODES"); m.node_group=_ng; apply_mod(o,"e")
def remesh(o,vs):
    m=o.modifiers.new("r","REMESH"); m.mode='VOXEL'; m.voxel_size=vs; m.adaptivity=0; apply_mod(o,"r")
def decimate(o,ratio):
    m=o.modifiers.new("d","DECIMATE"); m.ratio=ratio; m.use_collapse_triangulate=True; apply_mod(o,"d")
def stats(o):
    bm=bmesh.new(); bm.from_mesh(o.data); nm=sum(1 for e in bm.edges if not e.is_manifold); f=len(bm.faces); bm.free()
    return "%s faces=%d nm=%d dims=%s"%(o.name,f,nm,[round(x,1) for x in o.dimensions])
def fix(o):
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=bm.verts[:],dist=0.001)
    bd=[e for e in bm.edges if e.is_boundary]
    if bd: bmesh.ops.holes_fill(bm,edges=bd,sides=0)
    bmesh.ops.triangulate(bm,faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
def section_loop(o,z):
    bm=bmesh.new(); bm.from_mesh(o.data)
    res=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,z),plane_no=(0,0,1))
    cut=[e for e in res['geom_cut'] if isinstance(e,bmesh.types.BMEdge)]
    adj={}
    for e in cut:
        a,b=e.verts; adj.setdefault(a,[]).append(b); adj.setdefault(b,[]).append(a)
    loops=[]; seen=set()
    for s in adj:
        if s in seen: continue
        loop=[s]; seen.add(s); prev=None; cur=s
        while True:
            nx=[v for v in adj[cur] if v is not prev and (v not in seen or v is s)]
            if not nx or nx[0] is s: break
            prev,cur=cur,nx[0]; seen.add(cur); loop.append(cur)
        loops.append([(v.co.x,v.co.y) for v in loop])
    bm.free(); return max(loops,key=len)
def prism(name,pts,z0,z1):
    bm=bmesh.new()
    bot=[bm.verts.new((x,y,z0)) for x,y in pts]; top=[bm.verts.new((x,y,z1)) for x,y in pts]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    for i in range(len(pts)):
        j=(i+1)%len(pts); bm.faces.new((bot[i],bot[j],top[j],top[i]))
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]); return link(name,bm)
def export(o,path):
    sel(o); bpy.ops.wm.stl_export(filepath=path,export_selected_objects=True,ascii_format=False,apply_modifiers=True)
