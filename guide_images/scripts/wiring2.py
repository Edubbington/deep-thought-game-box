from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f=ImageFont.truetype(F,20); fb=ImageFont.truetype(FB,22); fs=ImageFont.truetype(F,16); ft=ImageFont.truetype(FB,30)
W,H=1560,1260; im=Image.new("RGB",(W,H),(250,250,247)); d=ImageDraw.Draw(im)
d.text((40,25),"Deep Thought — header wiring (Pi 2, 40-pin, viewed from above, SD card slot at top)",font=ft,fill=(20,20,20))
# header: 2 columns x 20 rows. odd pins = inner column (left here), even = outer (right)
names={1:"3V3",2:"5V",3:"GPIO2",4:"5V",5:"GPIO3",6:"GND",7:"GPIO4",8:"TXD",9:"GND",10:"RXD",11:"GPIO17",12:"GPIO18",13:"GPIO27",14:"GND",15:"GPIO22",16:"GPIO23",17:"3V3",18:"GPIO24",19:"GPIO10",20:"GND",21:"GPIO9",22:"GPIO25",23:"GPIO11",24:"GPIO8",25:"GND",26:"GPIO7",27:"ID_SD",28:"ID_SC",29:"GPIO5",30:"GND",31:"GPIO6",32:"GPIO12",33:"GPIO13",34:"GND",35:"GPIO19",36:"GPIO16",37:"GPIO26",38:"GPIO20",39:"GND",40:"GPIO21"}
# connections: pin -> (device, role, color)
DISP=(70,130,220); AMP=(230,120,30); RING=(150,60,200); BTN=(40,160,90); PWR=(200,40,40); GND=(60,60,60)
conn={2:("5 V splice","ring 5 V + button LED +",RING),4:("Amp","VIN 5 V",AMP),9:("Amp","GND",AMP),12:("Amp","BCLK",AMP),35:("Amp","LRC",AMP),40:("Amp","DIN",AMP),
19:("LED ring","DIN (data in)",RING),14:("LED ring","GND",RING),
11:("Button","switch lead",BTN),20:("Button","other switch lead (GND)",BTN),25:("Button LED","– (GND)",BTN)}
danger={1,17}
x0,y0=640,110; pitch=46; cw=140
d.rounded_rectangle([x0-150,y0-30,x0+cw+30+180,y0+20*pitch+10],radius=14,fill=(35,80,45),outline=(20,50,30),width=3)
for i in range(20):
    for col,pin in ((0,2*i+1),(1,2*i+2)):
        cx=x0+col*cw+30; cy=y0+i*pitch
        fill=(240,220,60) if pin in conn else ((220,60,60) if pin in danger else (200,200,200))
        d.rectangle([cx-13,cy-13,cx+13,cy+13],fill=fill,outline=(10,10,10),width=2)
        d.text((cx-6 if pin<10 else -11+cx,cy-9),str(pin),font=fs,fill=(0,0,0))
# left labels for odd pins, right for even
for pin,(dev,role,colr) in sorted(conn.items()):
    i=(pin-1)//2; col=(pin-1)%2; cx=x0+col*cw+30; cy=y0+i*pitch
    txt=f"{dev} — {role}"
    if col==0:
        tx=x0-150-40; d.line([(tx,cy),(cx-16,cy)],fill=colr,width=4); tw=d.textlength(txt,font=f)
        d.rounded_rectangle([tx-tw-20,cy-16,tx-4,cy+16],radius=6,fill=colr); d.text((tx-tw-12,cy-12),txt,font=f,fill="white")
    else:
        tx=x0+cw+30+180+40; d.line([(cx+16,cy),(tx,cy)],fill=colr,width=4); tw=d.textlength(txt,font=f)
        d.rounded_rectangle([tx+4,cy-16,tx+tw+20,cy+16],radius=6,fill=colr); d.text((tx+12,cy-12),txt,font=f,fill="white")
for i in range(20):
    for col,pin in ((0,2*i+1),(1,2*i+2)):
        cx=x0+col*cw+30; cy=y0+i*pitch; nm=names[pin]; tw=d.textlength(nm,font=fs)
        if col==0: bx=cx-28-tw
        else: bx=cx+28
        d.rectangle([bx-5,cy-11,bx+tw+5,cy+11],fill=(35,80,45)); d.text((bx,cy-9),nm,font=fs,fill=(235,235,235))
# legend / notes
ly=y0+20*pitch+50
notes=[("Yellow pins are used. RED pins (1, 17) are 3.3 V — never put a 5 V lead on them.",(200,40,40)),
("Display: ribbon to the Pi's DISPLAY socket only. It is powered through the ribbon; no header pins.",DISP),
("5 V splice: one lead on pin 2, joined to the ring's 5 V lead and the button's LED + lead.",RING),
("Wi-Fi nano and USB mic → any USB port.   Power → micro-USB power socket via the panel-mount extension.",(20,20,20))]
for t,c in notes:
    d.ellipse([40,ly+6,56,ly+22],fill=c); d.text((70,ly),t,font=f,fill=(20,20,20)); ly+=34
im.save("final/wiring2.jpg",quality=92); print(im.size)
