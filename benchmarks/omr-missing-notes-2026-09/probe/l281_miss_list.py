#!/usr/bin/env python3
"""l281_miss_list: the misses the 2.81 follow-up shows Sean, and how they are grouped into images.

  * Sean's own tiles (`out/print/2.81-review/answers.json`): every SAMPLE tile whose answer is not a quarter or
    a dotted quarter (the controls are not misses). Printed = his word.
  * the hand-truth page (Brahms 317803 pdf 0, as corrected 2026-10-10): the members the quarter rule gets wrong on
    HIS boxes (`l281_score.py --json`, `judge == wrong_beam`), grouped by what his boxes show on the stem:
    BEAMED heads one image per bar (cell) -- every miss in the bar numbered; FLAGGED heads one image per bar.
  * the one head his boxes call bare whose print shows a flag his page does not box (`l281_score.
    PRINT_CHECK_UNBOXED_MARK`), marked as such.

    python3 l281_miss_list.py --scored b0-scored.json [--print-keys | --items]
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

REVIEW = REPO / "out" / "print" / "2.81-review"
QUARTER_VALUED = {"quarter", "dotted quarter", "double dotted quarter"}
PRINT_CHECK_UNBOXED_MARK = ("glyph/0/0/9/2/2",)


def tile_misses():
    man = json.loads((REVIEW / "manifest.json").read_text())
    ans = json.loads((REVIEW / "answers.json").read_text())
    out = []
    for t in sorted(man["tiles"], key=lambda t: t["id"]):
        if t["kind"] != "sample":
            continue
        a = str(ans.get(t["id"]) or "").strip().lower()
        if a in QUARTER_VALUED:
            continue
        out.append({"kind": "tile", "tile": t["id"], "keys": [t["hidden"]["key"]], "printed": a,
                    "movement": t["hidden"]["movement"], "page": t["hidden"]["pdf_page"],
                    "stratum": t["hidden"]["stratum"]})
    # the coordinator's order: the strict-subset eighths, the half, the no-stem eighths, the rest
    order = ["tile_04", "tile_09", "tile_27", "tile_22", "tile_02", "tile_11", "tile_29", "tile_07"]
    out.sort(key=lambda m: order.index(m["tile"]) if m["tile"] in order else len(order))
    return out


def hand_truth_items(scored):
    rows = json.loads(Path(scored).read_text())
    wrong = [r for r in rows if r["judge"] == "wrong_beam"]
    items = []
    by = {}
    for r in wrong:
        kind = "beam" if r.get("truth_levels_beam") else "flag"
        by.setdefault((kind, r["cell"]), []).append(r)
    # beam groups first (cell order), then flags
    def cell_order(cell):                      # "s0-st10-m3" -> (system, staff, measure), numeric
        s, st, m = cell.split("-")
        return (int(s[1:]), int(st[2:]), int(m[1:]))
    for (kind, cell), rs in sorted(by.items(), key=lambda kv: (kv[0][0] != "beam", cell_order(kv[0][1]))):
        rs.sort(key=lambda r: r["page_box"][0])
        items.append({"kind": "hand-truth-" + kind, "cell": cell, "keys": [r["key"] for r in rs],
                      "printed": "eighth", "movement": "brahms", "page": 0,
                      "truth_ids": [r["truth_id"] for r in rs],
                      "truth_beam_ids": sorted({b for r in rs for b in (r.get("truth_beam_ids") or [])}),
                      "truth_flag_ids": sorted({b for r in rs for b in (r.get("truth_flag_ids") or [])})})
    for k in PRINT_CHECK_UNBOXED_MARK:
        r = next(r for r in rows if r["key"] == k)
        items.append({"kind": "hand-truth-unboxed-flag", "cell": r["cell"], "keys": [k],
                      "printed": "eighth", "movement": "brahms", "page": 0,
                      "truth_ids": [r["truth_id"]], "truth_beam_ids": [], "truth_flag_ids": []})
    return items


def all_items(scored):
    return tile_misses() + hand_truth_items(scored)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--print-keys", action="store_true", help="the hand-truth keys, comma separated")
    ap.add_argument("--items", action="store_true")
    a = ap.parse_args()
    if a.print_keys:
        print(",".join(k for it in hand_truth_items(a.scored) for k in it["keys"]))
        return
    items = all_items(a.scored)
    if a.items:
        print(json.dumps(items, indent=1))
    else:
        for i, it in enumerate(items, 1):
            print(i, it["kind"], it.get("tile", it.get("cell")), it["printed"], it["keys"])


if __name__ == "__main__":
    main()
