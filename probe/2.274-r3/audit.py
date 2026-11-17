"""AUDITED scorer for Brahms p0 (rule 7: "check the scorer too"). truth_p0.py ("strict") needs both ends of a written arc within 2.5 sp of the printed arc's ends.
Sean's boxes are one per CELL (bar) and the labeling is not complete across a barline, so a printed arc whose box ENDS AT A CELL EDGE is only half-boxed: its true end lies beyond the edge. Audited rule:
  * an end within 1.5 sp of its own cell's left/right edge is OPEN: the written end may lie anywhere beyond it (<= 30 sp) -- never short of it by more than 2.5 sp;
  * a hand label over the SAME MARK as another one (|dx0|,|dx1| <= 40 px, y bands overlapping or within 20 px) is one printed mark: a written arc satisfies all of them;
  * a group of >= 3 hand boxes joined into one 'printed arc' is a chain of separate arcs (P27, P31): not scorable as one;
  * a hand arc with no ink-run and no kept detector box (`ghost`) is listed apart (it needs Sean's eye, not our file).
    python3 audit.py     -> audit.json (per printed arc, strict + audited, OFF and ON) and a summary
"""
import json
import collections
from load import *   # noqa
import truth_p0 as T  # noqa
import os
REACH = float(os.environ.get('AUD_REACH', '2.5'))
TAG = os.environ.get('AUD_TAG', '')

P, HEADS = printed()
C = json.load(open("census2.json"))
truth = json.load(open(S.TRUTH))
byid = {b["id"]: b for b in truth["boxes"]}
cells = {c["id"]: c for c in truth["cells"]}


def spans(arm):
    xml = (WORK / ("brahms.%s.musicxml" % arm)).read_text()
    boxes = T.boxes_p0(WORK / ("brahms.%s.mini-record.json" % arm))
    out = []
    for a in A.arcs_of_xml(xml):
        if not a["start"].startswith("glyph/0/") or a["start"] not in boxes or a["stop"] not in boxes:
            continue
        sa, sz = a["start"].split("/")[2:4], a["stop"].split("/")[2:4]
        ba, bz = boxes[a["start"]], boxes[a["stop"]]
        out.append(dict(kind=a["kind"], staff="/".join(sa), same=sa == sz, cl=(ba[0] + ba[2]) / 2, cr=(bz[0] + bz[2]) / 2, yc=((ba[1] + ba[3]) / 2 + (bz[1] + bz[3]) / 2) / 2, start=a["start"], stop=a["stop"]))
    import random
    n = int(os.environ.get('AUD_DROP', '0'))
    if n:
        random.Random(7).shuffle(out)
        out = out[n:]
    return out


# ---- truth-side facts per printed arc
for p, c in zip(P, C):
    assert p["x0"] and round(p["x0"]) == c["x0"]
    bx = [byid[i] for i in p["ids"]]
    left = min(bx, key=lambda b: b["rect"][0])
    right = max(bx, key=lambda b: b["rect"][2])
    p["open_L"] = abs(p["x0"] - cells[left["cell_id"]]["rect"][0]) <= 1.5 * SP
    p["open_R"] = abs(p["x1"] - cells[right["cell_id"]]["rect"][2]) <= 1.5 * SP
    p["origins"] = sorted({b["origin"] for b in bx})
    p["chain"] = (p["x1"] - p["x0"]) / SP > 35
    c["open_L"], c["open_R"], c["origins"], c["chain"] = p["open_L"], p["open_R"], p["origins"], p["chain"]
    c["ghost"] = c["box_cov_kept"] < 0.15 and c["run_cov"] == 0.0 and not p["chain"]

# duplicates: same staff, same extent, touching y bands
grp = list(range(len(P)))


def find(i):
    while grp[i] != i:
        grp[i] = grp[grp[i]]
        i = grp[i]
    return i


for i, a in enumerate(P):
    for j in range(i + 1, len(P)):
        b = P[j]
        if a["staff"] != b["staff"] or C[i]["ghost"] or C[j]["ghost"]:
            continue
        if abs(a["x0"] - b["x0"]) <= 40 and abs(a["x1"] - b["x1"]) <= 40:
            ya, yb = a["box"], b["box"]
            gap = max(ya[1], yb[1]) - min(ya[3], yb[3])
            if gap <= 0:
                grp[find(i)] = find(j)
for i, c in enumerate(C):
    c["mark"] = find(i)
marks = collections.defaultdict(list)
for i, c in enumerate(C):
    marks[c["mark"]].append(i)
for i, c in enumerate(C):
    c["dup_of"] = [k for k in marks[c["mark"]] if k != i]


def matches(p, w, tol_open=True):
    # the arc is matched by place, not by the cell's staff label (hand boxes in a cell's pad belong to the neighbouring staff): same system, heads' height within 6 sp of the box
    if not w["same"] and abs(int(w["start"].split("/")[3]) - int(w["stop"].split("/")[3])) > 0:
        return None
    if abs(w["yc"] - (p["box"][1] + p["box"][3]) / 2) > 6 * SP:
        return None
    dl, dr = (w["cl"] - p["x0"]) / SP, (w["cr"] - p["x1"]) / SP
    okl = abs(dl) <= REACH or (tol_open and p["open_L"] and -30 <= dl < 0)
    okr = abs(dr) <= REACH or (tol_open and p["open_R"] and 0 < dr <= 30)
    if not (okl and okr):
        return None
    return (abs(dl) + abs(dr))


res = {}
for arm in ("off", "on"):
    W = spans(arm)
    used = set()
    out = {}
    # marks first: one written arc satisfies every label of the mark; process in staff/x order
    order = sorted(range(len(P)), key=lambda i: (C[i]["ghost"], C[i]["chain"], i))
    done = {}
    mt = {}
    for i in order:
        p, c = P[i], C[i]
        if c["chain"]:
            out[i] = "chain"
            continue
        if c["ghost"]:
            out[i] = "ghost"
            continue
        m = c["mark"]
        if m in done:
            out[i] = done[m]
            continue
        best = None
        for k, w in enumerate(W):
            if k in used:
                continue
            sc = matches(p, w)
            if sc is None:
                continue
            kind_ok = w["kind"] == p["kind"]
            key = (0 if kind_ok else 1, sc)
            if best is None or key < best[0]:
                best = (key, k)
        # a mark of several labels: the kind of ANY label counts
        if best is None:
            out[i] = "none"
        else:
            used.add(best[1])
            w = W[best[1]]
            mt[i] = (w['start'], w['stop'], w['kind'])
            kinds = {P[j]["kind"] for j in marks[m]}
            out[i] = "right" if w["kind"] in kinds else "other_kind"
        done[m] = out[i]
    res[arm] = (out, [w for k, w in enumerate(W) if k not in used], W, mt)
for i, c in enumerate(C):
    c["strict_off"], c["strict_on"] = c["file_off"], c["file_on"]
    c["aud_off"], c["aud_on"] = res["off"][0][i], res["on"][0][i]
    c["aud_off_span"], c["aud_on_span"] = res["off"][3].get(i), res["on"][3].get(i)
json.dump(C, open("census3%s.json" % TAG, "w"), indent=1, default=str)
for arm in ("off", "on"):
    out, extra, W, mt = res[arm]
    cnt = collections.Counter(out.values())
    print(arm.upper(), "audited:", dict(cnt), "| strict right", sum(1 for c in C if c["strict_" + arm] == "right"), "| written arcs", len(W), "matching nothing", len(extra))
print("ghost", [c["n"] for c in C if c["ghost"]], "chain", [c["n"] for c in C if c["chain"]])
print("dup marks", [[C[k]["n"] for k in v] for v in marks.values() if len(v) > 1])
print("open L/R", sum(1 for p in P if p["open_L"]), sum(1 for p in P if p["open_R"]))
print("cross strict/audited ON", collections.Counter((c["strict_on"], c["aud_on"]) for c in C))
