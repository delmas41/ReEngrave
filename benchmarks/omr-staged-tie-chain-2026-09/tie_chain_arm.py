"""REACH FIRST, then the numbers — the tie CHAIN on a staged record.

    python3 benchmarks/omr-staged-tie-chain-2026-09/tie_chain_arm.py STAGED.json

⚠️⚠️ REACH IS PRINTED BEFORE ANYTHING ELSE, AND THAT ORDER IS THE POINT. *A
change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.* This document's
tie population is the first thing a reader needs, because every figure under
it is a share of it.

⚠️ NOTHING HERE RE-IMPLEMENTS THE PAIRING. It calls `_flatten_part`,
`_arcs_by_kind` and `tools.omr.export._paired_spans` — the same functions
`staged.export._pair_arcs` calls — so a reach figure cannot drift from what
the exporter does. The `EXPORT` block below then runs the real exporter and
prints its own counters beside them: two routes to one number, which is what
caught the first cut of the chain closure reading `{2: 50}` on a page whose
chains run to four notes.

⚠️ A DIRTY `provenance` DOES NOT SPOIL THIS ARM. It exports ONE record twice
(or reads one record twice) and never compares two records, which is the only
thing a dirty stamp forbids.
"""

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr import export as _legacy                       # noqa: E402
from tools.omr.staged import export as X                      # noqa: E402
from tools.omr.voicing import group_chords_in_measure         # noqa: E402


def reach(result):
    """The population, measured with the exporter's own pairing."""
    rec = X.Record(result)
    parts = X.build(rec)[0]
    c = collections.Counter()
    chains = []
    for part in parts:
        measures, arcs, kinds, spacings, tops, breaks = X._flatten_part(part)
        if not measures or not any(arcs):
            continue
        c["arc_boxes"] += sum(len(a) for a in arcs)
        c["arc_boxes_classed_tie"] += sum(
            1 for m in arcs for b in m if kinds.get(id(b)) == "tie")
        by_kind, _merged = X._arcs_by_kind(measures, arcs, kinds, spacings,
                                           tops, breaks)
        pool = by_kind.get("tie")
        if not pool:
            continue
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pool, spacings, tops, breaks):
            c["tie_groups_after_the_merge"] += 1
            if len(segments) > 1:
                c["tie_groups_merged_from_two_halves"] += 1
        spans = _legacy._paired_spans(measures, pool, spacings, tops, breaks,
                                      X._voice_of_notehead(rec, part))
        c["tie_links"] += len(spans)
        # ⚠️ Every head of every event, so a tie END can be asked whether the
        # chord it lands in writes the tie on IT or on the lowest member.
        where = {}
        for mi, m in enumerate(measures):
            for ev in group_chords_in_measure(m["detections"]):
                for h in ev.get("noteheads") or []:
                    where[id(h)] = (mi, ev.get("noteheads") or [])
        links = []
        for (sm, _sx), (tm, _tx), first, last in spans:
            links.append((id(first), id(last)))
            c["tie_links_crossing_a_barline"] += int(sm != tm)
            c["tie_links_crossing_a_system_break"] += int(
                any(b in range(sm + 1, tm + 1) for b in breaks))
            for head in (first, last):
                g = where.get(id(head))
                if g is None:
                    c["tie_end_head_in_no_event"] += 1
                    continue
                heads = g[1]
                if len(heads) > 1:
                    c["tie_ends_landing_in_a_chord"] += 1
                    if heads[0] is not head:
                        c["tie_ends_on_a_chord_member_that_is_NOT_lowest"] += 1
        chains.extend(X._chain_sizes(links).values())
    c["tie_chains"] = len(chains)
    c["tie_chains_longer_than_two_notes"] = sum(1 for n in chains if n > 2)
    return c, collections.Counter(chains)


EXPORT_KEYS = (
    "tie_links_marked", "tie_chains_marked", "tie_chains_over_two_notes",
    "tie_links_crossing_a_barline", "tie_links_crossing_a_system_break",
    "ties", "tie_spans_marked",
    "tie_starts_written_on_an_untied_note",
    "tie_stops_written_on_an_untied_note",
    "slurs", "slur_spans_marked", "notes", "rests")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("staged_json", nargs="+")
    args = ap.parse_args(argv)
    for path in args.staged_json:
        result = json.loads(pathlib.Path(path).read_text())
        print("=" * 72)
        print(path, " provenance:", result.get("provenance"))
        c, hist = reach(result)
        print("── REACH (the exporter's own pairing, no export run) ──")
        for k in sorted(c):
            print("  %-50s %d" % (k, c[k]))
        print("  chain length in NOTES -> how many:",
              {k: hist[k] for k in sorted(hist)})
        xml, rep = X.to_musicxml(result)
        print("── EXPORT (what the report now says) ──")
        for k in EXPORT_KEYS:
            print("  %-50s %d" % (k, rep["written"].get(k, 0)))
        print("  arcs_not_written:", rep["arcs_not_written"])
        print("  balance holds:", rep["balance"]["balanced"],
              " census unaccounted:",
              rep["status_census"].get("unaccounted"))
        for r in rep["families"]:
            if r["family"] in ("tie", "slur"):
                print("  census row:", {k: r.get(k) for k in (
                    "family", "detector_glyphs", "decided", "written",
                    "status")})
        print("  abstained_without_a_family:",
              rep["abstained_without_a_family"])
        # ⚠️ The two routes must agree, or one of them is wrong and the report
        # cannot say which. Printed rather than asserted: a record whose parts
        # do not join produces zeros on both sides and an assertion there
        # would read as a pass.
        same = (c["tie_links"] == rep["written"].get("tie_links_marked", 0)
                and c["tie_chains"] == rep["written"].get("tie_chains_marked",
                                                          0))
        print("  probe and exporter agree:", same)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
