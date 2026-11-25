import numpy as np, pickle, math
from collections import deque
xs,zs,mU=pickle.load(open("/home/claude/build/entry.pkl","rb")); _,_,mM=pickle.load(open("/home/claude/build/entry_mid.pkl","rb"))
i0=np.searchsorted(xs,34); X=xs[i0:]; Z=zs; mU=mU[i0:]; mM=mM[i0:]; NX,NZ=mU.shape; res=0.25
def dil(a,n):
    for _ in range(n):
        b=a.copy(); b[1:]|=a[:-1]; b[:-1]|=a[1:]; b[:,1:]|=a[:,:-1]; b[:,:-1]|=a[:,1:]; a=b
    return a
def notch(m,zc):
    mm=m.copy(); ia=np.searchsorted(X,57.0); ib=np.searchsorted(X,63.5); ja=np.searchsorted(Z,141.0); jb=np.searchsorted(Z,zc); mm[ia:ib,ja:jb]=False; return mm
def pts_of(poly,step=0.25):
    out=[]
    for (ax,az),(bx,bz) in zip(poly,poly[1:]+poly[:1]):
        L=math.hypot(bx-ax,bz-az); n=max(1,int(L/step)); out+=[(ax+(bx-ax)*k/n,az+(bz-az)*k/n) for k in range(n)]
    return out
def R(x0,x1,z0,z1): return [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]
def feasible(parts,goal,astep=1.0,amax=75,path=False):
    A=[a*astep for a in range(int(-amax/astep),int(amax/astep)+1)]; C=np.zeros((len(A),NX,NZ),bool)
    for polys,m in parts:
        P=[p for poly in polys for p in pts_of(poly)]
        for a,th in enumerate(A):
            c,s=math.cos(math.radians(th)),math.sin(math.radians(th))
            for dx,dz in set((int(round((px*c-pz*s)/res)),int(round((px*s+pz*c)/res))) for px,pz in P):
                xa,xb=max(0,-dx),min(NX,NX-dx); za,zb=max(0,-dz),min(NZ,NZ-dz); C[a,xa:xb,za:zb]|=m[xa+dx:xb+dx,za+dz:zb+dz]
    gi=int(round((goal[0]-X[0])/res)); gj=int(round((goal[1]-Z[0])/res)); ga=A.index(0)
    if C[ga,gi,gj]: return "goal blocked",None
    si=int(round((44-X[0])/res)); sj=int(round((122-Z[0])/res)); par={}
    seen=np.zeros_like(C); q=deque([(ga,gi,gj)]); seen[ga,gi,gj]=True
    while q:
        a,i,j=q.popleft()
        if i==si and j==sj:
            p=[(A[a],float(X[i]),float(Z[j]))]
            while (a,i,j) in par: a,i,j=par[(a,i,j)]; p.append((A[a],float(X[i]),float(Z[j])))
            return "OK",p
        for da,di,dj in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            b,k,l=a+da,i+di,j+dj
            if 0<=b<len(A) and 0<=k<NX and 0<=l<NZ and not seen[b,k,l] and not C[b,k,l]:
                seen[b,k,l]=True; q.append((b,k,l))
                if path: par[(b,k,l)]=(a,i,j)
    return "NO",None
# body frame: origin = speaker centre, +x = cone side (toward grille wall), z up
SPK=R(-7.75,7.75,-15.25,15.25); FR=R(1.55,7.75,-17.45,17.45); EAR=R(-1.5,1.5,-5,5)
if __name__=="__main__":
    goal=(79.0-7.75,163.0)   # frame top (z+17.45) at 181.2
    for mg in (2,):
        for nh in (0,9,12,15,18):
            parts=[([SPK,FR],dil(notch(mM,143+nh),mg)),([FR,EAR],dil(mU,mg))]
            print(f"clearance {mg*0.25} mm, notch {nh} mm tall:",feasible(parts,goal)[0])
