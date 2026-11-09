"""2.275 (Sean 2026-11-08: 'isn't all of this ink already claimed in the page read first?'): for every distinct ink NOT in the file (the
representative box of each p3b cluster) say what claim already holds its ink, whether that claim stood before the box, and which rule
refused the box first. READ-ONLY, no row filed.

Sources, all in the record: `Q.CLAIMED_AREA` (the register: barline / bracket / leading_column / clef / key_signature / meter / word / arc / hairpin,
page-px rectangles, filed by GATHER with a low obs id), `Q.STROKE_OWNER` (ADJUDICATE's per-cell verdict: owner family of every stroke), `Q.GLYPH_STROKES`
(the strokes the box stands on, with shares), `Q.STEM_SLASH` (the tremolo reader's per-stem rows), the first refusal = the p3b bucket.

usage: claims_probe.py PLATE RECORD INK.json PART.rows.jsonl OUT.json [SUBJECTS_JSON]
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import expand_result   # noqa: E402
from tools.omr.staged.export import Record              # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

plate, recp, inkp, rowsp, outp = sys.argv[1:6]
extra = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else None

# slim load (drops the two bulky id-list fields no reader here consults)
def _hook(o):
    if "quantity" in o and "outcome" in o:
        o.pop("considered", None)
        o.pop("correlated", None)
    return o


rec = Record(expand_result(json.loads(Path(recp).read_text(), object_hook=_hook)))
ink = json.load(open(inkp))
rows = {r["sub"]: r for r in (json.loads(l) for l in open(rowsp))}


def num(i):
    return int(i.split(":")[1])


# ---- register area claims, by page
areas = collections.defaultdict(list)   # page -> [(owner, box, id)]
for o in rec.obs_of(Q.CLAIMED_AREA):
    d = o.get("detail") or {}
    v = o.get("value")
    if not (isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)):
        continue   # arc / hairpin `unit: ink` rows carry [[cell, ordinal]] ids, not a rectangle
    pg = o["subject"].split("/")[1]
    areas[pg].append((d.get("owner"), [float(x) for x in v], num(o["id"]), d.get("unit"), d.get("standing")))
ARE_ORDER = ["barline", "bracket", "leading_column", "clef", "key_signature", "meter", "word", "hairpin", "arc"]

# ---- stroke owner verdicts per cell, glyph strokes per box, box ids
so = {}
for v in rec.verdicts_of(Q.STROKE_OWNER):
    so[v["subject"]] = v
gbox_id = {o["subject"]: num(o["id"]) for o in rec.obs_of(Q.GLYPH_BOX)}
gstr = {}
for o in rec.obs_of(Q.GLYPH_STROKES):
    gstr[o["subject"]] = o
# tremolo reader rows: Q.STEM_SLASH value>0 per stem row
slash = collections.defaultdict(list)
for o in rec.obs_of(Q.STEM_SLASH):
    if (o.get("value") or 0) > 0:
        p = o["subject"].split("/")
        slash[tuple(p[1:5]) if p[0] == "cell" else tuple(p[1:5])].append(o)
nowner = rec.verdicts_of(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
nv = {v["subject"]: v for v in nowner}


def overlap_share(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy / max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))


def analyse(sub):
    r = rows[sub]
    bb = r["bbox"]
    p = sub.split("/")
    out = {"sub": sub, "bucket": r["bucket"], "fate": r["fate"], "cls": r["cls"], "bbox": bb}
    held = {}
    for owner, box, aid, unit, standing in areas[p[1]]:
        s = overlap_share(bb, box)
        if s >= 0.5:
            held.setdefault(owner, []).append((round(s, 2), aid, unit, standing))
    out["area"] = {k: v[0] for k, v in held.items()}
    ak = next((k for k in ARE_ORDER if k in held), None)
    out["area_kind"] = ak
    out["area_before_box"] = (min(a[1] for k in held for a in held[k]) < gbox_id.get(sub, 10 ** 12)) if held else None
    # stroke owner family of the strokes under the box (largest share), from the cell verdict
    g = gstr.get(sub)
    fam, share = None, 0.0
    sh = []
    if g:
        d = g.get("detail") or {}
        sh = [(int(a), float(b)) for a, b in zip(g.get("value") or [], d.get("shares") or [])] \
            + [(int(a), float(b)) for a, b in (d.get("partial") or [])]
    v = so.get("cell/" + "/".join(p[1:5]))
    out["stroke_families"] = []
    if v and sh:
        st = (v.get("detail") or {}).get("strokes") or {}
        for ordn, shr in sorted(sh, key=lambda t: -t[1]):
            e = st.get(str(ordn))
            if e:
                out["stroke_families"].append([e[1], e[0], round(shr, 2)])
        if out["stroke_families"]:
            fam, share = out["stroke_families"][0][0], out["stroke_families"][0][2]
    out["stroke_family"] = fam
    out["stroke_family_share"] = share
    # tremolo: a slash read on a stem of this cell
    out["slash_rows_in_cell"] = len(slash.get(tuple(p[1:5]), ()))
    # the first refusal (ADJUDICATE notehead verdict) and the verdict's id vs the register's
    nvd = nv.get(sub)
    out["refusal_reason"] = nvd.get("reason") if nvd else None
    return out


if extra:
    subs = list(extra)
else:
    subs = [s for b in ink["members"] for s in ink["members"][b]]
res = [analyse(s) for s in subs]
json.dump(res, open(outp, "w"))
print(plate, "analysed", len(res))
print("area owners seen (rows)", {k: sum(1 for p in areas.values() for a in p if a[0] == k) for k in ARE_ORDER})
