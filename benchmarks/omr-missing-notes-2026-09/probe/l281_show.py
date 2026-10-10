#!/usr/bin/env python3
"""l281_show: what the extract holds for given head keys -- duration verdicts at every stage
(with the counters the decision branched on), HEAD_STEM, STEM_DIRECTION, the tip rows.

    python3 l281_show.py --ext DIR --tag brahms KEY [KEY ...]
"""
import argparse
import json
from pathlib import Path

FIELDS = ("beam_side", "stems_attached", "beams_by_stem", "beams_not_by_ink", "beams_not_by_ink_why",
          "beams_neighbour_staff", "beams_decided_arc", "beams_far_side", "beams_beyond_stem",
          "levels_certain", "levels_possible", "cv_beams", "yolo_beams", "yolo_kept",
          "dots_attached", "flags_attached", "head_is_open")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    ext = Path(a.ext)
    ver = json.loads((ext / f"{a.tag}-ver.json").read_text())["verdicts"]
    obs = json.loads((ext / f"{a.tag}-obs.json").read_text())
    ab = json.loads((ext / f"{a.tag}-abs.json").read_text())["tips_abs"]
    for k in a.keys:
        cell = "cell/" + "/".join(k.split("/")[1:5])
        print("==", k, obs["heads"].get(k, {}).get("cls"), "page box", obs["heads"].get(k, {}).get("page"))
        for r in ver.get(k, []):
            if r["q"] == "duration":
                print(f"  {r['stage']:9s} {r['decider']:36s} {r['outcome']:9s} {r['reason']}  value={r.get('value')}")
                if r["stage"] == "ADJUDICATE":
                    d = r["detail"]
                    print("     ", {x: d.get(x) for x in FIELDS if x in d})
                    print("      cands", r.get("cands"))
            elif r["q"] in ("head_stem", "stem_direction", "stem_value"):
                print(f"  {r['q']:14s} {r['outcome']:9s} {r['reason']} {r.get('value')}")
        print("  reach:", obs["reach"].get(k))
        for t in obs["tips"].get(cell, []):
            print("  tip row:", t)
        for t in ab.get(cell, []):
            print("  tip abst:", t)
        print("  stems in cell:", obs["stems"].get(cell))


if __name__ == "__main__":
    main()
