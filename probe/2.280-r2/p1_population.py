"""2.280 probe 1 (STAGED, read-only): the population. Which KEPT heads (notehead_is_not_a_notehead decided 'notehead') have no
stem row, by duration fate, on the frozen sample pages of the 20261104-night record slices (no full record is loaded: low memory).

`no stem row` = the shipped adjudicate_head_stem rule: no Q.STEM row of the head's own cell touches the head's detector box
(geometry.stem_touches_head, zero tolerance). Same function, same box convention (stem_value._head_xywh).

usage: python3 probe/2.280/p1_population.py litolff|brahms OUT.json [TAG=20261104-night | m4b-sample]
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.geometry import stem_touches_head          # noqa: E402
from tools.omr.staged.adjudicators.stem_value import _head_xywh, _same_stem_row   # noqa: E402

TAG = sys.argv[3] if len(sys.argv) > 3 else "20261104-night"
SL = Path(__import__("os").environ["R2_REC"])
plate, out = sys.argv[1], sys.argv[2]
d = SL / plate

glyph = {}          # sub -> dict(box, name, cell, conf)
stems = collections.defaultdict(list)   # cell sub -> [(id, box)]
cellsp = {}
reach = {}
for l in open(d / "observations.jsonl"):
    o = json.loads(l)
    q = o["quantity"]
    if q == "glyph_box":
        glyph[o["subject"]] = dict(box=o["value"], conf=o["score"], page_box=o["detail"].get("bbox_page_px"),
                                   cat=o["detail"].get("category"), id=o["id"])
    elif q == "stem":
        stems[o["subject"]].append((o["id"], o["value"]))
    elif q == "cell_staff_space":
        cellsp[o["subject"]] = o["value"]
    elif q == "head_stem_reach":
        reach[o["subject"]] = dict(dir=o["value"], **{k: o["detail"].get(k) for k in ("up_ext", "down_ext", "up_tip_y", "down_tip_y", "sp", "head_box_page")})

kept, dur = {}, {}
for l in open(d / "verdicts.jsonl"):
    v = json.loads(l)
    if v["quantity"] == "notehead_is_not_a_notehead":
        kept[v["subject"]] = (v["outcome"], v["reason"], v["value"])
    elif v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
        dur[v["subject"]] = (v["outcome"], v["reason"], (v.get("detail") or {}).get("head_stem"))

rows = []
for s, (oc, reason, val) in kept.items():
    if not (oc == "decided" and reason == "notehead"):
        continue
    g = glyph.get(s)
    if g is None:
        continue
    cell = "cell/" + s[6:].rsplit("/", 1)[0]
    head = _head_xywh(g["box"])
    allst = [(i, tuple(b)) for i, b in stems.get(cell, [])]
    touching = [i for i, b in allst if stem_touches_head(b, head)]
    # physical stems (adjudicate_head_stem's own clustering): rows that are one stem collapse
    reps = set()
    for i, b in allst:
        if stem_touches_head(b, head):
            cl = [(i2, b2) for i2, b2 in allst if i2 == i or _same_stem_row(b, b2)]
            reps.add(min(cl, key=lambda t: (-t[1][3], t[0]))[0])
    du = dur.get(s, (None, None, None))
    rows.append(dict(sub=s, cell=cell, page=int(s.split("/")[1]), cls=g["box"][0], conf=g["conf"], box=list(head),
                     page_box=g["page_box"], n_stem=len(touching), n_phys=len(reps), dur=du[0], dur_reason=du[1], sp=cellsp.get(cell),
                     reach=reach.get(s)))
json.dump(rows, open(out, "w"))

c = collections.Counter()
for r in rows:
    c[(r["dur"], r["n_stem"] == 0)] += 1
print(plate, "kept heads", len(rows), "pages", sorted({r["page"] for r in rows}))
for k, n in sorted(c.items(), key=lambda x: str(x)):
    print("  duration=%s no_stem=%s : %d" % (k[0], k[1], n))
nar = [r for r in rows if r["dur"] == "narrowed"]
print("narrowed", len(nar), "no stem row", sum(r["n_stem"] == 0 for r in nar),
      "(%.1f%%)" % (100.0 * sum(r["n_stem"] == 0 for r in nar) / max(1, len(nar))))
r2 = collections.Counter(r["dur_reason"] for r in nar if r["n_stem"] == 0)
print("  no-stem narrowed by reason:", dict(r2))
fam = [r for r in nar if r["dur_reason"] in ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined")]
print("beam-family narrowed", len(fam), "no stem touches", sum(r["n_stem"] == 0 for r in fam),
      "two+ physical stems touch (HEAD_STEM may narrow two_stems)", sum(r["n_phys"] >= 2 for r in fam),
      "one", sum(r["n_phys"] == 1 for r in fam))
