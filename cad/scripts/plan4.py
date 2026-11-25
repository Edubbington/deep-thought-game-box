import plan3m as P, numpy as np
base=P.m.copy()
def dil(a,n):
    for _ in range(n):
        b=a.copy(); b[1:]|=a[:-1]; b[:-1]|=a[1:]; b[:,1:]|=a[:,:-1]; b[:,:-1]|=a[:,1:]; a=b
    return a
def notch(zc):
    mm=base.copy(); ia=np.searchsorted(P.X,57.0); ib=np.searchsorted(P.X,63.5); ja=np.searchsorted(P.Z,141.0); jb=np.searchsorted(P.Z,zc); mm[ia:ib,ja:jb]=False; return mm
for margin_cells,label in ((2,"0.5 mm clearance all round"),(4,"1.0 mm clearance all round")):
    for zc in (143,146,148,150,152,155,158,162):
        P.m=dil(notch(zc),margin_cells); r=P.feasible(P.rect(15.5,30.5),(79.0-15.5/2-0.25*margin_cells,165.5))[0]
        print(label,": notch",zc-143,"mm tall ->",r)
        if r=="OK": break
