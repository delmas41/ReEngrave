#!/usr/bin/env python3
"""Does the recorded pad agree with what `recut_cells` DERIVES?

`annotate/recut_cells.choose_mode_and_cut` decides which pad a labeled batch
was cut with by cutting the page under each candidate mode and keeping the one
whose frames reproduce the manifest's recorded width / height / staff-line ys.
`MeasureCell.pad_above_staff_lines` now records the same fact directly. If the
two ever disagree, that is a far more interesting finding than the field: it
would mean one of them is not describing the crop that was taken.

⚠️ THIS PROBE DOES NOT REPLACE THE DERIVATION AND MUST NOT BE READ AS ARGUING
FOR IT. Every batch cut before the field existed has a manifest that records no
pad at all, so the derivation is the only thing that can read those; and the
derivation's abort-on-frame-mismatch is a safety property over irreplaceable
human verdicts. This measures agreement, nothing else.

Method, per (pdf, page) and per mode M in {pipeline, orchestral}:

  1. cut the page under M and write a manifest the way the real cutters do
     (`cell_canonical_w/h`, `staff_line_ys_canonical`) — deliberately WITHOUT
     any pad field, i.e. exactly what a legacy batch looks like;
  2. hand that manifest to `choose_mode_and_cut`, which derives a mode D;
  3. check D == M — the derivation works on this page at all;
  4. check every re-cut cell's RECORDED pad is consistent with D: each side is
     either D's default constant or the grown PAD_MAX_STAFF_LINES;
  5. check the record is not vacuously consistent — that at least one cell's
     recorded pad is INCONSISTENT with the mode that was not chosen. Without
     this, a page whose every cell grows to the ceiling would "agree" with
     both modes and prove nothing.

    python3 .../probe_pad_vs_derivation.py [--dpi 600]

Exits non-zero on disagreement, and on an empty or unresolvable input set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(REPO))

PAGES = [
    ("scan-beethoven5-litolff-p1",
     "library/editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 1),
    ("engraved-brahms1",
     "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf", 0),
]


def resolve(rel: str) -> Path:
    for root in (REPO, MAIN):
        p = root / rel
        if p.is_file():
            return p
    sys.exit(f"FATAL: input not found in {REPO} or {MAIN}: {rel}")


def manifest_of(cells) -> list[dict]:
    """A legacy manifest: the frame, and no word about the pad."""
    return [{
        "cell_id": f"c-sys{c.system_index}-s{c.staff_index}-m{c.measure_index}",
        "system_index": c.system_index,
        "staff_index": c.staff_index,
        "measure_index": c.measure_index,
        "cell_canonical_w": c.width,
        "cell_canonical_h": c.height,
        "staff_line_ys_canonical": list(
            getattr(c, "staff_line_ys_canonical_unlocalized", None)
            or c.staff_line_ys_canonical),
    } for c in cells]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    from tools.omr import measure_extractor as me
    from tools.omr.annotate import recut_cells as rc

    def pads_for(mode: str) -> tuple[float, float]:
        if mode == "orchestral":
            return float(rc.ORCH_PAD_STAFF_LINES), float(rc.ORCH_PAD_STAFF_LINES)
        return float(me.PAD_ABOVE_STAFF_LINES), float(me.PAD_BELOW_STAFF_LINES)

    ceiling = float(me.PAD_MAX_STAFF_LINES)
    problems: list[str] = []
    checked = 0

    for name, rel, page in PAGES:
        pdf = resolve(rel)
        for mode in rc.PADDING_MODES:
            print(f"\n=== {name} · cut as {mode} · {args.dpi}dpi ===", flush=True)
            cut = rc.cut_page(pdf, page, dpi=args.dpi, mode=mode)
            if not cut:
                sys.exit(f"FATAL: {name} produced no cells under {mode}")
            entries = manifest_of(cut)
            derived, found = rc.choose_mode_and_cut(
                pdf, page, entries, dpi=args.dpi,
                log=lambda s: print(s, flush=True))
            print(f"    derivation says: {derived}  (cut as {mode})")
            if derived != mode:
                problems.append(f"{name}/{mode}: derivation said {derived}")
                continue
            if not found.matched:
                sys.exit(f"FATAL: {name}/{mode}: derivation matched no cells")

            want = pads_for(derived)
            other = pads_for(
                "orchestral" if derived == "pipeline" else "pipeline")
            ok = lambda v, d: v in (d, ceiling)          # noqa: E731
            agree = disagrees_with_other = 0
            for _entry, cell in found.matched:
                a, b = cell.pad_above_staff_lines, cell.pad_below_staff_lines
                if a is None or b is None:
                    problems.append(f"{name}/{mode}: cell records no pad")
                    continue
                if ok(a, want[0]) and ok(b, want[1]):
                    agree += 1
                else:
                    problems.append(
                        f"{name}/{mode}: recorded ({a}, {b}) not consistent "
                        f"with derived {derived} {want}")
                if not (ok(a, other[0]) and ok(b, other[1])):
                    disagrees_with_other += 1
                checked += 1
            n = len(found.matched)
            print(f"    recorded pad consistent with the derived mode: "
                  f"{agree}/{n}")
            print(f"    ... and INCONSISTENT with the other mode: "
                  f"{disagrees_with_other}/{n}  (0 would mean the page cannot "
                  f"tell the modes apart)")
            if agree != n:
                problems.append(f"{name}/{mode}: only {agree}/{n} consistent")
            if disagrees_with_other == 0:
                problems.append(
                    f"{name}/{mode}: VACUOUS — every cell grew to the ceiling, "
                    f"so the record agrees with both modes")

    if not checked:
        sys.exit("FATAL: checked no cells — the probe measured nothing")
    print(f"\nchecked {checked} cells")
    if problems:
        print("DISAGREEMENT:")
        for p in problems:
            print("  " + p)
        return 1
    print("RESULT: PASS — the recorded pad agrees with the derivation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
