from plan5 import *
import pickle
_,_,m2=pickle.load(open("/home/claude/build/entry_mid2.pkl","rb")); m2=m2[i0:]
BLK=R(1.55,8.25,-8,8); mg=2
for name,polys,gx in (("bare speaker",[SPK],79.0-7.75),("speaker + ear blocks (0.5 mm proud)",[SPK,BLK],79.0-8.25)):
    for nh in (0,6,9,12,15,18,22):
        r=feasible([(polys,dil(notch(m2,143+nh),mg))],(gx,165.0))[0]; print(f"{name}: notch {nh} mm tall, 0.5 mm clearance -> {r}")
        if r=="OK": break
# exact geometry, zero clearance, no notch:
print("zero clearance, no notch, bare speaker:",feasible([([SPK],m2)],(79.5-7.75,165.0))[0])
