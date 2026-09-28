"""ROADMAP 2.15 pricing: GATHER ONCE (from a saved record), re-adjudicate
ONLY `Q.REST_IS_NOT_A_REST` (the one quantity this fix touches -- nothing
upstream of it in `adjudicate.ORDER` reads it, and downstream only EXPORT
does), then re-export BASE (the record exactly as saved -- this rule never
ran on it, and no flag exists to disable it) vs ARM (the same record with
the newly-decided refusals appended, `supersedes` set where an old verdict
existed) -- base and arm on the SAME gather, the SAME every-other-verdict,
differing in EXACTLY the rows this fix adds.

    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/r215_price.py \
        --record <record.json> --label <name> --out-dir <dir>

See FINDINGS.md §14d for the three-document numbers this produced.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate, export as EX, record_io  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401  registers them
from tools.omr.staged.record import Log, Q, Subject  # noqa: E402


def _row_no(row_id):
    try:
        return int(str(row_id).split(":")[-1])
    except (TypeError, ValueError):
        return 0


def rebuild_gather(rec: dict) -> Log:
    """A `Log` holding exactly this record's GATHER rows -- observations and
    abstentions, in emission order. Verdicts are NOT replayed: the point is
    to re-decide exactly one of them."""
    log = Log()
    rows = [(r, "obs") for r in rec.get("observations") or ()]
    rows += [(r, "abs") for r in rec.get("abstentions") or ()]
    rows.sort(key=lambda t: _row_no(t[0]["id"]))
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                       frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                       frame=r["frame"], reason=r["reason"], **detail)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"[{a.label}] loading via record_io.load_record ...", file=sys.stderr)
    data = record_io.load_record(a.record)
    rec = data["record"] if "record" in data else data
    print(f"[{a.label}] loaded {len(rec['observations'])} obs, "
         f"{len(rec['verdicts'])} verdicts in {time.time()-t0:.1f}s",
         file=sys.stderr)

    t1 = time.time()
    log = rebuild_gather(rec)
    print(f"[{a.label}] gather rebuilt in {time.time()-t1:.1f}s", file=sys.stderr)

    t2 = time.time()
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.REST_IS_NOT_A_REST,))
    print(f"[{a.label}] Q.REST_IS_NOT_A_REST re-adjudicated in "
         f"{time.time()-t2:.1f}s", file=sys.stderr)

    # The OLD verdict per subject, from the SAVED record.
    old_by_subject = {}
    for v in rec["verdicts"]:
        if v.get("quantity") == "rest_is_not_a_rest":
            old_by_subject[v["subject"]] = v

    new_json = log.to_json()
    new_by_subject = {v["subject"]: v for v in new_json["verdicts"]
                      if v["quantity"] == "rest_is_not_a_rest"}

    changed = []
    for subj, nv in new_by_subject.items():
        ov = old_by_subject.get(subj)
        already_refused = bool(ov and ov["value"] is True
                               and ov["outcome"] == "decided")
        if nv["outcome"] == "decided" and nv["value"] is True and not already_refused:
            changed.append((subj, nv, ov))

    print(f"[{a.label}] rest glyphs newly refused by 2.15: {len(changed)}",
         file=sys.stderr)
    by_reason: dict = {}
    for _subj, nv, _ov in changed:
        by_reason[nv["reason"]] = by_reason.get(nv["reason"], 0) + 1
    print(f"[{a.label}] by reason: {by_reason}", file=sys.stderr)

    # ARM = the original verdicts list plus the newly-decided rows appended.
    arm_verdicts = list(rec["verdicts"])
    next_id_no = max((_row_no(v["id"]) for v in rec["verdicts"]), default=0) + 1
    for subj, nv, ov in changed:
        row = dict(nv)
        row["id"] = f"vrd:r215-{next_id_no:07d}"
        next_id_no += 1
        row["subject"] = subj
        row["supersedes"] = ov["id"] if ov else None
        arm_verdicts.append(row)

    base_result = {"record": {"observations": rec["observations"],
                              "verdicts": rec["verdicts"],
                              "abstentions": rec.get("abstentions") or []}}
    arm_result = {"record": {"observations": rec["observations"],
                             "verdicts": arm_verdicts,
                             "abstentions": rec.get("abstentions") or []}}

    t3 = time.time()
    base_xml, base_rep = EX.to_musicxml(base_result)
    print(f"[{a.label}] BASE exported in {time.time()-t3:.1f}s", file=sys.stderr)
    t4 = time.time()
    arm_xml, arm_rep = EX.to_musicxml(arm_result)
    print(f"[{a.label}] ARM exported in {time.time()-t4:.1f}s", file=sys.stderr)

    report = {
        "label": a.label,
        "duplicates_refused": len(changed),
        "duplicates_by_reason": by_reason,
        "base": {
            "bars_held_out_sum": base_rep.get("bars_held_out_sum", {}).get("bars"),
            "written_notes": base_rep["written"].get("notes", 0),
            "written_rests": base_rep["written"].get("rests", 0),
            "written_measure_rests": base_rep["written"].get("measure_rests_read", 0),
            "notes_not_written_total": base_rep.get("notes_not_written_total"),
        },
        "arm": {
            "bars_held_out_sum": arm_rep.get("bars_held_out_sum", {}).get("bars"),
            "written_notes": arm_rep["written"].get("notes", 0),
            "written_rests": arm_rep["written"].get("rests", 0),
            "written_measure_rests": arm_rep["written"].get("measure_rests_read", 0),
            "notes_not_written_total": arm_rep.get("notes_not_written_total"),
            "not_a_rest_duplicate_box": arm_rep.get("notes_not_written", {}).get(
                "not_a_rest:rest_is_a_duplicate_box", 0),
        },
    }
    print(json.dumps(report, indent=2, default=str))

    out = out_dir / f"r215-pricing-{a.label}.json"
    out.write_text(json.dumps({"report": report, "changed": [
        {"subject": s, "reason": nv["reason"], "detail": nv.get("detail"),
         "old": (ov["value"] if ov else None)} for s, nv, ov in changed],
    }, indent=1, default=str))
    print(f"[{a.label}] wrote {out}", file=sys.stderr)

    (out_dir / f"r215-arm-{a.label}.musicxml").write_text(arm_xml)
    (out_dir / f"r215-base-{a.label}.musicxml").write_text(base_xml)
    print(f"[{a.label}] total {time.time()-t0:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
