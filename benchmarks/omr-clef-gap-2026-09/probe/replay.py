"""Roadmap 2.10, base vs arm on ONE saved record: INFER + a bounded EVALUATE.

⚠️ THIS IS AN INFER/EVALUATE-ONLY ARM AND IT IS BLIND TO GATHER AND TO
ADJUDICATE, exactly as `benchmarks/omr-infer-stage-2026-09/reinfer.py` says of
itself. It IMPORTS that module's `rebuild` and `control` rather than taking a
copy: a second replay would drift from the first and the drift is the failure
this repository keeps paying for. `fill_clef_gap` changes no gather and no
adjudicator, so the replay is a valid instrument for it; a `0` from here about
a GATHER change would prove nothing.

⚠️ THE BASE ARM IS RUN FIRST AND MUST BE A CLEAN N/N. With `OMR_CLEF_GAP=0`
the replay must reproduce the record's verdicts exactly AND export a
byte-identical file. A base that does not reproduce makes every arm number a
measurement of the harness.

⚠️ THE RECORDS ALREADY CARRY INFERENCES. Both whole-movement records were
gathered with `collapse_slot_index_to_family_block` ON, so re-running INFER
over them re-offers those subjects and the harness skips each one
`prior_is_decided`. That is the idempotence this arm relies on and it is
CHECKED (`reoffered_and_declined` below), not assumed.

    python3 benchmarks/omr-clef-gap-2026-09/probe/replay.py <record.json> \\
        --id beethoven5-litolff --out-json out/litolff.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-infer-stage-2026-09"))

from reinfer import control, rebuild                                # noqa: E402
from tools.omr.staged import evaluate, export, infer                # noqa: E402
from tools.omr.staged import consequences                           # noqa: E402,F401
from tools.omr.staged import inferences                             # noqa: E402,F401
from tools.omr.staged.record import Log, Outcome, Q                 # noqa: E402
from tools.omr.staged.record_io import load_record                  # noqa: E402


def _standing(rec: dict, quantity: str) -> dict:
    """`{subject: the standing verdict}` for one quantity, from raw JSON."""
    rows = [v for v in rec["verdicts"] if v["quantity"] == quantity]
    superseded = {v["supersedes"] for v in rows if v.get("supersedes")}
    return {v["subject"]: v for v in rows if v["id"] not in superseded}


def _clef_table(rec: dict) -> dict:
    return {s: (v["outcome"], v.get("value"), v.get("reason"), v["decider"])
            for s, v in _standing(rec, Q.CLEF).items()}


def run_arm(rec: dict, *, clef_gap: bool) -> dict:
    """One arm: rebuild, INFER, the bounded second EVALUATE, EXPORT.

    ⚠️ THE FLAG IS SET AROUND THE STAGE, not around the import. Both rule
    modules are already imported by the time this runs, and a predicate read
    at import time would make the arm a property of the process.
    """
    env = dict(os.environ)
    os.environ[infer.CLEF_GAP_ENV] = "1" if clef_gap else "0"
    try:
        log: Log = rebuild(rec)
        before = {v.id for v in log.all_verdicts()}
        ireport = infer.run(log, evaluate.Report([], [], []))
        causes = infer.inferred_verdicts(log)
        new_causes = [c for c in causes if c.id not in before]
        ereport = evaluate.run_over(log, new_causes)
    finally:
        os.environ.clear()
        os.environ.update(env)

    js = log.to_json()
    result = {"record": js}
    xml, report = export.to_musicxml(result)
    cov = export.coverage(result)

    new = [v for v in js["verdicts"] if v["id"] not in before]
    return {
        "xml": xml,
        "record": js,
        "n_new_verdicts": len(new),
        "new_by_quantity": dict(collections.Counter(v["quantity"] for v in new)),
        "all_new_verdicts_are_labelled_or_derived": all(
            infer.is_inferred(v) or v["decider"] in
            ("restate_pitch", "move_glyph", "respell_accidental")
            for v in new),
        "inference": ireport.to_json(),
        "reevaluation": {"fired": len(ereport.fired),
                         "by_rule": dict(collections.Counter(
                             f[0] for f in ereport.fired))},
        # ⚠️ The idempotence this arm rests on, CHECKED rather than assumed.
        "reoffered_and_declined": dict(collections.Counter(
            s[2] for s in ireport.skipped if s[2].startswith("prior_is_"))),
        "clefs": _clef_table(js),
        "notes_not_written": report["notes_not_written"],
        "notes_not_written_total": report["notes_not_written_total"],
        "notes_not_written_by_system": report["notes_not_written_by_system"],
        "balance": report["balance"],
        "n_note_elements": xml.count("<note"),
        "status_census_unaccounted": cov["status_census"]["unaccounted"],
        "status_census_balanced": (
            cov["status_census"]["n_filed"] == cov["status_census"]["n_families"]
            if "n_filed" in cov["status_census"] else None),
        "inferred_clefs": cov["inferred_clefs"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--id", required=True)
    ap.add_argument("--out-json")
    ap.add_argument("--write-arm", metavar="DIR",
                    help="write the ARM's record and MusicXML here, so "
                         "`omr-notehead-funnel-2026-09/probe/funnel.py` can "
                         "be run over them UNCHANGED — the per-staff gate is "
                         "that probe's question and it keeps it")
    ap.add_argument("--skip-control", action="store_true",
                    help="⚠️ only after the control has passed ONCE on this "
                         "record in this session; it is the slow half")
    a = ap.parse_args()

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    prov = doc.get("provenance")
    print(f"{a.id}: provenance {prov}")
    if not prov or prov.get("dirty") is None:
        print("⚠️ this record does not name the tree that built it",
              file=sys.stderr)

    if not a.skip_control:
        print("── CONTROL: does the rebuild reproduce the record? ──")
        if control(rec, rebuild(rec)) != 0:
            print("⚠️ REBUILD IS NOT THE RECORD — every number below would be "
                  "a measurement of the harness.", file=sys.stderr)
            return 2

    print("── BASE (OMR_CLEF_GAP=0) ──")
    base = run_arm(rec, clef_gap=False)
    print(f"   new verdicts {base['n_new_verdicts']}  "
          f"reoffered+declined {base['reoffered_and_declined']}")
    print("── ARM (OMR_CLEF_GAP=1) ──")
    arm = run_arm(rec, clef_gap=True)
    print(f"   new verdicts {arm['n_new_verdicts']} {arm['new_by_quantity']}")

    # ── the comparison ─────────────────────────────────────────────────────
    base_clefs, arm_clefs = base["clefs"], arm["clefs"]
    decided_changed = sorted(
        s for s, v in base_clefs.items()
        if v[0] == "decided" and arm_clefs.get(s) != v)
    abstained_before = sorted(s for s, v in base_clefs.items()
                              if v[0] == "abstained")
    by_reason: collections.Counter = collections.Counter()
    still: list = []
    for s in abstained_before:
        o, val, reason, _d = arm_clefs.get(s, ("missing", None, None, None))
        if o == "decided":
            by_reason[reason] += 1
        else:
            still.append((s, o, reason))

    summary = {
        "id": a.id,
        "provenance": prov,
        "base": {k: base[k] for k in (
            "n_new_verdicts", "reoffered_and_declined",
            "notes_not_written_total", "notes_not_written",
            "n_note_elements", "balance", "status_census_unaccounted",
            "inferred_clefs")},
        "arm": {k: arm[k] for k in (
            "n_new_verdicts", "new_by_quantity",
            "all_new_verdicts_are_labelled_or_derived", "reevaluation",
            "reoffered_and_declined", "notes_not_written_total",
            "notes_not_written", "n_note_elements", "balance",
            "status_census_unaccounted", "inferred_clefs")},
        "base_arm_is_deterministic": None,
        "base_arm_export_equals_the_records_own_export": None,
        "clef": {
            "abstained_before": len(abstained_before),
            "inferred_by_other_systems": by_reason.get(
                "clef_from_other_systems", 0),
            "inferred_by_instrument_convention": by_reason.get(
                "clef_from_instrument_convention", 0),
            "still_abstained": still,
            "decided_clefs_changed": decided_changed,
        },
        "no_pitch": {
            "before": base["notes_not_written"].get("no_pitch", 0),
            "after": arm["notes_not_written"].get("no_pitch", 0),
            "by_system_before": {k: v["no_pitch"] for k, v
                                 in base["notes_not_written_by_system"].items()
                                 if v.get("no_pitch")},
            "by_system_after": {k: v["no_pitch"] for k, v
                                in arm["notes_not_written_by_system"].items()
                                if v.get("no_pitch")},
        },
        "notes": {"before": base["n_note_elements"],
                  "after": arm["n_note_elements"],
                  "delta": arm["n_note_elements"] - base["n_note_elements"]},
        "refusal_deltas": {
            k: arm["notes_not_written"].get(k, 0) - v
            for k, v in sorted(base["notes_not_written"].items())
            if arm["notes_not_written"].get(k, 0) != v},
    }
    # ⚠️ THE CONTROL THAT MUST READ TRUE: the base arm run twice is the same
    # file. A base that is not deterministic makes every delta above noise.
    summary["base_arm_is_deterministic"] = (
        base["xml"] == run_arm(rec, clef_gap=False)["xml"])

    # ⚠️⚠️ AND THE ONE THAT MAY READ FALSE, REPORTED RATHER THAN ASSERTED.
    # The base arm re-runs the WHOLE INFER stage with only `OMR_CLEF_GAP`
    # off, so on a record gathered before `OMR_INFER` went default-ON
    # (2026-09-23) the base already carries the two DURATION rules'
    # inferences that the saved record does not. That is exactly why the BASE
    # ARM and not the RECORD is this measurement's baseline (CLAUDE.md §6b,
    # *base vs arm on ONE tree*) -- and it is printed, because a reader
    # comparing a table here with one cut from the record's own export would
    # otherwise attribute the duration rules' effect to this one.
    from_record = export.to_musicxml({"record": rec})[0]
    summary["base_arm_export_equals_the_records_own_export"] = (
        base["xml"] == from_record)

    print(json.dumps({k: v for k, v in summary.items()
                      if k != "base" and k != "arm"}, indent=2, default=str))
    print(f"   base/arm note elements: {summary['notes']}")
    if a.write_arm:
        d = Path(a.write_arm)
        d.mkdir(parents=True, exist_ok=True)
        # ⚠️ NOT A PIPELINE RECORD and it must not be fed to anything that
        # checks provenance — `reinfer.py` states the same caveat about its
        # own `--out`. It carries the record and nothing else.
        (d / f"{a.id}-arm.record.json").write_text(
            json.dumps({"record": arm["record"]}, default=str))
        # ⚠️ THE BASE RECORD TOO, so `funnel.py` can answer the per-staff gate
        # for BOTH arms. Cutting the base table from the RECORD instead would
        # put the duration rules' effect in this rule's column.
        (d / f"{a.id}-base.record.json").write_text(
            json.dumps({"record": base["record"]}, default=str))
        (d / f"{a.id}-arm.musicxml").write_text(arm["xml"])
        (d / f"{a.id}-base.musicxml").write_text(base["xml"])
        print(f"wrote the arm record and both files under {d}")

    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_json).write_text(json.dumps(summary, indent=1, default=str))
        print(f"wrote {a.out_json}")

    if not abstained_before:
        print("\n⚠️ ZERO ABSTAINED CLEFS ON THIS DOCUMENT. The rule is INERT "
              "here and that is a fact about the PAGE, not about the rule — "
              "reach before accuracy (CLAUDE.md §2 rule 5).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
