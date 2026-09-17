#!/usr/bin/env python3
"""REACH, per family, for the ten position quantities — and the flag-off control.

    python3 benchmarks/omr-family-positions-2026-09/probe/position_reach.py \
        library/editions/.../imslp984073.pdf --pages 1 \
        --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
        --out benchmarks/omr-family-positions-2026-09/out/reach-p1.json

⚠️⚠️ **REACH FIRST, AND THIS PROBE EXITS NON-ZERO DECLARING ITSELF DEAD AT
ZERO.** A change that moves nothing because it is INERT and one that moves
nothing because the page holds nothing to move are the same number, and this
repo has already paid for that twice — the dotted-rest arm printed a clean zero
that was about a document holding twenty `aug_dot` rows, and the wedge arm was
run on a document with no hairpins at all. So the first thing printed is how
many rows each family produced, the exit code is non-zero if that is zero
everywhere, and a family at zero is a FINDING reported by name rather than a
gap in a table.

## THE CONTROL IS STRONGER THAN A FILE DIFF, AND IT CAN FAIL

Both arms run over the SAME prepared pages with the SAME detector object in
ONE process, so the detector jitter this repo documents (0.83 -> 0.69 on one
hairpin box across runs on byte-identical code) cannot enter. The control is
then an exact one:

    every row the OFF arm produced is in the ON arm, unchanged, and the
    ON arm's surplus is EXACTLY the position rows

That is byte-identity stated over the record rather than over a file, and it
would go red on any accidental perturbation of an existing row — which a
whole-file md5 would also catch, but this also says WHICH row.

⚠️ **THE POSITIVE CONTROL: `--prove-the-control-can-fail`** deliberately
perturbs one existing row in the ON arm and asserts the comparison goes RED.
Without it, an arm that compared a log with itself would pass identically.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import gather as G                       # noqa: E402
from tools.omr.staged import pipeline as P                     # noqa: E402
from tools.omr.staged import positions as POS                  # noqa: E402
from tools.omr.staged.record import Observation, Q             # noqa: E402

#: quantity -> the family it measures the ink of. ⚠️ IMPORTED FROM `capture`,
#: never restated: that table is what `capture --check` grades against, and a
#: second copy here would let this probe report a family the tool does not.
from tools.omr.staged.capture import (                         # noqa: E402
    STAFF_GRID_POSITION, UNSCORED, _families_of, _is_position)

POSITION_QUANTITIES = sorted(q for q in UNSCORED if _is_position(q))


def _rows_by_signature(log):
    """Every row as (quantity, subject, kind, value, sorted detail) -> count.

    ⚠️ ROW IDS ARE EXCLUDED ON PURPOSE. `Log._next_id` is a running counter,
    so inserting ten thousand position rows renumbers nothing that came before
    them but WOULD change ids if the position rows were interleaved. Comparing
    on CONTENT asks the question that matters — did an existing row change —
    and is not answered by a counter.
    """
    out = collections.Counter()
    for row in log.all_rows():
        kind = type(row).__name__
        value = getattr(row, "value", None)
        detail = getattr(row, "detail", {}) or {}
        out[(row.quantity, row.subject.to_key(), kind, repr(value),
             repr(sorted(detail.items(), key=lambda kv: kv[0])))] += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="1")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--no-surya", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--prove-the-control-can-fail", action="store_true")
    a = ap.parse_args()

    pages = []
    for part in a.pages.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            pages.extend(range(int(lo), int(hi) + 1))
        else:
            pages.append(int(part))

    det = None
    if a.weights:
        from tools.omr.yolo_detector import YoloDetector
        det = YoloDetector(a.weights)

    t0 = time.time()
    prepared = P.prepare_pages(a.pdf, pages, dpi=a.dpi)
    t_prep = time.time() - t0

    surya = not a.no_surya
    kw = dict(detector=det, imgsz=a.imgsz, pdf_path=a.pdf,
              surya_fallback=surya, ocr_fallback=surya)

    os.environ[POS.POSITIONS_ENV] = "0"
    assert not POS.positions_enabled(), "the OFF arm did not express itself"
    t0 = time.time()
    log_off = G.gather(prepared, **kw)
    t_off = time.time() - t0

    os.environ[POS.POSITIONS_ENV] = "1"
    assert POS.positions_enabled(), "the ON arm did not express itself"
    t0 = time.time()
    log_on = G.gather(prepared, **kw)
    t_on = time.time() - t0

    off = _rows_by_signature(log_off)
    on = _rows_by_signature(log_on)
    if a.prove_the_control_can_fail:
        # ⚠️ PERTURB AN EXISTING ROW, not a position row: the control's claim
        # is that nothing ALREADY ON THE RECORD moved, so the mutant has to be
        # an already-present row or it tests nothing.
        victim = next(k for k in off if k[0] == Q.GLYPH_BOX)
        on = collections.Counter(on)
        on[victim] -= 1
        on[victim + ("PERTURBED",)] = 1

    missing = {k: c for k, c in off.items() if on.get(k, 0) != c}
    surplus_q = collections.Counter()
    for k, c in on.items():
        if off.get(k, 0) != c:
            surplus_q[k[0]] += c - off.get(k, 0)
    off_only_position = [q for q in POSITION_QUANTITIES
                         if any(k[0] == q for k in off)]

    # ── REACH, PER FAMILY, FIRST ────────────────────────────────────────────
    obs = collections.Counter()
    abst = collections.Counter()
    for row in log_on.all_rows():
        if row.quantity.upper() not in POSITION_QUANTITIES \
                and row.quantity != Q.CELL_POSITION_BASIS:
            continue
        (obs if isinstance(row, Observation) else abst)[row.quantity] += 1

    families = {}
    for q in POSITION_QUANTITIES:
        key = q.lower()
        for fam in _families_of(q):
            families[fam] = {"quantity": key,
                             "observed": obs.get(key, 0),
                             "abstained": abst.get(key, 0)}

    print(f"pages {pages}  dpi {a.dpi}  weights "
          f"{pathlib.Path(a.weights).name if a.weights else 'NONE'}  "
          f"surya {'on' if surya else 'off'}")
    print(f"prepare {t_prep:6.1f}s   gather OFF {t_off:6.1f}s   "
          f"gather ON {t_on:6.1f}s   position cost "
          f"{t_on - t_off:+.1f}s ({100.0 * (t_on - t_off) / max(t_off, 1e-9):+.1f}%)")
    print()
    print(f"{'family':14s} {'quantity':26s} {'rows':>6s} {'abstain':>8s}")
    print("-" * 58)
    total = 0
    for fam in sorted(families):
        r = families[fam]
        total += r["observed"]
        print(f"{fam:14s} {r['quantity']:26s} {r['observed']:6d} "
              f"{r['abstained']:8d}")
    basis = abst.get(Q.CELL_POSITION_BASIS, 0)
    print(f"{'(no grid)':14s} {Q.CELL_POSITION_BASIS:26s} {'-':>6s} "
          f"{basis:8d}")
    print()

    zero = [f for f, r in families.items() if r["observed"] == 0]
    if zero:
        print(f"⚠️ ZERO ROWS on {len(zero)} of {len(families)} families: "
              f"{', '.join(sorted(zero))}")
        print("   A family at zero is a FINDING about this document's ink, "
              "not a gap in this table.")
        print()

    # ── THE CONTROL ─────────────────────────────────────────────────────────
    print("── CONTROL: flag-off is byte-identical over the record ──")
    print(f"  rows in the OFF arm                  {sum(off.values()):7d}")
    print(f"  OFF rows CHANGED or MISSING in ON    {len(missing):7d}"
          f"   (must be 0)")
    print(f"  ON arm surplus, by quantity          "
          f"{dict(surplus_q) if surplus_q else '{}'}")
    print(f"  position quantities in the OFF arm   "
          f"{off_only_position}   (must be [])")

    surplus_is_only_positions = all(
        q.upper() in POSITION_QUANTITIES or q == Q.CELL_POSITION_BASIS
        or q == "PERTURBED"
        for q in surplus_q)
    ok = (not missing) and surplus_is_only_positions and not off_only_position

    if a.prove_the_control_can_fail:
        print()
        if ok:
            print("⚠️⚠️ POSITIVE CONTROL FAILED: the comparison passed with a "
                  "row deliberately perturbed. It cannot fail, so a green "
                  "result from it means nothing.")
            return 3
        print("✅ POSITIVE CONTROL: the comparison went RED on a perturbed "
              "row, so a green result from it is worth something.")
        return 0

    if not ok:
        print("\n⚠️⚠️ CONTROL FAILED — flag-off is NOT byte-identical.")
        for k in list(missing)[:10]:
            print(f"   {k[0]} {k[1]}")
        return 2

    print("\n✅ CONTROL: every OFF row is unchanged in ON, and the whole "
          "surplus is position rows.")

    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps({
            "pdf": a.pdf, "pages": pages, "dpi": a.dpi,
            "weights": a.weights, "surya": surya,
            "seconds": {"prepare": t_prep, "gather_off": t_off,
                        "gather_on": t_on},
            "families": families,
            "cell_position_basis_abstentions": basis,
            "rows_off": sum(off.values()), "rows_on": sum(on.values()),
            "control_ok": ok,
        }, indent=2, sort_keys=True))
        print(f"   wrote {a.out}")

    if total == 0:
        print("\n⚠️⚠️ DEAD: ZERO position rows on this document. This probe "
              "measured nothing and its control proves only that nothing "
              "changed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
