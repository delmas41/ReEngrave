"""RUN INFER ALONE over a saved post-EVALUATE record.

⚠️ THE POINT IS THE CONTROL. Running the staged CLI twice on a scan compares
two DETECTOR runs as much as two rules, and detector jitter here is documented
and real — the same four hairpin boxes' confidences moved between runs on
byte-identical code. This rebuilds a `Log` from ONE saved record's rows —
observations, abstentions AND verdicts, supersession intact — and runs INFER
over it, so two arms differ only in the rule under test. No detector jitter,
and no adjudication jitter either.

⚠️⚠️ WHAT THIS IS BLIND TO, STATED HERE BECAUSE THE NEXT PERSON RUNS THE TOOL
WITHOUT READING THE WRITE-UP. It isolates INFER over a FIXED gather AND a
FIXED adjudication, so it is blind BY CONSTRUCTION to BOTH:

  * a GATHER change — a new quantity, a new field, a changed frame — never
    enters the rebuild, exactly as `readjudicate.py` is blind to one. A
    `--control` here would pass cleanly across such a change and prove
    nothing.
  * an ADJUDICATE change — a different candidate set, a different `support`
    ordering, a verdict that used to abstain and now narrows. Those are
    `readjudicate.py`'s subject, not this tool's.

  It is therefore the THIRD instrument with a named blind spot, beside
  `readjudicate.py` (blind to GATHER) and `reexport_arm.py` (the mirror, on
  the export side). Answering *"did GATHER change what INFER sees"* needs two
  full re-gathers; answering *"did ADJUDICATE change what INFER sees"* needs
  `readjudicate.py` in front of this one.

⚠️ `--control` VERIFIES THE REBUILD BEFORE ANY ARM IS READ. It replays the
record and compares every verdict against the one the pipeline wrote. A
rebuild that does not reproduce the record is not a control, and a silent
mismatch would make every number here a measurement of the harness.

⚠️ `--out` DOES NOT WRITE A PIPELINE RECORD. It writes `{"record": ...}` plus
the inference report and nothing else, so an arm is missing the sibling keys
the CLI emits — `adjudication`, `agreement`, `evaluation`, `stubs`,
`summary`, `provenance`. An arm must NOT be fed to anything that checks
provenance: it would read as unprovenanced because this tool never had it to
copy, not because the run was untrustworthy.

    python3 benchmarks/omr-infer-stage-2026-09/reinfer.py <record.json> --control
    python3 benchmarks/omr-infer-stage-2026-09/reinfer.py <record.json> \
        --out out/inferred.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import evaluate, infer                     # noqa: E402
from tools.omr.staged import inferences                          # noqa: E402,F401
from dataclasses import replace                                  # noqa: E402
from tools.omr.staged.record import (Candidate, Log, Outcome,     # noqa: E402
                                     Subject, UphillConsequence,
                                     Verdict)


def _row_no(row_id: str) -> int:
    try:
        return int(str(row_id).split(":")[-1])
    except (TypeError, ValueError):
        return 0


def rebuild(rec: dict, skip_verdicts: frozenset = frozenset()) -> Log:
    """One Log holding exactly the saved record's rows, in emission order.

    ⚠️ VERDICTS ARE REPLAYED TOO, WITH THEIR ORIGINAL IDS, which is what makes
    this an INFER-only arm rather than a re-adjudication. `Log.record`'s
    single-pass guard is left live: the original run satisfied it, so a replay
    in id order satisfies it as well — and if it ever does not, that is a real
    finding about the record and must not be silenced.

    ⚠️ The id counter is advanced PAST every replayed row. Otherwise INFER's
    first verdict would be handed `vrd:000001`, colliding with a replayed one
    — a silent overwrite in a dict keyed by id, and the kind of fault that
    shows up as a plausible number rather than an error.
    """
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: _row_no(t[0]["id"]))
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"),
                        derived_from=tuple(r.get("basis") or ()), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)

    # ⚠️⚠️ `Verdict.single_pass_revision` IS SET, IS READ BY THE FIXPOINT
    # GUARD, AND IS NEVER SERIALISED. `record.py` sets it at :835 and reads it
    # at :1026, and `Verdict.to_json` does not carry it — so **no saved record
    # can be replayed through `Log.record`'s guard**, and the first attempt
    # here died on `UphillConsequence` for a verdict the original run had
    # accepted (`reconcile_duration`, the pipeline's one sanctioned loop:
    # durations vote the meter, the meter re-reads the durations).
    #
    # It is a REAL DEFECT in the record layer and it is NOT FIXED HERE, on
    # purpose: adding a key to `Verdict.to_json` changes the serialisation of
    # every record in the tree, which is exactly the "perturbs upstream by
    # existing" hazard this stage is required not to cause. It is reported in
    # FINDINGS §5g and ranked for a session that can price it.
    #
    # The replay is faithful instead, and COUNTED: a verdict the guard refuses
    # is retried once with the flag set — justified because the ORIGINAL run
    # accepted it, so this is restoring a fact the record lost rather than
    # granting a new exemption. ⚠️ The count is printed. A silent blanket
    # `single_pass_revision=True` would hide a genuine fixpoint, which is the
    # one thing that guard exists to catch.
    restored = 0
    for v in sorted(rec["verdicts"], key=lambda v: _row_no(v["id"])):
        # ⚠️ `skip_verdicts` LEAVES A QUANTITY OUT SO A CALLER CAN RE-DECIDE
        # IT over this record's own GATHER rows and everything else the run
        # concluded. It defaults to nothing, so every existing caller gets the
        # faithful replay this function was written for; a caller that skips
        # something owns its own control, because `control()` below compares
        # against the FULL record and will report the omission as a difference
        # rather than hiding it.
        if v["quantity"] in skip_verdicts:
            continue
        built = Verdict(
            id=v["id"], subject=Subject.from_key(v["subject"]),
            quantity=v["quantity"], outcome=Outcome(v["outcome"]),
            value=v.get("value"), decider=v["decider"], reason=v["reason"],
            considered=tuple(v.get("considered") or ()),
            used=tuple(v.get("used") or ()),
            missing=tuple(v.get("missing") or ()),
            declined=tuple(v.get("declined") or ()),
            excluded=tuple(tuple(e) for e in (v.get("excluded") or ())),
            correlated=tuple(frozenset(g) for g in (v.get("correlated") or ())),
            candidates=tuple(Candidate(c["value"], c["support"])
                             for c in (v.get("candidates") or ())),
            basis=tuple(v.get("basis") or ()),
            margin=v.get("margin"), supersedes=v.get("supersedes"),
            detail=dict(v.get("detail") or {}),
        )
        try:
            log.record(built)
        except UphillConsequence:
            log.record(replace(built, single_pass_revision=True))
            restored += 1
    if restored:
        print(f"⚠️ {restored} verdicts replayed with single_pass_revision "
              f"restored — the record does not carry that field (FINDINGS §5g)")

    highest = max([_row_no(r["id"]) for r in rec["observations"]]
                  + [_row_no(r["id"]) for r in rec.get("abstentions", [])]
                  + [_row_no(v["id"]) for v in rec["verdicts"]] + [0])
    log._n = highest                                    # noqa: SLF001
    log.freeze()
    return log


def _index(rows):
    return {r["id"]: r for r in rows}


def control(rec: dict, log: Log) -> int:
    """Does the rebuild reproduce the record, row for row, before any arm?"""
    want = _index(rec["verdicts"])
    got = _index(log.to_json()["verdicts"])
    same = diff = 0
    kinds: collections.Counter = collections.Counter()
    for rid, w in want.items():
        g = got.get(rid)
        if g is None:
            kinds["absent from the rebuild"] += 1
            diff += 1
            continue
        if (g["outcome"] == w["outcome"] and g["value"] == w["value"]
                and g["quantity"] == w["quantity"]
                and g["subject"] == w["subject"]
                and g["supersedes"] == w["supersedes"]
                and len(g["candidates"]) == len(w["candidates"])):
            same += 1
        else:
            diff += 1
            kinds[f"{w['outcome']}->{g['outcome']}"] += 1
    extra = len(got) - len(want)
    n_obs_want = len(rec["observations"])
    n_obs_got = len(log.to_json()["observations"])
    print(f"CONTROL: {same} of {len(want)} verdicts reproduced exactly, "
          f"{diff} differ, {extra:+d} extra")
    print(f"         {n_obs_got} of {n_obs_want} observations replayed")
    if kinds:
        print("        ", kinds.most_common())
    ok = diff == 0 and extra == 0 and n_obs_got == n_obs_want
    if not ok:
        print("⚠️ THE REBUILD IS NOT THE RECORD. Every number from this tool "
              "would be a measurement of the harness.", file=sys.stderr)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true",
                    help="replay and diff against the record, changing nothing")
    ap.add_argument("--out", help="write {record, inference} here")
    ap.add_argument("--json", help="write the summary figures here")
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    # ⚠️ PROVENANCE, REPORTED NOT ENFORCED. A record that cannot name its tree
    # is still a valid record; what must not happen is a comparison that
    # silently treats two unnamed trees as the same one.
    prov = doc.get("provenance")
    print(f"record provenance: {prov}")
    if not prov or prov.get("commit") is None or prov.get("dirty") is None:
        print("⚠️ this record does not fully name the tree that built it; "
              "do not compare it with another unnamed record.", file=sys.stderr)

    log = rebuild(rec)
    if a.control:
        return control(rec, log)

    before = {v["id"] for v in rec["verdicts"]}
    report = infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))

    js = log.to_json()
    new = [v for v in js["verdicts"] if v["id"] not in before]
    summary = {
        "reach": report.reach,
        "inferred": len(report.inferred),
        "skipped_reasons": collections.Counter(s[2] for s in report.skipped),
        "by_rule": collections.Counter(i[0] for i in report.inferred),
        "new_verdicts": len(new),
        "all_new_are_labelled": all(infer.is_inferred(v) for v in new),
    }
    print(json.dumps(summary, indent=2, default=str))

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"record": js, "inference": report.to_json()},
            indent=1, default=str))
        print(f"wrote {a.out}")
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=2, default=str))

    # ⚠️ DEAD-INSTRUMENT CHECK, on the same reasoning as `reach.py`: a rule
    # that inferred nothing because the page holds nothing and a rule that is
    # inert produce the same zero, so the tool says which it cannot tell.
    if not report.inferred:
        print("\n⚠️ INFERRED NOTHING. Run probe/reach.py on this record "
              "before reading that as a result: an inert rule and a page with "
              "nothing to infer about are the same number here.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
