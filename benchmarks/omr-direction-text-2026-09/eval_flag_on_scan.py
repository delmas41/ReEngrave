"""What does turning `--direction-text` ON actually do to a SCAN, end to end?

`SCAN_2026-09-01.md` measured the READER on a scan — 74 candidates over five
pages, 17 accepted, not one invented word, ~37% recall. That answers "is the
reader any good on 1870 paper". It does not answer the question a DEFAULT has to
answer, which is the one `docs/next-steps-omr-2026-09-01.md` §4b leaves open:

    turn the flag on, run the pipeline the way a user runs it, and ask what
    came out DIFFERENT.

The distinction matters because the two failure modes a default has to rule out
are invisible to a reader-level score. A reader with perfect precision can still
make the output worse by attaching a correctly-read word to the wrong beat — the
engraved benchmark priced that at DOUBLE, since musicdiff charges the beat it
went to and the beat it left. And a pass that walks the page dict can perturb
something that has nothing to do with directions.

So this runs each page TWICE, exports both, and compares the two files:

    directions   what the reader proposed, read, and placed
    words        how many <words> actually reached the file
    elsewhere    every difference between the two exports that is NOT a
                 <direction> block — which must be EMPTY, or the flag is not
                 the additive pass it is documented to be

**`elsewhere` is the whole point.** The accuracy case for the flag was made on
engravings and the recall case against it was made on scans; neither says
whether it is SAFE to leave on.

⚠️ **AND A NON-EMPTY `elsewhere` IS NOT BY ITSELF EVIDENCE ABOUT THE FLAG** —
which is the lesson this harness learned the hard way, on its own first run.
Page 84 came back with 485 lines of difference outside every `<direction>`:
part names shifted across seven staves, a clef, and note content. It looked
exactly like the flag perturbing the pipeline, and it is not. Running the SAME
configuration twice reproduces all 485 lines with the reader OFF in both runs.
The page is simply not reproducible, and the reason is visible in
`label_tiers`: Surya resolved 10 margin labels in one run and 1 in the next.

So the control is no longer optional and no longer manual. Any page with a
non-empty `elsewhere` is re-run OFF a second time, and the report says which of
the two it is:

    FLAG      the two OFF runs agree and the ON run does not — the flag did it
    UNSTABLE  the two OFF runs already disagree — the page did it, not the flag

A harness that can only say "something changed" hands its user a conclusion it
has not earned.

    python3 benchmarks/omr-direction-text-2026-09/eval_flag_on_scan.py \
        --pdf library/editions/beethoven/symphony-5-op67/beethoven--*imslp575951.pdf \
        --pages 16 22 39 78 84
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.export import to_musicxml            # noqa: E402
from tools.omr.transcribe import transcribe          # noqa: E402

#: A <direction> block is what the reader adds, so it is the one difference the
#: comparison expects. Removing whole blocks rather than just the <words> line
#: keeps <direction-type>, <offset> and the wrapper from reading as noise.
_DIRECTION = re.compile(r"[ \t]*<direction[ >].*?</direction>\n?", re.S)


def without_directions(xml: str) -> str:
    return _DIRECTION.sub("", xml)


def run(pdf: Path, page: int, weights: str, *, direction_text: bool) -> dict:
    result = transcribe(pdf_path=pdf, pages=[page], weights=weights,
                        progress=False, read_direction_text=direction_text)
    return {"result": result, "xml": to_musicxml(result)}


def _diff(a: str, b: str) -> list[str]:
    return list(difflib.unified_diff(without_directions(a).splitlines(),
                                     without_directions(b).splitlines(),
                                     lineterm="", n=0))


def compare_page(pdf: Path, page: int, weights: str) -> dict:
    off = run(pdf, page, weights, direction_text=False)
    on = run(pdf, page, weights, direction_text=True)

    info = ((on["result"].get("direction_text") or {}).get("pages") or [{}])[0]
    elsewhere = _diff(off["xml"], on["xml"])

    # A difference is only the FLAG's if the page is reproducible without it.
    # See the warning in the module docstring: page 84 of this edition changes
    # by 485 lines between two runs that both have the reader off.
    verdict, control = "clean", []
    if elsewhere:
        off2 = run(pdf, page, weights, direction_text=False)
        control = _diff(off["xml"], off2["xml"])
        verdict = "UNSTABLE" if control else "FLAG"

    return {
        "page": page,
        "n_candidates": info.get("n_candidates", 0),
        "n_read": info.get("n_read", 0),
        "n_accepted": info.get("n_accepted", 0),
        "n_placed": (on["result"].get("direction_text") or {}).get("n_placed", 0),
        "rejected": info.get("rejected", []),
        "words_off": off["xml"].count("<words"),
        "words_on": on["xml"].count("<words"),
        "seconds_off": off["result"]["runtime"]["total_s"],
        "seconds_on": on["result"]["runtime"]["total_s"],
        "seconds_direction_text": on["result"]["runtime"].get("direction_text_s"),
        # Empty means the flag changed nothing but directions. Kept in full
        # rather than as a count: a single line of it would need reading.
        "elsewhere": elsewhere,
        # "clean" | "FLAG" (two OFF runs agree, ON differs) | "UNSTABLE" (the
        # two OFF runs already disagree, so the flag is not what moved it).
        "verdict": verdict,
        "control_off_vs_off": control,
    }


def _verdict_cell(row: dict) -> str:
    """`CLEAN`, or the size of the difference and whose fault it is."""
    if not row["elsewhere"]:
        return "CLEAN"
    return f"{len(row['elsewhere'])} lines {row['verdict']}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--pages", type=int, nargs="+", required=True)
    ap.add_argument("--weights", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    weights = args.weights
    if weights is None:
        from tools.omr.transcribe import DEFAULT_WEIGHTS
        weights = DEFAULT_WEIGHTS

    rows = [compare_page(args.pdf, p, weights) for p in args.pages]

    print(f"{'page':>5} {'cand':>5} {'read':>5} {'acc':>4} {'placed':>7} "
          f"{'words':>6} {'s off':>7} {'s on':>7} {'s dir':>7}  elsewhere")
    for r in rows:
        print(f"{r['page']:>5} {r['n_candidates']:>5} {r['n_read']:>5} "
              f"{r['n_accepted']:>4} {r['n_placed']:>7} "
              f"{r['words_off']}->{r['words_on']:<4} "
              f"{r['seconds_off']:>7.1f} {r['seconds_on']:>7.1f} "
              f"{r['seconds_direction_text']:>7.1f}  "
              f"{_verdict_cell(r)}")

    placed = sum(r["n_placed"] for r in rows)
    words = sum(r["words_on"] for r in rows)
    blamed = [r["page"] for r in rows if r["verdict"] == "FLAG"]
    unstable = [r["page"] for r in rows if r["verdict"] == "UNSTABLE"]
    off_t = sum(r["seconds_off"] for r in rows)
    on_t = sum(r["seconds_on"] for r in rows)

    print(f"\n  {placed} directions placed, {words} <words> in the files")
    # Placed-but-not-exported is the recognised-then-dropped shape on the newest
    # layer, and it is reported here rather than left to be noticed: the three
    # ENGRAVED works export every word they place, so a gap is scan-specific.
    if placed != words:
        lost = [(r["page"], r["n_placed"] - r["words_on"])
                for r in rows if r["n_placed"] != r["words_on"]]
        print(f"  !! {placed - words} placed and never exported, by page: {lost}")
    print(f"  {off_t:.1f}s -> {on_t:.1f}s  (+{100 * (on_t - off_t) / off_t:.0f}%)")

    if blamed:
        print(f"  !! the FLAG changed something other than directions on {blamed}")
    if unstable:
        print(f"  {unstable} differ, but their two same-configuration runs differ "
              f"too — the page is not reproducible and the flag is not why")
    if not blamed and not unstable:
        print("  every export is identical outside its <direction> blocks")

    if args.out:
        args.out.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"  wrote {args.out}")
    return 1 if blamed else 0


if __name__ == "__main__":
    raise SystemExit(main())
