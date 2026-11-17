"""For every rest-only red bar (my crop look), re-cut its page and find the whole-rest-shaped ink piece: its measures, whether the search's shape test passes,
and which detector boxes (facts) sit on it.   blobprobe.py PLATE OUT.json"""
import json, sys, collections
sys.path.insert(0, ".")
sys.path.insert(0, "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad")
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import rhythm as RH
from tools.omr.staged.lane_report import LIB, PLATES
from restonly_lists import LIT, BRA

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/"
plate, out = sys.argv[1], sys.argv[2]
SEL = LIT if plate == "litolff" else BRA
tag = "lit-a" if plate == "litolff" else "bra-a"
extra = json.load(open(S + "2311/%s.extra.json" % tag))
f = json.load(open(S + "2311/%s.facts.json" % tag))
bars = [(st, b) for st, s in SEL.items() for b in s.split()]
bypage = collections.defaultdict(list)
for st, b in bars:
    bypage[int(b.split("/")[0])].append((st, b))
res = {}
for page, items in sorted(bypage.items()):
    pws, cells = prepare_pages(str(LIB / PLATES[plate]["pdf"]), [page], dpi=600)[0]
    for st, b in items:
        box = extra["cell_box"][b]
        best = min(((sum(abs(a - c) for a, c in zip(getattr(cl, "bbox_page_px", (1e9,) * 4), box)), cl) for cl in cells), key=lambda t: t[0])[1]
        c = best
        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        grid = G._cell_grid(c)
        comps = G._ink_components(c) or []
        up = c.upscale_factor
        cb = c.bbox_page_px
        r = dict(stratum=st, blobs=[], boxes=[])
        if grid and len(lines) >= 5:
            half = grid[1]
            sp = half * 2
            bottom = lines[-1]
            W = c.image_no_staff.shape[1]
            for (x, y, w, h, area) in comps:
                hs, ws = h / sp, w / sp
                step = (bottom - (y + h / 2.0)) / half
                if abs(step - RH.WHOLE_REST_STEP) <= 1.5 and 0.3 <= hs <= 1.3 and 0.8 <= ws <= 2.6:
                    asp = ws / hs
                    pb = [cb[0] + x / up, cb[1] + y / up, cb[0] + (x + w) / up, cb[1] + (y + h) / up]
                    r["blobs"].append(dict(h_sp=round(hs, 3), w_sp=round(ws, 3), aspect=round(asp, 3), step=round(step, 3), xc=round((x + w / 2) / W, 3),
                                           shaped=bool(RH._rest_shaped(hs, asp)), page_box=[round(v, 1) for v in pb], area_fill=round(area / (w * h), 3)))
        pre = "glyph/%s/" % b
        for k, g in f["glyphs"].items():
            if k.startswith(pre) and g.get("cls") not in ("staff", "ledgerLine", None) and not g["cls"].startswith(("beam", "tie", "slur", "dynamic", "accidental", "key", "clef", "brace", "time", "artic", "arpeg", "aug", "flag")):
                r["boxes"].append(dict(k=k.split("/")[-1], cls=g["cls"], fate=g["fate"], box=[round(v, 1) for v in g["box"]]))
        res[b] = r
        print(b, st, [(x["h_sp"], x["w_sp"], x["aspect"], x["shaped"]) for x in r["blobs"]], [(x["cls"], x["fate"]) for x in r["boxes"]], flush=True)
    json.dump(res, open(out, "w"))
json.dump(res, open(out, "w"))
