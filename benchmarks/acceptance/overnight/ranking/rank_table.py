"""The 2.229 product ranking (fix-actions per page, biggest first) for a BASE and a TAG record, side by side, and beside the
10-29 ranking (benchmarks/acceptance/FINDINGS.md "2026-10-29 product ranking").

Kind definitions are the ranking lane's, checked against FINDINGS on the 20261022-night Litolff record (counts on the same 9
loaded pages: ties/slurs 757 vs 751 quoted, dots 74 vs 73, heads 306 vs 309, red bars 265 vs 246 -- the FINDINGS figures are
from the 10-29 gather, so they differ by what changed between the records, not by definition).
  ROADMAP 2.316 (Sean 2026-11-18, count notes and arcs, not boxes): the two headline rows count what is printed, from `counted_marks`:
     "ties and slurs not written (arcs)"  = old-box refusals that are still refusals + page arc runs read and not written; a box a written page arc REPLACED
                                            and a box the old path RETIRED are not arcs lost (shown apart), a page run no detector box agrees with is shown apart
     "printed notes not written (candidate lost)" = head boxes with no written twin at their place and not claimed as other ink (overlapping boxes are one note);
                                            the duplicates of a written note and the non-note ink are shown apart, never counted as lost notes
     the old BOX rows stay printed beside them, labelled "(boxes, old figure)", so a night stays comparable with the ones before 2.316.
  1 ties and slurs not written (boxes, old figure) = every `arcs_not_written` reason except `not_an_arc:*` (an UPPER bound, see FINDINGS)
  2 red bars                   = bars written red (durations do not add up)
  3 unread empty bars          = the bars written as unread. FINDINGS' "bar printing a whole rest" is ~70% Litolff / ~65% Brahms
                                 of these by the lane's crops; that share is NOT recomputed here (needs a crop look)
  4 pitched heads not written (boxes, old figure) = dropped_unknown_duration + dropped_no_pitch (exporter accounting)
  5 dots decided, never placed = dot_role abstained_dot_role_ambiguous, LESS the dot-class boxes whose own ink is under the stroke map's
                                 floor (`counted_view`, ROADMAP 2.265: a speck is not a dot); the specks are printed under the table
  pages                        = the COUNTED sample pages only (2.265); the context page is loaded, never counted
  check load                   = blue notes / rests in the file
usage: rank_table.py WORKDIR PLATE BASE_ARM TAG_ARM NPAGES   (reads WORKDIR/PLATE.ARM.rank.json from rank_counts.py; NPAGES = counted pages)
"""
import json
import sys

# FINDINGS.md "2026-10-29 product ranking" table, quoted (per page, Litolff / Brahms). Not recomputed.
QUOTED = {
    "ties and slurs not written (boxes, old figure)": {"litolff": 83, "brahms": 160},
    "red bars": {"litolff": 27.3, "brahms": 20.5},
    "unread empty bars": {"litolff": 31.0, "brahms": 14.5},
    "pitched heads not written (boxes, old figure)": {"litolff": 34.3, "brahms": 46.3},
    "dots decided, never placed": {"litolff": 8.1, "brahms": 17.1},
    "blue notes (check load)": {"litolff": 138.4, "brahms": 107.0},
    "blue rests (check load)": {"litolff": 3.8, "brahms": 13.2},
}


DOTS_KIND = "dots abstained (dot_role_ambiguous, specks out; mostly non-dot ink, 2.234)"


def specks_of(path):
    d = json.load(open(path))["totals_over_loaded_pages"]
    return d.get("dot_specks_in_the_dots_row", 0), d["dot_role_not_placed"].get("abstained_dot_role_ambiguous", 0)


def new_counts(path):
    """ROADMAP 2.316: `(printed notes not written, census, arcs row, arcs count)` from a rank.json, None where the export predates 2.316 (never a 0 in its place)."""
    tot = json.load(open(path))["totals_over_loaded_pages"]
    nc, ac = tot.get("notes_census"), tot.get("arcs_count")
    return (nc["notes"]["candidate_lost"] if nc else None), nc, (ac["not_written_total"] if ac else None), ac


def kinds(path):
    d = json.load(open(path))
    rows, tot = d["rows"], d["totals_over_loaded_pages"]

    def r(k):
        return rows.get(k, {}).get("counted_total", 0)
    arcs = sum(v for k, v in tot["arcs_not_written"].items() if isinstance(v, int) and not k.startswith("not_an_arc:"))
    lost_notes, _nc, arcs_new, _ac = new_counts(path)
    return {
        "ties and slurs not written (arcs)": arcs_new,
        "ties and slurs not written (boxes, old figure)": arcs,
        "red bars": r("red_bar"),
        "unread empty bars": r("unread_empty_bar"),
        "printed notes not written (candidate lost)": lost_notes,
        "pitched heads not written (boxes, old figure)": r("dropped_unknown_duration") + r("dropped_no_pitch"),
        DOTS_KIND: tot["dot_role_not_placed"].get("abstained_dot_role_ambiguous", 0) - tot.get("dot_specks_in_the_dots_row", 0),
        "blue notes (check load)": r("blue_note"),
        "blue rests (check load)": r("blue_rest"),
    }


def main():
    work, plate, base, tag, n = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    a = kinds("%s/%s.%s.rank.json" % (work, plate, base))
    b = kinds("%s/%s.%s.rank.json" % (work, plate, tag))
    print("%s ranking, fix-actions per page over %d loaded pages, biggest first by TAG (BASE=%s TAG=%s)" % (plate, n, base, tag))
    print("%-46s %9s %9s %8s %12s   %s" % ("kind", "BASE/pg", "TAG/pg", "delta", "10-29 rank", "(totals BASE -> TAG)"))
    def num(v):
        return -1 if v is None else v
    order = sorted((k for k in b if "check load" not in k), key=lambda k: -num(b[k])) + [k for k in b if "check load" in k]
    for k in order:
        q = QUOTED.get(k, {}).get(plate)
        if a[k] is None and b[k] is None:
            print("%-46s %9s %9s %8s %12s   n/a (an export made before 2.316)" % (k, "-", "-", "-", "-" if q is None else "%.1f" % q))
            continue
        x, y = a[k], b[k]
        print("%-46s %9s %9s %8s %12s   %s -> %s" % (k, "-" if x is None else "%.1f" % (x / n), "-" if y is None else "%.1f" % (y / n),
                                                      "-" if x is None or y is None else "%+.1f" % ((y - x) / n),
                                                      "-" if q is None else "%.1f" % q, "n/a" if x is None else x, "n/a" if y is None else y))
    for arm, nm in ((base, "BASE"), (tag, "TAG")):
        _ln, nc, _an, ac = new_counts("%s/%s.%s.rank.json" % (work, plate, arm))
        if nc:
            bx = nc["boxes"]
            print("%s notes: written %d of %d printed; named apart (never lost notes): duplicates of a written note %d boxes, non-note ink %d boxes, "
                  "duplicate with no written twin %d boxes; candidate lost by fate %s" % (
                      nm, nc["notes"]["written"], nc["notes"]["printed"], bx["duplicate_of_written"], bx["non_note_ink"], bx["duplicate_no_written_twin"],
                      {c: v for c, v in nc["notes"]["candidate_lost_by_cause"].items() if v}))
        if ac:
            ap = ac["apart"]
            print("%s arcs: old-box refusals %d + page runs read and not written %s; named apart: boxes replaced by a written page arc %d, old box path retired %d "
                  "(bookkeeping boxes), boxes that are no arc %d, unwitnessed page runs %s (mostly fakes; counting them: %d)" % (
                      nm, ac["old_box_refusals"], ac["page_runs_not_written"], ap["replaced_by_page_arc_boxes"], ap["old_box_path_retired_boxes"],
                      ap["not_an_arc_boxes"], ap["unwitnessed_page_runs"], ac["with_unwitnessed"]))
    for arm, nm in ((base, "BASE"), (tag, "TAG")):
        sp, raw = specks_of("%s/%s.%s.rank.json" % (work, plate, arm))
        print("%s dots row: %d abstained dot_role_ambiguous, %d of them dot-class boxes under the stroke floor (specks) -> %d counted" % (nm, raw, sp, raw - sp))


if __name__ == "__main__":
    main()
