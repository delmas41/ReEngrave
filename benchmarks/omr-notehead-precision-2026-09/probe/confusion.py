"""ROADMAP 2.4a — confusion table against the print, and the `no_stem` overlap.

Joins `notehead_is_not_a_notehead`'s verdicts (re-derived, same isolated
adjudicate-one-decision method as `measure.py`) against:

  1. The stem-crop-pass's + notehead-width's own blind print verdicts
     (`benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-*.json`,
     joined through their crop manifests), on the SUBJECT ADDRESS.
  2. The record's OWN `Q.STEM_DIRECTION` verdicts with `reason == "no_stem"`,
     to report how much of that population is ALSO refused here (the honest
     form of "no_stem shrinks by the barline share" — nothing in the
     pipeline subtracts one from the other automatically; this computes the
     overlap directly rather than assuming a wiring that does not exist).

    python3 probe/confusion.py <record.json> --label litolff --out out/x.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

WIDTH_PROBE_DIR = ROOT / "benchmarks" / "omr-notehead-width-2026-09" / "probe"
sys.path.insert(0, str(WIDTH_PROBE_DIR))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject              # noqa: E402
from contamination import adjudications, truth_of                # noqa: E402

NEEDED = (Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
          Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.NOTEHEAD_CLASS)


def build_gather_log(rec: dict) -> Log:
    log = Log()
    for r in rec["observations"]:
        if r["quantity"] not in NEEDED:
            continue
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                    frame=r["frame"], score=r.get("score"), **detail)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    result = json.load(open(a.record))
    rec = result["record"]

    log = build_gather_log(rec)
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    verdicts_by_subject = {
        v["subject"]: v for v in log.to_json()["verdicts"]
        if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD}

    # ── 1. the print confusion table ────────────────────────────────────────
    adj = adjudications()
    if not adj:
        print("DEAD: no crop-pass adjudication files found", file=sys.stderr)
        return 2
    matrix = collections.Counter()
    matched_rows = []
    for _src, pub, r, subj, _kd in adj:
        if pub != a.label or not subj:
            continue
        v = verdicts_by_subject.get(subj)
        if v is None:
            continue         # this print-adjudicated subject is not a
                              # notehead-classed glyph on this record (e.g. a
                              # stem crop, a whole-note crop keyed elsewhere)
        truth = truth_of(r)
        refused = v["value"] is True
        matrix[(truth, refused)] += 1
        matched_rows.append({"subject": subj, "truth": truth,
                             "refused": refused, "reason": v["reason"]})
    print(f"print-joined rows for {a.label}: {len(matched_rows)}",
         file=sys.stderr)

    confusion = {}
    for truth in ("NOT a notehead", "IS a notehead", "cannot tell"):
        confusion[truth] = {"refused": matrix.get((truth, True), 0),
                            "kept": matrix.get((truth, False), 0)}
    # anything with an unknown verdict word
    unknown = [k for k in matrix if k[0].startswith("UNKNOWN")]
    if unknown:
        confusion["UNKNOWN"] = {str(k): v for k, v in matrix.items()
                                if k[0].startswith("UNKNOWN")}

    # ── 2. the no_stem overlap ───────────────────────────────────────────────
    no_stem_subjects = {v["subject"] for v in rec["verdicts"]
                        if v["quantity"] == Q.STEM_DIRECTION
                        and v.get("reason") == "no_stem"}
    refused_subjects = {s for s, v in verdicts_by_subject.items()
                        if v["value"] is True}
    overlap = no_stem_subjects & refused_subjects
    out = {
        "label": a.label,
        "print_confusion": confusion,
        "matched_rows": matched_rows,
        "cost_on_confirmed_heads": confusion["IS a notehead"]["refused"],
        "caught_of_not_a_notehead": confusion["NOT a notehead"]["refused"],
        "missed_of_not_a_notehead": confusion["NOT a notehead"]["kept"],
        "no_stem_population": len(no_stem_subjects),
        "refused_population": len(refused_subjects),
        "no_stem_AND_refused": len(overlap),
        "no_stem_share_refused":
            (len(overlap) / len(no_stem_subjects)) if no_stem_subjects else None,
    }
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "matched_rows"},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
