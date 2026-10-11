"""ROADMAP 2.12m -- choose the blind tiles for the long-chord-stem rule.

    python3 benchmarks/omr-shape-role-2026-09/select_artic_2_12m_tiles.py \
        --pair brahms out/2.12m/brahms-whole-1009-base.json out/2.12m/brahms-whole-1009-arm.json \
        [--pair litolff B A ...] --out selection.json [--seed 20261010]

Inputs are `readjudicate_artic_side.py` outputs, base (origin/main) and arm
(this branch), on ONE record. CATEGORIES (manifest only; Sean never sees them):

  newly_decided   base abstained `stem_contradicts_class_side`, arm decided
                  `stem_tip_of_long_chord` -- EVERY one is tiled.
  refused         arm still abstained `stem_contradicts_class_side` with
                  `long_chord_stem` in {no_ledger_head_on_stem,
                  mark_not_at_stem_tip} -- up to 4, seeded.
  control         `glyph/23/1/7/9/4` (Brahms pdf 23, Sean's 2.12f round-2 tile
                  6: "Connected to note below") -- the rule must decide it.

Tile order is shuffled (seeded) so the category cannot be read off the number.
"""
from __future__ import annotations

import argparse
import json
import random

CONTROL = "glyph/23/1/7/9/4"
REFUSALS = ("no_ledger_head_on_stem", "mark_not_at_stem_tip")


def _read(o):
    d = o["detail"] or {}
    if o["outcome"] == "decided":
        return ("decided %s: owner %s (stem %s, far head %s at position %s, "
                "tip gap %s spaces, chord %s heads)" % (
                    o["reason"], o["value"], d.get("stem_direction"),
                    d.get("far_head"), d.get("far_head_position"),
                    d.get("tip_gap_spaces"), d.get("chord_heads")))
    return ("%s %s (nearest head %s, stem %s, long_chord_stem %s, far head %s at "
            "position %s, tip gap %s spaces, chord %s heads)" % (
                o["outcome"], o["reason"], d.get("nearest_head"),
                d.get("stem_direction"), d.get("long_chord_stem"),
                d.get("long_chord_far_head"), d.get("long_chord_far_head_position"),
                d.get("long_chord_tip_gap_spaces"), d.get("long_chord_chord_heads")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=3, action="append", required=True,
                    metavar=("DOC", "BASE", "ARM"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--refused", type=int, default=4)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)

    new, refused, control = [], [], []
    for doc, bp, ap_ in a.pair:
        bj, aj = json.load(open(bp)), json.load(open(ap_))
        b = {r["subject"]: r for r in bj["articulations"]}
        for r in aj["articulations"]:
            s, ao, bo = r["subject"], r["owner"], b[r["subject"]]["owner"]
            if not r.get("mark_bbox_page"):
                continue
            item = {"doc": doc, "pdf": aj["pdf"], "page": r["page"], "subject": s,
                    "mark_bbox_page": r["mark_bbox_page"], "class": r["class"],
                    "read_before": _read(bo), "read_after": _read(ao)}
            if doc == "brahms" and s == CONTROL:
                control.append(dict(item, category="control_tile6"))
            elif ao["outcome"] == "decided" and ao["reason"] == "stem_tip_of_long_chord":
                new.append(dict(item, category="newly_decided"))
            elif (ao["reason"] == "stem_contradicts_class_side"
                  and (ao["detail"] or {}).get("long_chord_stem") in REFUSALS):
                refused.append(dict(item, category="refused:%s"
                                    % ao["detail"]["long_chord_stem"]))
    rng.shuffle(refused)
    tiles = new + refused[:a.refused] + control
    rng.shuffle(tiles)
    for i, t in enumerate(tiles, 1):
        t["n"] = i
    print("newly decided %d, refused pool %d (taking %d), control %d"
          % (len(new), len(refused), min(a.refused, len(refused)), len(control)))
    json.dump(tiles, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
