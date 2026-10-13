#!/usr/bin/env python3
"""l281p2_why_infer: ROADMAP 2.81 PHASE 2 -- why do INFER's two column rules settle ~none of the bare-stem
population? For every standing NARROWED `beam_discounted_uncertain` duration in a saved record, the FIRST gate of
`collapse_duration_by_column` / `collapse_duration_to_barline` it fails, in the rules' own order. A reading probe:
it decides nothing and re-implements no gate beyond naming it (the gates are `inferences._walk` / `_propose`).

    python3 l281p2_why_infer.py RECORD
"""
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-infer-stage-2026-09"))

import reinfer  # noqa: E402
from l281p2_reinfer import rebuild_without_infer  # noqa: E402
from tools.omr.staged import inferences  # noqa: E402
from tools.omr.staged.infer import independent_groups  # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q, Subject  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    from tools.omr.staged.record_io import load_record
    doc = load_record(sys.argv[1])
    rec = doc["record"] if "record" in doc else doc
    log, _dropped = rebuild_without_infer(rec)
    members = []
    for v in log.all_verdicts():
        pass
    systems = log.subjects(Kind.SYSTEM)
    why = collections.Counter()
    total = 0
    for system in systems:
        spans = {s.sub.to_key(): s for s in inferences._walk(log, system)}
        cells = [c for c in log.subjects(Kind.CELL)
                 if c.page == system.page and c.system == system.system]
        for cell in cells:
            from tools.omr.staged.consequences import _standing
            for v in _standing(log, cell, Q.DURATION):
                if v.outcome is not Outcome.NARROWED or v.reason != inferences.BARE_STEM_REASON:
                    continue
                total += 1
                col_v = log.verdict(Q.ONSET_COLUMN, system)
                if col_v is None or col_v.outcome is not Outcome.DECIDED:
                    why["1 no decided onset-column verdict on the system"] += 1
                    continue
                span = spans.get(v.subject.to_key())
                if span is None:
                    why["2 the head stands in no known onset column (or its event was not grouped/owned)"] += 1
                    continue
                if span.endpoint_is_unknown:
                    why["3 something follows it that landed in no column (end unknown)"] += 1
                    continue
                # witnesses: other staves at the same column with the SAME endpoint
                others = [(st2, e2) for st2, e2 in sorted(span.at_col.get(span.k, {}).items())
                          if st2 != span.staff and span.endpoints.get((st2, span.k)) == span.endpoint]
                if not others:
                    why["4 no other staff stands at its column with the same endpoint"] += 1
                    continue
                votes = {}
                ids = []
                for st2, e2 in others:
                    beats, vids = inferences._event_beats(log, st2, span.cell, system, e2["glyphs"])
                    if beats is None:
                        continue
                    if span.runs_to_barline and inferences._witness_is_meter_derived(log, vids):
                        continue
                    votes.setdefault(beats, []).extend(vids)
                    ids.extend(vids)
                if not votes:
                    why["5 the same-span staves hold no DECIDED (meter-free) length"] += 1
                    continue
                if len(votes) > 1:
                    why["6 the witnesses disagree among themselves"] += 1
                    continue
                if len(independent_groups(log, tuple(ids))) < inferences.COLUMN_MIN_INDEPENDENT_WITNESSES:
                    why["7 fewer than 2 independent witnesses"] += 1
                    continue
                beats = next(iter(votes))
                match = [c for c in v.candidates if isinstance(c.value, dict)
                         and c.value.get("beats") is not None and abs(float(c.value["beats"]) - beats) < 1e-9]
                if len(match) != 1:
                    why["8 the witnesses name a length the reader never admitted"] += 1
                    continue
                why["9 WOULD FIRE"] += 1
    print(f"standing narrowed beam_discounted_uncertain durations (after EVALUATE): {total}")
    for k, n in sorted(why.items()):
        print(f"  {n:5d}  {k}")


if __name__ == "__main__":
    main()
