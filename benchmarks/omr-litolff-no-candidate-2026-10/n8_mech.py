import json,sys,collections
exec(open("n5_sub.py").read().split('if __name__')[0])
B=json.load(open(sys.argv[1]))["boxes"]; T=json.load(open(sys.argv[2]))
def mech(b):
    h,w=b["h_sp"],b["w_sp"]
    if w<0.45 and h>=1.6: return "thin-tall (barline/letter-like)"
    if h<1.6: return "short <1.6 sp"
    if h>4.6 or w>2.2: return "huge (merged)"
    if b["cls"]=="accidentalDoubleSharp": return "doublesharp class, normal size"
    return "normal size, flat/natural/sharp class"
c=collections.Counter(); c2=collections.Counter(); c3=collections.defaultdict(collections.Counter)
for b in B:
    tw=any(x["owner"] and x["owner"][0]=="decided" for x in T[b["key"]])
    m="twin decided" if tw else mech(b)
    c[m]+=1
    if m=="normal size, flat/natural/sharp class": c3[m][sub(b)]+=1
    if m=="short <1.6 sp": c3[m][b["cls"]]+=1
    c2[b["cls"]]+=1
print(len(B),dict(c)); print(dict(c2))
for k,v in c3.items(): print(k,dict(v))
print("absorbed",sum(b["absorbed"] for b in B))
