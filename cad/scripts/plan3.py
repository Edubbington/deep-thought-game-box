import numpy as np, pickle, math
from collections import deque
xs,zs,mask=pickle.load(open("/home/claude/build/entry.pkl","rb"))
i0=np.searchsorted(xs,34); m=mask[i0:]; X=xs[i0:]; Z=zs; NX,NZ=m.shape; res=0.25
def pts_of(poly,step=0.25):
    out=[]
    for (ax,az),(bx,bz) in zip(poly,poly[1:]+poly[:1]):
        L=math.hypot(bx-ax,bz-az); n=max(1,int(L/step))
        out+= [(ax+(bx-ax)*k/n,az+(bz-az)*k/n) for k in range(n)]
    return out
def feasible(poly,goal,astep=1.0,amax=75,want_path=False):
    P=pts_of(poly); A=[a*astep for a in range(int(-amax/astep),int(amax/astep)+1)]; C=np.zeros((len(A),NX,NZ),bool)
    for a,th in enumerate(A):
        c,s=math.cos(math.radians(th)),math.sin(math.radians(th))
        for dx,dz in set((int(round((px*c-pz*s)/res)),int(round((px*s+pz*c)/res))) for px,pz in P):
            xa,xb=max(0,-dx),min(NX,NX-dx); za,zb=max(0,-dz),min(NZ,NZ-dz)
            C[a,xa:xb,za:zb]|=m[xa+dx:xb+dx,za+dz:zb+dz]
    gi=int(round((goal[0]-X[0])/res)); gj=int(round((goal[1]-Z[0])/res)); ga=A.index(0)
    if C[ga,gi,gj]: return "goal blocked",None
    si=int(round((44-X[0])/res)); sj=int(round((122-Z[0])/res))
    par={} ; seen=np.zeros_like(C); q=deque([(ga,gi,gj)]); seen[ga,gi,gj]=True
    while q:
        a,i,j=q.popleft()
        if i==si and j==sj:
            path=[(A[a],X[i],Z[j])]
            while (a,i,j) in par: a,i,j=par[(a,i,j)]; path.append((A[a],X[i],Z[j]))
            return "OK",path
        for da,di,dj in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            b,k,l=a+da,i+di,j+dj
            if 0<=b<len(A) and 0<=k<NX and 0<=l<NZ and not seen[b,k,l] and not C[b,k,l]:
                seen[b,k,l]=True; q.append((b,k,l))
                if want_path: par[(b,k,l)]=(a,i,j)
    return "NO",None
def rect(t,h): return [(-t/2,-h/2),(t/2,-h/2),(t/2,h/2),(-t/2,h/2)]
if __name__=="__main__":
    print("exact geometry, no safety margin, 0.25 mm / 1 deg:")
    for t,h in ((15.5,30.5),(15.5,28.5),(15.0,30.5),(14.5,30.5),(14.0,30.5),(13.0,30.5)):
        print(" rect",t,"x",h,":",feasible(rect(t,h),(79.5-t/2,165.5))[0])
