import json
spec=json.load(open("spec2.json"))
L={"r0":"rest merged frag nat nat frag bar stem rest stem rest rest",
"r1":"bar nat nat flat rest merged nat nat rest rest stem nat",
"r2":"nat flat flat stem flatcrop nat stem natcrop rest rest rest rest",
"r3":"frag stem bar stem stem flatcrop stem stem stem nat clef stem",
"r4":"merged natcrop frag nat nat stem stem natcrop rest frag nat nat",
"r5":"stem stem stem nat merged stem frag rest stem stem nat bar",
"r6":"merged sharpcrop sharp nat frag rest sharpcrop nat stem dyn natcrop stem",
"r7":"unclear rest stem dyn stem flatcrop rest nat sharp flatcrop stem rest",
"r8":"nat stem flatcrop frag stem stem"}
out=json.load(open("looks1.json"))
for n,s in L.items():
    toks=s.split(); assert len(toks)==len(spec[n]),(n,len(toks),len(spec[n]))
    for k,l in zip(spec[n],toks): out[k]=l
json.dump(out,open("looks_all.json","w"),indent=0)
import collections; print(len(out), collections.Counter(out.values()))
