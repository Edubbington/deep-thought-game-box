from plan5 import *
goal=(79.0-7.75,163.0); mg=2
tests={
 "speaker alone, notch 15":[([SPK],dil(notch(mM,158),mg))],
 "speaker + bars, notch 15":[([SPK,FR],dil(notch(mM,158),mg))],
 "speaker + bars, notch 22":[([SPK,FR],dil(notch(mM,165),mg))],
 "end section (frame+ear), no notch":[([FR,EAR],dil(mU,mg))],
 "end section frame only, no notch":[([FR],dil(mU,mg))],
 "speaker + side-only frame (no top/bottom bars), notch 15 + ends":[([SPK],dil(notch(mM,158),mg)),([R(1.55,7.75,-15.25,15.25),EAR],dil(mU,mg))],
}
for k,v in tests.items(): print(k,":",feasible(v,goal)[0])
