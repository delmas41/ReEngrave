"""What the derived coverage check reports, on the committed 11-work truth pool.

`benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/` holds
all eleven benchmark works' truth AND that run's export, in git — so the
funnel that answers the module docstring's own objection ("a check that
reported it would list 55 elements, be ignored, and then be deleted") can be
printed on a clean clone, with no `orchestral_eval` run and no weights.

⚠️ THE `.omr.musicxml` FILES ARE FROM AN OLDER TREE. Reading a leftover export
is the defect `export_coverage` was rewritten to remove, and a broken exporter
would look healthy against them. So this prices the TABLES — is every gap head
accounted for — and says nothing about the current exporter. `python3 -m
tools.omr.export_coverage --all` on a machine with real fixtures is the one
that prices the exporter.

    python3 benchmarks/omr-export-gaps-2026-09/probe-ornaments-2026-09-08/probe_derived_coverage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr import accuracy_record as ar          # noqa: E402
from tools.omr import export_coverage as ec          # noqa: E402

FIXTURES = (ROOT / "benchmarks" / "omr-margin-window-truncation-2026-09"
            / "out" / "fixtures-control")

#: The allow-list `compare()` iterated until 2026-09-08, reproduced so the
#: before/after is a measurement rather than a memory.
OLD_VISIBLE = {
    "accidental", "articulations", "accent", "barline", "bar-style", "beam",
    "dot", "dynamics", "fermata", "lyric", "metronome", "notations", "slur",
    "stem", "tied", "time-modification", "tuplet", "wedge", "words",
}


def main() -> int:
    truths, ours = [], []
    for work in ar.BENCHMARK_WORKS:
        truths.append(ec._strip_prolog((FIXTURES / f"{work}.musicxml").read_text()))
        ours.append((FIXTURES / f"{work}.omr.musicxml").read_text())
    truth = "<pool>" + "".join(truths) + "</pool>"
    ours_xml = "".join(ours)

    index = ec.notation_index(truth)
    counts = ec.element_counts(ours_xml)
    heads = ec.compare(truth, ours_xml)
    where = ec.gap_locations(truth)

    print(f"POSITIVE CONTROLS   {len(truths)} works pooled "
          f"(BENCHMARK_WORKS has {len(ar.BENCHMARK_WORKS)})")
    print(f"                    truth: {index['note'].count} <note>, "
          f"{len(index)} distinct in-measure elements")
    print(f"                    ours:  {counts['note']} <note>, "
          f"{len(counts)} distinct elements\n")

    categorical = [n for n in index if counts[n] == 0]
    reported = [g for g in heads if g[0] not in ec.NOT_NOTATION]
    print("THE FUNNEL — the answer to \"55 elements, ignored, then deleted\"")
    print(f"  every element inside <measure>                  {len(index):4d}")
    print(f"  ... minus the ones we DO emit (categorical)      {len(categorical):4d}"
          "   <- the \"55\"")
    print(f"  ... minus every element whose PARENT is missing  {len(heads):4d}")
    print(f"  ... minus NOT_NOTATION ({', '.join(sorted(ec.NOT_NOTATION))})"
          f"  {len(reported):4d}\n")

    old = sorted(n for n in OLD_VISIBLE if index.get(n) and counts[n] == 0)
    print(f"THE OLD ALLOW-LIST would have reported {len(old)}: {old}")
    missed = sorted(g[0] for g in heads if g[0] not in OLD_VISIBLE)
    print(f"  and was blind to {len(missed)}: {missed}")
    print(f"  including <ornaments>: {'ornaments' in missed}\n")

    print("EVERY GAP HEAD, WITH ITS TIER")
    for name, n, _ in heads:
        tier = ("bookkeeping" if name in ec.NOT_NOTATION else
                "known gap" if name in ec.KNOWN_GAPS else "UNEXPLAINED")
        seen = "  " if name in OLD_VISIBLE else "* "
        print(f"  {seen}{name:20s} truth {n:5d}  [{tier:11s}]  {where[name]}")
    print("\n  (* = invisible to the pre-2026-09-08 check)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
