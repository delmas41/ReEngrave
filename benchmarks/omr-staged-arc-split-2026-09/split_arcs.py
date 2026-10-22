"""WHY does `_paired_spans` refuse an arc? A read-only split, no truth file.

`benchmarks/omr-staged-arc-export-2026-09` reports one number --
`arc_binds_fewer_than_two_notes` -- and the handoff that landed it ranked
splitting that number first, because "arcs over notes that exist but were not
detected" and "arcs whose notes are there and the geometry missed them" need
different repairs.

⚠️ THE SPLIT NEEDS NOTHING BUT THE RECORD. The staged export calls
`_paired_spans(..., voice_of={})`, so the one-voice half of that function's
rule is structurally unreachable on this path and EVERY refusal is the two-note
minimum. Asserted below by AST rather than assumed, because if a voice map ever
arrives this classifier silently starts mixing two causes.

⚠️ IT IS A PARTITION AND SAYS SO. A + B + C + paired must equal the merged
group count the exporter itself reports, and `paired` must equal what the file
holds plus the chord collapse. A classifier that merely produces plausible
buckets is how a bucket stops being evidence -- see `--pad-sweep`, whose first
reading was inverted by an index map that looked fine.

    python3 split_arcs.py <staged.json>
    python3 split_arcs.py <staged.json> --pad-sweep
"""
from __future__ import annotations

import collections
import inspect
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged.export import Record         # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402
from tools.omr import export as L                  # noqa: E402


def _assert_voice_map_is_empty() -> None:
    """⚠️ The premise of the whole classifier, checked rather than believed.

    `_paired_spans` refuses on FOUR conditions: fewer than two heads under the
    arc, both ends on one detection, fewer than two heads in the START head's
    voice, and both in-voice ends on one detection. The last two can only fire
    with a non-empty `voice_of`. The staged path passes `{}`, so they cannot --
    and this classifier would silently misattribute them if that changed.
    """
    src = inspect.getsource(SX._pair_arcs)
    flat = "".join(src.split())
    assert "breaks,{})" in flat, (
        "the staged arc pairing no longer passes an EMPTY voice map -- the "
        "one-voice refusals are now reachable and this classifier, which "
        "attributes every refusal to the two-note minimum, is wrong")


def _origin_of_each_measure(part) -> list:
    """`(page, system, staff, cell)` per flattened measure.

    ⚠️ `range(run.n_measures)`, NOT `sorted(run.cells)`. `_flatten_part`
    appends a measure for EVERY index of the run, including ones that grew no
    `Cell` -- so a `sorted(run.cells)` map slides on the first empty bar. It
    was written that way first, and the sibling-staff rate it produced (39 of
    170) was wrong in the direction that FLATTERED the hypothesis under test;
    the corrected map reads 163 of 170, which the null then kills anyway. The
    length assertion is what makes the difference loud.
    """
    origin = []
    for run in part:
        for ci in range(run.n_measures):
            origin.append((run.page, run.system, run.staff, ci))
    return origin


def _noteheads_by_cell(parts) -> dict:
    """`(page, system, cell) -> [(staff, x_centre)]` over the whole page."""
    out = collections.defaultdict(list)
    for part in parts:
        for run in part:
            for ci, cell in run.cells.items():
                for det in L._measure_noteheads({"detections": cell.detections}):
                    b = det["bbox_page"]
                    out[(run.page, run.system, ci)].append(
                        (run.staff, b[0] + b[2] / 2.0))
    return out


def _classify(measures, segments, covered) -> str:
    """Which refusal this is -- and ⚠️ each bucket ASSERTS the claim its name
    makes, because the partition above cannot.

    A mutation arm proved it: collapsing A into B leaves every group in exactly
    one bucket, so the partition stays green and the reported answer is wrong.
    The bucket NAME is the claim a reader trusts and the only part they cannot
    check by reading, so it is checked here.
    """
    if len(covered) == 1 or (covered and covered[0][2] is covered[-1][2]):
        return "C_exactly_one_head_under_the_span"
    bar_heads = sum(len(L._measure_noteheads(measures[i])) for i, _ in segments)
    if bar_heads == 0:
        return "A_no_head_anywhere_in_the_arcs_own_bars"
    assert bar_heads > 0, "B claims the bars hold heads and they do not"
    return "B_bars_hold_heads_none_under_the_span"


def split(parts, pad: float = L._SLUR_ARC_PAD_NOTEHEADS):
    """`(cause counter, sibling counter)` over every merged arc group."""
    cause: collections.Counter = collections.Counter()
    sibling: collections.Counter = collections.Counter()
    by_cell = _noteheads_by_cell(parts)
    for part in parts:
        measures, arcs, kinds, spacings, tops, breaks = SX._flatten_part(part)
        if not measures or not any(arcs):
            continue
        origin = _origin_of_each_measure(part)
        assert len(origin) == len(measures), (len(origin), len(measures))
        by_kind, n_groups = SX._arcs_by_kind(measures, arcs, kinds, spacings,
                                             tops, breaks)
        # ⚠️ THE PARTITION, TAKEN FROM THE EXPORTER'S OWN COUNT. `_arcs_by_kind`
        # returns the group total rather than letting a caller derive it --
        # because `len(out[kind])` is the number of BARS, which is what an
        # earlier version summed. Every group must land in exactly one bucket;
        # a classifier whose buckets merely look plausible is not evidence.
        seen_before = sum(cause.values())
        for _kind, pools in by_kind.items():
            for segments in L._merge_arcs_across_barlines(
                    measures, pools, spacings, tops, breaks):
                covered = L._noteheads_under(measures, segments,
                                             pad_notehead_widths=pad)
                paired = (len(covered) >= 2
                          and covered[0][2] is not covered[-1][2])
                c = "PAIRED" if paired else _classify(measures, segments,
                                                      covered)
                cause[c] += 1
                # ⚠️ THE NULL TRAVELS WITH THE SIGNAL. "A sibling staff has
                # heads under this x" is counted for the PAIRED arcs too,
                # because on a 12-part page almost any x has someone playing
                # and the rate is meaningless without its base rate.
                m0 = segments[0][0]
                pg, sy, st, ci = origin[m0]
                ax = segments[0][1][0]
                bx = segments[-1][1][0] + segments[-1][1][2]
                if any(s2 != st and ax <= xc <= bx
                       for (s2, xc) in by_cell.get((pg, sy, ci), ())):
                    sibling[c] += 1
        assert sum(cause.values()) - seen_before == n_groups, (
            "the buckets do not partition this part's merged arcs: "
            f"{sum(cause.values()) - seen_before} classified vs "
            f"{n_groups} groups")
    return cause, sibling


def _anchor_paired_against_the_file(path: str, paired: int) -> None:
    """⚠️ THE PARTITION ALONE CANNOT SEE WHICH BUCKET A GROUP LANDED IN.

    Inverting the `paired` test still puts every group in exactly one bucket,
    so the partition assertion above stays green -- a mutation arm proved it.
    The same lesson the arc export itself recorded: *counting spans cannot see
    a frame error; only naming the NOTES can.*

    So `PAIRED` is anchored to something OUTSIDE this classifier: the arcs the
    exporter actually WRITES, plus the ones it drops at write time when a
    span's ends land in one chord. A group this probe calls paired is exactly
    a group `_paired_spans` returned, and those are the only two places one can
    end up.
    """
    xml, report = SX.to_musicxml(json.load(open(path)))
    written = report["written"]
    chord = report.get("arcs_not_written", {}).get("arc_ends_in_one_chord", 0)
    marked = written.get("slurs", 0) + written.get("ties", 0) + chord
    assert paired == marked, (
        f"this probe calls {paired} groups paired; the exporter wrote "
        f"{written.get('slurs', 0)} slurs + {written.get('ties', 0)} ties and "
        f"dropped {chord} into one chord = {marked}")


def main(argv) -> int:
    path = argv[1]
    rec = Record(json.load(open(path)))
    _assert_voice_map_is_empty()
    parts, _prov, _dropped, placement = SX.build(rec)

    # ── REACH, before any split ──────────────────────────────────────────────
    n_arcs = len(list(rec.obs_of(Q.ARC_BOX)))
    print(f"REACH: {n_arcs} arc_box rows, {sum(len(p) for p in parts)} "
          f"staff-runs, {len(parts)} parts")
    print(f"       drops BEFORE pairing: {dict(placement) or 'none'}")
    if not n_arcs:
        print("       ⚠️ this document shows NO arcs -- nothing below can move")
        return 0

    if "--pad-sweep" in argv:
        return _pad_sweep(parts)

    cause, sibling = split(parts)
    _anchor_paired_against_the_file(path, cause["PAIRED"])
    paired = cause.pop("PAIRED", 0)
    paired_sib = sibling.pop("PAIRED", 0)
    refused = sum(cause.values())
    print(f"\nMERGED GROUPS: {refused + paired}   "
          f"(refused {refused}, paired {paired})")
    for k in sorted(cause):
        print(f"  {k:<42} {cause[k]:>4}  ({cause[k] / refused:5.1%})")

    print("\n⚠️ A RATE, NEVER A COUNT OF ERRORS, and the base rate is the "
          "point -- a sibling staff playing under this x is a CANDIDATE for "
          "`arc_owner` only if it is rarer among the arcs that DID pair:")
    for k in sorted(cause):
        n, d = sibling.get(k, 0), cause[k]
        print(f"  {k:<42} {n:>4} of {d:<4} ({n / d:5.1%})")
    print(f"  {'PAIRED (the null)':<42} {paired_sib:>4} of {paired:<4} "
          f"({paired_sib / paired:5.1%})   <- base rate")
    return 0


def _pad_sweep(parts) -> int:
    """Is bucket B the PAD, or the arc geometry?

    ⚠️ `_SLUR_ARC_PAD_NOTEHEADS` (0.25) was read off a real GAP on an ENGRAVED
    Brahms page -- 54 of 75 near-misses within 0.19 notehead widths and the
    next at 0.32 -- and its docstring calls it a PLATEAU. No scan has ever
    priced it. A smooth decay with no plateau means the gap is not there, and
    widening is then buying pairings by reaching further with nothing to stop
    at, which is the symmetric metric's own trap in a different currency.

    ⚠️ Column A is pad-INVARIANT by construction (it is checked before the pad
    applies), so its flatness is a wiring check on this sweep and NOT evidence
    about anything.
    """
    print(f"\nPAD SWEEP (ships at {L._SLUR_ARC_PAD_NOTEHEADS} notehead widths)")
    print(f"{'pad':>6} {'paired':>7} {'A none':>7} {'B miss':>7} {'C one':>7}")
    for pad in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        c, _s = split(parts, pad=pad)
        print(f"{pad:>6} {c['PAIRED']:>7} "
              f"{c['A_no_head_anywhere_in_the_arcs_own_bars']:>7} "
              f"{c['B_bars_hold_heads_none_under_the_span']:>7} "
              f"{c['C_exactly_one_head_under_the_span']:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
