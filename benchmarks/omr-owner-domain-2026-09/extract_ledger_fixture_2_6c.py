"""ROADMAP 2.6c (second half) — cut the test fixture for the ledger-direction
helper from the two 27b arm records, for the six heads Sean adjudicated
against the print in 2.7b.8 (the four kept by 2.7b's rung exception on
Litolff, the two on Breitkopf).

Writes `tools/omr/tests/fixtures/ledger_direction_2_6c.json`: per head, its
own `Q.GLYPH_BOX` / `Q.NOTEHEAD_CLASS` / band / ladder rows, the lines and
spacing of every staff of its system within 12 spaces, every `ledgerLine`
box in its cell and in the SAME-INDEX cell of every one of those staves
(with its `ledger_is_not_a_ledger` verdict), the cell's unit and box, and
the `instrument` / `clef` verdicts of those staves (for the range veto).

Read ONLY through `record_io.load_record` (CLAUDE.md, 1.1b).

    python3 benchmarks/omr-owner-domain-2026-09/extract_ledger_fixture_2_6c.py \
        --litolff <litolff-arm.record.json> --breitkopf <brahms-arm.record.json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged.record_io import load_record  # noqa: E402

#: Sean's verdicts, `benchmarks/omr-accidental-2026-09/out/print/
#: 2.7b-crop-manifest.json` / `2.7b-brk-crop-manifest.json` (sheet #).
HEADS = {
    "litolff": {
        "glyph/16/1/7/14/0": ("belongs_to_filed_staff", 1),
        "glyph/10/1/2/12/6": ("belongs_to_the_nearer_staff", 4),
        "glyph/8/0/6/12/7": ("not_a_note", 10),
        "glyph/12/0/11/14/1": ("belongs_to_filed_staff", 14),
    },
    "breitkopf": {
        "glyph/9/0/11/0/1": ("belongs_to_filed_staff", 18),
        "glyph/4/1/2/8/31": ("belongs_to_the_nearer_staff", 22),
    },
}

OUT = Path("tools/omr/tests/fixtures/ledger_direction_2_6c.json")


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
    for head, (sean, sheet) in heads.items():
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
            inst = vby.get((sk, "instrument"))
            clef = vby.get((sk, "clef"))
            staves[sk] = {
                "staff_lines": L["value"], "staff_spacing": S["value"],
                "instrument": (inst["value"] if inst and inst["outcome"]
                               == "decided" else None),
                "clef": (clef["value"] if clef and clef["outcome"]
                         == "decided" else None)}
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
        npv = vby.get((head, "notehead_is_not_a_notehead"))
        out.append({
            "subject": head, "sean": sean, "sheet": sheet,
            "glyph_box": {"value": box["value"], "detail": box["detail"]},
            "notehead_class": (_last(rows, "notehead_class") or {}).get("value"),
            "band_rows": [[o["value"], o["detail"]] for o in rows
                          if o["quantity"] == "glyph_band_distance"],
            "ladder_rows": [[o["value"], o["detail"]] for o in rows
                            if o["quantity"] == "glyph_ladder"],
            "staves": staves,
            "ledgers": ledgers,
            "cell": {"key": cell_key,
                     "cell_staff_space": ([css["value"], css["detail"]]
                                          if css else None),
                     "cell_box": cbox["value"] if cbox else None},
            "on_the_arm_record": {
                "glyph_owner": ([own["outcome"], own["value"], own["reason"]]
                                if own else None),
                "notehead_is_not_a_notehead": (
                    [npv["outcome"], npv["value"], npv["reason"]]
                    if npv else None)},
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--litolff", required=True)
    ap.add_argument("--breitkopf", required=True)
    a = ap.parse_args(argv)
    heads = (extract(a.litolff, HEADS["litolff"])
             + extract(a.breitkopf, HEADS["breitkopf"]))
    doc = {"source": {"litolff": a.litolff, "breitkopf": a.breitkopf},
           "made_by": "benchmarks/omr-owner-domain-2026-09/"
                      "extract_ledger_fixture_2_6c.py",
           "heads": heads}
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}: {len(heads)} heads, "
          f"{sum(len(h['ledgers']) for h in heads)} ledger boxes")


if __name__ == "__main__":
    main()
