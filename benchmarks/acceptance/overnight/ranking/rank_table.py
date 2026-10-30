"""The 2.229 product ranking (fix-actions per page, biggest first) for a BASE and a TAG record, side by side, and beside the
10-29 ranking (benchmarks/acceptance/FINDINGS.md "2026-10-29 product ranking").

Kind definitions are the ranking lane's, checked against FINDINGS on the 20261022-night Litolff record (counts on the same 9
loaded pages: ties/slurs 757 vs 751 quoted, dots 74 vs 73, heads 306 vs 309, red bars 265 vs 246 -- the FINDINGS figures are
from the 10-29 gather, so they differ by what changed between the records, not by definition).
  1 ties and slurs not written = every `arcs_not_written` reason except `not_an_arc:*` (an UPPER bound, see FINDINGS)
  2 red bars                   = bars written red (durations do not add up)
  3 unread empty bars          = the bars written as unread. FINDINGS' "bar printing a whole rest" is ~70% Litolff / ~65% Brahms
                                 of these by the lane's crops; that share is NOT recomputed here (needs a crop look)
  4 pitched heads not written  = dropped_unknown_duration + dropped_no_pitch (exporter accounting)
  5 dots decided, never placed = dot_role abstained_dot_role_ambiguous
  check load                   = blue notes / rests in the file
usage: rank_table.py WORKDIR PLATE BASE_ARM TAG_ARM NPAGES   (reads WORKDIR/PLATE.ARM.rank.json from rank_counts.py)
"""
import json
import sys

# FINDINGS.md "2026-10-29 product ranking" table, quoted (per page, Litolff / Brahms). Not recomputed.
QUOTED = {
    "ties and slurs not written": {"litolff": 83, "brahms": 160},
    "red bars": {"litolff": 27.3, "brahms": 20.5},
    "unread empty bars": {"litolff": 31.0, "brahms": 14.5},
    "pitched heads not written": {"litolff": 34.3, "brahms": 46.3},
    "dots decided, never placed": {"litolff": 8.1, "brahms": 17.1},
    "blue notes (check load)": {"litolff": 138.4, "brahms": 107.0},
    "blue rests (check load)": {"litolff": 3.8, "brahms": 13.2},
}


def kinds(path):
    d = json.load(open(path))
    rows, tot = d["rows"], d["totals_over_loaded_pages"]

    def r(k):
        return rows.get(k, {}).get("counted_total", 0)
    arcs = sum(v for k, v in tot["arcs_not_written"].items() if isinstance(v, int) and not k.startswith("not_an_arc:"))
    return {
        "ties and slurs not written": arcs,
        "red bars": r("red_bar"),
        "unread empty bars": r("unread_empty_bar"),
        "pitched heads not written": r("dropped_unknown_duration") + r("dropped_no_pitch"),
        "dots decided, never placed": tot["dot_role_not_placed"].get("abstained_dot_role_ambiguous", 0),
        "blue notes (check load)": r("blue_note"),
        "blue rests (check load)": r("blue_rest"),
    }


def main():
    work, plate, base, tag, n = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    a = kinds("%s/%s.%s.rank.json" % (work, plate, base))
    b = kinds("%s/%s.%s.rank.json" % (work, plate, tag))
    print("%s ranking, fix-actions per page over %d loaded pages, biggest first by TAG (BASE=%s TAG=%s)" % (plate, n, base, tag))
    print("%-30s %9s %9s %8s %12s   %s" % ("kind", "BASE/pg", "TAG/pg", "delta", "10-29 rank", "(totals BASE -> TAG)"))
    order = sorted((k for k in b if "check load" not in k), key=lambda k: -b[k]) + [k for k in b if "check load" in k]
    for k in order:
        q = QUOTED.get(k, {}).get(plate)
        print("%-30s %9.1f %9.1f %+8.1f %12s   %d -> %d" % (k, a[k] / n, b[k] / n, (b[k] - a[k]) / n,
                                                           "-" if q is None else "%.1f" % q, a[k], b[k]))


if __name__ == "__main__":
    main()
