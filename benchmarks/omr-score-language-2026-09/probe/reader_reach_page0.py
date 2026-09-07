#!/usr/bin/env python3
"""Can the PRODUCTION reader ladder reach the language evidence on page 0?

The whole signal rests on a document printing its roster in full somewhere, and
in an orchestral score that somewhere is the first page of a movement. So the
question that decides whether this is buildable is not "is the language
determinable" — `measure_reach.py` answers that — but **"does the pipeline's
own label reader see the words".**

⚠️ It is a real question and not a formality, because the answer differs by
RUNG. On Beethoven 6 / Litolff page 0 — the document carrying the fault this
work is about — the text-layer rung returns **zero labels** while the page's
text layer plainly holds `Oboi. / Clarinetti inB / Fagotti. / Corni in F. /
Violino J. / Violino II. / Viola. / Violoncello e Basso.`: a movement-head page
indents its first system and carries a title block, and `detect_staves` finds
15 staves where the music has twelve. `_read_labels_for_page` escalates to
Surya exactly when the text layer comes back thin, and Surya reads it.

    OMR_SURYA_KEEP_ALIVE=0 python3 \\
        benchmarks/omr-score-language-2026-09/probe/reader_reach_page0.py

⚠️ Needs `.venv-surya` (symlink it into a worktree — CLAUDE.md's second
symlink). NEVER `pkill -f llama-server`: the resident server is shared, and
`OMR_SURYA_KEEP_ALIVE=0` is what makes this run own its own worker.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr import score_language as L                      # noqa: E402
from tools.omr import staff_labels_surya as surya              # noqa: E402
from tools.omr.preprocessing import render_page                # noqa: E402
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr.staff_labels import read_staff_labels           # noqa: E402

#: ⚠️ Resolved against the MAIN checkout, not `ROOT`. The legacy
#: `tools/omr/training/data/imslp/...` paths are symlinks into the central score
#: library that `tools.library.ingest relink` creates, and a fresh git worktree
#: has none of them — the same shape as the four venv/weights symlinks CLAUDE.md
#: records. `library_root()` resolves to the main checkout for exactly this
#: reason, so one machine keeps one store.
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
DEFAULT_PDF = (MAIN / "tools/omr/training/data/imslp/beethoven-symphony-6"
                    / "pdfs/imslp-504082/score.pdf")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    page = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(page)
    print(f"{args.pdf.name} p{args.page}: {len(pws.staves)} staves detected\n")

    rungs: dict[str, list[str]] = {
        "text layer": [lab.text for lab in read_staff_labels(pws)]}
    if surya.available():
        t0 = time.time()
        rungs["surya"] = [lab.text
                          for lab in surya.read_staff_labels_surya(pws)]
        print(f"(surya: {time.time() - t0:.1f} s)\n")
    else:
        print("⚠️ surya unavailable — symlink .venv-surya; the text-layer row "
              "alone cannot answer this question\n")

    rows = {}
    for rung, labels in rungs.items():
        reading = L.detect(labels)
        votes = {k: v for k, v in reading.votes.items() if v}
        print(f"{rung:12s} {len(labels):3d} labels -> "
              f"{reading.language or 'ABSTAINS':8s} "
              f"share {reading.share:.2f}  votes {votes}")
        print(f"             {labels}")
        rows[rung] = {"labels": labels, "language": reading.language,
                      "diagnostic_votes": reading.n_diagnostic,
                      "share": round(reading.share, 4),
                      "votes": reading.votes}

    reached = [r for r, v in rows.items() if v["language"]]
    print(f"\nlanguage reachable by the production ladder: "
          f"{'YES via ' + ', '.join(reached) if reached else 'NO'}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"pdf": str(args.pdf), "page": args.page, "dpi": args.dpi,
             "staves": len(pws.staves), "rungs": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
