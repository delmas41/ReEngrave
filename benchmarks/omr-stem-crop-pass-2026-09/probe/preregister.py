"""DRAW THE SAMPLE, BEFORE LOOKING AT ONE PIXEL OF PRINT.

⚠️⚠️ COMMIT ORDER IS THE CLAIM. A hand-adjudicated rate is only evidence if
the rows were chosen before the answers were seen; otherwise the sample fits
itself to what was found, which is the failure `CATEGORIES.md` was committed
alone and first to prevent. The precedent is
`omr-prefill-admission-2026-09/PHASE_C_CELLS.json` -- cells and their status
recorded BEFORE labeling. So this script writes the sample and its provenance
and is committed in its own commit; the crops come after.

STRATIFICATION is by the rejection census's own six buckets, PER PUBLISHER,
because CLAUDE.md's own reading of that census is that its top cause INVERTS
between the two plates. Pooling would hide exactly the thing under test.

⚠️ `too WIDE` is deliberately OVERSAMPLED. It is the largest single filter
cost and the one thing this pass can settle that nothing else can: the width
cap's recoveries are estimated at 83.6% real by convention-vs-convention and
explicitly NOT trusted. Measured off the row files, `width_cap_recovered` is
211 of 237 WIDE heads on Litolff and 341 of 358 on Breitkopf -- so the WIDE
stratum IS very nearly the width-cap population, and a rate taken on it is
the number the decision wants.

⚠️ A POSITIVE CONTROL is drawn in the same act, from the DISJOINT population
of heads whose stem the record DECIDED. It is read blind and first. Its
purpose is to price the eye, not the pipeline: an eye that cannot recover a
direction the pipeline already read cannot be trusted to report an absence.

SEED is fixed and printed. Rows are sorted by subject before sampling so the
draw does not depend on record iteration order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

SEED = 20260918

BUCKETS = [
    "too WIDE (w > 0.6 spaces)",
    "too SHORT (h < 2.0 spaces)",
    "NO component overlaps the head at all",
    "a component WAS accepted (pair rule dropped it)",
    "at a CELL EDGE (0.8 spaces)",
    "too TALL (h > 8.0 spaces)",
]
# n per bucket per publisher. WIDE is oversampled; see the docstring.
TARGET = {
    "too WIDE (w > 0.6 spaces)": 30,
    "too SHORT (h < 2.0 spaces)": 12,
    "NO component overlaps the head at all": 12,
    "a component WAS accepted (pair rule dropped it)": 12,
    "at a CELL EDGE (0.8 spaces)": 12,
    "too TALL (h > 8.0 spaces)": 12,
}
CONTROL_N = 16   # per publisher, from the DECIDED population


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", required=True,
                    help="census_rows.py outputs, one per publisher")
    ap.add_argument("--decided", nargs="+", required=True,
                    help="decided_rows.py outputs, same order")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if len(a.rows) != len(a.decided):
        print("one --decided per --rows", file=sys.stderr)
        return 2

    print(f"SEED {SEED}")
    doc_out, total = [], 0
    for rp, dp in zip(a.rows, a.decided):
        rows_f, dec_f = Path(rp), Path(dp)
        rows_d = json.loads(rows_f.read_text())
        dec_d = json.loads(dec_f.read_text())
        label = rows_d["label"]
        rows = [r for r in rows_d["rows"] if r.get("bbox_page_px")]
        print(f"\n== {label}")
        print(f"   population {len(rows)} stemless heads with a page box "
              f"(of {rows_d['no_stem']}), {dec_d['decided']} decided")
        # ⚠️ one RNG per publisher, seeded by the shared SEED plus the label,
        # so adding a publisher cannot change another's draw.
        rng = random.Random(f"{SEED}:{label}")
        strata = {}
        for b in BUCKETS:
            pool = sorted((r for r in rows if r["bucket"] == b),
                          key=lambda r: r["subject"])
            want = min(TARGET[b], len(pool))
            pick = rng.sample(pool, want) if want else []
            n_rec = sum(1 for r in pick if r["width_cap_recovered"])
            strata[b] = {
                "population": len(pool),
                "width_cap_recovered_in_population":
                    sum(1 for r in pool if r["width_cap_recovered"]),
                "n_drawn": want,
                "width_cap_recovered_in_sample": n_rec,
                "subjects": sorted(r["subject"] for r in pick),
            }
            total += want
            print(f"   {b:<50} pop {len(pool):>5}  draw {want:>3}"
                  f"  (width-cap {n_rec:>3})")
        cpool = sorted(dec_d["rows"], key=lambda r: r["subject"])
        cpick = rng.sample(cpool, min(CONTROL_N, len(cpool)))
        print(f"   {'POSITIVE CONTROL (decided heads)':<50} "
              f"pop {len(cpool):>5}  draw {len(cpick):>3}")
        doc_out.append({
            "label": label,
            "rows_file": str(rows_f), "rows_md5": md5(rows_f),
            "decided_file": str(dec_f), "decided_md5": md5(dec_f),
            "pdf": rows_d["pdf"], "pages": rows_d["pages"],
            "strata": strata,
            "positive_control": {
                "population": len(cpool),
                "n_drawn": len(cpick),
                # ⚠️ the READ direction is recorded so a later reader can
                # check the blind pass was scored against it and not fitted
                # to it -- the adjudication file must be committed FIRST.
                "subjects": sorted(
                    [r["subject"], r["read_direction"]] for r in cpick),
            },
        })

    payload = {
        "what": "pre-registered stratified sample for the stem crop pass",
        "seed": SEED,
        "targets": TARGET,
        "control_n": CONTROL_N,
        "verdict_vocabulary": {
            "stem_printed_up": "a stroke is printed, attached, running UP",
            "stem_printed_down": "a stroke is printed, attached, running DOWN",
            "no_stem_printed": "the head carries no stroke (e.g. a whole "
                               "note) -- the pipeline's abstention is RIGHT",
            "not_a_notehead": "the box does not hold a notehead at all",
            "cannot_tell": "the print does not settle it; NEVER to be "
                           "converted into a definite answer",
        },
        "publishers": doc_out,
        "total_drawn": total,
    }
    Path(a.out).write_text(json.dumps(payload, indent=1))
    print(f"\ntotal stemless heads drawn: {total}")
    print(f"wrote {a.out}")
    return 0 if total else 2


if __name__ == "__main__":
    raise SystemExit(main())
