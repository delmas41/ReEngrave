"""Brahms p0, FILE level: written ties/slurs (from the exported MusicXML) vs hand truth (data/hand-truth tie/slur boxes), matched by place.
Also: every truth arc's detector box (if any) and that box's fate.   usage: p0score.py  [no args]"""
import json, collections, xml.etree.ElementTree as ET
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record

T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
D = json.load(open("/private/tmp/claude-501/arcs/brahms.json"))
print("truth dpi", T["dpi"], "state", T["state"], "page", T["width"], T["height"])
u = L.PLATES["brahms"]["unit"]
truth = [dict(cls=b["cls"], x0=b["rect"][0], y0=b["rect"][1], x1=b["rect"][2], y1=b["rect"][3], cell=b["cell_id"], id=b["id"])
         for b in T["boxes"] if b["cls"] in ("tie", "slur")]
print("truth", collections.Counter(t["cls"] for t in truth), "unit", u)

# glyph boxes for page 0 (need the record's observations: reuse via a light scan of the saved json for glyph_box rows on page 0)
import re
boxes = {}
rec = D  # placeholder
xml = open("/private/tmp/claude-501/arcs/brahms.musicxml").read()
GB = json.load(open("/private/tmp/claude-501/arcs/brahms.glyphboxes.json"))
root = ET.fromstring(xml)
spans = []
for part in root.iter("part"):
    open_slur = {}
    open_tie = {}
    for m in part.findall("measure"):
        for el in m.findall("note"):
            rg = el.get("rg")
            b = GB.get(rg)
            if not b or b["page"] != 0:
                # still track opens for cross-page safety
                pass
            pit = el.find("pitch")
            key = None
            if pit is not None:
                key = (pit.findtext("step"), pit.findtext("octave"), el.findtext("voice"))
            for t in el.findall("tie"):
                if t.get("type") == "start":
                    open_tie[key] = rg
                elif t.get("type") == "stop" and key in open_tie:
                    spans.append(("tie", open_tie.pop(key), rg))
            nt = el.find("notations")
            if nt is not None:
                for s in nt.findall("slur"):
                    n = (s.get("number"), el.findtext("voice"))
                    if s.get("type") == "start":
                        open_slur[n] = rg
                    elif s.get("type") == "stop" and n in open_slur:
                        spans.append(("slur", open_slur.pop(n), rg))
W = []
for kind, a, b in spans:
    ba, bb = GB.get(a), GB.get(b)
    if not ba or not bb or ba["page"] != 0 or bb["page"] != 0:
        continue
    ax, ay = (ba["box"][0] + ba["box"][2]) / 2, (ba["box"][1] + ba["box"][3]) / 2
    bx_, by_ = (bb["box"][0] + bb["box"][2]) / 2, (bb["box"][1] + bb["box"][3]) / 2
    W.append(dict(kind=kind, x0=min(ax, bx_), x1=max(ax, bx_), y0=min(ay, by_), y1=max(ay, by_)))
print("written spans on page 0:", collections.Counter(w["kind"] for w in W))


def xov(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def score(w, t):
    # x overlap relative to the shorter; y: truth box centre within the span's y range +- 5 spaces
    ov = xov(w["x0"], w["x1"], t["x0"], t["x1"])
    short = max(1.0, min(w["x1"] - w["x0"], t["x1"] - t["x0"]))
    cy = (t["y0"] + t["y1"]) / 2
    if not (w["y0"] - 5 * u <= cy <= w["y1"] + 5 * u):
        return 0.0
    return ov / short


cands = sorted(((score(w, t), i, j) for i, w in enumerate(W) for j, t in enumerate(truth)), reverse=True)
usedw, usedt, pairs = set(), set(), []
for s, i, j in cands:
    if s < 0.6:
        break
    if i in usedw or j in usedt:
        continue
    usedw.add(i); usedt.add(j); pairs.append((i, j, s))
res = collections.Counter()
for i, j, s in pairs:
    res[(W[i]["kind"], truth[j]["cls"])] += 1
print("matched (written kind, truth kind):", dict(res))
inv = collections.Counter(W[i]["kind"] for i in range(len(W)) if i not in usedw)
mis = collections.Counter(truth[j]["cls"] for j in range(len(truth)) if j not in usedt)
print("INVENTED (written, no truth):", dict(inv), " MISSING (truth, not written):", dict(mis))
# missing truth -> detector box fate
rows = [r for r in D["rows"] if r["page"] == 0 and r["box"]]


def iou(a, b):
    iw = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]); ih = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0
    i = iw * ih
    return i / (a[2] * a[3] + b[2] * b[3] - i)


miss_fates = collections.Counter()
miss_list = []
for j, t in enumerate(truth):
    if j in usedt:
        continue
    tb = (t["x0"], t["y0"], t["x1"] - t["x0"], t["y1"] - t["y0"])
    best = max(rows, key=lambda r: iou(r["box"], tb), default=None)
    sc = iou(best["box"], tb) if best else 0
    fate = best["fate"] if best and sc >= 0.3 else "NO_DETECTOR_BOX(iou<0.3)"
    miss_fates[(t["cls"], fate)] += 1
    miss_list.append(dict(truth=t, fate=fate, iou=round(sc, 2), sub=best["sub"] if best and sc >= 0.3 else None))
for k, v in sorted(miss_fates.items(), key=lambda kv: -kv[1]):
    print("  missing", k, v)
# invented -> nearest truth?
json.dump(dict(missing=miss_list, written=W, pairs=[(i, j) for i, j, s in pairs]), open("/private/tmp/claude-501/arcs/p0score.json", "w"), default=str)
tt = collections.Counter(t["cls"] for t in truth)
for k in ("tie", "slur"):
    right = sum(1 for i, j, s in pairs if W[i]["kind"] == k and truth[j]["cls"] == k)
    wr = sum(1 for w in W if w["kind"] == k)
    print(k, "truth", tt[k], "written", wr, "right", right, "recall %.2f precision %.2f" % (right / tt[k], right / max(1, wr)))
