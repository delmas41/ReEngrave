"""Run industrial / open-source OMR engines on OUR engraved fixtures, scored by OUR scorer.

Published OMR-NED figures (Sheet Music Benchmark, LEGATO 2) are measured on other
corpora and are NOT comparable to this repo's headline — a pooled OMR-NED is a
property of the work set it is pooled over. The valid comparison is this one:
the same 11 fixtures `orchestral_eval` regenerates, the same musicdiff bridge,
one row per engine.

Engines:
  - audiveris  /Applications/Audiveris.app       (5.11.0, batch CLI, takes PDF)
  - oemer      ~/Library/Python/3.9/bin/oemer    (0.1.8, takes PNG; known 2-staff
               grand-staff assertion — orchestral failure is an expected finding)
  - homr       <repo>/.venv-homr/bin/homr        (0.7.0, takes PNG)

Usage (from the repo root or a worktree):
    python3 benchmarks/omr-vs-industry-2026-09/run_industry.py                 # everything
    python3 benchmarks/omr-vs-industry-2026-09/run_industry.py --engines audiveris
    python3 benchmarks/omr-vs-industry-2026-09/run_industry.py --works beethoven-sym5-mvt1

Resumable: an engine/work pair with a recorded result in results.json is skipped
unless --force. Fixtures are build products regenerated into ./fixtures/
(gitignored), never committed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

# The scorer venv is repo-root-relative and absent in a worktree — point at the
# main checkout unless the caller already did (see CLAUDE.md, OMR-NED section).
MAIN_CHECKOUT = Path("/Users/seanjohnson/Desktop/ReEngrave")
if "OMRNED_PYTHON" not in os.environ:
    cand = MAIN_CHECKOUT / ".venv-omrned" / "bin" / "python"
    if cand.exists():
        os.environ["OMRNED_PYTHON"] = str(cand)

from tools.omr import accuracy_record  # noqa: E402
from tools.omr import omr_ned  # noqa: E402
from tools.omr.training import orchestral_eval  # noqa: E402

import fitz  # noqa: E402

FIXTURES = HERE / "fixtures"
OUT = HERE / "out"
RESULTS = HERE / "results.json"

AUDIVERIS = Path("/Applications/Audiveris.app/Contents/MacOS/Audiveris")
OEMER = Path.home() / "Library" / "Python" / "3.9" / "bin" / "oemer"
HOMR = MAIN_CHECKOUT / ".venv-homr" / "bin" / "homr"

PNG_DPI = 300          # what oemer/homr receive; Audiveris rasterizes the PDF itself
TIMEOUT_S = 1800       # per engine per work


def build_fixture(work_id: str) -> tuple[Path, Path]:
    """(truth_xml, pdf) — regenerated via the benchmark's own excerpt()."""
    truth = FIXTURES / f"{work_id}.musicxml"
    pdf = FIXTURES / f"{work_id}.pdf"
    if truth.exists() and pdf.exists():
        return truth, pdf
    first, last = orchestral_eval.DEFAULT_MEASURES
    xml, pdf, _last_used, _ly = orchestral_eval.excerpt(work_id, first, last, FIXTURES)
    return xml, pdf


def page_png(pdf: Path) -> Path:
    png = pdf.with_suffix(".png")
    if not png.exists():
        with fitz.open(pdf) as doc:
            pix = doc[0].get_pixmap(dpi=PNG_DPI)
            pix.save(png)
    return png


# ── engines: each returns the produced MusicXML path or raises ───────────────

def run_audiveris(work_id: str, pdf: Path) -> Path:
    out_dir = OUT / "audiveris" / work_id
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    # Audiveris 5.11 in batch mode does not exit after a successful export on
    # macOS (a non-daemon thread lingers) — measured: export done in ~60 s,
    # process still alive 11 min later. So poll for the export instead of
    # waiting on the process, then kill it.
    # OCR languages on, so Audiveris competes at full strength on text
    # (directions, lyrics). The 2026-09-04 first pass ran without them.
    env = dict(os.environ, TESSDATA_PREFIX="/Users/seanjohnson/audiveris-tessdata")
    proc = subprocess.Popen(
        [str(AUDIVERIS), "-batch", "-export", "-output", str(out_dir), str(pdf)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )
    def _produced() -> list:
        hits = sorted(out_dir.rglob("*.mxl")) + sorted(out_dir.rglob("*.xml"))
        return [p for p in hits if "opus" not in p.name]
    t0 = time.time()
    try:
        while time.time() - t0 < TIMEOUT_S:
            if proc.poll() is not None:
                break
            hits = _produced()
            # settle: the file must be non-empty and untouched for a few seconds
            if hits and hits[0].stat().st_size > 0 and \
                    time.time() - hits[0].stat().st_mtime > 5:
                break
            time.sleep(3)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    produced = _produced()
    if not produced:
        raise RuntimeError("no MusicXML produced (rc=%s)" % proc.returncode)
    return produced[0]


def run_oemer(work_id: str, pdf: Path) -> Path:
    png = page_png(pdf)
    out_xml = OUT / "oemer" / f"{work_id}.musicxml"
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(OEMER), "-o", str(out_xml), str(png)],
        capture_output=True, text=True, timeout=TIMEOUT_S,
    )
    # oemer treats -o as a directory prefix in some versions; glob defensively.
    if not out_xml.exists():
        hits = sorted(out_xml.parent.glob(f"{png.stem}*.musicxml"))
        if hits:
            return hits[0]
        raise RuntimeError(
            "no MusicXML produced (rc=%d)\n%s" % (proc.returncode,
                                                  (proc.stderr or proc.stdout)[-2000:]))
    return out_xml


def run_homr(work_id: str, pdf: Path) -> Path:
    png = page_png(pdf)
    work_png = OUT / "homr" / f"{work_id}.png"
    work_png.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(png, work_png)
    proc = subprocess.run(
        [str(HOMR), str(work_png)],
        capture_output=True, text=True, timeout=TIMEOUT_S,
    )
    hits = sorted(work_png.parent.glob(f"{work_id}*.musicxml")) + \
        sorted(work_png.parent.glob(f"{work_id}*.xml"))
    if not hits:
        raise RuntimeError(
            "no MusicXML produced (rc=%d)\n%s" % (proc.returncode,
                                                  (proc.stderr or proc.stdout)[-2000:]))
    return hits[0]


ENGINES = {
    "audiveris": run_audiveris,
    "oemer": run_oemer,
    "homr": run_homr,
}


def load_results() -> dict:
    if RESULTS.exists():
        return json.loads(RESULTS.read_text())
    return {"_comment": "one row per engine per work; written by run_industry.py",
            "png_dpi": PNG_DPI, "engines": {}}


def save_results(res: dict) -> None:
    RESULTS.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=list(ENGINES),
                    choices=list(ENGINES))
    ap.add_argument("--works", nargs="+",
                    default=list(accuracy_record.BENCHMARK_WORKS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    if "OMRNED_PYTHON" not in os.environ:
        print("error: no .venv-omrned found — bootstrap it in the main checkout",
              file=sys.stderr)
        return 2

    res = load_results()
    for engine in args.engines:
        res["engines"].setdefault(engine, {})

    print("building fixtures ...", flush=True)
    fixtures = {}
    for work in args.works:
        fixtures[work] = build_fixture(work)
        print("  %s ok" % work, flush=True)

    for engine in args.engines:
        runner = ENGINES[engine]
        for work in args.works:
            row = res["engines"][engine].get(work)
            if row and not args.force:
                print("skip %s/%s (recorded)" % (engine, work), flush=True)
                continue
            truth, pdf = fixtures[work]
            print("run  %s/%s ..." % (engine, work), flush=True)
            t0 = time.time()
            record = {"seconds": None, "status": None}
            try:
                pred = runner(work, pdf)
                record["seconds"] = round(time.time() - t0, 1)
                record["pred_path"] = str(pred.relative_to(HERE))
                score = omr_ned.score_pair(pred=pred, truth=truth, name=work)
                record["status"] = "ok"
                record["omr_ned"] = score["omr_ned"]
                record["omr_ed"] = score["omr_ed"]
                record["truth_symbols"] = score["truth_symbols"]
                record["pred_symbols"] = score["pred_symbols"]
                cats = score.get("categories") or {}
                record["top_categories"] = dict(
                    sorted(cats.items(), key=lambda kv: -kv[1])[:5])
                print("     %.4f  (%d edits, %.0fs)" %
                      (score["omr_ned"], score["omr_ed"], record["seconds"]),
                      flush=True)
            except subprocess.TimeoutExpired:
                record["seconds"] = round(time.time() - t0, 1)
                record["status"] = "timeout"
                print("     TIMEOUT after %ds" % TIMEOUT_S, flush=True)
            except Exception as exc:  # engine failure IS a benchmark result
                record["seconds"] = round(time.time() - t0, 1)
                record["status"] = "failed"
                record["error"] = str(exc)[:2000]
                print("     FAILED: %s" % str(exc).splitlines()[0][:120], flush=True)
            res["engines"][engine][work] = record
            save_results(res)

    # summary
    print("\n%-11s %8s %8s %8s" % ("engine", "pooled", "edits", "scored"))
    for engine in args.engines:
        rows = [r for r in res["engines"][engine].values() if r.get("status") == "ok"]
        n_all = len(res["engines"][engine])
        if rows:
            ed = sum(r["omr_ed"] for r in rows)
            denom = sum(r["truth_symbols"] + r["pred_symbols"] for r in rows)
            print("%-11s %8.4f %8d %5d/%d" % (engine, ed / denom, ed, len(rows), n_all))
        else:
            print("%-11s %8s %8s %5d/%d" % (engine, "-", "-", 0, n_all))
    print("\nwrote %s" % RESULTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
