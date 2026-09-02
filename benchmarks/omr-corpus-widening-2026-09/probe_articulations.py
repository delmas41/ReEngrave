"""Would an x-aligned, side-aware rule put each articulation on the right note?

`export.py` contains the string "articulation" once, in a docstring. The
detector meanwhile fires `artic*` freely — 102 staccati on Mozart 40 alone,
charged back as exactly 102 `insarticulation` edits. Before writing an
attachment rule, this measures whether the obvious one is good enough, and in
the unit the dot fix insisted on: STAFF SPACES and notehead widths, never the
mark's own bounding box.

THE RULE UNDER TEST. A staccato or accent is printed directly above or below
the notehead it belongs to, and the DSv2 class says which side (`...Above` /
`...Below`). So: take the notehead whose x-centre is nearest the mark's, on the
correct side, within `--max-dx` notehead widths.

Scored by index against the truth: within one (part, measure) both sides are in
reading order, the fixture is engraved from its own truth, so the n-th predicted
notehead is the n-th truth note. A mark that lands on note k is correct when
truth note k carries an articulation.

    python3 benchmarks/omr-corpus-widening-2026-09/probe_articulations.py
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

from music21 import converter

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "benchmarks" / "omr-corpus-widening-2026-09" / "fixtures"
CANON = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"


def truth_marks(path: pathlib.Path) -> dict:
    """(part ordinal, measure ordinal) -> {note index: n_articulations}."""
    score = converter.parse(str(path))
    out: dict = {}
    for pi, part in enumerate(score.parts):
        for mi, m in enumerate(part.getElementsByClass("Measure")):
            per: dict[int, int] = {}
            for ni, n in enumerate(m.recurse().notes):
                if n.articulations:
                    per[ni] = len(n.articulations)
            out[(pi, mi)] = per
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-dx", type=float, default=0.75,
                    help="x tolerance in NOTEHEAD WIDTHS")
    ap.add_argument("--works", nargs="+", default=None)
    args = ap.parse_args()

    works = args.works or [p.stem[:-4] for base in (CANON, FIX)
                           for p in sorted(base.glob("*.omr.json"))]
    tot = collections.Counter()
    print(f"{'work':26s} {'marks':>6s} {'placed':>7s} {'onArtic':>8s} "
          f"{'truthMarks':>11s}  precision")
    for w in works:
        base = FIX if (FIX / f"{w}.omr.json").is_file() else CANON
        omr, truth = base / f"{w}.omr.json", base / f"{w}.musicxml"
        if not (omr.is_file() and truth.is_file()):
            continue
        tm = truth_marks(truth)
        j = json.loads(omr.read_text())
        n_marks = placed = correct = 0
        staff_ord = 0
        for pg in j["pages"]:
            for s in pg["systems"]:
                for st in s["staves"]:
                    for mi, m in enumerate(st["measures"]):
                        nh = [d for d in m["detections"]
                              if d["category"] == "notehead"]
                        nh.sort(key=lambda d: d["bbox_page"][0])
                        marks = [d for d in m["detections"]
                                 if d["class"].startswith("artic")]
                        if not nh:
                            n_marks += len(marks)
                            continue
                        widths = [d["bbox_page"][2] for d in nh]
                        nw = sorted(widths)[len(widths) // 2] or 1
                        for a in marks:
                            n_marks += 1
                            ax, ay, aw, ah = a["bbox_page"]
                            acx, acy = ax + aw / 2.0, ay + ah / 2.0
                            above = a["class"].endswith("Above")
                            best = None
                            for idx, d in enumerate(nh):
                                nx, ny, nwd, nht = d["bbox_page"]
                                ncx, ncy = nx + nwd / 2.0, ny + nht / 2.0
                                if above and acy >= ncy:
                                    continue
                                if not above and acy <= ncy:
                                    continue
                                dx = abs(acx - ncx) / nw
                                if dx > args.max_dx:
                                    continue
                                if best is None or dx < best[0]:
                                    best = (dx, idx)
                            if best is None:
                                continue
                            placed += 1
                            if best[1] in tm.get((staff_ord, mi), {}):
                                correct += 1
                    staff_ord += 1
        t = sum(len(v) for v in tm.values())
        if n_marks or t:
            print(f"{w:26s} {n_marks:>6d} {placed:>7d} {correct:>8d} "
                  f"{t:>11d}  "
                  f"{(correct / placed if placed else 0):.3f}")
        tot["marks"] += n_marks; tot["placed"] += placed
        tot["correct"] += correct; tot["truth"] += t
    print(f"\nTOTAL marks={tot['marks']} placed={tot['placed']} "
          f"landing-on-an-articulated-note={tot['correct']} "
          f"truth-articulated-notes={tot['truth']}")
    if tot["placed"]:
        print(f"precision {tot['correct'] / tot['placed']:.3f}   "
              f"placement rate {tot['placed'] / max(1, tot['marks']):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
