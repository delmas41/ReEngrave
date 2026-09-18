"""IS IT THE ERASURE? Read the stems off the ORIGINAL image and count.

`filter_sweep_arm.py` established that relaxing every filter `detect_stems`
exposes reaches only 287 of 793 heads: **506 never survive step 3, the
vertical morphological opening, as one component.** The hypothesis is the one
CLAUDE.md already names for a different rung -- *"a thin glyph is BROKEN by
erasure where the lines crossed it"* -- and which
`key_signature_locator` was measured failing under in those words: *"on a scan
whose staff-line removal leaves every glyph in pieces, nothing
accidental-sized survives."*

THE TEST IS ONE LINE OF SUBSTITUTION AND NEEDS NO NEW CODE. `line_detection`
prefers `cell.image_no_staff` and falls back to `cell.image`. Withhold the
erased variant and the SAME detector reads the SAME cell off the original
raster, where a stem crossing a staff line is continuous ink.

⚠️ WHY THIS IS NOT OBVIOUSLY SELF-DEFEATING. The opening kernel is VERTICAL
(one staff space tall, one pixel wide), and a staff line is one or two pixels
TALL -- so the opening erases horizontal rules by construction. Reading the
original does not hand the detector the staff lines; it hands it stems that
are not cut into pieces by their removal. Whether that is true is the
measurement.

⚠️ AND IT IS NOT A PROPOSAL TO SWITCH. CLAUDE.md's rule -- *erase for the CV
consumer, bound the search for everyone else, never erase for the detector* --
is measured, and this arm prices only RECALL against the record's own
`no_stem` population. The cost side is reported beside it and is a floor.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

RELAXED = {"drop_accidental_pairs": False, "max_height_lines": 24.0,
           "min_height_lines": 1.0, "max_width_lines": 1.5}


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.line_detection import detect_stems

    heads, accid, rec_stems = {}, collections.defaultdict(list), \
        collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "glyph_box":
            v = o.get("value")
            if not (isinstance(v, list) and len(v) == 5):
                continue
            name, box = str(v[0]), tuple(float(x) for x in v[1:])
            if name.startswith("notehead"):
                heads[o["subject"]] = box
            elif name.startswith("accidental") or name.startswith("key"):
                p = o["subject"].split("/")
                accid["cell/" + "/".join(p[1:5])].append(box)
        elif q == "stem":
            rec_stems[o["subject"]].append(tuple(float(x) for x in o["value"]))
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    print(f"{a.label}: {len(missing)} heads abstain `no_stem`")

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    print(f"re-cut in {time.time() - t0:.0f}s")

    ARMS = {
        "ERASED, shipped (control)":  (True, {}),
        "ERASED, all filters relaxed": (True, RELAXED),
        "ORIGINAL, shipped filters":   (False, {}),
        "ORIGINAL, all filters relaxed": (False, RELAXED),
    }
    store: dict[str, dict[str, list]] = {k: {} for k in ARMS}
    for (pws, cells), pg in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            erased = getattr(c, "image_no_staff", None)
            for name, (use_erased, kw) in ARMS.items():
                # ⚠️ withhold the erased variant, restore it immediately --
                # `detect_stems` falls back to `cell.image` on its own.
                if not use_erased:
                    c.image_no_staff = None
                try:
                    got = detect_stems(c, **kw)
                finally:
                    c.image_no_staff = erased
                store[name][ck] = [(float(d.x_canonical), float(d.y_canonical),
                                    float(d.width_canonical),
                                    float(d.height_canonical)) for d in got]

    base = store["ERASED, shipped (control)"]
    shared = set(base) & set(rec_stems)
    same = sum(1 for k in shared if sorted(base[k]) == sorted(rec_stems[k]))
    print(f"\n== CONTROL: {same} of {len(shared)} cells reproduce the record")
    out = {"label": a.label, "no_stem": len(missing),
           "control_identical": same, "control_cells": len(shared), "arms": {}}
    if not shared or same != len(shared):
        print("DEAD: the re-cut does not reproduce the record.", file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2

    # was the erased variant even present? a silent fallback would make the
    # two image arms identical and the whole comparison vacuous.
    n_missing_erased = sum(
        1 for (pws, cells), pg in prepared for c in cells
        if getattr(c, "image_no_staff", None) is None)
    print(f"   cells with NO erased variant (would make the arms identical): "
          f"{n_missing_erased}")

    print(f"\n{'arm':<32} {'strokes':>8} {'recovers':>9} {'of 793':>8} "
          f"{'new':>7} {'on accid':>9}")
    for name, s in store.items():
        rec = 0
        for sub in missing:
            p = sub.split("/")
            ck = "cell/" + "/".join(p[1:5])
            if ck in s and any(overlaps(heads[sub], st) for st in s[ck]):
                rec += 1
        new = onacc = 0
        for ck, sts in s.items():
            extra = [st for st in sts if st not in base.get(ck, [])]
            new += len(extra)
            onacc += sum(1 for st in extra
                         if any(overlaps(st, ac) for ac in accid.get(ck, [])))
        tot = sum(len(v) for v in s.values())
        out["arms"][name] = {"strokes": tot, "recovered": rec,
                             "new_strokes": new, "new_on_accidental": onacc}
        print(f"{name:<32} {tot:>8} {rec:>9} {rec/max(1,len(missing)):>7.1%} "
              f"{new:>7} {onacc:>9}")

    e = out["arms"]["ERASED, all filters relaxed"]["recovered"]
    o = out["arms"]["ORIGINAL, all filters relaxed"]["recovered"]
    verdict_line = ("The erasure IS the binding constraint."
                    if o > e else
                    "The erasure is NOT the binding constraint -- the loss "
                    "is elsewhere.")
    print(f"\n⚠️  THE COMPARISON THAT MATTERS: with every filter relaxed, "
          f"the erased image reaches {e} and the original reaches {o}. "
          f"{verdict_line}")
    out["binding_constraint_is_erasure"] = bool(o > e)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
