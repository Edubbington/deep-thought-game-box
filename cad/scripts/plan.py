import numpy as np, pickle, math, sys
from collections import deque
xs,zs,mask=pickle.load(open("/home/claude/build/entry.pkl","rb"))
# downsample to 0.5 mm, region x 30..84, z 98..184
st=2; m=mask[::st,::st]; X=xs[::st]; Z=zs[::st]
i0=np.searchsorted(X,30); m=m[i0:]; X=X[i0:]
# safety margin 0.25mm: dilate obstacle by one cell (0.5) in 4-neighbourhood? use the 0.25 grid: dilate fine mask by 1 cell then downsample
f=mask.copy(); f[1:]|=mask[:-1]; f[:-1]|=mask[1:]; f[:,1:]|=mask[:,:-1]; f[:,:-1]|=mask[:,1:]
m=f[::st,::st][i0:]
NX,NZ=m.shape; res=0.5
def shape_pts(poly,step=0.5):
    pts=[]
    for (ax,az),(bx,bz) in zip(poly,poly[1:]+poly[:1]):
        L=math.hypot(bx-ax,bz-az); n=max(1,int(L/step))
        for k in range(n): pts.append((ax+(bx-ax)*k/n,az+(bz-az)*k/n))
    return pts
def feasible(poly,goal,angs=range(-90,91,3),verbose=False):
    # poly: points relative to the reference point, at theta=0 (x toward grille wall, z up)
    pts=shape_pts(poly); A=list(angs); C=np.zeros((len(A),NX,NZ),bool)
    for a,th in enumerate(A):
        c,s=math.cos(math.radians(th)),math.sin(math.radians(th)); col=np.zeros((NX,NZ),bool)
        offs=set((int(round((px*c-pz*s)/res)),int(round((px*s+pz*c)/res))) for px,pz in pts)
        for dx,dz in offs:
            # reference at (i,j) collides if m[i+dx,j+dz]
            src=np.zeros((NX,NZ),bool)
            xa,xb=max(0,-dx),min(NX,NX-dx); za,zb=max(0,-dz),min(NZ,NZ-dz)
            src[xa:xb,za:zb]=m[xa+dx:xb+dx,za+dz:zb+dz]; col|=src
        C[a]=col
    gi=int(round((goal[0]-X[0])/res)); gj=int(round((goal[1]-Z[0])/res)); ga=A.index(0)
    if C[ga,gi,gj]: return "goal blocked"
    si=int(round((42-X[0])/res)); sj=int(round((120-Z[0])/res))
    seen=np.zeros_like(C); q=deque()
    q.append((ga,gi,gj)); seen[ga,gi,gj]=True   # search backwards from the goal
    while q:
        a,i,j=q.popleft()
        if i==si and j==sj: return "OK"
        for da,di,dj in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            b,k,l=a+da,i+di,j+dj
            if 0<=b<len(A) and 0<=k<NX and 0<=l<NZ and not seen[b,k,l] and not C[b,k,l]: seen[b,k,l]=True; q.append((b,k,l))
    return "NO"
def rect(t,h): return [(-t/2,-h/2),(t/2,-h/2),(t/2,h/2),(-t/2,h/2)]
if __name__=="__main__":
    for t,h in ((16.9,31.25),(15.5,30.5),(15.5,31.25),(15.0,30.5),(14.0,30.5),(15.5,25),(15.5,20),(12,30.5),(10,30.5)):
        # final: against the grille wall (x=79.7 face), top at 181.45
        print(t,h,feasible(rect(t,h),(79.7-t/2,181.45-h/2)))
