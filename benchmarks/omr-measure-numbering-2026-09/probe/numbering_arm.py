"""The A/B: one artefact numbered twice, per PART and per DOCUMENT.

    python3 benchmarks/omr-measure-numbering-2026-09/probe/numbering_arm.py
    python3 benchmarks/omr-measure-numbering-2026-09/probe/numbering_arm.py --check

⚠️⚠️ **WHY THIS IS NOT A RE-EXPORT, AND WHAT IT COSTS.** A cloud container has
no `omr-weights/` and no `library/`, so no staged record can be gathered here
and none is committed — `benchmarks/omr-cleanup-count-2026-09/out/` holds the
EXPORTED file and the SYSTEM MAP, not `record-p1-p4.json`. So the arm cannot
call `to_musicxml` on the real document. What it does instead is the same
move `export_arm.py` made when it built that map: it reconstructs the
exporter's own `StaffRun` objects from the map — which was asserted
measure-for-measure against this very XML when it was written — and calls the
**SHIPPED** `export._document_bar_offsets` on them. The rule under test is
therefore the one in the tree, not a restatement of it; what is reconstructed
is only its INPUT.

⚠️ THE BLIND SPOT, STATED RATHER THAN BURIED. An arm that re-numbers an
already-exported file is blind by construction to anything upstream of
`_part_xml`: a GATHER change, a join change, a note that did or did not reach
the file. It can say *"the numbers move here and the music does not"* and it
cannot say *"the exporter as a whole still behaves"* — that is the unit
suite's job, and `tools/omr/tests/test_staged_measure_numbering.py` drives
`to_musicxml` end to end on synthetic records for exactly that reason.

⚠️ ONE FIDELITY CONDITION IS CHECKED RATHER THAN ASSUMED. The map drops a
staff-run with zero measures, and a run whose `measure_partition` DECIDED zero
would be a vote for 0 that the map cannot show — so the arm asserts that every
system's map entries account for every staff the export's own provenance says
that system had (`staves_per_system`). If they ever do not, the
reconstruction is incomplete and the arm says so instead of scoring.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as SX          # noqa: E402

SYSTEM_MAP = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"
XML = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml"
OUT = HERE / "out"


# ─────────────────────────────────────────────────────────────────────────────
# Reconstruction — the exporter's own structures, from the exporter's own map
# ─────────────────────────────────────────────────────────────────────────────


def rebuild_parts(smap):
    """`[[StaffRun, ...], ...]` in the exporter's own part and system order."""
    by_part = collections.defaultdict(list)
    order = []
    for sd in smap["systems"]:
        key = (sd["page"], sd["system"])
        order.append(key)
        for st in sd["staves"]:
            run = SX.StaffRun(
                key=SX._staff_key(key[0], key[1], st["staff"]),
                page=key[0], system=key[1], staff=st["staff"],
                clef=st.get("clef"), fifths=st.get("fifths"),
                n_measures=int(st["n_measures"]),
                # ⚠️ TRUE ONLY BECAUSE THE FIDELITY CHECK BELOW PASSES. A map
                # entry exists iff the run wrote measures, and a run that
                # wrote measures is one whose partition decided.
                n_measures_decided=True)
            by_part[st["part_index"]].append((order.index(key), run))
    parts = []
    for pi in sorted(by_part):
        parts.append([r for _o, r in sorted(by_part[pi], key=lambda e: e[0])])
    return parts, order


def fidelity_problems(smap):
    """Does the map account for every staff the export says each system had?"""
    problems = []
    widths = set(smap["part_join"]["staves_per_system"])
    for sd in smap["systems"]:
        n = len(sd["staves"])
        if n not in widths:
            problems.append(
                "p%d/s%d: the map holds %d staves, the export's own "
                "staves_per_system is %s — a zero-measure run is missing and "
                "the reconstruction cannot see its vote"
                % (sd["page"], sd["system"], n, sorted(widths)))
    return problems


# ─────────────────────────────────────────────────────────────────────────────
# The two numberings, and the renumbered file
# ─────────────────────────────────────────────────────────────────────────────


def per_part_numbers(parts):
    """`{part_index: [(system_key, bar_in_system, number)]}` — the INCUMBENT."""
    out = {}
    for pi, part in enumerate(parts):
        n, rows = 0, []
        for run in part:
            for i in range(run.n_measures):
                n += 1
                rows.append(((run.page, run.system), i, n))
        out[pi] = rows
    return out


def document_numbers(parts, offsets):
    out = {}
    for pi, part in enumerate(parts):
        rows = []
        for run in part:
            base = offsets[(run.page, run.system)]
            for i in range(run.n_measures):
                rows.append(((run.page, run.system), i, base + i + 1))
        out[pi] = rows
    return out


_PART_SPLIT = re.compile(r'(?=  <part id=")')
_MEASURE = re.compile(r'(<measure number=")(\d+)(">)')


def renumber(xml, scheme):
    """Rewrite ONLY the `number=` attribute, part by part, in document order.

    ⚠️ IT REPLACES POSITIONALLY, never by matching the old number onto the new
    one. The nth `<measure>` of part P takes the nth number `scheme` gives
    part P — so a scheme that happened to agree with the incumbent on some
    measures cannot smuggle a mis-ordering past the diff.
    """
    chunks = _PART_SPLIT.split(xml)
    out, pi = [], 0
    for chunk in chunks:
        m = re.match(r'  <part id="(P\d+)"', chunk)
        if not m:
            out.append(chunk)
            continue
        wanted = [n for _k, _i, n in scheme[pi]]
        it = iter(wanted)
        seen = [0]

        def sub(mo):
            seen[0] += 1
            return mo.group(1) + str(next(it)) + mo.group(3)

        new = _MEASURE.sub(sub, chunk)
        if seen[0] != len(wanted):
            raise SystemExit(
                "part %s: the file holds %d measures, the scheme %d — the map "
                "and the file disagree" % (m.group(1), seen[0], len(wanted)))
        out.append(new)
        pi += 1
    if pi != len(scheme):
        raise SystemExit("the file holds %d parts, the scheme %d"
                         % (pi, len(scheme)))
    return "".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# The controls
# ─────────────────────────────────────────────────────────────────────────────


def instants(scheme):
    """`{number: {(page, system, bar_in_system)}}` — what each number names."""
    out = collections.defaultdict(set)
    for rows in scheme.values():
        for key, i, n in rows:
            out[n].add((key[0], key[1], i))
    return out


def strip_numbers(xml):
    return _MEASURE.sub(lambda m: m.group(1) + "N" + m.group(3), xml)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="write the renumbered file to out/")
    args = ap.parse_args()

    smap = json.loads(SYSTEM_MAP.read_text())
    xml = XML.read_text()
    parts, order = rebuild_parts(smap)

    # ── 0. REACH, before anything else ──────────────────────────────────────
    print("=" * 78)
    print("0. REACH — what this instrument can speak about")
    print("=" * 78)
    n_sys = len(order)
    n_staff_systems = sum(len(sd["staves"]) for sd in smap["systems"])
    n_meas = sum(run.n_measures for part in parts for run in part)
    print("   document        : %s" % smap["record"])
    print("   record commit   : %s (dirty=%s)"
          % (smap["provenance"]["commit"][:8], smap["provenance"]["dirty"]))
    print("   parts           : %d" % len(parts))
    print("   systems         : %d  (%s)"
          % (n_sys, ", ".join("p%d/s%d" % k for k in order)))
    print("   staff-systems   : %d" % n_staff_systems)
    print("   measures in file: %d" % n_meas)
    widths = collections.Counter(len(sd["staves"]) for sd in smap["systems"])
    print("   staves/system   : %s" % dict(sorted(widths.items())))
    suppressing = sum(1 for part in parts if len(part) < n_sys)
    print("   parts TACET on at least one system: %d of %d  <-- the population"
          % (suppressing, len(parts)))
    if not parts or n_meas == 0 or suppressing == 0:
        print()
        print("INSTRUMENT DEAD: a document where every part appears on every")
        print("system numbers identically under both schemes and this arm")
        print("has NOTHING to measure. It is not a clean result.")
        return 2

    problems = fidelity_problems(smap)
    if problems:
        print()
        print("RECONSTRUCTION INCOMPLETE:")
        for p in problems:
            print("  -", p)
        return 2
    print("   reconstruction  : every system's map entries account for every")
    print("                     staff the export's own provenance records")

    # ── 1. the rule's answer ────────────────────────────────────────────────
    offsets, numbering = SX._document_bar_offsets(parts)
    print()
    print("=" * 78)
    print("1. THE RULE — `export._document_bar_offsets`, called, not restated")
    print("=" * 78)
    print("   scheme: %s   document_bars: %s   refused: %s"
          % (numbering["scheme"], numbering["document_bars"],
             numbering.get("refused", "—")))
    print()
    print("   %-8s %6s %8s %9s  %s"
          % ("system", "bars", "offset", "deciding", "readings"))
    for row in numbering["systems"]:
        print("   %-8s %6s %8s %9d  %s"
              % (row["system"], row["bars"], row["offset"],
                 row["staves_deciding"], row["readings"]))
    if offsets is None:
        print()
        print("   The rule REFUSED on this document; there is no A/B to run.")
        return 1

    old = per_part_numbers(parts)
    new = document_numbers(parts, offsets)

    # ── 2. the A/B ──────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("2. THE A/B — per-part numbering vs document numbering")
    print("=" * 78)
    moved = sum(1 for pi in old
                for (a, b) in zip(old[pi], new[pi]) if a[2] != b[2])
    print("   measures whose number MOVES : %d of %d  (%.1f%%)"
          % (moved, n_meas, 100.0 * moved / n_meas))
    print()
    print("   %-5s %6s %7s   %s" % ("part", "meas", "moved", "first bar of each system"))
    for pi in sorted(old):
        mv = sum(1 for a, b in zip(old[pi], new[pi]) if a[2] != b[2])
        firsts = []
        for key in order:
            o = next((n for k, i, n in old[pi] if k == key and i == 0), None)
            w = next((n for k, i, n in new[pi] if k == key and i == 0), None)
            firsts.append("--" if o is None
                          else ("%d" % o if o == w else "%d>%d" % (o, w)))
        print("   P%-4d %6d %7d   %s"
              % (pi + 1, len(old[pi]), mv, " ".join("%7s" % f for f in firsts)))

    # ── 3. does a number name ONE instant? ──────────────────────────────────
    print()
    print("=" * 78)
    print("3. DOES `<measure number=N>` NAME ONE INSTANT?")
    print("=" * 78)
    for label, scheme in (("per-part (incumbent)", old), ("document (new)", new)):
        inst = instants(scheme)
        bad = {n: v for n, v in inst.items() if len(v) > 1}
        print("   %-22s numbers used %4d   AMBIGUOUS %4d"
              % (label, len(inst), len(bad)))
        if bad:
            worst = sorted(bad.items())[:3]
            for n, v in worst:
                print("        number %-4d names %s"
                      % (n, ", ".join("p%d/s%d bar %d" % t for t in sorted(v))))
    # ⚠️ AND THE CONVERSE, which the count above cannot see: under the document
    # scheme every instant must also have exactly ONE number.
    back = collections.defaultdict(set)
    for rows in new.values():
        for key, i, n in rows:
            back[(key[0], key[1], i)].add(n)
    multi = {k: v for k, v in back.items() if len(v) > 1}
    print("   instants carrying more than one number under the new scheme: %d"
          % len(multi))

    # ── 4. THE IDENTICAL-MUSIC CONTROL ──────────────────────────────────────
    print()
    print("=" * 78)
    print("4. THE IDENTICAL-MUSIC CONTROL — and it can fail")
    print("=" * 78)
    new_xml = renumber(xml, new)
    same_stripped = strip_numbers(xml) == strip_numbers(new_xml)
    print("   byte-identical outside the `number=` attribute : %s"
          % same_stripped)
    # POSITIVE CONTROL: the files are NOT identical with the numbers in, or the
    # renumbering did nothing and the line above is vacuous.
    differs = xml != new_xml
    print("   the two files DO differ (positive control)     : %s" % differs)
    control_old = renumber(xml, old)
    round_trip = control_old == xml
    print("   re-applying the INCUMBENT scheme reproduces the")
    print("   committed file byte for byte                   : %s" % round_trip)

    if args.write:
        OUT.mkdir(exist_ok=True)
        (OUT / "beethoven5-mvt1-p1-p4.document-numbered.musicxml").write_text(new_xml)
        (OUT / "numbering.json").write_text(json.dumps(
            {"numbering": numbering,
             "moved": moved, "measures": n_meas,
             "per_part_ambiguous_numbers": len(
                 {n for n, v in instants(old).items() if len(v) > 1}),
             "document_ambiguous_numbers": len(
                 {n for n, v in instants(new).items() if len(v) > 1})},
            indent=2))
        print()
        print("   written to %s" % OUT)

    ok = (same_stripped and differs and round_trip and not multi
          and not {n for n, v in instants(new).items() if len(v) > 1})
    print()
    print("ALL CONTROLS PASS" if ok else "A CONTROL FAILED")
    if args.check and not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
