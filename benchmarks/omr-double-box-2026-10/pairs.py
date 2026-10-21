"""2.185: every pair of detector boxes that overlap on the PAGE (same page), from an extract.py file.
usage: pairs.py EXTRACT.json OUT.json   -> list of pairs {a,b,iou,cont,same_cell,...} for IoU>0 (staff/brace boxes excluded: they span the system)."""
import json, sys, collections, re
d = json.load(open(sys.argv[1]))
SKIP = {"staff", "brace"}
bx = [b for b in d["boxes"] if b["bbox"] and b["cls"] not in SKIP]
byp = collections.defaultdict(list)
for i, b in enumerate(bx):
    byp[int(b["subject"].split("/")[1])].append(i)
def cell(s): return "/".join(s.split("/")[:5])
pairs = []
for p, idx in byp.items():
    idx.sort(key=lambda i: bx[i]["bbox"][0])
    for ai in range(len(idx)):
        a = bx[idx[ai]]; A = a["bbox"]
        for bi in range(ai + 1, len(idx)):
            b = bx[idx[bi]]; B = b["bbox"]
            if B[0] >= A[2]: break
            iw = min(A[2], B[2]) - max(A[0], B[0]); ih = min(A[3], B[3]) - max(A[1], B[1])
            if iw <= 0 or ih <= 0: continue
            inter = iw * ih; aa = (A[2]-A[0])*(A[3]-A[1]); bb = (B[2]-B[0])*(B[3]-B[1])
            iou = inter / (aa + bb - inter)
            pairs.append(dict(a=idx[ai], b=idx[bi], iou=round(iou, 4), cont=round(inter / min(aa, bb), 4),
                              same_cell=cell(a["subject"]) == cell(b["subject"])))
json.dump(dict(pairs=pairs, nbox=len(bx)), open(sys.argv[2], "w"))
print(len(bx), "boxes", len(pairs), "overlapping pairs")
