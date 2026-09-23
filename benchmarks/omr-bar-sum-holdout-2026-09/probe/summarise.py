"""Trim an arm's export report to something that belongs in the tree.

The full report names EVERY held bar, which on Brahms 1 is 4,560 rows and
2.3 MB — the right size for the artefact and the wrong size for git. This
writes the counts, the balances, and a 40-row sample verbatim, plus (for
Litolff) every held bar inside the count page, which is the window a human
actually opens against the plate.
"""
from __future__ import annotations

import collections
import json
import sys

O = "benchmarks/omr-bar-sum-holdout-2026-09/out/"


def summarise(doc: str) -> None:
    r = json.load(open(O + "arm-%s.report.json" % doc))
    held = r["bars_held_out_sum"]
    rows = held["held"]
    out = {k: v for k, v in held.items() if k != "held"}
    out["by_part_id"] = dict(collections.Counter(
        h["part"] for h in rows).most_common())
    out["by_kind"] = dict(collections.Counter(
        "overfull" if max(h["quarters"]) > h["want_quarters"] else "short"
        for h in rows))
    out["carried_meter"] = sum(1 for h in rows if h.get("meter_carried_in_file"))
    out["two_voice"] = sum(1 for h in rows if len(h["voices"]) > 1)
    out["sample_first_40"] = rows[:40]
    json.dump({
        "document": doc,
        "bars_held_out_sum": out,
        "written": r["written"],
        "balance": r["balance"],
        "notes_not_written": r["notes_not_written"],
        "arcs_not_written": r["arcs_not_written"],
        "articulation_balance": r["articulation_balance"],
        "ornament_balance": r["ornament_balance"],
        "wedge_balance": r["wedge_balance"],
        "fermata_balance": r["fermata_balance"],
        "direction_balance": r["direction_balance"],
        "status_census_unaccounted": r["status_census"]["unaccounted"],
        "part_join": r.get("part_join"),
    }, open(O + "arm-%s.summary.json" % doc, "w"), indent=1)
    print("%s: %d held bars, summary written" % (doc, held["bars"]))


def count_page() -> None:
    r = json.load(open(O + "arm-litolff.report.json"))
    page = [h for h in r["bars_held_out_sum"]["held"]
            if 49 <= int(h["measure"]) <= 82]
    json.dump({"_readme": "Every bar ROADMAP 2.8 held out inside the Litolff "
                          "count page (manifest pdf index 3 = bars 49-82). "
                          "Coordinates are (page, system, staff, cell); "
                          "`measure` is the document bar number the exported "
                          "file carries.",
               "n": len(page), "bars": page},
              open(O + "held-bars-litolff-count-page.json", "w"), indent=1)
    print("count page: %d held bars" % len(page))


if __name__ == "__main__":
    for d in (sys.argv[1:] or ["engraved", "litolff", "brahms"]):
        summarise(d)
    count_page()
