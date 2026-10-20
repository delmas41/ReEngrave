"""ROADMAP 2.176b probe -- re-decide ONE page slice (current code, shipped defaults) and dump, for a page's boxes, the live
`notehead_is_not_a_notehead` verdict and the live duration verdict. usage: probe_2_176b_tile8.py SLICEDIR_PARENT DOC PAGE
Writes SLICEDIR_PARENT/probe_DOC_PAGE.json {live_refusal{g: verdict}, duration{g: brief}, boxes{g: [value, bbox_page_px]}, meters[...]}."""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

SP, DOC, PG = sys.argv[1], sys.argv[2], int(sys.argv[3])
D = os.path.join(SP, DOC)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        out += [json.loads(line) for line in open(p)]
    return out


def live(vs, q):
    ch = collections.defaultdict(list)
    for v in vs:
        if v["quantity"] == q and v["subject"].startswith("glyph/"):
            ch[v["subject"]].append(v)
    out = {}
    for g, c in ch.items():
        sup = {x.get("supersedes") for x in c if x.get("supersedes")}
        out[g] = ([x for x in c if x["id"] not in sup] or c)[-1]
    return out


rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
res = log.to_json()
vs = res["verdicts"]
ref, dur = live(vs, "notehead_is_not_a_notehead"), live(vs, "duration")
boxes = {o["subject"]: [o["value"], o["detail"].get("bbox_page_px")] for o in res["observations"]
         if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/%d/" % PG)}
meters = [[o["subject"], o["quantity"], o["value"], (o.get("detail") or {}).get("cell")] for o in res["observations"]
          if o["quantity"] in ("meter_template", "meter_ocr", "meter_template_at_bar", "meter_ocr_at_bar")]
out = dict(refusal={g: [v["value"], v.get("reason"), v.get("outcome")] for g, v in ref.items()},
           duration={g: [v["outcome"], (v["value"] or {}).get("written") if isinstance(v["value"], dict) else None, v.get("reason")]
                     for g, v in dur.items()}, boxes=boxes, meters=meters)
json.dump(out, open(os.path.join(SP, "probe_%s_%d.json" % (DOC, PG)), "w"), default=str)
print("verdicts", len(vs), "boxes", len(boxes), "refused", sum(1 for v in ref.values() if v["value"] is True))
