"""Two censuses over the measurement estate, both read-only.

A. VISIBILITY. For each of the 14 pipeline stages the status board names, does
   each input family (engraved / scan) have a NUMBER at all? A stage with no
   number is not a 0 and not a 100 — it is a ceiling of zero information, and
   the board already says so in prose. This counts it.

B. STAMPS. Of every committed benchmark result JSON, how many carry the two
   things a figure needs before it can be differenced against another: the
   COMMIT it was measured on, and the ERA (work set / row set / transform
   version) it was pooled over. `tools/omr/accuracy_record.py` enforces both for
   the engraved headline; nothing enforces either anywhere else.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import require_nonempty  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "measurement-hygiene.json"
CONTENT = ROOT / "docs" / "progress-dashboard.content.json"

COMMIT_KEYS = ("commit", "git_head", "git_sha", "head", "sha", "rev")
ERA_KEYS = ("benchmark", "era", "work_set", "transform_version", "protocol",
            "arm", "tag", "headline_is")


def visibility() -> dict:
    content = json.loads(CONTENT.read_text())
    stages = content["pipeline"]["stages"]
    out = {"n_stages": len(stages), "stages": []}
    blind = {"engraved": [], "scan": []}
    for s in stages:
        rec = {"n": s["n"], "name": s["name"]}
        for fam in ("engraved", "scan"):
            cell = s.get(fam) or {}
            has_metric = bool(cell.get("metric"))
            has_rate = cell.get("rate") is not None
            scoreable = has_metric or has_rate
            rec[fam] = {
                "scoreable": scoreable,
                "reason": None if scoreable else cell.get("display"),
            }
            if not scoreable:
                blind[fam].append("%s %s — %s" % (s["n"], s["name"], cell.get("display")))
        out["stages"].append(rec)
    out["blind"] = blind
    out["summary"] = {
        "engraved_stages_with_no_number": len(blind["engraved"]),
        "scan_stages_with_no_number": len(blind["scan"]),
        "stages_blind_on_both_sides": sum(
            1 for s in out["stages"]
            if not s["engraved"]["scoreable"] and not s["scan"]["scoreable"]),
    }
    return out


def stamps() -> dict:
    rows = []
    for p in sorted((ROOT / "benchmarks").rglob("*.json")):
        rel = str(p.relative_to(ROOT))
        if "/fixtures/" in rel or "/out/" in rel or "/cells/" in rel:
            continue
        name = p.name
        if not re.match(r"^(results|current-accuracy|.*-arm|.*-comparison)", name):
            continue
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        keys = set(doc.keys())
        # a commit may be nested one level down, per run/arm — current-accuracy
        # keeps it under runs.<config>.commit, and a top-level-only check would
        # report that file as unstamped, which it is not.
        nested = set()
        for v in doc.values():
            if isinstance(v, dict):
                for vv in v.values():
                    if isinstance(vv, dict):
                        nested |= set(vv.keys())
                nested |= set(v.keys())
        rows.append({
            "path": rel,
            "has_commit": bool((keys | nested) & set(COMMIT_KEYS)),
            "has_era": bool(keys & set(ERA_KEYS)),
            "n_rows": len(doc.get("rows") or doc.get("works") or []) or None,
        })
    require_nonempty(rows, "result artefacts", ROOT / "benchmarks", "results*.json")
    n = len(rows)
    return {
        "n_result_artefacts": n,
        "with_commit": sum(1 for r in rows if r["has_commit"]),
        "with_era": sum(1 for r in rows if r["has_era"]),
        "with_both": sum(1 for r in rows if r["has_commit"] and r["has_era"]),
        "with_neither": sum(1 for r in rows if not r["has_commit"] and not r["has_era"]),
        "machine_checked_era": 1,
        "machine_checked_era_note": "exactly one artefact has an era stamp a "
                "test refuses to let drift: current-accuracy.json, guarded by "
                "accuracy_record.check() + test_accuracy_record.py. Every other "
                "`era` here is prose a reader must notice.",
        "note": "`has_era` is generous — any of %s counts, and `protocol` names "
                "the configuration but NOT the row set. Only "
                "benchmarks/omr-ned-2026-08/current-accuracy.json carries a "
                "machine-CHECKED era (accuracy_record.check refuses a record "
                "whose stamp disagrees with BENCHMARK_WORKS)." % (ERA_KEYS,),
        "rows": rows,
    }


def main() -> int:
    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_measurement_hygiene.py",
        "visibility": visibility(),
        "stamps": stamps(),
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    v = doc["visibility"]
    print("VISIBILITY — %d stages" % v["n_stages"])
    print(json.dumps(v["summary"], indent=1))
    for fam in ("engraved", "scan"):
        print(" %s blind at:" % fam)
        for b in v["blind"][fam]:
            print("   ", b)
    s = doc["stamps"]
    print("\nSTAMPS — %d result artefacts: commit %d, era %d, both %d, neither %d"
          % (s["n_result_artefacts"], s["with_commit"], s["with_era"],
             s["with_both"], s["with_neither"]))
    for r in s["rows"]:
        if not r["has_commit"]:
            print("   no commit: %s (rows=%s)" % (r["path"], r["n_rows"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
