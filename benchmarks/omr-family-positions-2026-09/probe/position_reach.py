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
import ast
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

#: family -> the GATHER-stage INK row its position is measured on.
#:
#: ⚠️⚠️ THIS IS WHAT MAKES A ZERO ATTRIBUTABLE, and without it the table cannot
#: tell the two zeros apart. A family with NO position rows is either *the
#: producer is silent* (a bug) or *this page holds none of that ink* (a fact
#: about the document), and those are opposite conclusions. Printing the SHAPE
#: row count beside the position count answers it on the same run, for free.
#:
#: ⚠️ It is NOT `export.FAMILIES`, which maps a family to its DECISION
#: quantity (`Q.PITCH`, `Q.ARC_KIND`, `Q.WEDGE_ANCHOR`). What a position is
#: measured on is the ink row, one stage earlier.
INK_OF = {
    "rest": Q.REST,
    "slur": Q.ARC_BOX, "tie": Q.ARC_BOX,
    "articulation": Q.ARTICULATION_MARK,
    "fermata": Q.FERMATA_MARK,
    "ornament": Q.ORNAMENT_MARK,
    "tuplet": Q.TUPLET_MARKER,
    "time": Q.METER_GLYPH,
    "dynamic": Q.DYNAMIC_LETTER,
    "wedge": Q.WEDGE_BOX,
    "direction": Q.DIRECTION_WORD,
    # the three that already had a position, for the control
    "note": Q.GLYPH_BOX, "clef": Q.CLEF_GLYPH, "key": Q.KEYSIG_MARKER,
}


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
             _detail_key(detail))] += 1
    return out


def _detail_key(detail) -> str:
    """A canonical spelling of a detail dict, container order normalised.

    A control that compares RECORDS should compare them by a canonical
    spelling rather than by `repr`, because `repr` of an unordered container
    can differ for identical content. That is why this exists.

    ⚠️⚠️ **IT IS NOT THE EXPLANATION FOR THE 23-ROW CONTROL FAILURE ON LITOLFF
    p1-4, AND AN EARLIER VERSION OF THIS DOCSTRING SAID IT WAS.** That claim
    was written after canonicalising made the SINGLE-PAGE p4 arm pass, and
    before the four-page arm was re-run — **a mechanism asserted without being
    measured**, the fault CLAUDE.md names. Re-run, p1-4 fails identically with
    this canonical key in place.

    **The cause is the PIPELINE's own run-to-run non-determinism in the
    direction reader**, established by running `--off-vs-off` TWICE: the
    second run reproduces the same 23 `direction_word` rows with the flag OFF
    in both arms. See FINDINGS §6a — including that the FIRST `--off-vs-off`
    run passed, and that one green attribution arm nearly bought a false
    accusation against this flag.
    """
    def norm(v):
        if isinstance(v, (set, frozenset)):
            return ("set", sorted(map(repr, v)))
        if isinstance(v, (list, tuple)):
            return ("seq", [norm(x) for x in v])
        if isinstance(v, dict):
            return ("map", sorted((str(k), norm(x)) for k, x in v.items()))
        return ("val", repr(v))
    return repr(sorted(((str(k), norm(v)) for k, v in detail.items()),
                       key=lambda kv: kv[0]))


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
    ap.add_argument("--off-vs-off", action="store_true", help=(
        "run BOTH arms with the flag OFF. ⚠️⚠️ THE ATTRIBUTION ARM: if the "
        "comparison still fails, the difference is the PIPELINE's own "
        "non-determinism between two gathers and not this flag's. Run it "
        "before believing — or reporting — any control failure. "
        "⚠️⚠️ AND RUN IT TWICE: this arm PASSED on its first run over "
        "Litolff p1-4 and FAILED on its second over the same pages, with the "
        "flag off in both. One green attribution arm is not evidence of "
        "determinism — it is one pair that happened to agree."))
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

    # ⚠️ THE SECOND ARM'S FLAG IS SET EXPLICITLY IN BOTH MODES. Under
    # `--off-vs-off` it is set to "0" rather than left alone: an arm that
    # expresses itself by NOT setting the variable is the hazard CLAUDE.md
    # records costing ten red tests, and here it would silently make the
    # attribution arm identical to the ordinary one.
    os.environ[POS.POSITIONS_ENV] = "0" if a.off_vs_off else "1"
    assert POS.positions_enabled() != a.off_vs_off, \
        "the second arm did not express itself"
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

    ink = collections.Counter()
    for row in log_on.all_rows():
        if isinstance(row, Observation):
            ink[row.quantity] += 1

    families = {}
    for q in POSITION_QUANTITIES:
        key = q.lower()
        for fam in _families_of(q):
            families[fam] = {"quantity": key,
                             "observed": obs.get(key, 0),
                             "abstained": abst.get(key, 0),
                             "ink_quantity": INK_OF.get(fam),
                             "ink_rows": ink.get(INK_OF.get(fam, ""), 0)}

    print(f"pages {pages}  dpi {a.dpi}  weights "
          f"{pathlib.Path(a.weights).name if a.weights else 'NONE'}  "
          f"surya {'on' if surya else 'off'}")
    print(f"prepare {t_prep:6.1f}s   gather OFF {t_off:6.1f}s   "
          f"gather ON {t_on:6.1f}s   position cost "
          f"{t_on - t_off:+.1f}s ({100.0 * (t_on - t_off) / max(t_off, 1e-9):+.1f}%)")
    print()
    print(f"{'family':14s} {'quantity':26s} {'rows':>6s} {'abstain':>8s} "
          f"{'ink':>6s}  attribution")
    print("-" * 86)
    total = 0
    for fam in sorted(families):
        r = families[fam]
        total += r["observed"]
        # ⚠️ THE TWO ZEROS, TOLD APART ON THE SAME RUN. See `INK_OF`.
        if r["observed"] or r["abstained"]:
            why = ""
        elif r["ink_rows"] == 0:
            why = "no such ink on this page"
        else:
            why = f"⚠️ {r['ink_rows']} ink rows and NO position"
        print(f"{fam:14s} {r['quantity']:26s} {r['observed']:6d} "
              f"{r['abstained']:8d} {r['ink_rows']:6d}  {why}")
    basis = abst.get(Q.CELL_POSITION_BASIS, 0)
    print(f"{'(no grid)':14s} {Q.CELL_POSITION_BASIS:26s} {'-':>6s} "
          f"{basis:8d}")
    print()

    zero = [f for f, r in families.items() if r["observed"] == 0]
    starved = [f for f in zero if families[f]["ink_rows"] > 0]
    if zero:
        print(f"⚠️ ZERO ROWS on {len(zero)} of {len(families)} families: "
              f"{', '.join(sorted(zero))}")
        print("   Of those, this page holds NO ink for "
              f"{len(zero) - len(starved)} — a fact about the document.")
        if starved:
            print(f"   ⚠️⚠️ AND {len(starved)} HAVE INK AND NO POSITION, which "
                  f"is a fault in the producer: {', '.join(sorted(starved))}")
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

    if a.off_vs_off:
        print()
        print("── ATTRIBUTION ARM: BOTH arms ran with the flag OFF ──")
        if missing or surplus_q:
            print(f"  ⚠️⚠️ {len(missing)} rows DIFFER between two gathers of "
                  f"the same pages with the flag OFF in BOTH.")
            print(f"     surplus by quantity: {dict(surplus_q)}")
            print("     So a difference of this size and in these quantities "
                  "is the PIPELINE's own non-determinism, NOT this flag's.")
            for k in list(missing)[:10]:
                print(f"     {k[0]} {k[1]}")
            return 0
        print("  ✅ two flag-OFF gathers are identical, so a failure in the "
              "ordinary arm WOULD be attributable to the flag.")
        return 0

    if not ok:
        print("\n⚠️⚠️ CONTROL FAILED — flag-off is NOT byte-identical.")
        print("   ⚠️ DO NOT ATTRIBUTE THIS TO THE FLAG WITHOUT RUNNING "
              "`--off-vs-off` FIRST: two gathers of the same pages are not "
              "guaranteed identical, and a reader that differs between runs "
              "produces exactly this.")
        # ⚠️ NAME THE FIELD, NOT JUST THE ROW. A control that reports *these
        # rows changed* sends the next reader on three diagnostic runs to find
        # out HOW, which is what happened here. Pair each changed OFF
        # signature with the ON signature at the same (quantity, subject,
        # kind) and print the first field that differs.
        on_by_addr = collections.defaultdict(list)
        for k in on:
            on_by_addr[k[:3]].append(k)
        for k in list(missing)[:10]:
            print(f"   {k[0]} {k[1]}")
            for cand in on_by_addr.get(k[:3], ()):
                if cand == k:
                    continue
                if cand[3] != k[3]:
                    print(f"      value: OFF={k[3]}  ON={cand[3]}")
                else:
                    # ⚠️ NAME THE KEY, DO NOT PRINT A PREFIX. A truncated
                    # dump of two long detail strings shows only where the
                    # TRUNCATION fell — this printed "first divergence at
                    # char 160" three times running, which is the cut, not
                    # the field. Parse both back and diff by key.
                    a_d = dict(ast.literal_eval(k[4]))
                    b_d = dict(ast.literal_eval(cand[4]))
                    for key in sorted(set(a_d) | set(b_d)):
                        if a_d.get(key) != b_d.get(key):
                            print(f"      detail `{key}`: "
                                  f"OFF={a_d.get(key)!r}  ON={b_d.get(key)!r}")
                break
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
