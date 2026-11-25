import plan, numpy as np
from plan import *
base=plan.m.copy()
def trimmed(zc):
    mm=base.copy(); ia=np.searchsorted(plan.X,57.0); ib=np.searchsorted(plan.X,63.5); ja=np.searchsorted(plan.Z,141.0); jb=np.searchsorted(plan.Z,zc)
    mm[ia:ib,ja:jb]=False; return mm
print("true speaker body alone (15.5 x 30.5), no wall trimmed:", feasible(rect(15.5,30.5),(78.8-15.5/2,181.0-30.5/2)))
for t,h,name in ((15.5,31.25,"basket no back plate"),(16.9,31.25,"basket v2 as printed")):
    for zc in (150,155,160,165,170,175,182):
        plan.m=trimmed(zc); r=feasible(rect(t,h),(78.8-t/2,181.0-h/2)); print(f"{name}: inner wall trimmed up to z={zc} (removes {zc-143} mm): {r}")
        if r=="OK": break
plan.m=base
