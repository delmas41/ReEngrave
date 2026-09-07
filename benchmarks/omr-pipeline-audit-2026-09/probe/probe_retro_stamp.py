"""Propose the era stamp `scan_eval.py` does not write, and retro-fit it.

`tools/omr/accuracy_record.py` makes the engraved headline undateable-proof: the
record carries a `benchmark` block naming the work set and the date it last
changed, and `check()` refuses a record whose stamp disagrees with the code's own
`BENCHMARK_WORKS`. The scan harness has none of that. Its results files are
distinguishable only by `len(rows)`, across four row-set eras.

⚠️ THE MAPPING IS A WASTING ASSET. The commit that wrote each file is still
recoverable from `git log -1 -- <path>` today. It stops being recoverable the
moment someone reformats, moves or regenerates one, and nothing warns.

This proposes the stamp and DEMONSTRATES it on COPIES under `stamped-copies/`.
It does not modify `tools/omr/` or any existing artefact — a stamping change to
the harness needs its own review.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_retro_stamp.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import require_nonempty  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "retro-stamp.json"
COPIES = HERE / "stamped-copies"
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"

#: What the scan harness should stamp, mirroring accuracy_record's `benchmark`.
STAMP_SHAPE = {
    "name": "the harness's name, e.g. 'scan-e2e'",
    "since": "ISO date the ROW SET last changed — what makes an old file legibly old",
    "rows": "the row_ids the figure is pooled over, in order",
    "n_rows": "len(rows), so a truncated file is detectable",
    "commit": "git rev-parse --short HEAD at measurement time",
    "fixture_sha": "⚠️ REQUIREMENT ADDED 2026-09-07. A per-row sha256 of every "
                   "input file, computed so that it CAN VERIFY REPRODUCTION. "
                   "`results-normalised-arm-20row.json` stamps "
                   "`sha.normalised_truth` as a RAW sha256 of a derived truth "
                   "that music21 re-ids on every write — so it looks like a "
                   "provenance field and cannot serve as one, which is worse "
                   "than having none. Any hash of a GENERATED file must be "
                   "canonicalised the way "
                   "probe_derived_truth_unmoved.py::_canonical does, and the "
                   "stamp must say which kind it is.",
    "arm": "the --tag, i.e. WHICH predictions",
    "flags": "every OMR_* env var that was set, and its value",
    "note": "why a figure under a different row set is not a comparison",
}


def git_commit_for(path: Path) -> dict:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%h|%ad|%s", "--date=short",
         "--", str(path.relative_to(ROOT))],
        capture_output=True, text=True).stdout.strip()
    if not out:
        return {"commit": None, "date": None, "subject": None,
                "recoverable": False}
    h, d, s = out.split("|", 2)
    return {"commit": h, "date": d, "subject": s, "recoverable": True}


def main() -> int:
    COPIES.mkdir(exist_ok=True)
    files = require_nonempty(sorted(SCAN.glob("results*.json")),
                             "scan results files", SCAN, "results*.json")
    rows, stamped = [], 0
    for f in files:
        doc = json.loads(f.read_text())
        rowlist = doc.get("rows") or []
        ids = [r["row_id"].split(".")[0] for r in rowlist if isinstance(r, dict)]
        tags = sorted({r["row_id"].split(".", 1)[1] for r in rowlist
                       if isinstance(r, dict) and "." in r["row_id"]})
        g = git_commit_for(f)
        pooled = doc.get("pooled") or {}
        rec = {
            "path": str(f.relative_to(ROOT)),
            "n_rows": len(ids),
            "arm_tags_in_file": tags,
            "has_commit_already": any(k in doc for k in ("git_head", "commit")),
            "recovered": g,
            "pooled_omr_ned": pooled.get("omr_ned"),
            "pooled_n_rows": pooled.get("n_rows"),
        }
        rows.append(rec)
        # the demonstration: the same file with a stamp, written to a COPY
        proposed = {
            "name": "scan-e2e",
            "since": None,          # a human sets this when the row set changes
            "rows": ids,
            "n_rows": len(ids),
            "commit": g["commit"],
            "commit_source": "RETRO-FITTED from `git log -1 -- <path>` on "
                             "2026-09-07, NOT recorded at measurement time",
            "arm": tags[0] if len(tags) == 1 else tags,
            "flags": doc.get("protocol"),
            "note": "A pooled OMR-NED is a property of this row set as much as "
                    "of the pipeline. A figure measured under a different set is "
                    "a different measurement, not a comparison.",
        }
        out_copy = COPIES / f.name
        stamped_doc = {"benchmark": proposed, **doc}
        out_copy.write_text(json.dumps(stamped_doc, indent=1) + "\n")
        stamped += 1

    eras = {}
    for r in rows:
        eras.setdefault(r["n_rows"], []).append(r["path"].split("/")[-1])

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/probe_retro_stamp.py",
        "proposal": {
            "where": "benchmarks/omr-scan-e2e-2026-09/scan_eval.py, written into "
                     "every results file as a top-level `benchmark` block",
            "shape": STAMP_SHAPE,
            "hash_rule": "a stamped hash must be verifiable. Raw sha256 for an "
                         "INPUT file that is byte-stable (a truth fixture, a "
                         "prediction); a CANONICAL hash for anything generated "
                         "by a writer with its own randomness. Label which.",
            "plus_a_check": "a `SCAN_ROWS` constant in code + a check() that "
                            "refuses a results file whose `benchmark.rows` "
                            "disagrees with it — the exact shape "
                            "accuracy_record.check() already has, and the reason "
                            "the engraved headline cannot silently cross an era.",
        },
        "did_not_modify": ["tools/omr/**", "benchmarks/omr-scan-e2e-2026-09/**"],
        "demonstrated_on_copies_in": str(COPIES.relative_to(ROOT)),
        "coverage": {
            "n_files": len(rows),
            "n_stamped_copies_written": stamped,
            "already_carrying_a_commit": sum(1 for r in rows if r["has_commit_already"]),
            "commit_recoverable_from_git_today": sum(1 for r in rows
                                                     if r["recovered"]["recoverable"]),
            "commit_NOT_recoverable": [r["path"] for r in rows
                                       if not r["recovered"]["recoverable"]],
        },
        "eras_present": {str(k): v for k, v in sorted(eras.items())},
        "files": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc["coverage"], indent=1))
    print("\nrow-set eras in one directory:")
    for k, v in sorted(eras.items()):
        print("  %2d rows: %d files — %s" % (k, len(v), ", ".join(v[:3])
                                             + (" …" if len(v) > 3 else "")))
    print("\nper-file recovered commits:")
    for r in rows:
        print("  %-46s rows=%-3d commit=%-9s %s"
              % (r["path"].split("/")[-1], r["n_rows"],
                 r["recovered"]["commit"] or "-", r["recovered"]["date"] or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
