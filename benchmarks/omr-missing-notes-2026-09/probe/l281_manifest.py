#!/usr/bin/env python3
"""l281_manifest: a plain-text view of `manifest.json` -- one line per tile of OUR reading (the hidden
fields), the strata, and the tiles whose frame control did not pass.

    python3 l281_manifest.py --dir OUT_DIR
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    m = json.loads((Path(a.dir) / "manifest.json").read_text())
    print("question:", m["question"], "| seed", m["seed"], "| frame sizes", m["frame_sizes"])
    print("frame control:", m["frame_control"])
    for t in sorted(m["tiles"], key=lambda t: t["id"]):
        h = t["hidden"]
        fc = t["frame_control"]
        fail = "" if fc["inside"] > fc["left"] and fc["inside"] > fc["right"] else "  <-- FRAME CONTROL DID NOT PASS"
        if t["kind"] == "control":
            print(f"{t['id']:10s} CONTROL {h['control']:6s} {h['key']}  truth: levels={h['truth']['truth_levels']} "
                  f"dots={h['truth']['truth_dots']}{fail}")
        else:
            print(f"{t['id']:8s} {h['movement']:8s} p{h['pdf_page']:<3d} stratum {h['stratum']}  tip={h['tip_status']:9s} "
                  f"stroke_at_tip={str(h['stroke_at_tip']):5s} dots={h['dots_read']}  ours: {h['our_reading']}  "
                  f"later={h['later_stages']['stage']}/{h['later_stages']['outcome']}"
                  f"{'/L' + str(h['later_stages']['beam_levels']) if h['later_stages']['beam_levels'] is not None else ''}"
                  f"  {h['key']}{fail}")


if __name__ == "__main__":
    main()
