"""ROADMAP 2.22 -- base vs arm, from the two `held_funnel_mvt_2_22.py` dumps.

Prints held bars, released / newly held (by cell), `<note>` elements, the
exporter's `notes_not_written`, and `reconcile_duration`'s own firing count
is read off the arm's summary where present.

    python3 .../price_2_22.py <out dir> <base label> <arm label>
"""
import json
import sys


def main():
    R, base, arm = sys.argv[1:4]
    b = json.load(open(f"{R}/{base}-redecided.held.json"))
    a = json.load(open(f"{R}/{arm}-redecided.held.json"))
    cb = {tuple(x["cell"]) for x in b["bars"]}
    ca = {tuple(x["cell"]) for x in a["bars"]}
    out = {
        "bars_held_out_sum": [b["bars_held_out_sum"], a["bars_held_out_sum"]],
        "of_bars_with_events": [b["of_bars_with_events"],
                                a["of_bars_with_events"]],
        "released": len(cb - ca), "newly_held": len(ca - cb),
        "newly_held_cells": sorted(ca - cb)[:20],
        "notes_in_file": [b["notes_in_file"], a["notes_in_file"]],
        "notes_not_written_changed": {
            k: [b["notes_not_written"].get(k, 0), a["notes_not_written"].get(k, 0)]
            for k in sorted(set(b["notes_not_written"]) | set(a["notes_not_written"]))
            if b["notes_not_written"].get(k, 0) != a["notes_not_written"].get(k, 0)},
        "written_changed": {
            k: [b["written"].get(k, 0), a["written"].get(k, 0)]
            for k in ("notes", "rests", "measure_rests_read", "bars_with_events")
            if b["written"].get(k) != a["written"].get(k)},
    }
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(f"{R}/price-{arm}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
