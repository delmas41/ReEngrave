"""ROADMAP 2.126 control: every black head of Sean's Brahms 317803 pdf 0 hand truth, truth class vs the record's duration, base vs arm.

    python3 benchmarks/omr-beam-confirm-2026-10/truth_durations.py BASE0.json ARM0.json [OUT.json]

Truth class of a black head (Sean's own boxes; pairing is geometric, not his statement): his STEM box touching the head, then a FLAG box on that
stem's far end (flagged), else a BEAM box over the stem's column that reaches its far end (beamed), else bare. Record side: the standing
`Q.DURATION` verdict of the head's glyph subject, matched to the truth head by box IoU >= 0.5. Status per head:
  right      decided, and `beam_levels > 0` agrees with flagged/beamed (resp. == 0 with bare)
  wrong      decided, disagrees
  narrowed   a narrowing (candidates)       abstained   an abstention       missing   no matching glyph / no verdict
Reported as transitions base -> arm. The control that can fail: a head whose arm status is `wrong` and was not `wrong` at base is printed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import judged  # noqa: E402

TRUTH = "data/hand-truth/pages/imslp317803/0.json"
SP = 32.25


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0.0


def truth_classes():
    d = json.load(open(TRUTH))
    B = d["boxes"]
    heads = [b for b in B if b["cls"].startswith("noteheadBlack")]
    stems = [b for b in B if b["cls"] == "stem"]
    flags = [b for b in B if b["cls"].startswith("flag")]
    beams = [b for b in B if b["cls"] == "beam"]
    out = {}
    for h in heads:
        hx0, hy0, hx1, hy1 = h["rect"]
        mine = [s for s in stems if s["rect"][0] <= hx1 + 6 and s["rect"][2] >= hx0 - 6
                and s["rect"][1] <= hy1 + 6 and s["rect"][3] >= hy0 - 6]
        if not mine:
            out[h["id"]] = ("no_stem", h["rect"])
            continue
        cls = "bare"
        for s in mine:
            sx0, sy0, sx1, sy1 = s["rect"]
            ends = [sy0, sy1]
            if any(f["rect"][0] <= sx1 + 12 and f["rect"][2] >= sx0 - 12 and f["rect"][1] <= sy1 + 12 and f["rect"][3] >= sy0 - 12
                   and (abs(f["rect"][1] - e) < 1.2 * SP or abs(f["rect"][3] - e) < 1.2 * SP) for f in flags for e in ends):
                cls = "flagged"
            elif any(b["rect"][0] <= sx1 + 8 and b["rect"][2] >= sx0 - 8
                     and min(abs(b["rect"][1] - e) for e in ends) < 0.8 * SP
                     or (b["rect"][0] <= sx1 + 8 and b["rect"][2] >= sx0 - 8 and any(b["rect"][1] - 4 <= e <= b["rect"][3] + 4 for e in ends))
                     for b in beams):
                cls = "beamed"
        out[h["id"]] = (cls, h["rect"])
    return out


def record_side(path):
    path = Path(path)
    boxes = {}
    for o in judged.iter_array(path, "observations"):
        sub = o.get("subject")
        if isinstance(sub, str) and sub.startswith("glyph/0/") and o.get("quantity") == "glyph_box":
            b = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(b, list) and len(b) == 4:
                boxes[sub] = [float(x) for x in b]
    by = {}
    for v in judged.iter_verdicts(path):
        if v.get("quantity") == "duration" and v.get("subject") in boxes:
            by.setdefault(v["subject"], []).append(v)
    standing = {}
    for sub, vs in by.items():
        sup = {x.get("supersedes") for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in sup] or vs
        standing[sub] = live[-1]
    return boxes, standing


def status(tclass, v):
    if tclass == "no_stem":
        return "no_truth_stem"
    if v is None:
        return "missing"
    if v["outcome"] == "decided":
        val = v.get("value") or {}
        lv = val.get("beam_levels")
        if lv is None:
            return "other"
        want = 0 if tclass == "bare" else 1
        return "right" if (lv > 0) == (want > 0) else "wrong"
    if v["outcome"] == "narrowed":
        return "narrowed"
    return "abstained"


def main():
    base_p, arm_p = sys.argv[1], sys.argv[2]
    T = truth_classes()
    sides = {}
    for tag, p in (("base", base_p), ("arm", arm_p)):
        boxes, st = record_side(p)
        m = {}
        for tid, (tc, rect) in T.items():
            best, bs = None, 0.0
            for sub, b in boxes.items():
                s = iou(b, rect)
                if s > bs:
                    best, bs = sub, s
            if bs >= 0.5:
                m[tid] = (best, status(tc, st.get(best)), st.get(best))
            else:
                m[tid] = (None, "missing" if tc != "no_stem" else "no_truth_stem", None)
        sides[tag] = m
    rows = []
    trans = {}
    for tid, (tc, rect) in T.items():
        b, a = sides["base"][tid], sides["arm"][tid]
        trans[(b[1], a[1])] = trans.get((b[1], a[1]), 0) + 1
        if b[1] != a[1]:
            rows.append({"truth": tid, "class": tc, "subject": a[0] or b[0], "base": b[1], "arm": a[1],
                         "base_reason": (b[2] or {}).get("reason"), "arm_reason": (a[2] or {}).get("reason")})
    tot = {tag: {} for tag in sides}
    for tag in sides:
        for tid in T:
            s = sides[tag][tid][1]
            tot[tag][s] = tot[tag].get(s, 0) + 1
    print("truth classes:", {c: sum(1 for t in T.values() if t[0] == c) for c in ("bare", "beamed", "flagged", "no_stem")})
    for tag in sides:
        print(tag, dict(sorted(tot[tag].items())))
    print("transitions (base -> arm), changed only:")
    for k, v in sorted(trans.items()):
        if k[0] != k[1]:
            print(f"  {k[0]:>10s} -> {k[1]:<10s} {v}")
    lost = [r for r in rows if r["base"] == "right" and r["arm"] != "right"]
    newly_wrong = [r for r in rows if r["arm"] == "wrong"]
    print("LOST (right at base, not right at arm):", len(lost))
    print("NEWLY WRONG:", len(newly_wrong))
    for r in rows:
        print(" ", r)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps({"totals": tot, "changed": rows}, indent=1, default=str))


main()
