import sys; sys.path.insert(0,'/home/claude/build')
exec(open('/home/claude/build/guide_render.py').read().split("# ---------- 1. print bed")[0])
pr=half("P_Plinth",(0,0,0),(1,0,0),keep_pos=True); rr=half("P_Riser",(0,0,0),(1,0,0),keep_pos=True)
shot("mate_section",[pr,rr],(-1,0,0.0),W=1100,H=700,zoom=0.6,center=Vector((0,-20,-5)))
