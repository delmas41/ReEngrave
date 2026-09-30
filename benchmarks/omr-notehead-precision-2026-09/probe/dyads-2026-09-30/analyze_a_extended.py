"""Extended candidate set: same as population A but WITHOUT requiring
horizontal box overlap -- dx up to 1.6x median head width, dy<=1.2 spaces.
This is needed to even have a chance of including real dyads (offset heads),
since population A's own overlap requirement structurally excludes an
opposite-side second. Reports the side-of-stem split on this wider set so
the manager's convention can be checked against BOTH kinds of pair.
"""
import pickle, json
from collections import defaultdict, Counter

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))

def cell_of(subject):
    parts = subject.split("/")
    return "/".join(["cell"] + parts[1:5])

def glyph_index_of(subj):
    return int(subj.split("/")[-1])

gbox = {o["subject"]: o for o in d["by_q_page"]["glyph_box"]}
nclass = {o["subject"]: o["value"] for o in d["by_q_page"]["notehead_class"]}
npos = {o["subject"]: o["value"] for o in d["by_q_page"]["notehead_staff_position"]}
cell_ss = {o["subject"]: o["value"] for o in d["by_q_page"]["cell_staff_space"]}
notehead_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["notehead_is_not_a_notehead"]}
event_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["event"]}

stems_by_cell = defaultdict(list)
for o in d["by_q_page"]["stem"]:
    stems_by_cell[o["subject"]].append(o["value"])

by_cell = defaultdict(list)
for subj in nclass:
    by_cell[cell_of(subj)].append(subj)

HEAD_W_MEDIAN = 149.0

def nearest_stem_and_sides(cellkey, cx1, cy1, cx2, cy2):
    stems = stems_by_cell.get(cellkey, [])
    if not stems:
        return None
    ymid = (cy1 + cy2) / 2.0
    best = None
    best_key = None
    for (sx, sy, sw, sh) in stems:
        scx = sx + sw / 2.0
        covers = sy - 50 <= ymid <= sy + sh + 50
        dd = abs(scx - (cx1 + cx2) / 2.0)
        key = (0 if covers else 1, dd)
        if best is None or key < best_key:
            best_key = key
            best = (scx, sy, sw, sh, covers)
    scx = best[0]
    side1 = "right" if cx1 > scx else "left"
    side2 = "right" if cx2 > scx else "left"
    return dict(stem_x_center=scx, stem_covers=best[4], side1=side1, side2=side2,
                same_side=(side1 == side2))

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

pairs = []
for cellkey, subjs in by_cell.items():
    ss = cell_ss.get(cellkey)
    if not ss:
        continue
    subjs = sorted(subjs, key=glyph_index_of)
    n = len(subjs)
    for i in range(n):
        for j in range(i + 1, n):
            s1, s2 = subjs[i], subjs[j]
            if nclass[s1] != nclass[s2]:
                continue
            _, x1, y1, w1, h1 = gbox[s1]["value"]
            _, x2, y2, w2, h2 = gbox[s2]["value"]
            cx1, cy1 = x1 + w1 / 2.0, y1 + h1 / 2.0
            cx2, cy2 = x2 + w2 / 2.0, y2 + h2 / 2.0
            dy_sp = abs(cy1 - cy2) / ss
            if dy_sp > 1.2:
                continue
            dx = abs(cx1 - cx2)
            if dx > 1.6 * HEAD_W_MEDIAN:
                continue
            ox0, ox1 = max(x1, x2), min(x1 + w1, x2 + w2)
            overlap = max(0.0, ox1 - ox0)
            r = nearest_stem_and_sides(cellkey, cx1, cy1, cx2, cy2)
            rec = dict(
                cell=cellkey, g1=s1, g2=s2, cls=nclass[s1],
                dy_spaces=dy_sp, dx_px=dx, overlap_px=overlap,
                has_overlap=overlap > 0,
                refused1=notehead_verdict.get(s1, {}).get("value"),
                refused2=notehead_verdict.get(s2, {}).get("value"),
                verdict1=notehead_verdict.get(s1, {}).get("reason"),
                verdict2=notehead_verdict.get(s2, {}).get("reason"),
                event_status=event_status(cellkey, glyph_index_of(s1), glyph_index_of(s2)),
            )
            if r is None:
                rec["stem_side"] = "no_stem_in_cell"
            else:
                rec.update(r)
                rec["stem_side"] = "same" if r["same_side"] else "opposite"
            pairs.append(rec)

print("extended candidate pairs (dy<=1.2sp, dx<=1.6 head-widths, no overlap requirement):", len(pairs))
print("has_overlap distribution:", Counter(p["has_overlap"] for p in pairs))
print("\nstem_side x has_overlap crosstab:")
ct = Counter((p["has_overlap"], p["stem_side"]) for p in pairs)
for k, v in sorted(ct.items()):
    print(k, v)

print("\nrefusal status vs stem_side (both stand / one refused):")
def status(p):
    if p["refused1"] or p["refused2"]:
        return "one_refused"
    return "both_stand"
ct2 = Counter((status(p), p["stem_side"]) for p in pairs)
for k, v in sorted(ct2.items()):
    print(k, v)

with open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/pairs_a_extended.json", "w") as f:
    json.dump(pairs, f, indent=1, default=str)
