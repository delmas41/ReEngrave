#!/usr/bin/env python3
"""l281_later: what the stages AFTER ADJUDICATE did with the 2.81 population, per movement
(measure (c) of the brief). EVALUATE (`reconcile_duration`, `share_stem_value`,
`reconcile_chord_duration`) and INFER (`collapse_duration_by_column`,
`collapse_duration_to_barline`) supersede a narrowed duration verdict; the CURRENT verdict is
the last one nothing supersedes. Counts here are over ALL record heads too, so that "INFER
settled 0 of this population" is read against "INFER settled N elsewhere" -- the control that
says the stage ran at all.

    python3 l281_later.py --ext DIR --tag brahms [--scored scored.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_population import build, level_of, wilson  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--scored", default=None)
    a = ap.parse_args()
    d, pop, n_heads, sc = build(a.ext, a.tag)
    ver = d["ver"]["verdicts"]
    print(f"== {a.tag}: population {len(pop)}")
    # (1) the stage control: INFER's duration verdicts over EVERY head of the record
    allc = collections.Counter()
    for key, rows in ver.items():
        if key not in d["obs"]["heads"]:
            continue
        for r in rows:
            if r["q"] == Q.DURATION and r["stage"] in ("EVALUATE", "INFER"):
                allc[(r["stage"], r["decider"], r["outcome"])] += 1
    print("all heads, duration verdicts written by EVALUATE / INFER (the stage control):")
    for k, v in sorted(allc.items()):
        print(f"   {k}: {v}")
    # (2) the population
    cur = collections.Counter()
    for m in pop:
        cur[(m["final_stage"], m["final_decider"], m["final_outcome"],
             level_of(m["final_value"]) if m["final_outcome"] == "decided" else None)] += 1
    print("population: current verdict by (stage, decider, outcome, beam level):")
    for k, v in sorted(cur.items(), key=lambda kv: -kv[1]):
        print(f"   {k}: {v}")
    settled = [m for m in pop if m["final_stage"] != "ADJUDICATE"]
    print(f"settled by a later stage: {len(settled)} of {len(pop)} "
          f"({100.0 * len(settled) / max(1, len(pop)):.1f}%); "
          f"INFER {sum(1 for m in pop if m['final_stage'] == 'INFER')}")
    lv = collections.Counter(level_of(m["final_value"]) for m in settled)
    print("  settled to beam level:", dict(lv))
    # which settled to a level the ADJUDICATE candidates did not hold?
    nc = 0
    for m in settled:
        cands = {c.get("beam_levels") for c in (m["cands"] or [])}
        if level_of(m["final_value"]) not in cands:
            nc += 1
    print(f"  settled outside the narrowing's own candidates: {nc}")
    if a.scored:
        rows = json.loads(Path(a.scored).read_text())
        j = [r for r in rows if r["judge"] in ("right", "wrong_beam", "wrong_fill")]
        s = [r for r in j if r["final_stage"] != "ADJUDICATE"]
        print(f"hand truth (page 0): judged {len(j)}; settled by a later stage {len(s)}")
        for r in s:
            print(f"   {r['key']} {r['final_stage']} level {r['final_level']} truth {r['judge']}"
                  f" (truth level {r.get('truth_levels')})")


if __name__ == "__main__":
    main()
