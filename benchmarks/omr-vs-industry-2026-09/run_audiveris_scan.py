"""Audiveris on the SCAN benchmark's five scored pages, scored by our bridge.

The engraved comparison (run_industry.py) covered Audiveris's best case —
clean LilyPond renders. This is the other half: the same five real scanned
pages `scan_eval.py` pools, same trimmed truths, same scorer. Our side of the
table is read from the scan benchmark's own results.json rather than re-run.

    python3 benchmarks/omr-vs-industry-2026-09/run_audiveris_scan.py

Resumable; writes results-audiveris-scan.json beside results.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
if "OMRNED_PYTHON" not in os.environ:
    os.environ["OMRNED_PYTHON"] = str(MAIN / ".venv-omrned" / "bin" / "python")

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import omr_ned  # noqa: E402

import fitz  # noqa: E402

SCAN_BENCH = MAIN / "benchmarks" / "omr-scan-e2e-2026-09"
# Trimmed truths are build products; the main checkout's fixtures dir has the
# canonical set (this worktree's is empty).
TRUTH_DIRS = [SCAN_BENCH / "fixtures",
              MAIN / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures"]
OUT = HERE / "out" / "audiveris-scan"
RESULTS = HERE / "results-audiveris-scan.json"
AUDIVERIS = Path("/Applications/Audiveris.app/Contents/MacOS/Audiveris")
TIMEOUT_S = 1800


def truth_for(row_id: str) -> Path:
    for d in TRUTH_DIRS:
        p = d / f"{row_id}.truth.musicxml"
        if p.is_file():
            return p
    raise FileNotFoundError(f"no trimmed truth for {row_id} in {TRUTH_DIRS}")


MAX_PIXELS = 19_500_000  # Audiveris hard-refuses images over 20 MP


def page_png(src: Path, page_index: int, dest: Path) -> tuple[Path, int]:
    """Render one page at the highest DPI (<= 600) under Audiveris's 20 MP cap.

    600 is what our own pipeline reads; Audiveris's own PDF rasterization
    (300 dpi) drops the small-format Litolff print below its minimum interline,
    while a flat 600 puts the folio pages (Brahms: 46 MP) over its maximum
    image size — so the DPI adapts per page and is recorded per row."""
    with fitz.open(src) as doc:
        rect = doc[page_index].rect
        px_at_600 = (rect.width / 72 * 600) * (rect.height / 72 * 600)
        dpi = 600 if px_at_600 <= MAX_PIXELS else int((MAX_PIXELS / px_at_600) ** 0.5 * 600)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            pix = doc[page_index].get_pixmap(dpi=dpi)
            pix.save(dest)
    return dest, dpi


def run_audiveris(row_id: str, pdf: Path) -> Path:
    out_dir = OUT / row_id
    out_dir.mkdir(parents=True, exist_ok=True)
    def _produced() -> list:
        hits = sorted(out_dir.rglob("*.mxl")) + sorted(out_dir.rglob("*.xml"))
        return [p for p in hits if "opus" not in p.name]
    if _produced():
        return _produced()[0]
    env = dict(os.environ, TESSDATA_PREFIX="/Users/seanjohnson/audiveris-tessdata")
    proc = subprocess.Popen(
        [str(AUDIVERIS), "-batch", "-export",
         "-constant", "org.audiveris.omr.sheet.SheetStub.stepTimeOut=900",
         "-output", str(out_dir), str(pdf)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )
    t0 = time.time()
    try:
        while time.time() - t0 < TIMEOUT_S:
            if proc.poll() is not None:
                break
            hits = _produced()
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


def main() -> int:
    scan_results = json.loads((SCAN_BENCH / "results-restamp-composed.json").read_text())
    works = json.loads((SCAN_BENCH / "works.json").read_text())
    rows_meta = {r["row_id"]: r
                 for r in (works["rows"] if isinstance(works, dict) else works)}
    ours = {r["row_id"].split(".restamp")[0]: r for r in scan_results["rows"]}
    lib = library_root()

    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else {"rows": {}}
    for row_id, our in ours.items():
        if res["rows"].get(row_id, {}).get("status") == "ok":
            print("skip %s (recorded ok)" % row_id, flush=True)
            continue
        meta = rows_meta[row_id]
        src_pdf = lib / meta["edition"]["catalog_path"]
        page_ix = meta["page"]["pdf_page_index"]
        truth = truth_for(row_id)
        page_img, dpi = page_png(src_pdf, page_ix, OUT / row_id / "page.png")
        record_dpi = dpi
        print("run  %s (page %d of %s) ..." % (row_id, page_ix, src_pdf.name),
              flush=True)
        t0 = time.time()
        record = {"label": meta["label"], "seconds": None, "input_dpi": record_dpi}
        try:
            pred = run_audiveris(row_id, page_img)
            record["seconds"] = round(time.time() - t0, 1)
            try:
                score = omr_ned.score_pair(pred=pred, truth=truth, name=row_id)
            except Exception:
                # Some Audiveris exports (overfull measures) crash music21's
                # makeTies inside musicdiff; a makeNotation=False pass-through
                # re-serialization adds/removes no symbols.
                norm = pred.with_suffix(".norm.musicxml")
                subprocess.run(
                    [os.environ["OMRNED_PYTHON"], "-c",
                     "import music21,sys; s=music21.converter.parse(sys.argv[1], forceSource=True); "
                     "s.write('musicxml', fp=sys.argv[2], makeNotation=False)",
                     str(pred), str(norm)], check=True, capture_output=True)
                pred = norm
                record["normalized"] = True
                score = omr_ned.score_pair(pred=pred, truth=truth, name=row_id)
            record.update(status="ok", omr_ned=score["omr_ned"],
                          omr_ed=score["omr_ed"],
                          truth_symbols=score["truth_symbols"],
                          pred_symbols=score["pred_symbols"],
                          pred_path=str(pred.relative_to(HERE)))
            cats = score.get("categories") or {}
            record["top_categories"] = dict(
                sorted(cats.items(), key=lambda kv: -kv[1])[:5])
            print("     audiveris %.4f vs ours %.4f  (%d edits, %.0fs)" %
                  (score["omr_ned"], our["omr_ned"]["omr_ned"], score["omr_ed"],
                   record["seconds"]), flush=True)
        except Exception as exc:
            record.update(status="failed", error=str(exc)[:2000],
                          seconds=round(time.time() - t0, 1))
            print("     FAILED: %s" % str(exc).splitlines()[0][:120], flush=True)
        res["rows"][row_id] = record
        RESULTS.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")

    ok = [r for r in res["rows"].values() if r.get("status") == "ok"]
    if ok:
        ed = sum(r["omr_ed"] for r in ok)
        denom = sum(r["truth_symbols"] + r["pred_symbols"] for r in ok)
        res["pooled"] = {"omr_ned": ed / denom, "omr_ed": ed,
                         "n_rows": len(ok)}
        RESULTS.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        print("\naudiveris pooled over %d scan rows: %.4f (%d edits)"
              % (len(ok), ed / denom, ed))
        print("ours (recorded):                    %.4f (%d edits)"
              % (scan_results["pooled"]["omr_ned"],
                 scan_results["pooled"]["omr_ed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
