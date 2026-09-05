"""Is a staff's `instrument` evidence about the join, or a RESTATEMENT of it?

The mis-join at Beethoven 5 p.4 (`probe_misjoined_slots.py`) invites an obvious
repair: refuse the ordinal join where the two systems' READ INSTRUMENTS disagree
at a position. This probe asks whether the field a repair would read can carry
that signal at all.

It cannot. `contextual.py` assigns instruments BY SLOT —
`instrument_by_slot`, and line ~748 writes
`staff["instrument_source"] = instrument_source.get(slot, "label")` onto every
staff of the slot — and the slot assignment IS the ordinal join. So the two
systems' staves in one slot get the same instrument by construction, and
`instrument_source: "label"` is a SLOT-level fact, not a claim that a label was
printed on that staff in that system.

Measured over every multi-system row of the 20-row scan era: the field agrees
across systems at 100% of positions in exactly the 7 rows whose ordinal join
SUCCEEDS, and disagrees widely in the 3 where it refuses. The correlation is
perfect because it is circular.

⚠️ CONSEQUENCE FOR ANY LABEL-DISAGREEMENT CHECK. The signal has to be taken
from the RAW per-(system, position) label reading, before contextual propagates
by slot — not from `staff["instrument"]` / `staff["instrument_source"]`. A check
built on the staff field is structurally incapable of firing.

⚠️ CONSEQUENCE FOR PHASE 2's COUNT SOURCE. A count keyed on the staff's
`instrument` inherits the join it was meant to be independent of. On
`beethoven-sym5-mvt1-575951-p4` position 6 the field reads `Timpani[label]` in
BOTH systems while system 1 prints `Violino I` — a label propagated onto a
staff that does not print one.

FIXTURE PROVENANCE. 20-row transcriptions from
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. The main checkout's `fixtures/` still holds
the ELEVEN-row era's `.restamp-composed` set.

    python3 benchmarks/omr-structural-parts-2026-09/probe_instrument_is_slot_level.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.export import _stitch_slots  # noqa: E402

DEFAULT_FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    fixtures = Path(args.fixtures)

    report = {}
    print(f"{'row':<34} {'sizes':>10} {'pos':>4} {'identical':>10} "
          f"{'ordinal join':>13}")
    for p in sorted(fixtures.glob(f"*{SUFFIX}")):
        rid = p.name[:-len(SUFFIX)]
        result = json.loads(p.read_text())
        systems = [s for pg in result.get("pages", [])
                   for s in pg.get("systems", []) if s.get("staves")]
        if len(systems) < 2:
            continue
        n = min(len(s["staves"]) for s in systems)
        same = sum(1 for k in range(n) if len({
            (s["staves"][k].get("instrument"),
             s["staves"][k].get("instrument_source")) for s in systems}) == 1)
        joined = _stitch_slots(result) is not None
        report[rid] = {"sizes": [len(s["staves"]) for s in systems],
                       "positions": n, "identical": same,
                       "ordinal_join_succeeds": joined}
        print(f"{rid:<34} {str(report[rid]['sizes']):>10} {n:>4} "
              f"{f'{same}/{n}':>10} "
              f"{'SUCCEEDS' if joined else 'refuses':>13}")

    joins = [v for v in report.values() if v["ordinal_join_succeeds"]]
    refus = [v for v in report.values() if not v["ordinal_join_succeeds"]]
    print(f"\njoin SUCCEEDS ({len(joins)} rows): identical at "
          f"{sum(v['identical'] for v in joins)}/"
          f"{sum(v['positions'] for v in joins)} positions")
    print(f"join refuses  ({len(refus)} rows): identical at "
          f"{sum(v['identical'] for v in refus)}/"
          f"{sum(v['positions'] for v in refus)} positions")
    print("\nThe field agrees exactly when the join succeeds because the join "
          "is what assigns it.\nIt is a restatement of the join, not evidence "
          "about it.")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = Path(__file__).resolve().parent / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()

# ── CORRECTION, 2026-09-05 ───────────────────────────────────────────────────
# The docstring above and commit dfb5e59a both said that on
# `beethoven-sym5-mvt1-984073-p4` position 6 "no label reached contextual". That
# is FALSE, and the code says so: `_resolve_ambiguous_labels` iterates
# `for label in staff_labels` and sets `instrument_source[slot] =
# "score_order_ambiguity"` at contextual.py:287 ONLY inside that loop — so the
# value cannot be set for a staff that had no label. Its presence is proof a
# label WAS read.
#
# What actually happened, corroborated per-rung by the labels workstream
# (surya 'Tp.' AND tesseract 'Tp.' on 984073-p4 system 2 position 6):
# `Tp.` was read, `candidates_for_alias("tp")` returned (Timpani, Trumpet), and
# `score_layouts.resolve_ambiguous_label` asked the LAYOUT FIT which one — and
# the fit names that slot a trumpet, because the ordinal join forced two
# different staff sequences into one slot sequence. `575951-p4` is the control:
# same label, same alias, uncorrupted fit, keeps Timpani.
#
# ⚠️ So the wrong instrument is NOT independent evidence for the wrong join. It
# is a CONSEQUENCE of the join presenting as evidence for it — a working
# mechanism fed a corrupted premise, whose output corroborates the corruption.
# Recorded as class 6 in docs/discussion-detector-right-output-wrong-2026-09-04.md.
#
# The 99/99 measurement below is UNAFFECTED and its reading is strengthened:
# the field agrees across systems wherever the join succeeds because the join
# assigns it, and now we know the one page where a raw label could have
# contradicted it had that label overturned by the same join.
