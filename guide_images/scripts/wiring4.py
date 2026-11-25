from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f=ImageFont.truetype(F,20); fb=ImageFont.truetype(FB,22); fs=ImageFont.truetype(F,16); ft=ImageFont.truetype(FB,30)
W,H=1640,1440; im=Image.new("RGB",(W,H),(250,250,247)); d=ImageDraw.Draw(im)
d.text((40,25),"Deep Thought — header wiring (Pi 2, 40-pin, viewed from above, SD card slot at top)",font=ft,fill=(20,20,20))
# header: 2 columns x 20 rows. odd pins = inner column (left here), even = outer (right)
names={1:"3V3",2:"5V",3:"GPIO2",4:"5V",5:"GPIO3",6:"GND",7:"GPIO4",8:"TXD",9:"GND",10:"RXD",11:"GPIO17",12:"GPIO18",13:"GPIO27",14:"GND",15:"GPIO22",16:"GPIO23",17:"3V3",18:"GPIO24",19:"GPIO10",20:"GND",21:"GPIO9",22:"GPIO25",23:"GPIO11",24:"GPIO8",25:"GND",26:"GPIO7",27:"ID_SD",28:"ID_SC",29:"GPIO5",30:"GND",31:"GPIO6",32:"GPIO12",33:"GPIO13",34:"GND",35:"GPIO19",36:"GPIO16",37:"GPIO26",38:"GPIO20",39:"GND",40:"GPIO21"}
# connections: pin -> (device, role, color)
DISP=(70,130,220); AMP=(230,120,30); RING=(150,60,200); BTN=(40,160,90); PWR=(200,40,40); GND=(60,60,60)
RED=(210,40,40); GRN=(25,140,75); GRY=(135,135,140); BLK=(30,30,30); BLU=(50,100,210); YEL=(235,200,30)
conn={2:("RED","from the 5 V splice",RED),11:("GREEN","button switch",GRN),20:("GREEN","button switch (the other one)",GRN),25:("GREY","button LED –",GRY),
19:("GREEN","LED ring data (comes from the ring)",GRN),14:("BLACK","LED ring GND",BLK),
9:("BLACK","amp cable, G",BLK),4:("RED","amp cable, V",RED),12:("BLUE","amp cable, BCL",BLU),35:("GREEN","amp cable, LRC",GRN),40:("YELLOW","amp cable, DIN",YEL)}
danger={1,17}
x0,y0=700,110; pitch=46; cw=140
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
        d.rounded_rectangle([tx-tw-20,cy-16,tx-4,cy+16],radius=6,fill=colr); d.text((tx-tw-12,cy-12),txt,font=f,fill="black" if colr==YEL else "white")
    else:
        tx=x0+cw+30+180+40; d.line([(cx+16,cy),(tx,cy)],fill=colr,width=4); tw=d.textlength(txt,font=f)
        d.rounded_rectangle([tx+4,cy-16,tx+tw+20,cy+16],radius=6,fill=colr); d.text((tx+12,cy-12),txt,font=f,fill="black" if colr==YEL else "white")
for i in range(20):
    for col,pin in ((0,2*i+1),(1,2*i+2)):
        cx=x0+col*cw+30; cy=y0+i*pitch; nm=names[pin]; tw=d.textlength(nm,font=fs)
        if col==0: bx=cx-28-tw
        else: bx=cx+28
        d.rectangle([bx-5,cy-11,bx+tw+5,cy+11],fill=(35,80,45)); d.text((bx,cy-9),nm,font=fs,fill=(235,235,235))
# legend / notes
ly=y0+20*pitch+40
d.text((40,ly),"Pin colours",font=fb,fill=(20,20,20)); ly+=36
for colr,t in (((240,220,60),"Yellow pin = a wire goes on this pin"),((220,60,60),"Red pin (1 and 17) = 3.3 V power. Leave empty. Never put a wire on these."),((200,200,200),"Grey pin = not used. Leave empty.")):
    d.rectangle([40,ly,66,ly+26],fill=colr,outline=(10,10,10),width=2); d.text((80,ly+1),t,font=f,fill=(20,20,20)); ly+=34
ly+=10; d.text((40,ly),"Labels",font=fb,fill=(20,20,20)); ly+=36
for t in ("Each label is the colour of the wire that goes on that pin.",
          "You have four greens. Two come from the button (pins 11 and 20, either way round), one comes from the LED ring (pin 19),",
          "and one is in the amp's five-wire cable (pin 35). Follow each back to where it starts, or tag them with tape, before plugging in.",
          "The two reds: the loose one from the splice goes on pin 2; the one in the amp's cable goes on pin 4.",
          "The two blacks: the one from the ring goes on pin 14; the one in the amp's cable goes on pin 9.",
          "Display: ribbon only.   Wi-Fi and mic: any USB port.   Power: micro-USB socket, via the panel-mount cable."):
    d.text((40,ly),t,font=f,fill=(20,20,20)); ly+=32
im.save("final/wiring4.jpg",quality=92); print(im.size)
