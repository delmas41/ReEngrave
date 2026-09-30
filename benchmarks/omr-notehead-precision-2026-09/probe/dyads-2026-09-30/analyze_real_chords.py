"""Look directly at every EVENT verdict of kind=='chord' on page 3 (any
size), and for each 2-glyph chord measure the staff-position gap (in half-
steps/lines-and-spaces) between its two members, whether their boxes
overlap, and which side of the nearest stem each head's centre falls on.
This is the population that actually tests the manager's stem-side
convention, since it is the reader's own chord grouping, not a geometric
guess.
"""
import pickle, json
from collections import defaultdict, Counter

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))

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

rows = []
for cellkey, ev in event_verdict.items():
    if ev.get("outcome") != "decided":
        continue
    for e in ev["value"].get("events", []):
        if e.get("kind") != "chord":
            continue
        glyphs = e.get("glyphs", [])
        if len(glyphs) < 2:
            continue
        prefix = cellkey.replace("cell", "glyph", 1)
        subjs = [f"{prefix}/{gi}" for gi in glyphs]
        # all pairs within the chord
        for i in range(len(subjs)):
            for j in range(i + 1, len(subjs)):
                s1, s2 = subjs[i], subjs[j]
                if s1 not in gbox or s2 not in gbox:
                    continue
                pos1, pos2 = npos.get(s1), npos.get(s2)
                if pos1 is None or pos2 is None:
                    continue
                _, x1, y1, w1, h1 = gbox[s1]["value"]
                _, x2, y2, w2, h2 = gbox[s2]["value"]
                cx1, cy1 = x1 + w1/2, y1 + h1/2
                cx2, cy2 = x2 + w2/2, y2 + h2/2
                ss = cell_ss.get(cellkey, 100.0)
                dy_sp = abs(cy1 - cy2) / ss
                pos_gap = abs(pos1 - pos2)  # in half-steps (each staff line/space = 1 unit? check)
                ox0, ox1 = max(x1, x2), min(x1+w1, x2+w2)
                overlap = max(0.0, ox1 - ox0)
                r = nearest_stem_and_sides(cellkey, cx1, cy1, cx2, cy2)
                rows.append(dict(
                    cell=cellkey, g1=s1, g2=s2, cls1=nclass.get(s1), cls2=nclass.get(s2),
                    pos1=pos1, pos2=pos2, pos_gap=pos_gap, dy_spaces=dy_sp,
                    has_overlap=overlap > 0,
                    refused1=notehead_verdict.get(s1, {}).get("value"),
                    refused2=notehead_verdict.get(s2, {}).get("value"),
                    stem_side=("no_stem_in_cell" if r is None else ("same" if r["same_side"] else "opposite")),
                    stem_covers=(None if r is None else r["stem_covers"]),
                ))

print("total chord-member pairs:", len(rows))
print("\npos_gap distribution (rounded):")
print(Counter(round(r["pos_gap"], 1) for r in rows))
print("\nstem_side x pos_gap<=1.2 (close, candidate 2nd/unison) vs >1.2 (wider chord interval):")
close = [r for r in rows if r["pos_gap"] <= 1.2]
wide = [r for r in rows if r["pos_gap"] > 1.2]
print("close (<=1.2 staff-pos units):", len(close), Counter((r["has_overlap"], r["stem_side"]) for r in close))
print("wide (>1.2):", len(wide), Counter((r["has_overlap"], r["stem_side"]) for r in wide))

json.dump(rows, open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/chord_pairs.json", "w"), indent=1, default=str)
