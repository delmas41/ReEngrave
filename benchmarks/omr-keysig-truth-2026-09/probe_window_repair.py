#!/usr/bin/env python3
"""A/B two candidate header-window repairs, on ONE page load, then re-read.

    python3 benchmarks/omr-keysig-truth-2026-09/probe_window_repair.py

⚠️ ONE `prepare_pages`, THREE ARMS. Rendering, staff detection and barline
detection happen once and every arm reads the same `PageWithStaves`, so no
segmentation jitter can enter the comparison — the staged pipeline's own
"one gather, exported twice" rule, applied to a window instead of a file.

The arms:

  base   what ships. The right edge is the system's first barline at least
         `min_width_spaces` right of x0, else a width cap.
  A      THE OPENING RULE IS EXCLUDED BY IDENTITY. `measure_header_window`'s
         own comment says the distance test exists to keep "the system's own
         initial rule" out of the candidates — but the system's opening rule
         is `min(barline x)` for that system and can be named directly,
         whereas a distance measured from x0 fails exactly when x0 is wrong,
         which is the case it is there for.
  B      A, plus x0 CLAMPED so the window cannot begin more than the
         configured left margin left of that same opening rule.

Neither arm introduces a constant. A removes a test; B reuses
`left_margin_spaces`, which already exists and already means "how far left of
the system's start the window begins".
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")
PAGES = [1, 2, 3, 4]


def window(pws, staff, cfg, left_edge, opening_rule, arm):
    """The shipped rule, with the arm's change folded in. Mirrors
    `staff_header.measure_header_window` line for line so the A/B is about the
    change and not about a re-implementation."""
    spacing = max(1.0, staff.line_spacing_px)
    x0 = max(0, left_edge - int(round(cfg.left_margin_spaces * spacing)))
    if arm == "B" and opening_rule is not None:
        floor = opening_rule - int(round(cfg.left_margin_spaces * spacing))
        x0 = max(x0, min(floor, opening_rule))
    min_w = int(round(cfg.min_width_spaces * spacing))
    max_w = int(round(cfg.max_width_spaces * spacing))
    page_w = pws.page.binary.shape[1]
    cands = [bl.x for bl in pws.barlines
             if bl.system_index == staff.system_index and bl.x >= x0 + min_w]
    if arm in ("A", "B") and opening_rule is not None:
        cands = [x for x in cands if x != opening_rule]
    if cands and min(cands) <= x0 + max_w:
        x1, src = min(cands), "barline"
    else:
        x1, src = x0 + max_w, "width_cap"
    x1 = min(int(x1), page_w,
             staff.x_end if staff.x_end > x0 + min_w else page_w)
    if x1 - x0 < min_w:
        return None
    return int(x0), int(x1), src


def main(argv: list[str]) -> int:
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.staff_header import (DEFAULT_CONFIG, HEADER_MEASURE_INDEX,
                                        _build_measure_cell, system_left_edge)
    from tools.omr.staff_line_removal import remove_staff_lines_from_cell
    from tools.omr.header_ink import refine_staff_lines_in_cell
    from tools.omr.key_signature_locator import locate_key_signature
    from tools.omr.key_signature_template import read_key_signature

    cfg = DEFAULT_CONFIG
    truth = json.loads((HERE / "truth.json").read_text())
    by_sys = {(t["page"], t["system"]): t for t in truth["systems"]}
    graded = json.loads((HERE / "grade-before.json").read_text())
    read_clef = {(g["page"], g["system"], g["staff"]): g["read_clef"]
                 for g in graded}

    arms = ["base", "A", "B"]
    res: dict[str, list] = {a: [] for a in arms}

    for pws, _cells in prepare_pages(str(ROOT / PDF), PAGES):
        p = pws.page.page_index
        local = _system_local(pws.staves)
        for sysi in sorted({s.system_index for s in pws.staves}):
            left = system_left_edge(pws, sysi, cfg)
            if left is None:
                continue
            bls = [bl.x for bl in pws.barlines if bl.system_index == sysi]
            rule = min(bls) if bls else None
            spec = by_sys.get((p, sysi))
            if spec is None:
                continue
            for st in sorted((s for s in pws.staves if s.system_index == sysi),
                             key=lambda x: x.top_y):
                _, i = local[st.staff_index]
                if i >= len(spec["lineup"]):
                    continue
                inst = spec["lineup"][i]
                t = truth["instruments"][inst]
                clef = read_clef.get((p, sysi, i))
                for arm in arms:
                    w = window(pws, st, cfg, left, rule, arm)
                    row = {"page": p, "system": sysi, "staff": i,
                           "instrument": inst, "truth_fifths": t["fifths"],
                           "loc_fifths": None, "tpl_fifths": None,
                           "width_spaces": None}
                    if w is None or clef is None:
                        res[arm].append(row)
                        continue
                    x0, x1, _src = w
                    row["width_spaces"] = round(
                        (x1 - x0) / max(1.0, st.line_spacing_px), 2)
                    cell = _build_measure_cell(pws, st, sysi, x0, x1,
                                               HEADER_MEASURE_INDEX)
                    if cell is None:
                        res[arm].append(row)
                        continue
                    refine_staff_lines_in_cell(cell)
                    remove_staff_lines_from_cell(cell)
                    try:
                        f = locate_key_signature(cell, clef)
                        if f is not None:
                            row["loc_fifths"] = f.read.fifths
                    except Exception:                         # noqa: BLE001
                        pass
                    try:
                        tp = read_key_signature(cell, clef)
                        if tp is not None:
                            row["tpl_fifths"] = tp.fifths
                    except Exception:                         # noqa: BLE001
                        pass
                    res[arm].append(row)

    def grade(rows, field):
        t = {"correct": 0, "wrong": 0, "abstained": 0}
        for r in rows:
            v = r[field]
            if v is None:
                t["abstained"] += 1
            elif v == r["truth_fifths"]:
                t["correct"] += 1
            else:
                t["wrong"] += 1
        return t

    print(f"{'arm':<6} {'reader':<9} {'correct':>7} {'wrong':>6} "
          f"{'abstain':>8}   narrow windows (<10 spaces)")
    for arm in arms:
        narrow = sum(1 for r in res[arm]
                     if r["width_spaces"] is not None
                     and r["width_spaces"] < 10)
        for reader, field in (("locator", "loc_fifths"),
                              ("template", "tpl_fifths")):
            g = grade(res[arm], field)
            print(f"{arm:<6} {reader:<9} {g['correct']:>7} {g['wrong']:>6} "
                  f"{g['abstained']:>8}   {narrow if reader=='locator' else ''}")

    # Did any arm change a window OUTSIDE the system it was aimed at?
    base = {(r["page"], r["system"], r["staff"]): r["width_spaces"]
            for r in res["base"]}
    for arm in ("A", "B"):
        moved = [(k, base[k], r["width_spaces"])
                 for r in res[arm]
                 if (k := (r["page"], r["system"], r["staff"]))
                 and base.get(k) != r["width_spaces"]]
        bysys: dict[tuple, int] = {}
        for k, _b, _n in moved:
            bysys[(k[0], k[1])] = bysys.get((k[0], k[1]), 0) + 1
        print(f"\narm {arm}: {len(moved)} of {len(res['base'])} windows change"
              f"  {dict(sorted(bysys.items()))}")

    json.dump(res, (HERE / "window-repair.json").open("w"), indent=1)
    print(f"\nwrote {HERE / 'window-repair.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
