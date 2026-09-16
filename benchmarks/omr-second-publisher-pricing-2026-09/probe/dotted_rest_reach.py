"""THE DOTTED REST, on the document its own FINDINGS named — REACH ONLY.

`benchmarks/omr-staged-dotted-rest-2026-09/FINDINGS.md`: the repair moved ZERO
verdicts on Litolff Beethoven 5 because that plate holds **20 `aug_dot` rows in
total**, and it names *"Breitkopf Brahms 1 is the document to re-run it on"* —
which fires **656**. This asks whether the 33x bigger dot population actually
reaches a REST.

⚠️⚠️ IT NEEDS NO ARM, AND THAT IS THE POINT. The dotted-rest repair is ALREADY
IN the tree the shared record was gathered on, so the record's own `duration`
verdicts carry the answer: a rest ruling is `{"is_rest": true, "dots": N}`. Re-
adjudicating to discover a number the artefact already states would be paying
two hours for the tool's own output.

⚠️ REACH IS NOT PAYOFF. `dots > 0` on a rest says the rule FIRED, never that
the page prints a dot there. The Litolff work's own conclusion — *this is
CONSISTENCY, not payoff, and must never be quoted as a reading improvement* —
is inherited, not re-litigated.

    python3 dotted_rest_reach.py --record R [--record R2 ...]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="append", required=True)
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()

    out = {}
    for i, path in enumerate(a.record):
        label = a.label[i] if i < len(a.label) else path
        rec = json.load(open(path))["record"]
        obs = collections.Counter(o["quantity"] for o in rec["observations"])
        dots_gathered = obs.get("aug_dot", 0)
        rests_gathered = obs.get("rest", 0)

        note_dots = rest_dots = notes = rests = 0
        rest_dot_rows = []
        for v in rec["verdicts"]:
            if v["quantity"] != "duration" or v.get("outcome") != "decided":
                continue
            val = v.get("value") or {}
            if not isinstance(val, dict):
                continue
            n = int(val.get("dots") or 0)
            if val.get("is_rest"):
                rests += 1
                if n:
                    rest_dots += 1
                    rest_dot_rows.append({"subject": v["subject"],
                                          "dots": n,
                                          "beats": val.get("beats")})
            else:
                notes += 1
                if n:
                    note_dots += 1

        print(f"=== {label} ===")
        print(f"  gathered   `aug_dot` rows          {dots_gathered:>6}")
        print(f"  gathered   `rest` rows             {rests_gathered:>6}")
        print(f"  decided    NOTE durations          {notes:>6}"
              f"   of which DOTTED {note_dots:>5}")
        print(f"  decided    REST durations          {rests:>6}"
              f"   of which DOTTED {rest_dots:>5}"
              f"   <-- the repair's reach")
        for r in rest_dot_rows[:20]:
            print(f"      {r['subject']:<26} dots={r['dots']} "
                  f"beats={r['beats']}")
        print()
        out[label] = {"aug_dot_rows": dots_gathered,
                      "rest_rows": rests_gathered,
                      "note_durations": notes, "dotted_notes": note_dots,
                      "rest_durations": rests, "dotted_rests": rest_dots,
                      "dotted_rest_rows": rest_dot_rows}

    if not out:
        print("NOTHING READ — dead instrument.", file=sys.stderr)
        return 2
    if not any(v["aug_dot_rows"] for v in out.values()):
        print("NO `aug_dot` ROWS IN ANY RECORD — a zero here would be about "
              "the projection, not about the pages.", file=sys.stderr)
        return 2
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
        print(f"wrote -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
