"""Transcribe every row of both corpora ONCE, resumably, and keep the JSON.

Why not `scan_eval` / `orchestral_eval`: those score, and scoring is not the
question here. This benchmark asks what the pipeline READ — staff counts,
instruments, clefs, key signatures — which is the transcription itself. Running
the scorers would cost the musicdiff bridge and the fixture rebuild for output
this never looks at.

⚠️ RESUMABLE BY DESIGN. Two long runs were killed on this machine the day before
this was written, and the ones that cost nothing were the ones that could be
restarted. A row whose output JSON already exists is skipped, so an interrupted
run resumes by being run again.

⚠️ Thread-limited on purpose — another agent prices arms on the same machine.
Set the OMP/MKL caps in the environment before importing torch, which is what
the `--threads` flag does by re-execing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "readings"

SCAN_WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"


def _engraved_fixtures() -> Path:
    """Where the rendered engraved excerpts live.

    ⚠️ They are BUILD PRODUCTS in a gitignored directory, so a fresh worktree
    has none — the same asymmetry `library_root()` already handles by resolving
    to the MAIN checkout. We reuse the excerpts the canonical run rendered
    rather than rebuilding them: `excerpt()` would re-render every work through
    LilyPond to produce byte-identical input for pages this benchmark does not
    score. The PDF is a deterministic render of a committed reference, so
    reusing it is reuse, not staleness — unlike the `.omr.json` beside it,
    which this benchmark deliberately regenerates because it predates the
    roster default.
    """
    local = REPO / "benchmarks/omr-orchestral-e2e/fixtures"
    if any(local.glob("*.pdf")):
        return local
    return _library_root().parent / "benchmarks/omr-orchestral-e2e/fixtures"


def scan_rows() -> list[dict]:
    doc = json.loads(SCAN_WORKS.read_text())
    rows = doc["rows"]
    out = []
    for r in rows:
        out.append({
            "row_id": r["row_id"],
            "corpus": "scan",
            "pdf": str(_library_root() / r["edition"]["catalog_path"]),
            "page": r["page"]["pdf_page_index"],
        })
    return out


def engraved_rows() -> list[dict]:
    from tools.omr.accuracy_record import BENCHMARK_WORKS
    out = []
    fixtures = _engraved_fixtures()
    for w in BENCHMARK_WORKS:
        pdf = fixtures / f"{w}.pdf"
        out.append({"row_id": w, "corpus": "engraved",
                    "pdf": str(pdf), "page": 0,
                    "missing": not pdf.exists()})
    return out


def _library_root():
    from tools.library.score_library import library_root
    return library_root()


def run_one(row: dict, dpi: int) -> tuple[str, float]:
    dest = OUT / f"{row['corpus']}--{row['row_id']}.omr.json"
    if dest.exists():
        return "skip", 0.0
    if row.get("missing"):
        return "missing-pdf", 0.0
    t0 = time.time()
    cmd = [sys.executable, "-u", "-m", "tools.omr.transcribe", row["pdf"],
           "--pages", str(row["page"]), "--out", str(dest) + ".part"]
    if dpi:
        cmd += ["--dpi", str(dpi)]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        (OUT / f"{row['corpus']}--{row['row_id']}.FAILED.log").write_text(
            proc.stdout + "\n===STDERR===\n" + proc.stderr)
        return "FAIL", time.time() - t0
    # Atomic-ish: only name it the real thing once it parsed. A half-written
    # JSON that resume() then SKIPS is the failure this guards.
    part = Path(str(dest) + ".part")
    json.loads(part.read_text())
    part.rename(dest)
    return "ok", time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", choices=["scan", "engraved", "both"],
                    default="both")
    ap.add_argument("--dpi", type=int, default=0,
                    help="0 = the CLI default (600). Do not 'unify' this with "
                         "the backend's 300 — see CLAUDE.md's knobs table.")
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()

    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(args.threads)

    sys.path.insert(0, str(REPO))
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    if args.corpus in ("scan", "both"):
        rows += scan_rows()
    if args.corpus in ("engraved", "both"):
        rows += engraved_rows()

    # ⚠️ Assert the input counts before trusting anything downstream. An audit
    # that can return "nothing found" must first prove it looked at something.
    n_scan = sum(1 for r in rows if r["corpus"] == "scan")
    n_eng = sum(1 for r in rows if r["corpus"] == "engraved")
    print(f"rows: {len(rows)} total ({n_scan} scan, {n_eng} engraved)",
          flush=True)
    if args.corpus == "both" and (n_scan, n_eng) != (20, 11):
        print(f"REFUSING: expected 20 scan + 11 engraved, got {n_scan}+{n_eng}",
              file=sys.stderr)
        return 2

    tallies: dict[str, int] = {}
    for i, row in enumerate(rows, 1):
        status, secs = run_one(row, args.dpi)
        tallies[status] = tallies.get(status, 0) + 1
        print(f"[{i:3d}/{len(rows)}] {status:12s} {secs:6.1f}s  "
              f"{row['corpus']}/{row['row_id']}", flush=True)
    print("TALLY", json.dumps(tallies), flush=True)
    print("CORPUS_DONE", flush=True)
    return 0 if not tallies.get("FAIL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
