from plan5 import *
import pickle
_,_,me=pickle.load(open("/home/claude/build/entry_ear2.pkl","rb")); me=me[i0:]
t=me.copy(); t[1:-1]&=~(~me[:-2]&~me[2:]); me=t
def cham(t,h,c): return [(-t/2+c,-h/2),(t/2-c,-h/2),(t/2,-h/2+c),(t/2,h/2-c),(t/2-c,h/2),(-t/2+c,h/2),(-t/2,h/2-c),(-t/2,-h/2+c)]
S=cham(15.5,30.5,2.0); goal=(79.5-7.75,165.0)
BL=[(1.55,-4),(6.25,-4),(7.75,-2.5),(7.75,2.5),(6.25,4),(1.55,4)]
r,p=feasible([([S],mM),([BL,EAR],me)],goal,path=True); print("speaker (2 mm rounded corners) + ear blocks 6.2 x 8, front edges chamfered 1.5:",r)
if p: print(" way in (tilt deg, x, z of speaker centre), every 12th step:",[(a,round(x,1),round(z,1)) for a,x,z in p[::-1][::12]])
