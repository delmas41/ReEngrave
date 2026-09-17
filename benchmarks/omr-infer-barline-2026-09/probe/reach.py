"""REACH FIRST — the endpoint split, and rule 2's own funnel.

⚠️⚠️ THE `191` IN THE FIRST RULE'S FINDINGS IS NOT RULE 2'S POPULATION, AND
CITING IT AS ONE WOULD BE WRONG. That figure is *narrowed durations with no
next COLUMNED onset*, which is two different things added together:

    (None, True)   the barline      -> rule 2's actual population
    (None, False)  UNKNOWN          -> something follows and it landed in no
                                      column, so nobody knows when this note
                                      stops, and BOTH rules decline it

This probe splits them, then walks rule 2's own funnel stop by stop. It
reports reach BEFORE any result, because a change that moves nothing because
it is INERT and one that moves nothing because the page holds NOTHING TO MOVE
are the same number.

⚠️ It SELF-CHECKS against the rule's own output: the funnel's survivor count
must equal what `collapse_duration_to_barline` actually proposes. A duplicated
loop that drifts from the rule it describes is an instrument measuring itself.

    python3 benchmarks/omr-infer-barline-2026-09/probe/reach.py <record.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import inferences as I                     # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q             # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "omr-infer-stage-2026-09"))
from reinfer import rebuild                                       # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", help="write the figures here")
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")
    log = rebuild(rec)

    endpoint = collections.Counter()
    f = collections.Counter()
    proposed = 0

    for system in log.subjects(Kind.SYSTEM):
        spans = I._walk(log, system)
        for s in spans:
            if s.end is not None:
                endpoint["ends at an onset column (rule 1)"] += 1
                continue
            if s.endpoint_is_unknown:
                endpoint["UNKNOWN: something follows, in no column"] += 1
                continue
            endpoint["runs to the BARLINE (rule 2)"] += 1

            # rule 2's funnel, stop by stop
            same = [st2 for st2 in s.at_col.get(s.k, {})
                    if st2 != s.staff
                    and s.endpoints.get((st2, s.k)) == s.endpoint]
            if not same:
                f["1 STOP: no other staff runs k -> barline"] += 1
                continue
            votes, ids, refused = {}, [], 0
            for st2 in same:
                beats, vids = I._event_beats(
                    log, st2, s.cell, system, s.at_col[s.k][st2]["glyphs"])
                if beats is None:
                    continue
                if I._witness_is_meter_derived(log, vids):
                    refused += 1
                    continue
                votes.setdefault(beats, []).extend(vids)
                ids.extend(vids)
            if refused:
                f[f"(witnesses refused as meter-derived: {refused})"] += 1
            if not votes:
                f["2 STOP: no witness with a DECIDED, non-meter length"] += 1
                continue
            if len(votes) > 1:
                f["3 STOP: the witnesses disagree"] += 1
                continue
            groups = I.independent_groups(log, tuple(ids))
            if len(groups) < I.COLUMN_MIN_INDEPENDENT_WITNESSES:
                f["4 STOP: fewer than 2 INDEPENDENT witnesses"] += 1
                continue
            beats = next(iter(votes))
            match = [c for c in (s.prior.candidates or ())
                     if isinstance(c.value, dict)
                     and c.value.get("beats") is not None
                     and abs(float(c.value["beats"]) - beats) < 1e-9]
            if len(match) != 1:
                f[f"5 STOP: {len(match)} candidates carry that length"] += 1
                continue
            f["SURVIVES"] += 1

        proposed += len(I.collapse_duration_to_barline(log, system))

    print("\n── THE ENDPOINT SPLIT ────────────────────────────────────────")
    total = sum(endpoint.values())
    for k, v in endpoint.most_common():
        print(f"  {v:6d}  {k}")
    print(f"  {total:6d}  narrowed durations standing in a column")

    print("\n── RULE 2's FUNNEL ───────────────────────────────────────────")
    for k, v in sorted(f.items()):
        print(f"  {v:6d}  {k}")

    survived = f["SURVIVES"]
    print(f"\nfunnel survivors: {survived}   rule proposals: {proposed}")
    ok = survived == proposed
    print("SELF-CHECK: " + ("the funnel matches the rule" if ok else
                            "⚠️ THE FUNNEL HAS DRIFTED FROM THE RULE"))

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"endpoint_split": dict(endpoint), "funnel": dict(f),
             "proposed": proposed, "self_check_ok": ok}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
