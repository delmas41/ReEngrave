"""THE DECIDING ARM: `detect_stems(..., drop_accidental_pairs=False)`.

`_drop_paired_strokes` rejects two vertical strokes whose centres are within
0.9 staff spaces and which overlap vertically by 0.6 of the shorter, and
**drops BOTH**. Its premise is that *"successive notes are set further apart
than an accidental's own strokes"* -- a claim about how tightly a plate sets
notes, measured on 14 hand-counted cells. `probe_pair_rule.py` found the
missing stems standing beside a close vertical partner at 94.6% / 79.8%
against 80.7% / 15.7% for the stems we read. This runs the rule itself.

⚠️ IT RE-CUTS THE CELLS, so the FIRST thing it does is prove the re-cut is
faithful: with the flag at its shipped value the stems it finds must
reproduce the `Q.STEM` rows already on the record. **A re-cut that does not
reproduce the record is not an arm, it is a different document**, and the
probe exits non-zero rather than reporting a delta from it.

⚠️ IT SCORES BOTH DIRECTIONS. The rule exists for a reason its own docstring
records -- summed |error| 60 -> 24 over 14 hand-counted cells -- so turning it
off BUYS stems and PAYS in false ones. The cost is measured against the
record's own `accidental*` detections: a new stroke standing on an accidental
is what the rule was written to remove.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parents[1] / "benchmarks"
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="e.g. 1,2,3,4")
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.line_detection import detect_stems

    # ── the record: noteheads, accidentals, stems, and the stem verdicts ──
    heads: dict[str, tuple] = {}
    accid: dict[str, list] = collections.defaultdict(list)
    rec_stems: dict[str, list] = collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "glyph_box":
            v = o.get("value")
            if not (isinstance(v, list) and len(v) == 5):
                continue
            name = str(v[0])
            box = (float(v[1]), float(v[2]), float(v[3]), float(v[4]))
            if name.startswith("notehead"):
                heads[o["subject"]] = box
            elif name.startswith("accidental") or name.startswith("key"):
                p = o["subject"].split("/")
                accid["cell/" + "/".join(p[1:5])].append(box)
        elif q == "stem":
            v = o["value"]
            rec_stems[o["subject"]].append((float(v[0]), float(v[1]),
                                            float(v[2]), float(v[3])))
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    print(f"{a.label}: record holds {len(heads)} noteheads, "
          f"{sum(len(v) for v in rec_stems.values())} stem rows in "
          f"{len(rec_stems)} cells, {sum(len(v) for v in accid.values())} "
          f"accidental boxes")

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = prepare_pages(a.pdf, pages, dpi=600)
    print(f"re-cut {len(prepared)} pages in {time.time() - t0:.0f}s")

    # ── map re-cut cells onto the record's cell keys ──────────────────────
    #  The record numbers a staff by (system, staff-within-system); a re-cut
    #  cell knows only its page-wide `staff_index`. `prepare_pages` returns
    #  the page's staves in reading order, so the mapping is the grouping the
    #  pipeline itself makes -- rebuilt here the same way.
    from tools.omr.staged.gather import _system_local  # type: ignore
    on: dict[str, list] = {}
    off: dict[str, list] = {}
    for (pws, cells), pg in zip(prepared, pages):
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            for tag, store, flag in (("on", on, True), ("off", off, False)):
                got = detect_stems(c, drop_accidental_pairs=flag)
                store[ck] = [(float(d.x_canonical), float(d.y_canonical),
                              float(d.width_canonical),
                              float(d.height_canonical)) for d in got]
    print(f"cells re-cut and read: {len(on)}")

    # ── CONTROL: does the shipped arm reproduce the record? ───────────────
    shared = set(on) & set(rec_stems)
    same = sum(1 for k in shared
               if sorted(on[k]) == sorted(rec_stems[k]))
    n_on = sum(len(v) for v in on.values())
    n_rec = sum(len(v) for v in rec_stems.values())
    print(f"\n== CONTROL: the shipped flag against the record")
    print(f"   cells in both: {len(shared)}   identical stem sets: {same} "
          f"({same / max(1, len(shared)):.1%})")
    print(f"   stems: re-cut {n_on}, record {n_rec}")
    out = {"label": a.label, "control": {
        "cells_shared": len(shared), "cells_identical": same,
        "stems_recut": n_on, "stems_record": n_rec}}
    if not shared or same / len(shared) < 0.90:
        print("\nDEAD: the re-cut does not reproduce the record, so a delta "
              "from it would not be this flag's.", file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2

    # ── the ARM ───────────────────────────────────────────────────────────
    n_off = sum(len(v) for v in off.values())
    print(f"\n== ARM: drop_accidental_pairs=False")
    print(f"   stems {n_on} -> {n_off}  ({n_off - n_on:+d})")

    gained = collections.Counter()
    for s, reason in verdict.items():
        if s not in heads:
            continue
        p = s.split("/")
        ck = "cell/" + "/".join(p[1:5])
        if ck not in off:
            continue
        h = heads[s]
        had = any(overlaps(h, st) for st in on.get(ck, []))
        now = any(overlaps(h, st) for st in off[ck])
        if not had and now:
            gained[reason] += 1
        elif had and not now:
            gained[f"LOST ({reason})"] += 1
    print("\n== heads that gain an overlapping stem box")
    for k, n in gained.most_common():
        print(f"   {k:<26} {n:>5}")
    out["gained"] = dict(gained)

    # ── the COST: new strokes standing on an accidental ───────────────────
    new_on_accid = new_total = 0
    for ck, stems in off.items():
        extra = [st for st in stems if st not in on.get(ck, [])]
        new_total += len(extra)
        for st in extra:
            if any(overlaps(st, ac) for ac in accid.get(ck, [])):
                new_on_accid += 1
    print(f"\n== COST: of {new_total} newly kept strokes, {new_on_accid} "
          f"stand on an accidental the detector found "
          f"({new_on_accid / max(1, new_total):.1%})")
    out["cost"] = {"new_strokes": new_total, "on_an_accidental": new_on_accid}

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
