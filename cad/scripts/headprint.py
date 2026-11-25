import bpy, bmesh, math, collections
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath="/home/claude/out/DeepThought_1_Head.stl"); o=bpy.context.selected_objects[0]
bm=bmesh.new(); bm.from_mesh(o.data)
zs=[v.co.z for v in bm.verts]; print("print height",round(max(zs),1))
bed=[f for f in bm.faces if f.normal.z<-0.95 and f.calc_center_median().z<0.1]
print("bed contact area mm2:",round(sum(f.calc_area() for f in bed)))
# overhang faces: normal pointing down more than 45deg from vertical wall => normal.z < -0.707 ; also 30-45deg band
def region(c):
    # map print coords back: model z = 250 - print z ; model y = -print y  (flip 180 about X) ; x same
    mz=250-c.z; my=-c.y; x=c.x
    if mz>240: return "top shoulders (outside, near bed)"
    if 143<=mz<=190 and 58<=x<=90: return "speaker cradle"
    if -110<my<-60 and 125<mz<230: return "display seat/window area (front)"
    if my>50 and 130<mz<190: return "wiring pad / anchors (back wall)"
    if mz<110: return "bottom rim / magnet bosses"
    return f"other z{int(mz)} y{int(my)}"
steep=collections.Counter(); mild=collections.Counter()
for f in bm.faces:
    c=f.calc_center_median()
    if c.z<0.3: continue
    if f.normal.z<-0.707: steep[region(c)]+=f.calc_area()
    elif f.normal.z<-0.5: mild[region(c)]+=f.calc_area()
print("\nOverhangs steeper than 45 deg (need support or bridging), mm2 by region:")
for k,v in steep.most_common(): print(f"  {k}: {v:.0f}")
print("\n30-45 deg faces (usually print ok), mm2 by region:")
for k,v in mild.most_common(): print(f"  {k}: {v:.0f}")
