"""lane-dot-not-a-note (ROADMAP 2.59): counts from the replays (OFF = the 10-07 night record re-adjudicated on today's tree
with the flag off, ON = with it on), plus a seeded montage of 40 dot-sized refused boxes cut from the print.

  python3 dot_not_a_note_counts.py <replay dir> [--seed 20261007]

Size test, stated before any count: a notehead-class box is DOT-SIZED when BOTH its width and height are <= 0.75 staff
spaces (a printed dot is ~0.5 sp, a notehead ~1.3 sp wide, `too_narrow`'s floor 1.0 sp).
Writes `out/dot_not_a_note_counts.json` beside this script and `out/print/dot_not_a_note_refused40.png`.
"""
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
from frame import render_page_matching_gather

DOCNAME = {"brahms": "brahms1-breitkopf", "lito": "beethoven5-litolff"}
MAXSP = 0.75


def load(d, short):
    return {m: json.loads((Path(d) / f"{short}_all_{m}.json").read_text()) for m in ("off", "on")}


def main(d, seed):
    out, refused_pool = {}, []
    for short in DOCNAME:
        try:
            R = load(d, short)
        except FileNotFoundError:
            continue
        off, on = R["off"], R["on"]
        c = collections.Counter()
        reasons_off, reasons_new = collections.Counter(), collections.Counter()
        flips = collections.Counter()
        for k, a in off["boxes"].items():
            b = on["boxes"][k]
            if a["w"] is None:
                continue
            c["notehead_class_boxes"] += 1
            sized = a["w"] <= MAXSP and a["h"] <= MAXSP
            if sized:
                c["dot_sized"] += 1
                ro = (a["np"] or {}).get("r") if (a["np"] or {}).get("v") is True else "KEPT"
                rb = (b["np"] or {}).get("r") if (b["np"] or {}).get("v") is True else "KEPT"
                reasons_off[ro] += 1
                reasons_new[rb] += 1
                if rb != "KEPT":
                    refused_pool.append((short, k, a, rb))
            if (a["np"] or {}).get("v") is not True and (b["np"] or {}).get("v") is True:
                c["newly_refused"] += 1
                c["newly_refused_dot_sized"] += int(sized)
                reasons_new["NEWLY:" + str(b["np"]["r"])] += 1
            if (a["np"] or {}).get("v") is True and (b["np"] or {}).get("v") is not True:
                c["refusal_lost"] += 1
            oa, ob = (a["own"] or {}), (b["own"] or {})
            if ob.get("r") == "dot_follows_note" and oa.get("v") != ob.get("v"):
                c["dot_shaped_box_owner_moved_to_the_dots_staff"] += 1
            da, db = (a["dur"] or {}).get("v"), (b["dur"] or {}).get("v")
            if da != db:
                c["notehead_duration_changed"] += 1
        c["dots"] = len(off["dots"])
        for k, a in off["dots"].items():
            b = on["dots"][k]
            ra, rb = (a["role"] or {}).get("v"), (b["role"] or {}).get("v")
            oa, ob = (a["role"] or {}).get("o"), (b["role"] or {}).get("o")
            if (oa, ra) != (ob, rb):
                flips[f"role {oa}:{ra} -> {ob}:{rb}"] += 1
            if (a["own"] or {}).get("v") != (b["own"] or {}).get("v"):
                flips["owner moved to the note's staff" if (b["own"] or {}).get("r") == "dot_follows_note" else "owner changed otherwise"] += 1
                if (a["own"] or {}).get("o") != "decided":
                    flips["  (the dot had no decided owner before)"] += 1
            if rb == "augmentation":
                c["dots_read_as_lengthening_on"] += 1
            if ra == "augmentation":
                c["dots_read_as_lengthening_off"] += 1
        out[short] = dict(counts=dict(c), dot_sized_reasons_off=dict(reasons_off), dot_sized_reasons_on=dict(reasons_new),
                          dot_changes=dict(flips))
    p = HERE / "out" / "dot_not_a_note_counts.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    # ---- seeded montage: 40 dot-sized refused boxes, cut from the print ----
    rng = random.Random(seed)
    pick = rng.sample(refused_pool, min(40, len(refused_pool)))
    tiles, grays = [], {}
    for short, k, a, why in pick:
        page = int(k.split("/")[1])
        if (short, page) not in grays:
            grays[(short, page)] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOCNAME[short]]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        g = grays[(short, page)]
        b = a["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        half = 44
        crop = cv2.cvtColor(g[int(cy - half):int(cy + half), int(cx - half):int(cx + half)], cv2.COLOR_GRAY2BGR)
        crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(crop, (int((b[0] - (cx - half)) * 3) - 2, int((b[1] - (cy - half)) * 3) - 2),
                      (int((b[2] - (cx - half)) * 3) + 2, int((b[3] - (cy - half)) * 3) + 2), (0, 140, 255), 1)
        pad = np.full((34, crop.shape[1], 3), 255, np.uint8)
        cv2.putText(pad, f"{len(tiles) + 1}. {short} p{page} {k.split('/', 2)[2]}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(pad, f"{why}  {a['w']:.2f}x{a['h']:.2f} sp", (2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (90, 90, 90), 1, cv2.LINE_AA)
        tiles.append(np.vstack([pad, crop]))
    cols = 8
    rows = []
    for i in range(0, len(tiles), cols):
        grp = tiles[i:i + cols]
        while len(grp) < cols:
            grp.append(np.full_like(tiles[0], 255))
        rows.append(np.hstack(grp))
    op = HERE.parents[1] / "out/print/dot_not_a_note_refused40.png"
    op.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(op), np.vstack(rows))
    print("wrote", op, "tiles", len(tiles), "pool", len(refused_pool))
    (HERE / "out" / "dot_not_a_note_refused40.json").write_text(json.dumps([(s, k, why) for s, k, a, why in pick]))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
