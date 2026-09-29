"""ROADMAP 2.6f — cut the test fixture for the shared-own-structure discount
from the Breitkopf 27b arm record, for the seven §2.6c.3 contests read by eye
(FINDINGS §2.6c.3/§2.6f): every one is a note standing right at its NEAR
candidate's own first ledger, with a SECOND real `ledgerLine` box one more
space out that the far candidate's own, longer walk also reaches.

One head per contest (the subject filed under the candidate BASE named
correct, i.e. the near one) is enough: `test_staged_shared_structure_2_6f.py`
rebuilds both sides from the SAME fixture the way
`test_staged_ledger_direction.py`'s `_build` does.

Writes `tools/omr/tests/fixtures/shared_structure_2_6f.json`: per head, its
own `Q.GLYPH_BOX` / `Q.NOTEHEAD_CLASS` / band rows, the lines and spacing of
every staff of its system within 12 spaces, every `ledgerLine` box in its
cell and the same-index cell of every one of those staves (with its
`ledger_is_not_a_ledger` verdict) -- exactly `extract_ledger_fixture_2_6c.
py`'s shape, reused rather than re-derived.

Read ONLY through `record_io.load_record` (CLAUDE.md, 1.1b).

    python3 benchmarks/omr-owner-domain-2026-09/extract_shared_structure_fixture_2_6f.py \
        --breitkopf <brahms-arm.record.json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged.record_io import load_record  # noqa: E402

#: FINDINGS §2.6c.3's nine contests, the seven `ledger_direction` ones (the
#: two `range_veto` ones, #8/#9, are untouched by this fix -- not extracted).
#: `(head subject, BASE's -- and the correct -- staff)`.
HEADS = {
    "glyph/10/1/0/1/1": "staff/10/1/1",
    "glyph/10/1/0/2/8": "staff/10/1/1",
    "glyph/16/0/0/6/5": "staff/16/0/1",
    "glyph/16/0/0/7/4": "staff/16/0/1",
    "glyph/18/0/0/3/6": "staff/18/0/1",
    "glyph/18/0/0/4/13": "staff/18/0/1",
    "glyph/5/1/12/0/10": "staff/5/1/12",
}

OUT = Path("tools/omr/tests/fixtures/shared_structure_2_6f.json")


def _index(rec):
    by_sub = {}
    for o in rec["observations"]:
        by_sub.setdefault(o["subject"], []).append(o)
    vby = {}
    for v in rec["verdicts"]:
        vby[(v["subject"], v["quantity"])] = v
    return by_sub, vby


def _last(rows, q):
    got = [o for o in rows if o["quantity"] == q]
    return got[-1] if got else None


def extract(path, heads):
    rec = load_record(path)["record"]
    by_sub, vby = _index(rec)
    out = []
    for head, correct_staff in heads.items():
        _g, p, s, st, c, _gi = head.split("/")
        rows = by_sub.get(head, [])
        box = _last(rows, "glyph_box")
        bb = box["detail"]["bbox_page_px"]
        y = (bb[1] + bb[3]) / 2.0
        staves = {}
        for k in range(0, 40):
            sk = f"staff/{p}/{s}/{k}"
            L = _last(by_sub.get(sk, []), "staff_lines")
            S = _last(by_sub.get(sk, []), "staff_spacing")
            if not L or not S:
                continue
            ys = sorted(L["value"])
            if min(abs(ys[0] - y), abs(ys[-1] - y)) > 12 * S["value"]:
                continue
            staves[sk] = {"staff_lines": L["value"],
                          "staff_spacing": S["value"]}
        ledgers = []
        for sk in staves:
            cell_prefix = "glyph/" + "/".join(sk.split("/")[1:]) + f"/{c}/"
            for sub, rs in by_sub.items():
                if not sub.startswith(cell_prefix):
                    continue
                b = _last(rs, "glyph_box")
                if not b or b["value"][0] != "ledgerLine":
                    continue
                lv = vby.get((sub, "ledger_is_not_a_ledger"))
                ledgers.append({
                    "subject": sub, "value": b["value"],
                    "bbox_page_px": b["detail"].get("bbox_page_px"),
                    "verdict": ([lv["outcome"], lv["value"], lv["reason"]]
                                if lv else None)})
        cell_key = f"cell/{p}/{s}/{st}/{c}"
        crow = by_sub.get(cell_key, [])
        css = _last(crow, "cell_staff_space")
        cbox = _last(crow, "cell_box")
        own = vby.get((head, "glyph_owner"))
        out.append({
            "subject": head, "correct_staff": correct_staff,
            "glyph_box": {"value": box["value"], "detail": box["detail"]},
            "notehead_class": (_last(rows, "notehead_class") or {}).get("value"),
            "band_rows": [[o["value"], o["detail"]] for o in rows
                          if o["quantity"] == "glyph_band_distance"],
            "staves": staves,
            "ledgers": ledgers,
            "cell": {"key": cell_key,
                     "cell_staff_space": ([css["value"], css["detail"]]
                                          if css else None),
                     "cell_box": cbox["value"] if cbox else None},
            "on_the_arm_record_before_2_6f": (
                [own["outcome"], own["value"], own["reason"]]
                if own else None),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--breitkopf", required=True)
    a = ap.parse_args(argv)
    heads = extract(a.breitkopf, HEADS)
    doc = {"source": {"breitkopf": a.breitkopf},
           "made_by": "benchmarks/omr-owner-domain-2026-09/"
                      "extract_shared_structure_fixture_2_6f.py",
           "heads": heads}
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}: {len(heads)} heads, "
          f"{sum(len(h['ledgers']) for h in heads)} ledger boxes")


if __name__ == "__main__":
    main()
