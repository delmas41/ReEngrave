"""CLI for the staged pipeline.

    # the three stages on a real PDF, with weights
    python3 -m tools.omr.staged score.pdf --pages 0-2 \
        --weights omr-weights/<file>.pt --out staged.json

    # no weights: every cell abstains READER_UNAVAILABLE and it still runs
    python3 -m tools.omr.staged score.pdf --pages 0

    # a FILE, plus the record of what did not reach it
    python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> \
        --musicxml out.musicxml

    # the A/B: compare against a legacy transcribe result
    python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <...> \
        --against legacy.omr.json

⚠️ THIS RUNS NO BENCHMARK AND SCORES NOTHING. The divergence table is a
POPULATION, not a result: every `differ` row needs a human against the print
before it is a win or a loss.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_pages(spec: str) -> list:
    out = []
    for part in (spec or "0").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def _provenance() -> dict:
    """The commit this record was built from, and whether the tree was dirty.

    ⚠️ Best-effort and NEVER fatal: a record that cannot name its tree is
    still a valid record, and refusing to write one would trade a real
    transcription for a metadata nicety. It is the CONSUMER's job to refuse an
    unstamped comparison, which is where the decision belongs -- writing is
    not the place that can be wrong about it.
    """
    import subprocess
    here = str(Path(__file__).resolve().parent)

    def git(*args):
        # ⚠️ `check_output`, NEVER `subprocess.run` without `check=True`: run
        # returns a non-zero exit as EMPTY STDOUT WITH NO EXCEPTION, so
        # outside a git checkout the id would be `""` -- and two empty stamps
        # compare EQUAL. The meter session hit exactly that in its own guard.
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, cwd=here).decode().strip()

    out = {"commit": None, "dirty": None}
    try:
        # ⚠️⚠️ THE TWO FACTS ARE ATOMIC, AND THAT IS THE WHOLE POINT. An
        # earlier version set `commit` first and `dirty` second inside one
        # `try`, so a `git status` that failed left a record claiming a COMMIT
        # with dirtiness UNKNOWN -- and a consumer reading `dirty` as falsy
        # would call that tree CLEAN. A half-named tree is not a named tree.
        #
        # The general rule, from the meter session generalising my own dirty
        # rule back at me: ANYTHING THAT CANNOT UNIQUELY NAME A TREE MUST
        # NEVER COMPARE EQUAL TO ANYTHING, INCLUDING ITSELF. So both fields
        # are set together or neither is, and `None` is the only failure
        # value -- no magic string like "unknown", which two failing machines
        # would share.
        commit = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain"))
        out["commit"], out["dirty"] = commit, dirty
    except Exception as exc:                       # noqa: BLE001
        out = {"commit": None, "dirty": None,
               "error": f"{type(exc).__name__}: {exc}"}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="The staged pipeline: GATHER -> ADJUDICATE -> EVALUATE")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0")
    ap.add_argument("--weights", default=None,
                    help="YOLO weights. Omit to run with no detector at all -- "
                         "every cell abstains and the pipeline still completes.")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--against", default=None,
                    help="a legacy transcribe result JSON, for the divergence "
                         "table")
    ap.add_argument("--musicxml", default=None,
                    help="also EXPORT the run to MusicXML here. The coverage "
                         "report -- what the record could NOT carry -- goes "
                         "beside it as <path>.coverage.json.")
    # ⚠️ THE FREE RUNG NEEDS NO FLAG AND THE PAID ONES DO. `pdf_path` is now
    # always forwarded to `gather`, which turns on the PDF TEXT LAYER reader
    # -- free, and measured to read NOTHING on a 19th-century scan (0 labels
    # over 75 staves on Litolff Beethoven 5 p.1-4). The OCR rungs are what
    # actually read that edition (50 of 75) and they cost wall clock that
    # CLAUDE.md measures at ~75% of a whole-work run, so they are OPT-IN
    # rather than defaulted: a default that silently trebles a gather is a
    # decision somebody should take deliberately.
    ap.add_argument("--surya", action="store_true",
                    help="read margin labels with Surya where the PDF has no "
                         "text layer. Needed for ANY instrument identity on a "
                         "scan -- without it Q.MARGIN_LABEL stays empty and "
                         "the part join falls back to staff position.")
    ap.add_argument("--ocr", action="store_true",
                    help="also allow the Tesseract rung for margin labels.")
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args(argv)

    from . import legacy, pipeline

    detector = None
    if args.weights:
        from ..yolo_detector import YoloDetector
        detector = YoloDetector(args.weights)

    # ⚠️ ONE gather, including under `--against`. The legacy side is loaded
    # BEFORE the run and handed in, so the divergence table is built from the
    # same log the adjudication report describes. Until 2026-09-08 this
    # re-ran prepare/gather/adjudicate a second time, which doubled the work
    # and compared against a different pass of a detector with documented
    # run-to-run jitter.
    result = pipeline.run_staged(
        args.pdf, parse_pages(args.pages), detector=detector, dpi=args.dpi,
        conf_threshold=args.conf, imgsz=args.imgsz,
        surya_fallback=args.surya, ocr_fallback=args.ocr,
        legacy=legacy.load(args.against) if args.against else None,
        progress=args.progress)

    # ⚠️⚠️ WHICH TREE BUILT THIS RECORD. Without it, comparing two records is
    # an unprovenanced A/B: `regather_control.py` reporting "MOVED: nothing"
    # reads as "my change is inert" when it is equally consistent with having
    # compared two runs of the SAME tree, or a file with itself. That is the
    # cached-arm trap the meter session found in its own `run_arms.py`, one
    # layer down -- and the shape this project keeps paying for, where the
    # failure is never a wrong answer but a RIGHT-LOOKING one.
    #
    # ⚠️ A DIRTY TREE IS NEVER EQUAL TO ITSELF: a SHA cannot tell two sets of
    # uncommitted edits apart, so `dirty` is recorded and any consumer must
    # refuse to treat two dirty stamps as different-or-same. That rule is the
    # meter session's, adopted rather than re-derived.
    result["provenance"] = _provenance()
    text = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)

    if args.musicxml:
        from . import export as staged_export
        xml, report = staged_export.to_musicxml(result)
        Path(args.musicxml).write_text(xml)
        cov = Path(args.musicxml + ".coverage.json")
        cov.write_text(json.dumps(report, indent=2, default=str))
        print(f"wrote {args.musicxml} and {cov}")

    _report(result)
    if args.musicxml:
        staged_export._report(report)
    return 0


def _report(result: dict) -> None:
    adj = result["adjudication"]
    print("\n── ADJUDICATE ─────────────────────────────────────────", file=sys.stderr)
    print(f"  decided:   {adj['decided']}", file=sys.stderr)
    print(f"  abstained: {adj['abstained']}", file=sys.stderr)
    if adj["excluded_as_circular"]:
        print(f"  ⚠️ excluded as circular: {len(adj['excluded_as_circular'])}",
              file=sys.stderr)
    ag = result.get("agreement")
    if ag is not None:
        print("── GROUPS ─────────────────────────────────────────────",
              file=sys.stderr)
        for name, row in sorted(ag["per_redundancy"].items()):
            print(f"  {name}: {row['n_facts']} facts, "
                  f"{row['n_witnesses']} witnesses, "
                  f"{row['uninformative']} uninformative, {row['agreement']}",
                  file=sys.stderr)
        # ⚠️ A DECLARED redundancy that found nothing is named, because a zero
        # is a suspect and not a result.
        for key, gloss in (("declared_but_empty", "placed no fact"),
                           ("witnessed_by_nobody", "no witness spoke"),
                           ("checked_nothing",
                            "never two independent signals -- corroborated "
                            "NOTHING, however busy it looks")):
            if ag.get(key):
                print(f"  ⚠️ {key} ({gloss}): {ag[key]}", file=sys.stderr)
        print(f"  ⚠️ DISAGREEMENTS: {ag['n_disagreements']} "
              f"(each implicates its WHOLE group, not its dissenter)",
              file=sys.stderr)
    ev = result["evaluation"]
    print(f"── EVALUATE: {ev['counts']['fired']} fired, "
          f"{ev['counts']['skipped']} skipped", file=sys.stderr)
    print(f"── DECLARED STUBS: {len(result['stubs']['decisions'])} decisions, "
          f"{len(result['stubs']['consequences'])} consequences", file=sys.stderr)
    if "divergence" in result:
        print(f"── DIVERGENCE: {result['divergence']['counts']}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
