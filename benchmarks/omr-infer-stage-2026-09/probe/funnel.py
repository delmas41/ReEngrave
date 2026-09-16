"""WHICH CONDITION IS BINDING — the rule fired once on 357 narrowed durations.

⚠️ A near-zero result is only useful if it says WHERE the population went. The
coarse funnel in `reach.py` reports that all 357 narrowed durations sit on a
system with onset columns AND have other staves deciding in the same bar — so
the drop-off is entirely inside the rule's finer conditions, and this probe
walks them one at a time.

⚠️⚠️ IT DUPLICATES THE RULE'S LOOP, AND THEREFORE CHECKS ITSELF AGAINST THE
RULE. A probe that re-implements what it measures can disagree with it
silently — this repo's own `separate_causes` lesson. So the last thing it does
is run the REAL rule over the same log and assert its own `would_infer` count
equals the rule's. A mismatch exits non-zero and every number above it is
void.

It imports the rule's OWN helpers (`_events_with_x`, `_column_index`,
`_event_beats`) rather than restating them, so only the loop is duplicated,
never the geometry.

    python3 .../probe/funnel.py <record.json>
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

from reinfer import rebuild                                       # noqa: E402
from tools.omr.staged import inferences as I                      # noqa: E402
from tools.omr.staged import infer                                # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (                # noqa: E402
    ONSET_COLUMN_TOLERANCE_SPACES)
from tools.omr.staged.record import (Kind, Outcome, Q,            # noqa: E402
                                     Subject)


def main() -> int:
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json")
    a = ap.parse_args()

    doc = json.load(open(a.record))
    log = rebuild(doc["record"] if "record" in doc else doc)

    f: collections.Counter = collections.Counter()
    detail: collections.Counter = collections.Counter()
    would_infer = 0

    for system in log.subjects(Kind.SYSTEM):
        col_v = log.verdict(Q.ONSET_COLUMN, system)
        if col_v is None or col_v.outcome is not Outcome.DECIDED:
            continue
        spacing = (col_v.detail or {}).get("staff_spacing_px")
        if not spacing:
            continue
        tol = float(spacing) * ONSET_COLUMN_TOLERANCE_SPACES
        bars = {int(b["measure"]): b for b in (col_v.value or {}).get("bars", ())
                if "columns" in b}
        events = I._events_with_x(log, system)

        for (staff, cell), evs in sorted(events.items()):
            bar = bars.get(cell)
            if bar is None:
                continue
            columns = sorted(bar["columns"], key=lambda c: float(c["x_page"]))
            at_col, nxt = {}, {}
            for (st2, c2), evs2 in events.items():
                if c2 != cell:
                    continue
                idx = [(I._column_index(columns, e["x"], tol), e) for e in evs2]
                for pos, (ci, e) in enumerate(idx):
                    if ci is None:
                        continue
                    at_col.setdefault(ci, {})[st2] = e
                    follow = None
                    for ci2, _ in idx[pos + 1:]:
                        if ci2 is not None:
                            follow = ci2
                            break
                    nxt[(st2, ci)] = follow

            for e in evs:
                k = I._column_index(columns, e["x"], tol)
                for g in e["glyphs"]:
                    sub = Subject(Kind.GLYPH, page=system.page,
                                  system=system.system, staff=staff,
                                  cell=cell, glyph=g)
                    prior = log.verdict(Q.DURATION, sub)
                    if prior is None or prior.outcome is not Outcome.NARROWED:
                        continue
                    f["1 narrowed durations reached"] += 1
                    if k is None:
                        f["2 STOP: its event matched no column"] += 1
                        continue
                    f["2 its event is in a column"] += 1
                    end = nxt.get((staff, k))
                    if end is None:
                        f["3 STOP: no next onset in this bar (runs to the barline)"] += 1
                        continue
                    f["3 it has a next onset in this bar"] += 1
                    detail[f"   spans {end - k} column(s)"] += 1

                    votes, wit = {}, []
                    n_at_col = len(at_col.get(k, {})) - 1
                    for st2, e2 in sorted(at_col.get(k, {}).items()):
                        if st2 == staff:
                            continue
                        if nxt.get((st2, k)) != end:
                            continue
                        beats, ids = I._event_beats(log, st2, cell, system,
                                                    e2["glyphs"])
                        if beats is None:
                            continue
                        votes.setdefault(beats, []).extend(ids)
                        wit.extend(ids)
                    if not votes:
                        f["4 STOP: no witness spans k->m with a decided length"] += 1
                        detail[f"   staves at this column = {n_at_col}"] += 1
                        continue
                    f["4 at least one witness votes"] += 1
                    if len(votes) > 1:
                        f["5 STOP: the witnesses disagree"] += 1
                        continue
                    f["5 the witnesses are unanimous"] += 1
                    groups = infer.independent_groups(log, tuple(wit))
                    if len(groups) < I.COLUMN_MIN_INDEPENDENT_WITNESSES:
                        f["6 STOP: fewer than 2 INDEPENDENT witnesses"] += 1
                        detail[f"   witness verdicts={len(wit)} "
                               f"independent groups={len(groups)}"] += 1
                        continue
                    f["6 two or more independent witnesses"] += 1
                    beats = next(iter(votes))
                    match = [c for c in (prior.candidates or ())
                             if isinstance(c.value, dict)
                             and c.value.get("beats") is not None
                             and abs(float(c.value["beats"]) - beats) < 1e-9]
                    if len(match) != 1:
                        f[f"7 STOP: {len(match)} candidates carry that length"] += 1
                        continue
                    f["7 exactly one candidate carries that length"] += 1
                    would_infer += 1

    print("── FUNNEL ────────────────────────────────────────────────────")
    for k in sorted(f):
        print(f"  {f[k]:>6}  {k}")
    print("\n── WHERE THE BIG STOPS GO ────────────────────────────────────")
    for k, n in detail.most_common(12):
        print(f"  {n:>6}  {k}")
    print(f"\nwould infer: {would_infer}")

    # ⚠️ THE PROBE CHECKS ITSELF AGAINST THE RULE. A re-implementation that
    # disagrees with what it measures is worse than no probe.
    real = I.collapse_duration_by_column
    got = sum(len(real(log, s)) for s in log.subjects(Kind.SYSTEM))
    print(f"the rule itself proposes: {got}")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"funnel": dict(f), "detail": dict(detail),
             "would_infer": would_infer, "rule_proposes": got},
            indent=2, default=str))
    if got != would_infer:
        print("⚠️ THE PROBE AND THE RULE DISAGREE — every number above is void.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
