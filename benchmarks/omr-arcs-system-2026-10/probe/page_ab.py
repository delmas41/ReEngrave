"""ROADMAP 2.166 -- one page, GATHER + ADJUDICATE, flag OMR_SYSTEM_ARCS OFF vs ON, the detector run ONCE (cached) so
the two arms see the same boxes (CLAUDE §7: the detector reads the original cells in both arms).

Writes OUT.json: the ON arm's Q.SYSTEM_ARC rows, the glyph verdicts that differ OFF vs ON (notehead_is_not_a_notehead,
duration, pitch, arc_kind, tie_pair, rest/dot/accidental quantities), and every detector box whose canonical window
lost ink to the erase (with how much). Also OUT.cells.npz-free: nothing else is kept.
usage: page_ab.py DOC PAGE OUT.json      DOC = litolff | brahms
"""
import collections
import json
import os
import sys
import time

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr import acceptance as ACC  # noqa: E402
from tools.omr.staged import pipeline, weight_routing  # noqa: E402
from tools.omr.staged import arcs_system  # noqa: E402

DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
DOC, PAGE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
man = json.load(open("benchmarks/acceptance/manifest.json"))
doc = [d for d in man["documents"] if d["id"] == DOCS[DOC]][0]
pdf = str(ACC.resolve_path(doc["pdf"]))

QS = ("notehead_is_not_a_notehead", "duration", "pitch", "arc_kind", "tie_pair", "arc_owner", "arc_is_not_an_arc",
      "rest", "rest_is_not_a_rest", "dot_role", "augmentation_dot", "accidental", "stem", "notehead_fill",
      "beam", "flag")


class Cached:
    def __init__(self, det):
        self.det, self.cache = det, {}

    def detect(self, cell, *a, **k):
        key = (cell.page_index, cell.staff_index, cell.measure_index, repr(a), repr(sorted(k.items())))
        if key not in self.cache:
            self.cache[key] = self.det.detect(cell, *a, **k)
        import copy
        return copy.deepcopy(self.cache[key])

    def __getattr__(self, n):
        return getattr(self.det, n)


def live(verdicts):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["subject"].startswith("glyph/"):
            chains[(v["subject"], v["quantity"])].append(v)
    out = {}
    for k, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        v = ([x for x in ch if x["id"] not in sup] or ch)[-1]
        out[k] = (v["outcome"], json.dumps(v.get("value"), sort_keys=True, default=str)[:160], v.get("reason"))
    return out


t0 = time.time()
wpath, _, cls = weight_routing.resolve_staged_weights(pdf, [PAGE], weights="auto", route_weights=False)
from tools.omr.yolo_detector import YoloDetector  # noqa: E402
det = Cached(YoloDetector(wpath))
arms = {}
lost = []
for arm in ("off", "on"):
    if arm == "on":
        os.environ[arcs_system.ENV] = "1"
    else:
        os.environ.pop(arcs_system.ENV, None)
    prepared = pipeline.prepare_pages(pdf, [PAGE])
    res = pipeline.run_staged_on(prepared, detector=det, pdf_path=pdf, surya_fallback=False, ocr_fallback=False,
                                 input_domain_classification=cls, through="adjudicate")
    rec = res["record"]
    arms[arm] = dict(verdicts=live(rec["verdicts"]),
                     sysarc=[o for o in rec["observations"] if o["quantity"] == "system_arc"],
                     sysarc_abst=[a for a in rec.get("abstentions", []) if a.get("quantity") == "system_arc"],
                     boxes={o["subject"]: o for o in rec["observations"] if o["quantity"] == "glyph_box"})
    if arm == "on":
        # every box whose canonical window lost ink to the erase
        for pws, cells in prepared:
            for c in cells:
                orig = getattr(c, "image_no_staff_with_arcs", None)
                if orig is None:
                    continue
                er = (orig < 128) & ~(c.image_no_staff < 128)
                ys, xs = np.nonzero(er)
                if not len(ys):
                    continue
                up = float(c.upscale_factor)
                bx0, by0 = c.bbox_page_px[0], c.bbox_page_px[1]
                lost.append(dict(page=c.page_index, staff_index=c.staff_index, cell=c.measure_index,
                                 n=int(len(ys)), x0=bx0 + xs.min() / up, x1=bx0 + xs.max() / up,
                                 y0=by0 + ys.min() / up, y1=by0 + ys.max() / up))
        on_prepared = prepared
    print(arm, "%.0fs" % (time.time() - t0), flush=True)
os.environ.pop(arcs_system.ENV, None)

off, on = arms["off"]["verdicts"], arms["on"]["verdicts"]
changed = {}
for k in sorted(set(off) | set(on)):
    if k[1] not in QS and not k[1].startswith(("rest", "dot", "accidental", "notehead")):
        continue
    if off.get(k) != on.get(k):
        changed.setdefault(k[0], {})[k[1]] = dict(off=off.get(k), on=on.get(k))
same_boxes = set(arms["off"]["boxes"]) == set(arms["on"]["boxes"])
shapes = collections.Counter(o["value"] for o in arms["on"]["sysarc"])
pieces = sum(len(o["detail"]["pieces"]) for o in arms["on"]["sysarc"])
joined = sum(1 for o in arms["on"]["sysarc"] if len(o["detail"]["cells"]) > 1)
ab = collections.Counter(a.get("reason") for a in arms["on"]["sysarc_abst"])
tie_pair = collections.Counter(on[k][0] + ":" + str(on[k][2]) for k in on if k[1] == "tie_pair")
tie_pair_off = collections.Counter(off[k][0] + ":" + str(off[k][2]) for k in off if k[1] == "tie_pair")
kinds_on = collections.Counter(on[k][1] for k in on if k[1] == "arc_kind")
kinds_off = collections.Counter(off[k][1] for k in off if k[1] == "arc_kind")
out = dict(doc=DOC, page=PAGE, weights=wpath, same_detector_boxes=same_boxes,
           arcs=len(arms["on"]["sysarc"]), pieces_read=pieces, abstained=dict(ab), joined_across_barline=joined,
           shapes=dict(shapes), tie_pair_off=dict(tie_pair_off), tie_pair_on=dict(tie_pair),
           arc_kind_off=dict(kinds_off), arc_kind_on=dict(kinds_on),
           n_changed_glyphs=len(changed), changed=changed, erased_cells=lost,
           sysarc=arms["on"]["sysarc"], boxes={g: dict(detail=b.get("detail"), value=b.get("value"))
                                              for g, b in arms["on"]["boxes"].items()},
           seconds=round(time.time() - t0))
json.dump(out, open(OUT, "w"), indent=0, default=str)
print(json.dumps({k: out[k] for k in ("arcs", "pieces_read", "abstained", "joined_across_barline", "shapes",
                                      "n_changed_glyphs", "same_detector_boxes", "seconds")}), flush=True)
