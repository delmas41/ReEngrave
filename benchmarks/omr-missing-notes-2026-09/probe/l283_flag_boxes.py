#!/usr/bin/env python3
"""l283_flag_boxes: for Sean's flagged black heads, what the record holds about THEIR flag -- the detector's `flag*` boxes in
the head's cell (and whether a duration verdict used them), the head's CV stem / decided direction, and its `Q.HEAD_STEM_REACH`
row if the head was contested. Answers: why is `flags_attached` 0, and how many of the misses are missing STEMS rather than
missing flag READINGS. ROADMAP 2.83 probe.

    python3 l283_flag_boxes.py --record rec.json --rows truth_rows.json [--arm base|arm]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--arm", default="base")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    rows = json.loads(Path(a.rows).read_text())
    used = set()
    for v in run.verdicts:
        if v["quantity"] == Q.DURATION and v["decider"] == "adjudicate_duration":
            used.update(v.get("basis") or [])
    cnt = collections.Counter()
    for r in rows:
        if r["kind"] != "flag":
            continue
        key = r[a.arm + "_key"]
        if key is None:
            cnt["unmatched"] += 1
            continue
        g = run.glyphs[key]
        cell = g.cell_key
        flags = []
        for k, gg in run.glyphs.items():
            if gg.cell_key == cell and (gg.cls or "").startswith("flag"):
                fo = [o for o in run.obs_at(k, Q.GLYPH_BOX)]
                flags.append((k, gg.cls, [round(v) for v in gg.box_canon or []], any(o["id"] in used for o in run.obs_at(k, Q.FLAG))))
        stem = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        reach = run.obs_at(key, Q.HEAD_STEM_REACH)
        v = run.standing(key, Q.DURATION, "ADJUDICATE")
        det = (v or {}).get("detail") or {}
        cnt[("stem:" + (stem["outcome"] if stem else "none"), "reach:" + (reach[-1]["value"] if reach else "no_row"),
             "flag_boxes_in_cell:" + str(len(flags) > 0), "flags_attached:" + str(det.get("flags_attached")))] += 1
        print(r["truth"], key, "L=", r["level"], r[a.arm], "| stem", stem["outcome"] if stem else None, stem.get("reason") if stem else None,
              "| dir", sd["value"] if sd and sd["outcome"] == "decided" else None, "| reach", reach[-1]["value"] if reach else None,
              "| flag boxes in cell:", [(f[1], f[2], f[3]) for f in flags][:3], "| head box", [round(x) for x in g.box_canon or []])
    print()
    for k, n in cnt.most_common():
        print(n, k)


if __name__ == "__main__":
    main()
