"""Rank a cut batch by the hollow-notehead score and keep the best N.

    python3 rank_and_trim.py <batch-dir> <keep-n> [--min-score 1]

Rewrites `cells.json` to the kept cells, deletes the PNGs of the rest, and
writes `HOLLOW_HINTS.txt` — the per-cell candidate count, which is what the
labeller should read the way the first round read SHORT_BAR_HINTS.txt.

The score and its validation live in `hollow_score.py`. Against the first
round's 48 cells, where Sean's verdicts say which 25 hold a hollow head:

    score >= 1   selects 22, of which 20 真   precision 91%   (base rate 52%)
    score >= 2   selects 14, of which 14 真   precision 100%
    top-20       18 positives                            90%
    top-25       21 positives                            84%

Cells are kept in score order but the file is written back in page order so
the labelling UI walks the batch sensibly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hollow_score import score_cell

REPO = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "transcription-overnight-progress-426c90")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir", type=Path)
    ap.add_argument("keep", type=int)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--max-score", type=int, default=6)
    ap.add_argument("--repo-root", type=Path, default=REPO)
    args = ap.parse_args()

    batch = args.batch_dir
    cells = json.loads((batch / "cells.json").read_text())
    scored = []
    for c in cells:
        n, _ = score_cell(c, args.repo_root)
        scored.append((n, c))

    # A BAND, not a top-N. The score's precision is validated only at the low
    # end: on the first round's cells the positives scored 1-3 and the
    # negatives 0. On a lighter, denser print the count inflates without
    # meaning more half notes — Dvorak's top cells score 9-47 and are runs of
    # beamed semiquavers, where the "counters" are the gaps between beams and
    # the loops of the word `cresc.`. Scheherazade's band-2-4 cells, by
    # contrast, are whole notes and nothing else. So take the band and sample
    # inside it rather than sorting to the top.
    import random
    eligible = [(n, c) for n, c in scored if args.min_score <= n <= args.max_score]
    rng = random.Random(20260902)
    kept = eligible if len(eligible) <= args.keep else rng.sample(eligible, args.keep)
    kept_ids = {c["cell_id"] for _, c in kept}

    # Delete the PNGs of everything not kept, so `cells/` matches the manifest.
    removed = 0
    for _, c in scored:
        if c["cell_id"] in kept_ids:
            continue
        for key in ("cell_png_path", "nostaff_png_path"):
            p = c.get(key)
            if p:
                fp = args.repo_root / p
                if fp.exists():
                    fp.unlink(); removed += 1

    out = []
    hints = []
    for n, c in sorted(kept, key=lambda t: (t[1]["source_tag"], t[1]["system_index"],
                                            t[1]["staff_index"], t[1]["measure_index"])):
        c = {**c, "hollow_candidates": n}
        out.append(c)
        hints.append(f"{c['cell_id']}: {n} counter-shaped hole(s)")
    (batch / "cells.json").write_text(json.dumps(out, indent=2))
    (batch / "HOLLOW_HINTS.txt").write_text(
        "How many notehead-counter-shaped enclosed white regions each cell holds.\n"
        "A hollow notehead is an ink ring around a white lens, so a cell with one\n"
        "or more is worth looking at. It is a place to look, NOT a claim: a bled\n"
        "`p`, the eye of an `8` and a slur crossing a stem all make holes too.\n"
        "Label what the cell shows.\n\n" + "\n".join(hints) + "\n")

    dist = {}
    for n, _ in scored:
        dist[n] = dist.get(n, 0) + 1
    print(f"{batch.name}: {len(cells)} candidates -> kept {len(out)} "
          f"(score band {args.min_score}-{args.max_score}); deleted {removed} PNGs")
    print(f"   score distribution over candidates: {dict(sorted(dist.items()))}")
    if out:
        ks = [c['hollow_candidates'] for c in out]
        print(f"   kept scores: min {min(ks)} max {max(ks)} mean {sum(ks)/len(ks):.2f}")


if __name__ == "__main__":
    main()
