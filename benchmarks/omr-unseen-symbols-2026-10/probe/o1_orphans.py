"""ROADMAP 2.179 -- how many red-bar sub-floor boxes stand at the end of a stem that has no head (an ORPHAN stem)?

usage: python3 benchmarks/omr-unseen-symbols-2026-10/probe/o1_orphans.py RECORD CENSUS.json OUT.json
Reads the record's own CV stems (`Q.STEM`, cell canonical frame) and every head-family glyph box (any reader); a stem is an
orphan when no head box's centre sits in the 2.55 rescue window (`gather.STEM_WITNESS_*`) of either end. Each census sub-floor
box (page px, converted to the cell's canonical frame through the cell's own glyph boxes) is then tested against the orphan ends.
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

rec = load_record(sys.argv[1])["record"]
census = json.load(open(sys.argv[2]))
stems, heads, aff, sp = collections.defaultdict(list), collections.defaultdict(list), {}, {}
for o in rec["observations"]:
    q, s = o["quantity"], o["subject"]
    if q == "stem" and s.startswith("cell/"):
        stems[s[5:]].append(o["value"])
    elif q == "cell_staff_space" and s.startswith("cell/"):
        sp[s[5:]] = float(o["value"])
    elif q == "glyph_box" and s.startswith("glyph/"):
        ck = "/".join(s.split("/")[1:5])
        v, d = o["value"], o.get("detail") or {}
        if str(v[0]).startswith("notehead"):
            heads[ck].append((v[1] + v[3] / 2.0, v[2] + v[4] / 2.0))
        pb = d.get("bbox_page_px")
        if ck not in aff and isinstance(pb, list) and v[3] > 0 and pb[2] > pb[0]:
            k = v[3] / (pb[2] - pb[0])
            aff[ck] = (k, v[1] - pb[0] * k, v[2] - pb[1] * k)
out, tot = [], collections.Counter()
for i, e in enumerate(census):
    ck = e["bar"]
    space = sp.get(ck)
    if not space or ck not in aff:
        continue
    k, ox, oy = aff[ck]
    dx = G.STEM_WITNESS_HALF_WIDTH_SPACES * space
    dy = G.STEM_WITNESS_HALF_HEIGHT_SPACES * space
    orph = []
    for (x, y, w, h) in stems.get(ck, []):
        xc = x + w / 2.0
        ends = (y, y + h)
        if any(abs(hx - xc) <= dx and any(abs(hy - ey) <= dy for ey in ends) for hx, hy in heads.get(ck, [])):
            continue
        orph.append((xc, ends))
    hits = []
    for sb in e["subfloor"]:
        b = sb["box"]
        cx = ((b[0] + b[2]) / 2.0) * k + ox
        cy = ((b[1] + b[3]) / 2.0) * k + oy
        for xc, ends in orph:
            if abs(cx - xc) <= dx and any(abs(cy - ey) <= dy for ey in ends):
                hits.append(dict(sb))
                break
    tot["bars"] += 1
    tot["orphan_stems"] += len(orph)
    tot["bars_with_orphan"] += bool(orph)
    tot["hits"] += len(hits)
    tot["hits_head"] += sum(1 for h in hits if h["cls"].startswith("notehead"))
    tot["hits_rest"] += sum(1 for h in hits if h["cls"].startswith("rest"))
    tot["bars_with_hit"] += bool(hits)
    out.append(dict(i=i, bar=ck, orphans=len(orph), hits=hits))
json.dump(out, open(sys.argv[3], "w"), indent=0)
print(dict(tot))
