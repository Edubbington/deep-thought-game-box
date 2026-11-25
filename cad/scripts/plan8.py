from plan5 import *
import pickle
_,_,me=pickle.load(open("/home/claude/build/entry_ear.pkl","rb")); me=me[i0:]
thin=me.copy(); thin[1:-1]&=~(~me[:-2]&~me[2:]); print('removed single-column artifact cells:',int(me.sum()-thin.sum())); me=thin
for nm,mk in (('mid',mM),):
    t2=mk.copy(); t2[1:-1]&=~(~mk[:-2]&~mk[2:]); print(nm,'mask artifact cells:',int(mk.sum()-t2.sum()))
def cham(t,h,c): return [(-t/2+c,-h/2),(t/2-c,-h/2),(t/2,-h/2+c),(t/2,h/2-c),(t/2-c,h/2),(-t/2+c,h/2),(-t/2,h/2-c),(-t/2,-h/2+c)]
S=cham(15.5,30.5,2.0); goal=(79.5-7.75,165.0)
print("exact geometry, zero clearance:")
print(" speaker (2 mm rounded corners) alone:",feasible([([S],mM)],goal)[0])
for name,blk in (("ear blocks 6.2 thick x 16 tall, square",R(1.55,7.75,-8,8)),("ear blocks with the front edges chamfered 2 mm",[(1.55,-8),(5.75,-8),(7.75,-6),(7.75,6),(5.75,8),(1.55,8)]),("ear blocks 6.2 x 13 tall, chamfered",[(1.55,-6.5),(5.75,-6.5),(7.75,-4.5),(7.75,4.5),(5.75,6.5),(1.55,6.5)])):
    print(" speaker +",name,":",feasible([([S],mM),([blk,EAR],me)],goal)[0])
