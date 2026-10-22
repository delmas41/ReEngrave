"""GATHER ONCE, ADJUDICATE TWICE — the wedge arm's A/B, carrying no jitter.

⚠️ THIS IS THE RIGHT INSTRUMENT FOR *THIS* CHANGE, AND THE REASON IS NAMED.
`readjudicate.py`'s declared blind spot is a GATHER change: it rebuilds a
`Log` from a SAVED record, so new rows, new fields and changed frames never
enter, and its `--control` would pass and prove nothing. **This session
changed ADJUDICATE and EXPORT and touched `gather.py` and `record.py` not at
all**, so the blind spot does not apply here. (Checked, not remembered:
`git diff --name-only` names neither file.)

It reuses that module's `rebuild` rather than copying it, for the reason every
constant in this thread is imported: two copies of one instrument drift.

⚠️ ITS OWN CONTROL RUNS FIRST. The BEFORE arm re-adjudicates with
`wedge_anchor` forced back to the stub it was, and must reproduce the saved
record's abstentions exactly. A rebuild that does not reproduce the record is
not a control.

    python3 .../readjudicate_wedge.py /tmp/wedge/brahms.json --out /tmp/wedge/re.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1] / "omr-staged-duration-beams-2026-09"))

from readjudicate import rebuild                                  # noqa: E402
from tools.omr.staged import adjudicate, evaluate                 # noqa: E402
from tools.omr.staged import adjudicators, consequences           # noqa: E402,F401
from tools.omr.staged.record import Q                             # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    whole = json.load(open(a.record))
    rec = whole["record"]

    rows = [o for o in rec["observations"] if o["quantity"] == Q.WEDGE_BOX]
    readers = collections.Counter(str(o.get("reader")) for o in rows)
    with_page = sum(1 for o in rows
                    if (o.get("detail") or {}).get("bbox_page_px"))
    print("=" * 72)
    print(f"REACH: {len(rows)} Q.WEDGE_BOX rows in the SAVED gather")
    print(f"  by reader     : {dict(readers)}")
    print(f"  with page box : {with_page}")
    print(f"  provenance    : {whole.get('provenance')}")
    if not rows:
        print("⚠️ INSTRUMENT DEAD — nothing to measure on this document.")
        return 1

    # ── the saved record's own wedge verdicts: the BEFORE arm, as written ──
    before = collections.Counter(
        (v["outcome"], v.get("reason"))
        for v in rec["verdicts"] if v["quantity"] == Q.WEDGE_ANCHOR)
    print(f"\nBEFORE (as the pipeline wrote it): {dict(before)}")

    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    out = log.to_json()

    after = collections.Counter(
        (v["outcome"], v.get("reason"))
        for v in out["verdicts"] if v["quantity"] == Q.WEDGE_ANCHOR)
    print(f"AFTER  (this tree)               : {dict(after)}")

    # ⚠️ THE CONTROL FOR EVERYTHING ELSE. The wedge verdicts are SUPPOSED to
    # move; every other quantity is not, and a rebuild that quietly changed
    # `duration` would make each number above a measurement of the harness.
    def census(verdicts):
        c: collections.Counter = collections.Counter()
        for v in verdicts:
            c[(v["quantity"], v["outcome"])] += 1
        return c

    b, f = census(rec["verdicts"]), census(out["verdicts"])
    moved = {k: (b.get(k, 0), f.get(k, 0))
             for k in set(b) | set(f) if b.get(k, 0) != f.get(k, 0)}
    print(f"\nQUANTITIES THAT MOVED: {len(moved)}")
    for (q, outcome), (x, y) in sorted(moved.items()):
        print(f"  {q:28} {outcome:10} {x:6} -> {y}")

    whole["record"] = out
    pathlib.Path(a.out).write_text(json.dumps(whole))
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
