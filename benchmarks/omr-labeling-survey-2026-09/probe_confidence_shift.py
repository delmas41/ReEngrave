"""Is the fine-tune's "suppression" a THRESHOLD artifact?

Every round-3 and round-4 checkpoint emits far fewer symbols than production on
the 5-page scan benchmark — 3172-3364 against 4350 — and the whole of round 4
was spent looking for the cause in the training data. But the pipeline thresholds
detections at a FIXED `conf_threshold = 0.25`, and a fine-tune on a corpus whose
unlabeled ink is background does not only delete detections: it also pushes
their confidence down. If the ranking survives and only the calibration moved,
then nothing is forgotten and the fix is a per-checkpoint threshold, not a
different training method.

This asks the question directly. Same pages, same pipeline, two checkpoints, at
a floor low enough (0.05) that a detection which merely lost confidence is still
counted:

  * if the candidate's count at 0.05 is close to production's at 0.05, the
    detections are still THERE and the difference is calibration;
  * if it is short at 0.05 too, they are genuinely gone and the training
    method is the lever.

Reads the raw transcription JSONs rather than re-running the model, so it is
free once `scan_eval` has produced them for an arm.

    python3 .../probe_confidence_shift.py --arms prodbase=... r4=...
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

BENCH = Path("benchmarks/omr-scan-e2e-2026-09")


def detections(raw: dict):
    for page in raw.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    yield from measure.get("detections", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--arms", nargs="+", required=True,
                    help="tag=label pairs naming fixtures written by scan_eval "
                         "with that --tag (e.g. prodbase r4).")
    ap.add_argument("--cuts", nargs="+", type=float,
                    default=[0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50])
    ap.add_argument("--gate", metavar="BASELINE_TAG", default=None,
                    help="GATE AXIS 3 — class-space survival. Compare every "
                         "other arm's class inventory against this one's and "
                         "exit non-zero if a class the baseline reads often "
                         "has collapsed. A checkpoint can hold note recall and "
                         "still take a pipeline rule off the air: "
                         "rhythm.resolve_rhythms_for_cell consumes YOLO `beam` "
                         "and the ledger-ladder arbitration consumes "
                         "`ledgerLine`, and both went dark on every round-3/4 "
                         "candidate with nothing failing.")
    ap.add_argument("--gate-floor", type=int, default=20,
                    help="only classes the baseline reads at least this often "
                         "are gated — a class it barely reads cannot collapse "
                         "informatively.")
    ap.add_argument("--gate-ratio", type=float, default=0.25,
                    help="a gated class must survive at this fraction of the "
                         "baseline's count.")
    ap.add_argument("--gate-exempt", nargs="*", default=["staff"],
                    help="classes whose collapse is not a loss. Only `staff`, "
                         "which classical CV owns by project policy. ⚠️ An "
                         "earlier version of this list also exempted "
                         "`restWhole` on the grounds that production's 396 "
                         "over five pages must be the documented slur-arc "
                         "false-positive mode. Counted against the truth "
                         "files that is wrong in the other direction: those "
                         "five pages carry 801 resting bars (194 / 194 / 18 / "
                         "99 / 296 measure rests), and production reads 108 / "
                         "88 / 11 / 96 / 93 — UNDER the printed count on every "
                         "page, never over. Whole rests are a real loss here, "
                         "and the exemption was an assumption that survived "
                         "one paragraph of prose and no arithmetic.")
    a = ap.parse_args()

    works = json.loads((BENCH / "works.json").read_text())
    rows = [r["row_id"] for r in works["rows"]]
    if a.rows:
        rows = [r for r in rows if r in a.rows]

    out = {}
    for spec in a.arms:
        tag = spec.split("=", 1)[0]
        per_cut = collections.Counter()
        confs = []
        by_class_at_25 = collections.Counter()
        n_files = 0
        for row in rows:
            f = BENCH / "fixtures" / f"{row}.{tag}.omr.json"
            if not f.exists():
                print(f"  MISSING {f}")
                continue
            n_files += 1
            raw = json.loads(f.read_text())
            for d in detections(raw):
                c = float(d.get("confidence") or 0.0)
                confs.append(c)
                for cut in a.cuts:
                    if c >= cut:
                        per_cut[cut] += 1
                if c >= 0.25:
                    by_class_at_25[d.get("class") or d.get("smufl_name")] += 1
        out[tag] = {
            "files": n_files,
            "detections_total": len(confs),
            "at_cut": {str(c): per_cut[c] for c in a.cuts},
            "median_conf": round(statistics.median(confs), 4) if confs else None,
            "mean_conf": round(statistics.fmean(confs), 4) if confs else None,
            "top_classes_at_0.25": dict(by_class_at_25.most_common(15)),
            # the FULL inventory — the gate reads this, never the top-15, or a
            # class that collapses out of the printed list is invisible to it.
            "_all_classes_at_0.25": dict(by_class_at_25),
        }

    print(json.dumps({k: {kk: vv for kk, vv in v.items()
                          if kk != "_all_classes_at_0.25"}
                      for k, v in out.items()}, indent=1))

    if a.gate:
        base = out.get(a.gate)
        if base is None:
            print(f"GATE: baseline arm {a.gate!r} has no fixtures", file=sys.stderr)
            return 2
        failures = []
        for tag, arm in out.items():
            if tag == a.gate:
                continue
            for cls, n in base["_all_classes_at_0.25"].items():
                if n < a.gate_floor or cls in a.gate_exempt:
                    continue
                got = arm["_all_classes_at_0.25"].get(cls, 0)
                if got < n * a.gate_ratio:
                    failures.append((tag, cls, n, got))
        if failures:
            print("\nGATE AXIS 3 — CLASS-SPACE SURVIVAL: FAIL", file=sys.stderr)
            for tag, cls, n, got in failures:
                print(f"  {tag:12s} {cls:22s} baseline {n:4d} -> {got:4d}",
                      file=sys.stderr)
            return 1
        print("\nGATE AXIS 3 — CLASS-SPACE SURVIVAL: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
