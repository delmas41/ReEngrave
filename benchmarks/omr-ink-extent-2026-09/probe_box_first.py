"""Does ink-extent vs box-extent disagreement sort ALREADY-ADJUDICATED failures?

Falsification test of docs/breakthrough-2026-09-18-the-unit-of-enquiry.md §7.
READ-ONLY. Refuses to report unless all three controls pass.

⚠️ THE TWO POPULATIONS USE OPPOSITE BOX CONVENTIONS IN ONE RECORD:
   `glyph_box.value`        = [name, x, y, w, h]     (w/h)
   `ink.detail.ink_bbox_canonical` = [x0, y0, x1, y1] (corners)
Read the same way, a notehead's width comes out NEGATIVE (-108 px). Control 3
asserts the ink convention against the row's own width_spaces/height_spaces.
"""
import sys, json, collections, statistics
sys.path.insert(0, "benchmarks/omr-ledger-extrapolation-2026-09")
from recordstream import stream_array

REC = ("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
       "beethoven5-p1-p4-ink-identity.record.json")
CROP = "benchmarks/omr-stem-crop-pass-2026-09"

adj = {r["id"]: r["verdict"]
       for r in json.load(open(f"{CROP}/ADJUDICATION-litolff.json"))["rows"]}
man = {t["id"]: t for t in
       json.load(open(f"{CROP}/out/crop-manifest-litolff.json"))["tiles"]}
truth = {man[i]["subject"]: v for i, v in adj.items()
         if man.get(i, {}).get("subject")}
man_cls = {man[i]["subject"]: man[i].get("cls") for i in adj if man.get(i, {}).get("subject")}

boxes, ink_by_cell, sp_by_cell, conv_err = {}, collections.defaultdict(list), {}, []
for row in stream_array(REC, "observations"):
    q = row.get("quantity"); sub = row.get("subject") or ""
    if q == "glyph_box":
        v = row.get("value") or []
        if len(v) == 5:                     # [name, x, y, w, h]
            boxes[sub] = (v[0], float(v[1]), float(v[2]),
                          float(v[1]) + float(v[3]), float(v[2]) + float(v[4]))
    elif q == "ink":
        d = row.get("detail") or {}
        bb = d.get("ink_bbox_canonical")
        sp = d.get("cell_staff_space_px")
        if bb and len(bb) == 4:
            cell = sub.rsplit("/", 1)[0]
            ink_by_cell[cell].append([float(x) for x in bb])   # corners
            if sp: sp_by_cell[cell] = float(sp)
            ws, hs = d.get("width_spaces"), d.get("height_spaces")
            if sp and ws:                   # CONTROL 3
                conv_err.append(abs(((bb[2]-bb[0]) / float(sp)) - float(ws)))

present  = [s for s in truth if s in boxes]
clsok    = [s for s in present if boxes[s][0] == man_cls.get(s)]
c3 = statistics.median(conv_err) if conv_err else 9.9
print(f"CONTROL 1  subject present: {len(present)} of {len(truth)}")
print(f"CONTROL 2  class matches manifest: {len(clsok)} of {len(present)}")
print(f"CONTROL 3  ink corners reproduce its own width_spaces: median err {c3:.4f} spaces (n={len(conv_err)})")
if c3 > 0.05:            sys.exit("REFUSED: ink box convention not confirmed")
if len(clsok) < 50:      sys.exit("REFUSED: too few usable rows")
nh = [w for s,(c,x0,y0,x1,y1) in boxes.items() if str(c).startswith("notehead")
      for w in [(x1-x0)]]
print(f"CONTROL 4  notehead box median width {statistics.median(nh):.0f} px "
      f"(~1.3-1.5 staff spaces at ~100 px/space)")

def shape_of(sub):
    cls, x0, y0, x1, y1 = boxes[sub]
    cell = sub.rsplit("/", 1)[0]
    bw, bh = x1-x0, y1-y0
    barea = max(bw*bh, 1.0)
    hits = []
    for bb in ink_by_cell.get(cell, []):
        ix = max(0.0, min(x1, bb[2]) - max(x0, bb[0]))
        iy = max(0.0, min(y1, bb[3]) - max(y0, bb[1]))
        if ix*iy > 0.10*barea: hits.append(bb)
    if not hits: return "NO_INK_UNDER_BOX", 0.0
    bb = max(hits, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))
    iw, ih = bb[2]-bb[0], bb[3]-bb[1]
    ratio = (iw*ih)/barea
    if len(hits) >= 4:                  return "SHATTERED", ratio
    if ratio >= 3.0 and ih > 2.5*bh:    return "MERGE_TALL", ratio
    if ratio >= 3.0:                    return "MERGE_WIDE", ratio
    if ratio >= 1.5:                    return "BOX_IS_A_SUBPART", ratio
    return "AGREES", ratio

tab, rat = collections.defaultdict(collections.Counter), collections.defaultdict(list)
for s in clsok:
    shp, r = shape_of(s); tab[truth[s]][shp] += 1; rat[truth[s]].append(r)

order = ["AGREES","BOX_IS_A_SUBPART","MERGE_WIDE","MERGE_TALL","SHATTERED","NO_INK_UNDER_BOX"]
print("\n=== ink extent vs box extent, BY PRINT VERDICT (Litolff, n=%d) ===" % len(clsok))
for v in sorted(tab, key=lambda k: -sum(tab[k].values())):
    tot = sum(tab[v].values()); med = statistics.median(rat[v])
    print(f"  {v:20s} n={tot:3d}  median ink/box area={med:6.2f}   " +
          "  ".join(f"{k}={tab[v][k]}" for k in order if tab[v][k]))
heads = tab["stem_printed_up"] + tab["stem_printed_down"]; junk = tab["not_a_notehead"]
def sh(c,k="AGREES"):
    t=sum(c.values()); return c[k]/t if t else float('nan')
print(f"\nCONFIRMED NOTEHEADS n={sum(heads.values()):3d}  AGREES={sh(heads):.3f}  median ratio={statistics.median(rat['stem_printed_up']+rat['stem_printed_down']):.2f}")
print(f"CONFIRMED NON-HEADS n={sum(junk.values()):3d}  AGREES={sh(junk):.3f}  median ratio={statistics.median(rat['not_a_notehead']):.2f}")
