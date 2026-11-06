"""Score Brahms p0 against Sean's hand arcs (data/hand-truth/pages/imslp317803/0.json), per hand box, down the ledger (measure only).

    python3 handscore.py LEDGER.json ARCS.json [--out handscore.json]

A hand arc is one box per CELL (Sean boxed what each bar's crop shows), class slur|tie. A detector box 'matches' a hand box when they overlap
by IoU >= 0.2 or one holds the other's centre. Recall = hand boxes matched by a detector box that ADJUDICATE kept (not refused as a staff
line); a hand box matched only by a refused box, or by none, is a GATHER/refusal loss. Precision = kept detector boxes on p0 matched by a hand
box. The hand-arc FATE is the ledger fate of the curve that holds the matched box. NOT truth about the end notes: the hand file has none.
"""
import collections
import json
import pathlib
import sys

TRUTH = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b/data/hand-truth/pages/imslp317803/0.json")


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    i = (x1 - x0) * (y1 - y0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def holds(a, b):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return a[0] <= cx <= a[2] and a[1] <= cy <= a[3]


def main():
    led = json.load(open(sys.argv[1]))
    dump = json.load(open(sys.argv[2]))
    truth = [b for b in json.load(open(TRUTH))["boxes"] if b["cls"] in ("slur", "tie") and b.get("labeler") == "sean" or b["cls"] in ("slur", "tie")]
    truth = [b for b in truth if b["cls"] in ("slur", "tie")]
    rows = [r for r in led["rows"] if r.get("page") == 0]
    piece_curve = {}
    boxes = {o["subject"]: o["detail"]["bbox_page_px"] for o in dump["arc_box"] if o["subject"].split("/")[1] == "0"}
    for r in rows:
        for p in r["pieces"]:
            piece_curve[p] = r
    refused = {r["curve"] for r in rows if r["fate"] == "not_an_arc"}
    out = []
    for t in truth:
        tb = t["rect"]
        best, bi = None, 0.0
        for p, b in boxes.items():
            v = max(iou(tb, b), 0.5 if (holds(tb, b) or holds(b, tb)) else 0.0)
            if v > bi:
                best, bi = p, v
        if best is None or bi < 0.2:
            out.append(dict(id=t["id"], cls=t["cls"], origin=t["origin"], cell=t["cell_id"], fate="never_boxed", box=tb))
            continue
        r = piece_curve[best]
        out.append(dict(id=t["id"], cls=t["cls"], origin=t["origin"], cell=t["cell_id"], fate=r["fate"], kind=r.get("kind"), lost=(r.get("lost_at"), r.get("lost_rule")),
                        piece=best, curve=r["curve"], det_cls=boxes and None, box=tb))
    n = len(out)
    c = collections.Counter(o["fate"] for o in out)
    print("hand arcs on p0:", n, dict(collections.Counter(o["cls"] for o in out)))
    print("by origin:", dict(collections.Counter(o["origin"] for o in out)))
    print("fate per hand box:", dict(c))
    boxed = [o for o in out if o["fate"] != "never_boxed"]
    kept = [o for o in boxed if o["fate"] != "not_an_arc"]
    print("detector recall (boxed):  %d/%d = %.3f" % (len(boxed), n, len(boxed) / n))
    print("kept after adjudicate:    %d/%d = %.3f" % (len(kept), n, len(kept) / n))
    # precision: kept detector boxes on p0 matched by a hand box
    kept_boxes = [p for p, b in boxes.items() if piece_curve[p]["fate"] != "not_an_arc"]
    hit = 0
    for p in kept_boxes:
        if any(max(iou(t["rect"], boxes[p]), 0.5 if (holds(t["rect"], boxes[p]) or holds(boxes[p], t["rect"])) else 0.0) >= 0.2 for t in truth):
            hit += 1
    print("precision of kept boxes:  %d/%d = %.3f ; all boxes incl. refused: %d" % (hit, len(kept_boxes), hit / max(1, len(kept_boxes)), len(boxes)))
    print("WRITTEN (ledger 'written') of hand boxes: %d/%d = %.3f" % (c["written"], n, c["written"] / n))
    kc = collections.Counter((o["cls"], o["kind"]) for o in out if o["fate"] in ("written", "two_arcs", "wrong_note") and o.get("kind"))
    print("KIND of the written arc vs Sean's class (hand class, our decided kind):", dict(kc),
          "agree %d/%d" % (sum(v for (h, k), v in kc.items() if h == k), sum(kc.values())))
    kd = collections.Counter((o["cls"], o["kind"]) for o in out if o["fate"] == "dropped" and o.get("kind"))
    print("kind decided on the DROPPED hand arcs (hand class, kind):", dict(kd))
    lost = collections.Counter((o["lost"][0], o["lost"][1]) for o in out if o["fate"] == "dropped")
    print("hand arcs dropped, first rule:")
    for k, v in lost.most_common():
        print("   ", k, v)
    if "--out" in sys.argv:
        pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(out))


main()
