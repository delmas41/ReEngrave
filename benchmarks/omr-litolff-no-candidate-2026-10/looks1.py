import json
spec=json.load(open("spec1.json"))
# my look, round 1 (60 tiles, not blind: I knew the mechanical stratum). codes:
# stem = stem tip/piece; rest = a rest (8th/quarter/16th) boxed as an accidental; dyn = dynamic/text letter piece; bar = barline/bar-edge sliver;
# frag = tiny ink fragment/empty-looking box; clef = clef/key piece; nat/flat/sharp = a real accidental of that kind; merged = box over several glyphs (acc + head + slur/stem), unclear = cannot tell
L={"offbig":"rest merged unclear merged rest flat? rest rest rest","shortoff":"stem stem stem stem frag frag stem stem stem",
"shortleft":"stem stem stem stem frag stem stem bar stem","anchor":"frag nat nat nat nat nat nat nat nat",
"left":"unclear rest stem rest stem frag nat nat nat","nohead":"nat merged nat bar nat nat bar dyn nat","huge":"merged rest merged merged merged bar",
"mid":"stem flat rest nat nat nat"}
out={}
for n,s in L.items():
    for k,l in zip(spec[n],s.split()): out[k]=l
json.dump(out,open("looks1.json","w"),indent=0); print(len(out))
