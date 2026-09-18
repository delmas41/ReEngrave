"""TWO THINGS THE WIDTH TABLE CANNOT ANSWER ON ITS OWN.

1. `[L4]` -- *A whole notehead is wider than a black one, and the same
   height*, which `docs/engraving-conventions.md` files as **LITERATURE ONLY,
   untested on any plate**, and whose own falsifier is *"a plate where whole
   and half heads measure the same width"*.

   ⚠️ IT CANNOT BE TESTED ON THE DETECTOR'S CLASS LABEL, and the crop pass is
   why: of 31 heads the record calls WHOLE it adjudicated 17 and found **16 of
   17 to be class-FALSE** (time-signature digits, staff-line gaps, a dotted
   half, a hairpin). So a class split measures the CLASS, not the convention.
   Both are reported, apart, and the honest verdict is about the class.

2. THE RULER. `benchmarks/omr-stem-stroke-2026-09/stroke_arm.py` computed the
   same test on the same records and reported `thin_boxes` 44 / 576. This
   probe reproduced 44 / 576 from the record -- but the two denominators are
   NOT the same quantity: that lane divides the page box by the **mean of the
   four printed staff-line gaps** recomputed from `Q.STAFF_LINES`, this one by
   the gathered **`Q.STAFF_SPACING`**. Equal counts at the threshold is
   evidence; equal counts everywhere is the stronger claim, and it is checked
   here rather than assumed.

   ⚠️ NEITHER IS AN INDEPENDENT MEASUREMENT OF THE INK. Both read the
   DETECTOR's box. Whether the box is as wide as the printed head is a raster
   question and is out of scope -- said out loud because "1.49 spaces wide"
   reads like a fact about engraving and is a fact about a bounding box.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
CROPDIR = BENCH.parent / "omr-stem-crop-pass-2026-09"
sys.path.insert(0, str(BENCH.parent / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

FLOOR = 1.0
RECORDS = {
    "litolff": "beethoven5-p1-p4.record.json",
    "breitkopf": "brahms1-breitkopf-p0-p3.record.json",
}
# the figures `stroke_arm.py` committed, to be reproduced not relayed
STROKE_THIN = {"litolff": 44, "breitkopf": 576}
STROKE_PLAUS = {"litolff": 749, "breitkopf": 953}


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(p * len(s)))] if s else float("nan")


def band(v):
    return {"n": len(v), "min": round(min(v), 3), "p5": round(q(v, .05), 3),
            "median": round(q(v, .50), 3), "p95": round(q(v, .95), 3),
            "max": round(max(v), 3)} if v else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records-dir", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    out = {"floor": FLOOR}
    for pub, fn in RECORDS.items():
        rec = Path(a.records_dir) / fn
        widths = json.loads(
            (BENCH / "out" / f"{pub}-widths.json").read_text())["rows"]
        W = {r["subject"]: r for r in widths}

        # ---- the SECOND ruler: page box / mean printed line gap ----
        lines = {}
        for o in stream_array(rec, "observations"):
            if o.get("quantity") == "staff_lines":
                v = o.get("value")
                if isinstance(v, list) and len(v) >= 5:
                    lines[o["subject"]] = [float(x) for x in v]
        second = {}
        for s, r in W.items():
            p = s.split("/")
            L = lines.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
            if not L or len(L) < 5:
                continue
            sp = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
            if sp > 0:
                second[s] = r["w_page"] * r["staff_spacing"] / sp

        dif = [abs(second[s] - W[s]["w_page"]) for s in second]
        # ⚠️ THE CONTROL THAT MATTERS: do the two rulers put the same boxes on
        # the same side of the floor? A max-difference can be small while the
        # boxes at the boundary still swap sides.
        swap = [s for s in second
                if (second[s] < FLOOR) != (W[s]["w_page"] < FLOOR)]
        rulers = {
            "n_compared": len(second),
            "max_abs_diff_spaces": round(max(dif), 4) if dif else None,
            "median_abs_diff_spaces": round(q(dif, .5), 4) if dif else None,
            "boxes_that_swap_sides_of_the_floor": len(swap),
            "swap_subjects": sorted(swap)[:10],
        }

        # ---- reproduce the stroke lane's own two figures ----
        no_stem = [r for r in widths if r["reason"] == "no_stem"]
        thin_mine = sum(1 for r in no_stem if r["w_page"] < FLOOR)
        thin_theirs = sum(1 for r in no_stem
                          if r["subject"] in second
                          and second[r["subject"]] < FLOOR)
        plaus_theirs = sum(1 for r in no_stem
                           if r["subject"] in second
                           and second[r["subject"]] >= FLOOR)
        rulers["stroke_lane_thin_boxes"] = {
            "published": STROKE_THIN[pub],
            "this_probe_staff_spacing_ruler": thin_mine,
            "this_probe_line_gap_ruler": thin_theirs,
        }
        rulers["stroke_lane_plausible_heads"] = {
            "published": STROKE_PLAUS[pub], "line_gap_ruler": plaus_theirs}

        # ---- [L4] on the detector's CLASS ----
        fam = collections.defaultdict(list)
        for r in widths:
            if r["outcome"] != "decided":
                continue
            k = ("Whole" if "Whole" in r["cls"]
                 else "Half" if "Half" in r["cls"] else "Black")
            fam[k].append(r)
        l4_class = {k: {"w": band([x["w_page"] for x in v]),
                        "h": band([x["h_page"] for x in v])}
                    for k, v in sorted(fam.items())}

        out[pub] = {"rulers": rulers, "L4_by_detector_class_decided": l4_class}

    # ---- [L4] against the PRINT, on the whole-note contradictions ----
    adjf = CROPDIR / "ADJUDICATION-wholenotes.json"
    if adjf.exists():
        adj = json.loads(adjf.read_text())
        rows = adj["rows"] if isinstance(adj, dict) else adj
        tile = {}
        for mn, pub in (("crop-manifest-wholenotes-B.json", "breitkopf"),
                        ("crop-manifest-wholenotes-L.json", "litolff")):
            mp = CROPDIR / "out" / mn
            if mp.exists():
                for t in json.loads(mp.read_text())["tiles"]:
                    tile[t["id"]] = (pub, t["subject"])
        Wall = {}
        for pub in RECORDS:
            for r in json.loads(
                    (BENCH / "out" / f"{pub}-widths.json").read_text())["rows"]:
                Wall[(pub, r["subject"])] = r
        wn = []
        for r in rows:
            k = tile.get(r.get("id"))
            if not k or k not in Wall:
                continue
            w = Wall[k]
            wn.append({"id": r.get("id"), "pub": k[0], "subject": k[1],
                       "cls": w["cls"], "verdict": r.get("verdict"),
                       "w": round(w["w_page"], 3), "h": round(w["h_page"], 3),
                       "what": (r.get("reason") or "")[:120]})
        out["L4_against_the_print"] = {
            "n_adjudicated": len(rows), "joined": len(wn),
            "note": ("every row here is a box the RECORD calls a WHOLE "
                     "notehead; the crop pass found 16 of 17 class-FALSE, so "
                     "this measures the CLASS and not the convention"),
            "rows": sorted(wn, key=lambda x: x["w"]),
        }

    Path(a.json).write_text(json.dumps(out, indent=1))
    for pub in RECORDS:
        r = out[pub]["rulers"]
        print(f"== {pub}: two rulers over {r['n_compared']} boxes")
        print(f"   max |diff| {r['max_abs_diff_spaces']} spaces, median "
              f"{r['median_abs_diff_spaces']}; boxes swapping sides of the "
              f"floor: {r['boxes_that_swap_sides_of_the_floor']}")
        t = r["stroke_lane_thin_boxes"]
        print(f"   thin boxes  published {t['published']}  | "
              f"staff_spacing ruler {t['this_probe_staff_spacing_ruler']}  | "
              f"line-gap ruler {t['this_probe_line_gap_ruler']}")
        print(f"   [L4] DECIDED, by detector class (w p5/med/p95):")
        for k, v in out[pub]["L4_by_detector_class_decided"].items():
            b = v["w"]
            print(f"      {k:<6} n={b['n']:<5} {b['p5']:.3f} / "
                  f"{b['median']:.3f} / {b['p95']:.3f}")
    if "L4_against_the_print" in out:
        p = out["L4_against_the_print"]
        print(f"\n== [L4] against the print: {p['joined']} of "
              f"{p['n_adjudicated']} whole-class boxes joined")
        for x in p["rows"]:
            print(f"   {x['id']} {x['pub']:<10} w={x['w']:.2f} h={x['h']:.2f} "
                  f"{x['cls']:<22} {x['verdict']}")
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
