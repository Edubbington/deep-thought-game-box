import json, os, math
from PIL import Image, ImageDraw, ImageFont
F=None
for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
    if os.path.exists(p): F=p; break
font=ImageFont.truetype(F,22) if F else ImageFont.load_default()
big=ImageFont.truetype(F,26) if F else font
YEL=(255,214,0); DK=(20,20,24)
os.makedirs("final",exist_ok=True)
names=["exploded","riser","riser_back","plate_top","plate_under","core","core_cut","head_front","head_back","head_in_right","head_in_left"]
for n in names:
    im=Image.open(n+".png").convert("RGBA"); W,H=im.size
    meta=json.load(open(n+".json")); labs=meta["labels"]
    # crop to content bbox + margin
    g=im.convert("L"); bg=g.getpixel((2,2))
    diff=g.point(lambda v: 255 if abs(v-bg)>6 else 0); bb=diff.getbbox() or (0,0,W,H)
    m=40; crop=(max(0,bb[0]-m),max(0,bb[1]-m),min(W,bb[2]+m),min(H,bb[3]+m))
    # leave side gutters for labels
    im=im.crop(crop); W,H=im.size; labs=[(t,(x-crop[0],y-crop[1])) for t,(x,y) in labs]
    tmp=ImageDraw.Draw(im)
    lw=[tmp.textlength(t,font=font) for t,(x,y) in labs if x<W/2]; rw=[tmp.textlength(t,font=font) for t,(x,y) in labs if x>=W/2]
    pad=int(max(lw,default=0))+70; padR=int(max(rw,default=0))+70
    canvas=Image.new("RGBA",(W+pad+padR,H+80),(46,46,52,255)); canvas.paste(im,(pad,40)); im=canvas
    d=ImageDraw.Draw(im)
    L=[(t,(x+pad,y+40)) for t,(x,y) in labs]
    left=sorted([l for l in L if l[1][0]<W/2+pad],key=lambda l:l[1][1]); right=sorted([l for l in L if l[1][0]>=W/2+pad],key=lambda l:l[1][1])
    def layout(items,side):
        ys=[]; last=-1e9
        for t,(x,y) in items:
            yy=max(y,last+38); ys.append(yy); last=yy
        # shift up if overflow
        if ys and ys[-1]>im.size[1]-30:
            sh=ys[-1]-(im.size[1]-30); ys=[y-sh for y in ys]
        for (t,(x,y)),yy in zip(items,ys):
            tw=d.textlength(t,font=font)
            if side=="L": tx=pad-30-tw; ex=pad-20
            else: tx=pad+W+30; ex=pad+W+20
            d.line([(ex,yy),(x,y)],fill=YEL,width=3); d.ellipse([x-6,y-6,x+6,y+6],fill=YEL,outline=DK,width=2)
            d.rectangle([tx-8,yy-16,tx+tw+8,yy+16],fill=(30,30,34,230),outline=YEL,width=2)
            d.text((tx,yy-13),t,font=font,fill=(255,255,255))
    layout(left,"L"); layout(right,"R")
    im.convert("RGB").save("final/"+n+".jpg",quality=88)
    print(n, im.size)
# bed shots + assembled: just crop
for n in ["bed_Riser","bed_BasePlate","bed_Core","bed_Head","assembled"]:
    im=Image.open(n+".png").convert("RGB"); g=im.convert("L"); bg=g.getpixel((2,2))
    bb=g.point(lambda v:255 if abs(v-bg)>6 else 0).getbbox(); m=40
    im=im.crop((max(0,bb[0]-m),max(0,bb[1]-m),min(im.size[0],bb[2]+m),min(im.size[1],bb[3]+m)))
    im.save("final/"+n+".jpg",quality=88); print(n,im.size)
