import json,sys,collections
exec(open("n5_sub.py").read().split('if __name__')[0])
B=json.load(open(sys.argv[1]))["boxes"]; L=json.load(open(sys.argv[2])); T=json.load(open(sys.argv[3]))
NA={"stem","rest","frag","bar","dyn","clef"}
tab=collections.defaultdict(list)
for b in B:
    l=L[b["key"]]; tw=any(x["owner"] and x["owner"][0]=="decided" for x in T[b["key"]])
    if tw: bk=("0 duplicate: same ink written via a neighbouring cell's box",)
    elif l in NA: bk=("1 not an accidental",l)
    elif l in ("merged","unclear"): bk=("4 merged / cannot tell",sub(b))
    else: bk=("2/3 real accidental"+(" (box is a cropped piece)" if "crop" in l else ""),sub(b))
    tab[bk].append(b["key"])
tot=collections.Counter()
for k,v in sorted(tab.items()): print(len(v),k); tot[k[0]]+=len(v)
print(dict(tot))
json.dump({"|".join(k):v for k,v in tab.items()},open("final_s8.json","w"))
