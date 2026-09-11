"""THE LONE NOTE OF EACH UNDERFULL BAR, traced back to its own ink.

The population probe says a bar holds one note and half a bar's worth of time;
this says WHICH DETECTION that note is, where its box sits relative to the
staff, and what the record holds beside it. That is the join a cause needs:
"a whole rest read as a notehead" and "the staff above's note landed here" are
both one lone note in an underfull bar, and only the BOX tells them apart.

⚠️ It reports every lone bar in three buckets and the buckets are a PARTITION
with a residue -- `elsewhere` is printed, never folded into either story.

    python3 .../lone.py --record R --cands strict.json
"""
from __future__ import annotations

import argparse
import collections
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--cands", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]

    spacing, lines = {}, {}
    for o in rec["observations"]:
        k = tuple(int(x) for x in o["subject"].split("/")[1:4]) \
            if o["subject"].startswith("staff/") else None
        if o["quantity"] == "staff_spacing" and k:
            spacing[k] = float(o["value"])
        elif o["quantity"] == "staff_lines" and k:
            lines[k] = o["value"]

    box, cls, conf = {}, {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            pg = (o.get("detail") or {}).get("bbox_page_px")
            if pg:
                box[o["subject"]] = pg
            cls[o["subject"]] = o["value"][0]
        elif o["quantity"] == "glyph_conf":
            conf[o["subject"]] = o["score"]
    npos = {o["subject"]: o["value"] for o in rec["observations"]
            if o["quantity"] == "notehead_staff_position"}
    restcls = {o["subject"]: o["value"] for o in rec["observations"]
               if o["quantity"] == "rest"}

    pitch = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "pitch" and v["outcome"] == "decided":
            pitch[v["subject"]] = v["value"]

    cands = json.load(open(a.cands))
    lone = [c for c in cands if c.get("lone")]
    print(f"candidate bars                       {len(cands)}")
    print(f"  lone-note bars                     {len(lone)}")
    print(f"  record: notehead positions         {len(npos)}")
    print(f"  record: pitch verdicts             {len(pitch)}")
    print(f"  record: rest glyph rows            {len(restcls)}")
    print()

    buckets = collections.Counter()
    rows = []
    for c in lone:
        key = (c["page"], c["system"], c["staff"])
        pre = f"glyph/{c['page']}/{c['system']}/{c['staff']}/{c['cell']}/"
        here = [s for s in box if s.startswith(pre)]
        heads = [s for s in here if s in npos]
        rests_here = [(s, restcls[s]) for s in here if s in restcls]
        want = {e["pitch"] for e in c["events"] if e["pitch"]}
        # the written note: the head whose decided pitch is the one exported
        mine = [s for s in heads
                if pitch.get(s) and _spell(pitch[s]) in want]
        sp = spacing.get(key)
        ly = lines.get(key)
        rec_row = {
            "part": c["part"], "measure": c["measure"], "page": c["page"],
            "system": c["system"], "staff": c["staff"], "cell": c["cell"],
            "exported": sorted(want), "n_heads_in_cell": len(heads),
            "rests_in_cell": [r[1] for r in rests_here],
        }
        if not mine or not sp or not ly:
            buckets["unlocated"] += 1
            rec_row["bucket"] = "unlocated"
            rows.append(rec_row)
            continue
        s = mine[0]
        b = box[s]
        top, bot = min(ly), max(ly)
        cy = (b[1] + b[3]) / 2.0
        # staff position, bottom line = 0, one step per half space
        step = (bot - cy) / (sp / 2.0)
        rec_row.update({
            "subject": s, "a": round((b[2] - b[0]) / max(1e-6, b[3] - b[1]), 3),
            "cls": cls[s], "conf": round(conf.get(s) or 0, 3),
            "h_sp": round((b[3] - b[1]) / sp, 3),
            "w_sp": round((b[2] - b[0]) / sp, 3),
            "aspect": round((b[2] - b[0]) / max(1e-6, b[3] - b[1]), 3),
            "step_from_bottom_line": round(step, 2),
            "pos_recorded": npos.get(s),
        })
        if step > 8.5:
            rec_row["bucket"] = "above the staff"
        elif step < -0.5:
            rec_row["bucket"] = "below the staff"
        else:
            rec_row["bucket"] = "inside the staff"
        buckets[rec_row["bucket"]] += 1
        rows.append(rec_row)

    print("=== where the LONE note's own ink sits ===")
    for k, v in buckets.most_common():
        print(f"  {k:<22} {v}")
    print()

    inside = [r for r in rows if r.get("bucket") == "inside the staff"]
    if inside:
        pc = collections.Counter(r["step_from_bottom_line"] for r in inside)
        print("=== inside-the-staff: staff step of the lone note ===")
        print("    (a WHOLE REST hangs under the 4th line: step 6 down to 5)")
        for k, v in sorted(pc.items()):
            print(f"  step {k:>5}   {v}")
        print()
        h = sorted(r["h_sp"] for r in inside)
        asp = sorted(r["aspect"] for r in inside)
        print(f"  height  median {h[len(h)//2]:.3f}  [{h[0]:.3f}..{h[-1]:.3f}]")
        print(f"  aspect  median {asp[len(asp)//2]:.3f}  "
              f"[{asp[0]:.3f}..{asp[-1]:.3f}]")
        print(f"  cells that ALSO hold a detected rest: "
              f"{sum(1 for r in inside if r['rests_in_cell'])} of {len(inside)}")

    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(rows)} rows -> {a.json}")


def _spell(v):
    if isinstance(v, dict):
        return f"{v.get('step')}{v.get('octave')}"
    return str(v)


if __name__ == "__main__":
    main()
