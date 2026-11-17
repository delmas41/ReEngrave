import json,random,collections,sys
S=sys.argv[1]
d=json.load(open(S+"/census315.json"))
rng=random.Random(2315)
out={}
for plate,bars in d.items():
    bars.sort(key=lambda b:(b["page"],b["system"],b["staff"],b["cell"]))
    A=[b for b in bars if b["comp"] in("rest_boxes_only","rest+refused_other")]
    B=[b for b in bars if b["comp"] in("no_box","refused_other_only")]
    need=max(0,60-len(A))
    pickB=rng.sample(B,min(need,len(B)))
    pickB.sort(key=lambda b:(b["page"],b["system"],b["staff"],b["cell"]))
    out[plate]=dict(A=A,B=B,looked=A+pickB,nB=len(B),nBlook=len(pickB))
    print(plate,len(A),len(B),len(pickB))
json.dump(out,open(S+"/looked315.json","w"),default=str)
