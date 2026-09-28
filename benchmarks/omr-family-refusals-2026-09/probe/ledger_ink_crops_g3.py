#!/usr/bin/env python3
"""ROADMAP 3.4g-3 — the ink under a rung, RE-MEASURED off the PDF, and cropped.

    python3 .../ledger_ink_crops_g3.py --record <rec> --pdf <plate> \\
        --dpi 600 --label <label> [--subjects glyph/...] [--pick-kept N]

For each subject (a `ledgerLine` glyph on `--record`):

  1. re-prepare its page from the PDF exactly as GATHER does
     (`pipeline.prepare_pages`: render, staves, cells, staff-line erasure);
  2. find the SAME cell — `(page, system, staff, cell)` through GATHER's own
     `gather_geometry` numbering — and check it IS the same: the prepared
     cell's page box must match the record's `Q.CELL_BOX` within
     `--frame-tol` px and the rung's canonical box on the record must land on
     the record's page box through this cell's own upscale (FRAME CONTROLS —
     a mismatch refuses the subject, it is never re-matched by guess);
  3. measure `gather.ledger_ink_under` on the cell's ERASED raster with the
     record's own canonical box — the function GATHER calls, not a copy —
     and compare with the record's filed `Q.LEDGER_INK_UNDER` where there is
     one (a control that can fail);
  4. run TODAY's ledger decision over the record's rows plus the measured
     value, and report what it says;
  5. draw a crop: the cell as the detector saw it (left) and staff-erased as
     the ink witness saw it (right), staff lines GREEN, the rung box as a RED
     corner bracket, the three head windows (`on` / `above` / `below`) in
     MAGENTA with the best one solid, the two background windows in CYAN.

`--pick-kept N` adds N subjects the record's own verdicts KEEP with reason
`ink_under_the_rung`, spread over the pages and staves.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.omr.staged import adjudicate, gather                    # noqa: E402
from tools.omr.staged import adjudicators                          # noqa: E402,F401
from tools.omr.staged.adjudicators import family_precision as FP   # noqa: E402
from tools.omr.staged.record import (Kind, Log, Q, READERS,         # noqa: E402
                                     Subject)
from tools.omr.staged.record_io import load_record                 # noqa: E402

LEDGER = "ledgerLine"
NEEDED = (Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.CELL_STAFF_SPACE,
          Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE)


def build(rec, subjects, measured):
    """A Log of the rows the ledger decision reads, for the subjects' CELLS,
    plus the re-measured `Q.LEDGER_INK_UNDER` (never the record's own, so the
    verdict below is the PDF's, not the record's)."""
    cells = {Subject.from_key(s).at(Kind.CELL).to_key() for s in subjects}
    staves = {Subject.from_key(s).at(Kind.STAFF).to_key() for s in subjects}
    log = Log()
    for o in rec["observations"]:
        q = o.get("quantity")
        if q not in NEEDED:
            continue
        sub = Subject.from_key(o["subject"])
        if sub.kind is Kind.STAFF:
            if o["subject"] not in staves:
                continue
        else:
            try:
                ck = sub.at(Kind.CELL).to_key()
            except Exception:                              # noqa: BLE001
                continue
            if ck not in cells:
                continue
        log.observe(sub, q, o["value"], reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **dict(o.get("detail") or {}))
    for s, m in measured.items():
        if m is None:
            continue
        log.observe(Subject.from_key(s), Q.LEDGER_INK_UNDER, m["under"],
                    reader=READERS.CV_INK, frame="cell:reprobe",
                    ink_best_window=m["best_window"],
                    ink_windows=m["windows"],
                    ink_background=m["background"],
                    ink_background_windows=m["background_windows"])
    log.freeze()
    out = {}
    for v in adjudicate.run(log, order=(Q.LEDGER_IS_NOT_A_LEDGER,)):
        out[v.subject.to_key()] = v
    return out


def word(v) -> str:
    if v is None:
        return "<none>"
    if v.outcome.value != "decided":
        return f"ABSTAINED:{v.reason}"
    return f"refused:{v.reason}" if v.value is True else f"kept:{v.reason}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--label", required=True)
    ap.add_argument("--subjects", nargs="*", default=[])
    ap.add_argument("--names", nargs="*", default=[],
                    help="a tag per --subjects entry (e.g. sean1)")
    ap.add_argument("--pick-kept", type=int, default=0)
    ap.add_argument("--frame-tol", type=float, default=2.0)
    ap.add_argument("--pad-spaces", type=float, default=4.0)
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-family-refusals-2026-09/out/print")
    ap.add_argument("--manifest", required=True)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw
    from tools.omr.staged import pipeline

    rec = load_record(a.record)["record"]
    obs = {}
    for o in rec["observations"]:
        q = o.get("quantity")
        if q in (Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
                 Q.LEDGER_INK_UNDER):
            obs[(q, o["subject"])] = o
    rec_verdict = {v["subject"]: v for v in rec["verdicts"]
                   if v["quantity"] == Q.LEDGER_IS_NOT_A_LEDGER}

    jobs = [(s, (a.names[i] if i < len(a.names) else "subject"))
            for i, s in enumerate(a.subjects)]
    if a.pick_kept:
        kept = sorted(s for s, v in rec_verdict.items()
                      if v.get("reason") == "ink_under_the_rung")
        print(f"POPULATION: {len(kept)} kept `ink_under_the_rung` on the "
              f"record")
        rng = random.Random(20260927)
        # spread: one per staff first, then fill
        by_staff = {}
        for s in kept:
            by_staff.setdefault(Subject.from_key(s).at(Kind.STAFF).to_key(),
                                []).append(s)
        picks = []
        for st in sorted(by_staff):
            picks.append(rng.choice(by_staff[st]))
        rng.shuffle(picks)
        rest = [s for s in kept if s not in picks]
        rng.shuffle(rest)
        picks = (picks + rest)[:a.pick_kept + 2]
        jobs += [(s, "ink_kept") for s in picks]
    if not jobs:
        print("DEAD AT ZERO — no subjects")
        return 2

    pages = sorted({Subject.from_key(s).page for s, _ in jobs})
    print(f"preparing pages {pages} at {a.dpi} dpi ...", flush=True)
    prepared = pipeline.prepare_pages(a.pdf, pages, dpi=a.dpi)
    cell_of = {}
    for pws, cells in prepared:
        local = gather.gather_geometry(Log(), pws)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            cell_of[(c.page_index, key[0], key[1], c.measure_index)] = c

    measured, facts, refused = {}, {}, []
    for s, tag in jobs:
        sub = Subject.from_key(s)
        c = cell_of.get((sub.page, sub.system, sub.staff, sub.cell))
        box_o = obs.get((Q.GLYPH_BOX, s))
        cb_o = obs.get((Q.CELL_BOX, sub.at(Kind.CELL).to_key()))
        if c is None or box_o is None:
            refused.append({"subject": s, "why": "cell or box not found"})
            continue
        cb = [float(t) for t in (getattr(c, "bbox_page_px", None) or ())]
        rec_cb = [float(t) for t in (cb_o or {}).get("value") or ()]
        d_cell = (max(abs(p - q) for p, q in zip(cb, rec_cb))
                  if cb and rec_cb else None)
        _n, xc, yc, wc, hc = box_o["value"]
        up = float(getattr(c, "upscale_factor", 0) or 0)
        pb = (box_o.get("detail") or {}).get("bbox_page_px")
        d_box = None
        if pb and up and cb:
            back = [cb[0] + xc / up, cb[1] + yc / up,
                    cb[0] + (xc + wc) / up, cb[1] + (yc + hc) / up]
            d_box = max(abs(p - q) for p, q in zip(back, pb))
        ok = (d_cell is not None and d_cell <= a.frame_tol
              and d_box is not None and d_box <= a.frame_tol)
        if not ok:
            refused.append({"subject": s, "why": "FRAME CONTROL FAILED",
                            "cell_box_delta_px": d_cell,
                            "rung_box_delta_px": d_box})
            print(f"  {s}: FRAME CONTROL FAILED (cell {d_cell}, box {d_box})")
            continue
        grid = gather._cell_grid(c)
        space = grid[1] * 2.0 if grid else None
        m = gather.ledger_ink_under(c.image_no_staff, (xc, yc, wc, hc),
                                    space)
        filed = obs.get((Q.LEDGER_INK_UNDER, s))
        measured[s] = m
        facts[s] = {"tag": tag, "cell": c, "box": (xc, yc, wc, hc),
                    "space": space, "m": m, "cell_box_delta_px": d_cell,
                    "rung_box_delta_px": d_box,
                    "filed_under": None if filed is None
                    else float(filed["value"]),
                    "space_on_record": (obs.get((Q.CELL_STAFF_SPACE,
                                                 sub.at(Kind.CELL).to_key()))
                                        or {}).get("value")}

    verdicts = build(rec, list(measured), measured)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    n_kept_written = 0
    for s, tag in jobs:
        if s not in facts:
            continue
        if tag == "ink_kept":
            if n_kept_written >= a.pick_kept:
                continue
        f = facts[s]
        sub = Subject.from_key(s)
        c, (xc, yc, wc, hc), sp, m = f["cell"], f["box"], f["space"], f["m"]
        v_now = verdicts.get(s)
        v_rec = rec_verdict.get(s)
        rec_word = ("<none>" if v_rec is None else
                    (f"ABSTAINED:{v_rec.get('reason')}"
                     if v_rec["outcome"] != "decided" else
                     (f"refused:{v_rec.get('reason')}" if v_rec["value"] is True
                      else f"kept:{v_rec.get('reason')}")))
        img = c.image if c.image.ndim == 2 else c.image.mean(axis=2)
        era = c.image_no_staff
        H, W = era.shape
        cx, cy = xc + wc / 2.0, yc + hc / 2.0
        pad = a.pad_spaces * sp
        x0, x1 = int(max(0, cx - pad)), int(min(W, cx + pad))
        y0, y1 = int(max(0, cy - pad * 1.25)), int(min(H, cy + pad * 1.25))
        Z = max(1, int(round(420.0 / max(1, (x1 - x0)))))

        def panel(arr):
            p = Image.fromarray(np.asarray(arr[y0:y1, x0:x1],
                                           dtype=np.uint8)).convert("RGB")
            p = p.resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.NEAREST)
            dr = ImageDraw.Draw(p)
            for ly in (getattr(c, "staff_line_ys_canonical", None) or ()):
                y = (float(ly) - y0) * Z
                if 0 <= y < p.height:
                    dr.line([(0, y), (p.width, y)], fill=(0, 170, 60),
                            width=1)
            ww, wh = (gather.LEDGER_INK_WINDOW_SPACES[0] * sp,
                      gather.LEDGER_INK_WINDOW_SPACES[1] * sp)

            def rect(dy, col, width):
                ry = cy + dy * sp
                dr.rectangle([(cx - ww / 2 - x0) * Z, (ry - wh / 2 - y0) * Z,
                              (cx + ww / 2 - x0) * Z, (ry + wh / 2 - y0) * Z],
                             outline=col, width=width)
            for dy in gather.LEDGER_INK_BACKGROUND_SPACES:
                rect(dy, (0, 170, 200), 1)
            for name, dy in gather.LEDGER_INK_OFFSETS_SPACES:
                best = m is not None and m["best_window"] == name
                rect(dy, (200, 0, 200), 3 if best else 1)
            bx0, by0 = (xc - x0) * Z, (yc - y0) * Z
            bx1, by1 = (xc + wc - x0) * Z, (yc + hc - y0) * Z
            arm = max(6, int((bx1 - bx0) * 0.25))
            for (ax, ay, dx, dy2) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                      (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0),
                        width=2)
                dr.line([(ax, ay), (ax, ay + dy2 * arm)], fill=(220, 0, 0),
                        width=2)
            return p

        left, right = panel(img), panel(era)
        band = 100
        out_im = Image.new("RGB", (left.width + right.width + 12,
                                   left.height + band), "white")
        out_im.paste(left, (0, band))
        out_im.paste(right, (left.width + 12, band))
        cd = ImageDraw.Draw(out_im)
        staff = sub.at(Kind.STAFF).to_key()
        cd.text((6, 4), f"{s}   staff {staff} (GREEN = its lines)   [{tag}]",
                fill=(0, 0, 0))
        cd.text((6, 20), f"on the record: {rec_word}   ->   3.4g-3 with the "
                         f"re-measured ink: {word(v_now)}", fill=(140, 0, 0))
        if m is not None:
            cd.text((6, 36), f"ink under {m['under']} (best: {m['best_window']}"
                             f")  windows {m['windows']}", fill=(0, 0, 0))
            cd.text((6, 52), f"background {m['background']}  "
                             f"{m['background_windows']}   contrast "
                             f"{round(m['under'] - (m['background'] or 0), 4)}"
                             f"   KEPT: under >= {FP.LEDGER_INK_KEPT_MIN} & "
                             f"contrast >= {FP.LEDGER_INK_KEPT_CONTRAST_MIN}; "
                             f"REFUSED <= {FP.LEDGER_INK_REFUSED_MAX} under",
                    fill=(0, 0, 0))
        cd.text((6, 68), "LEFT: the cell as the detector saw it   RIGHT: "
                         "staff-erased, as the ink witness reads it",
                fill=(0, 0, 0))
        cd.text((6, 84), "RED bracket = the rung box   MAGENTA = head windows"
                         " (solid = best)   CYAN = background windows",
                fill=(0, 120, 45))
        fname = (f"g3-{a.label}-p{sub.page}-s{sub.system}-st{sub.staff}-"
                 f"c{sub.cell}-g{sub.glyph}-{tag}.png")
        out_im.save(out_dir / fname)
        if tag == "ink_kept":
            n_kept_written += 1
        manifest.append({
            "file": fname, "subject": s, "staff": staff, "tag": tag,
            "verdict_on_the_record": rec_word,
            "verdict_3_4g_3_remeasured": word(v_now),
            "ink": m,
            "filed_under_on_the_record": f["filed_under"],
            "cell_staff_space_px": round(sp, 3) if sp else None,
            "cell_staff_space_on_record": f["space_on_record"],
            "frame_control": {"cell_box_delta_px": f["cell_box_delta_px"],
                              "rung_box_delta_px": f["rung_box_delta_px"],
                              "tol_px": a.frame_tol},
            "VERDICT_none_yet": None,
        })
        print(f"  {s} [{tag}]: under {m and m['under']} bg "
              f"{m and m['background']} filed {f['filed_under']} -> "
              f"{word(v_now)}  (record: {rec_word})")
    Path(a.manifest).write_text(json.dumps({
        "record": Path(a.record).name, "dpi": a.dpi,
        "constants": {
            "LEDGER_INK_WINDOW_SPACES": gather.LEDGER_INK_WINDOW_SPACES,
            "LEDGER_INK_OFFSETS_SPACES": gather.LEDGER_INK_OFFSETS_SPACES,
            "LEDGER_INK_BACKGROUND_SPACES":
                gather.LEDGER_INK_BACKGROUND_SPACES,
            "LEDGER_INK_KEPT_MIN": FP.LEDGER_INK_KEPT_MIN,
            "LEDGER_INK_KEPT_CONTRAST_MIN": FP.LEDGER_INK_KEPT_CONTRAST_MIN,
            "LEDGER_INK_REFUSED_MAX": FP.LEDGER_INK_REFUSED_MAX},
        "refused_by_frame_control": refused,
        "crops": manifest}, indent=2, default=str))
    print("wrote", a.manifest, "and", len(manifest), "crops")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
