"""Population A: candidate doubled-head pairs on Litolff page 3.

A pair = two notehead-class glyphs in the same cell, same class, centres
within 1.2 staff spaces vertically (canonical, using that cell's own
cell_staff_space), and overlapping horizontally in canonical x.

For each pair we record: cell key, glyph indices, classes, staff positions,
canonical centres, dy (staff spaces), horizontal overlap fraction / IoU,
2.30's verdict on either member, the event grouping (chord vs separate),
duration verdicts, and -- for the manager's follow-up -- which side of the
nearest stem each head's centre falls on.
"""
import pickle, json
from collections import defaultdict

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))

def cell_of(subject):
    # glyph/3/sys/staff/cell/glyph -> cell/3/sys/staff/cell
    parts = subject.split("/")
    return "/".join(["cell"] + parts[1:5])

def glyph_idx(subject):
    return int(subject.split("/")[-1])

# index glyph_box by subject
gbox = {o["subject"]: o for o in d["by_q_page"]["glyph_box"]}
nclass = {o["subject"]: o["value"] for o in d["by_q_page"]["notehead_class"]}
npos = {o["subject"]: o["value"] for o in d["by_q_page"]["notehead_staff_position"]}
cell_ss = {o["subject"]: o["value"] for o in d["by_q_page"]["cell_staff_space"]}
notehead_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["notehead_is_not_a_notehead"]}
stemdir_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["stem_direction"]}
event_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["event"]}
duration_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["duration"]}

stems_by_cell = defaultdict(list)
for o in d["by_q_page"]["stem"]:
    stems_by_cell[o["subject"]].append(o["value"])  # [x,y,w,h] canonical

# group notehead glyphs by cell
by_cell = defaultdict(list)
for subj in nclass:
    by_cell[cell_of(subj)].append(subj)

pairs = []
for cellkey, subjs in by_cell.items():
    ss = cell_ss.get(cellkey)
    if not ss:
        continue
    subjs = sorted(subjs, key=glyph_idx)
    n = len(subjs)
    for i in range(n):
        for j in range(i + 1, n):
            s1, s2 = subjs[i], subjs[j]
            if nclass[s1] != nclass[s2]:
                continue
            b1 = gbox[s1]["value"]  # (name, x, y, w, h) canonical
            b2 = gbox[s2]["value"]
            _, x1, y1, w1, h1 = b1
            _, x2, y2, w2, h2 = b2
            cx1, cy1 = x1 + w1 / 2.0, y1 + h1 / 2.0
            cx2, cy2 = x2 + w2 / 2.0, y2 + h2 / 2.0
            dy_px = abs(cy1 - cy2)
            dy_sp = dy_px / ss
            if dy_sp > 1.2:
                continue
            # horizontal overlap
            ox0, ox1 = max(x1, x2), min(x1 + w1, x2 + w2)
            overlap = max(0.0, ox1 - ox0)
            if overlap <= 0:
                continue
            union = (w1 + w2) - overlap if overlap < min(w1, w2) else max(w1, w2)
            iou_x = overlap / union if union else 0.0
            # full-box IoU (2D)
            iy0, iy1 = max(y1, y2), min(y1 + h1, y2 + h2)
            ih = max(0.0, iy1 - iy0)
            inter_area = overlap * ih
            area1, area2 = w1 * h1, w2 * h2
            iou2d = inter_area / (area1 + area2 - inter_area) if (area1 + area2 - inter_area) else 0.0
            pairs.append(dict(
                cell=cellkey, g1=s1, g2=s2, cls=nclass[s1],
                pos1=npos.get(s1), pos2=npos.get(s2),
                cx1=cx1, cy1=cy1, cx2=cx2, cy2=cy2,
                w1=w1, h1=h1, w2=w2, h2=h2,
                dy_spaces=dy_sp, iou2d=iou2d, ss=ss,
                verdict1=notehead_verdict.get(s1, {}).get("reason"),
                verdict2=notehead_verdict.get(s2, {}).get("reason"),
                refused1=notehead_verdict.get(s1, {}).get("value"),
                refused2=notehead_verdict.get(s2, {}).get("value"),
                stemdir1=stemdir_verdict.get(s1, {}).get("value"),
                stemdir2=stemdir_verdict.get(s2, {}).get("value"),
            ))

print("total candidate pairs (population A):", len(pairs))

# Now classify by 2.30's own verdict
dup_caught = [p for p in pairs if p["refused1"] or p["refused2"]]
dup_missed = [p for p in pairs if not p["refused1"] and not p["refused2"]]
print("caught by 2.30 (one member refused notehead_is_a_duplicate_box or other):", len(dup_caught))
print("  of those, reason=notehead_is_a_duplicate_box specifically:",
      sum(1 for p in dup_caught if p["verdict1"] == "notehead_is_a_duplicate_box" or p["verdict2"] == "notehead_is_a_duplicate_box"))
print("neither member refused (both stand):", len(dup_missed))

# event/chord check for the "missed" pairs (both stand): did EVENT group them as one chord?
def glyph_index_of(subj):
    return int(subj.split("/")[-1])

def event_status(cellkey, gi1, gi2):
    ev = event_verdict.get(cellkey)
    if not ev or ev.get("outcome") != "decided":
        return "no_event_verdict"
    events = ev["value"].get("events", [])
    e1 = e2 = None
    for e in events:
        gl = e.get("glyphs", [])
        if gi1 in gl:
            e1 = e
        if gi2 in gl:
            e2 = e
    if e1 is None or e2 is None:
        return "one_or_both_not_in_any_event"
    if e1 is e2:
        return "same_event_" + e1.get("kind", "?")
    return "different_events"

for p in pairs:
    p["event_status"] = event_status(p["cell"], glyph_index_of(p["g1"]), glyph_index_of(p["g2"]))

from collections import Counter
print("\nevent_status over ALL candidate pairs:")
print(Counter(p["event_status"] for p in pairs))
print("\nevent_status over MISSED (neither refused) pairs:")
print(Counter(p["event_status"] for p in dup_missed))

# stem side-of test: for each pair, find nearest stem in the cell (canonical
# frame, same as glyph_box/stem), and record each head's side relative to
# the stem's x-center.
def nearest_stem_and_sides(cellkey, cx1, cy1, cx2, cy2):
    stems = stems_by_cell.get(cellkey, [])
    if not stems:
        return None
    # combined vertical band of the pair
    ymid = (cy1 + cy2) / 2.0
    best = None
    best_d = None
    for (sx, sy, sw, sh) in stems:
        scx = sx + sw / 2.0
        # does stem's y-range roughly cover ymid?
        covers = sy - 50 <= ymid <= sy + sh + 50
        d = abs(scx - (cx1 + cx2) / 2.0)
        key = (0 if covers else 1, d)
        if best is None or key < best_d:
            best_d = key
            best = (scx, sy, sw, sh, covers)
    if best is None:
        return None
    scx = best[0]
    side1 = "right" if cx1 > scx else "left"
    side2 = "right" if cx2 > scx else "left"
    return dict(stem_x_center=scx, stem_covers=best[4], side1=side1, side2=side2,
                same_side=(side1 == side2))

for p in pairs:
    r = nearest_stem_and_sides(p["cell"], p["cx1"], p["cy1"], p["cx2"], p["cy2"])
    if r is None:
        p["stem_side"] = "no_stem_in_cell"
        p["same_side"] = None
    else:
        p.update(r)
        p["stem_side"] = "same" if r["same_side"] else "opposite"

print("\nstem_side distribution over ALL candidate pairs:")
print(Counter(p["stem_side"] for p in pairs))
print("\nstem_side distribution over MISSED (neither refused, i.e. candidates for judging) pairs:")
print(Counter(p["stem_side"] for p in dup_missed))
print("\nstem_side distribution over CAUGHT (2.30 refused one) pairs:")
print(Counter(p["stem_side"] for p in dup_caught))

with open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/pairs_a.json", "w") as f:
    json.dump(pairs, f, indent=1, default=str)
print("\nwrote pairs_a.json,", len(pairs), "pairs")
