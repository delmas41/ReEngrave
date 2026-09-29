"""ROADMAP 2.6c.3 (evidence lane, no pipeline change) — crops of the 9
Breitkopf contests FINDINGS §2.6c.2 left "unadjudicated": every
`glyph_owner` contest whose winner FLIPS between the base tree (8100c9ff,
`ledger_direction` still an ADDITIVE +8.0 term) and today's main (the HARD
gate, plus 2.6d's CV rungs and 2.6e), where the reason on at least one side
is `ledger_direction`. The base-vs-arm diff (`diff_base_arm_2_6c.py` on
`out/2.6c-base-vs-arm-breitkopf.json`) counts these as 14 SUBJECT rows
(`ledger_direction->ledger_direction`) + 4 (`ledger_direction->range_veto`);
each contest is filed on TWO subjects (the same physical ink, once per
candidate staff's own cell, CLAUDE.md §10), so 18 subjects = 9 contests.
Both twins of a contest carry the identical winner (verified against
`out/2.6c3-target18.json`) -- one crop per contest, both subject ids named.

Because `ledger_direction` returns BEFORE any additive weight is summed
(2.6c.2), a wrongly-credited rung does not nudge a score, it DECIDES the
staff outright -- exactly the failure mode 2.6d.3's pre-merge check looked
for on a different page. This is that check on the 9 contests FINDINGS
named as open.

The 9 contest subject-pairs and the BASE tree's winner are hardcoded below
(derived once from `diff_base_arm_2_6c.py` run against a fresh
`readjudicate_owner_2_6c.py --dump` from an extracted 8100c9ff tree and from
today's main, over the SAME record -- CLAUDE.md §6b). This script re-reads
the record ONLY through `record_io.load_record`, ONCE, and re-decides
`glyph_owner` on TODAY's tree (this worktree) to get the live ledger detail
(credited rungs, their source detector/cv_ink, the excluded own-line rung).

Banded style of `crop_far_no_rungs_2_6c.py` / `crop_losers_2_6b.py`
(`_frame_ok` reused, frame control can fail): GREEN = the staff TODAY's
tree (ARM) awards the note to; BLUE = the staff the BASE tree awarded it to
(the answer that flipped). The note is bracketed RED. Every rung
`ledger_direction` counted TOWARD the ARM winner is boxed MAGENTA and
labelled with its source (`detector` / `cv_ink`); the rung read as the
note's OWN line (excluded from either side's ladder) is boxed dashed GREY.

    python3 benchmarks/omr-owner-domain-2026-09/crop_reversals_2_6c3.py \
        --record <brahms-arm.record.json> --pdf <breitkopf.pdf>

Record read ONLY through `record_io.load_record`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged.record import (  # noqa: E402
    Candidate, Outcome, Q, Subject, Verdict)
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from crop_losers_2_6b import _frame_ok  # noqa: E402

OUT_DIR = HERE / "out" / "print"
DPI = 600
INJECT = (Q.LEDGER_IS_NOT_A_LEDGER, Q.INSTRUMENT, Q.CLEF)

# (contest #, twin subject A, twin subject B, BASE winner). ARM winner and
# reason are re-decided live below, not hardcoded.
CONTESTS = [
    (1, "glyph/10/1/0/1/1", "glyph/10/1/1/1/7", "staff/10/1/1"),
    (2, "glyph/10/1/0/2/8", "glyph/10/1/1/2/1", "staff/10/1/1"),
    (3, "glyph/16/0/0/6/5", "glyph/16/0/1/6/7", "staff/16/0/1"),
    (4, "glyph/16/0/0/7/4", "glyph/16/0/1/7/11", "staff/16/0/1"),
    (5, "glyph/18/0/0/3/6", "glyph/18/0/1/3/7", "staff/18/0/1"),
    (6, "glyph/18/0/0/4/13", "glyph/18/0/1/4/10", "staff/18/0/1"),
    (7, "glyph/5/1/12/0/10", "glyph/5/1/13/0/8", "staff/5/1/12"),
    (8, "glyph/18/1/4/3/2", "glyph/18/1/5/3/2", "staff/18/1/5"),
    (9, "glyph/4/1/4/5/0", "glyph/4/1/5/5/1", "staff/4/1/5"),
]


def _outcome(v):
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[v["outcome"]]


def main(argv=None) -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    a = ap.parse_args(argv)

    rec = load_record(a.record)["record"]
    log, _ids = rebuild_gather(rec)
    log.freeze()
    superseded = {v.get("supersedes") for v in rec["verdicts"]
                  if v.get("supersedes")}
    current = {}
    for v in rec["verdicts"]:
        if v["id"] in superseded:
            continue
        current[(v["quantity"], v["subject"])] = v
    for (q, key), v in current.items():
        if q in INJECT:
            log.record(Verdict(
                id=log._next_id("vrd"), subject=Subject.from_key(key),
                quantity=q, outcome=_outcome(v), value=v["value"],
                decider=v["decider"], reason=v["reason"],
                candidates=tuple(Candidate(c["value"], c["support"])
                                 for c in (v.get("candidates") or ()))))
    A._ensure_decisions()
    spec = A.REGISTRY[Q.GLYPH_OWNER]

    glyph_box = {}
    rung_ink_by_row = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            glyph_box[o["subject"]] = o["detail"].get("bbox_page_px")
        elif o["quantity"] == "ledger_rung_ink":
            rung_ink_by_row[o["id"]] = o["detail"]
    geo = {}
    for o in rec["observations"]:
        if o["quantity"] in ("staff_lines", "staff_spacing"):
            geo.setdefault(o["subject"], {})[o["quantity"]] = o["value"]

    def rung_bbox(key: str):
        if key.startswith("cv:"):
            row_id = key[3:]
            d = rung_ink_by_row.get(row_id)
            return d.get("window_page_px") if d else None
        return glyph_box.get(key)

    font = ImageFont.load_default(size=20)
    big_font_cache = {}
    doc = fitz.open(a.pdf)
    pages = {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, refused = [], []

    for n, subA, subB, base_winner in CONTESTS:
        v = A.adjudicate_one(log, spec, Subject.from_key(subA))
        vB = A.adjudicate_one(log, spec, Subject.from_key(subB))
        assert (v.value, v.reason) == (vB.value, vB.reason), (subA, subB, v, vB)
        led = (v.detail or {}).get("ledger") or {}
        sides = led.get("sides") or {}
        cand_keys = list(sides.keys())
        if len(cand_keys) != 2 or any(
                "staff_lines" not in geo.get(c, {}) for c in cand_keys):
            refused.append({"contest": n, "why": "geometry missing"})
            continue
        arm_winner = v.value
        loser = [c for c in cand_keys if c != arm_winner][0]
        boxA = glyph_box.get(subA)
        boxB = glyph_box.get(subB)
        if not boxA or not boxB:
            refused.append({"contest": n, "why": "head box missing"})
            continue
        bb = [min(boxA[0], boxB[0]), min(boxA[1], boxB[1]),
              max(boxA[2], boxB[2]), max(boxA[3], boxB[3])]
        p = int(subA.split("/")[1])
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else Image.frombytes(
                      "L", (pm.width, pm.height), pm.samples).convert("RGB"))
            pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
        im, arr = pages[p]

        lines, sp = {}, {}
        for c in cand_keys:
            lines[c] = [float(y) for y in geo[c]["staff_lines"]]
            sp[c] = float(geo[c]["staff_spacing"])
        ok = {c: _frame_ok(arr, lines[c], sp[c]) for c in cand_keys}
        shifted = {c: [y + sp[c] / 2.0 for y in lines[c]] for c in cand_keys}
        broken = {c: _frame_ok(arr, shifted[c], sp[c]) for c in cand_keys}
        if not all(v2[0] for v2 in ok.values()) or any(
                v2[0] for v2 in broken.values()):
            refused.append({
                "contest": n, "why": "FRAME CONTROL FAILED",
                "contrast": {c: round(v2[1], 1) for c, v2 in ok.items()},
                "contrast_shifted": {c: round(v2[1], 1)
                                     for c, v2 in broken.items()}})
            continue

        # rungs to draw: credited "toward" rungs on EITHER side, plus every
        # "stands_on" (own line, excluded) rung named
        credited = []   # (bbox, staff, source)
        own_lines = set()
        for c in cand_keys:
            s = sides.get(c) or {}
            for rk, src in (s.get("sources") or {}).items():
                bx = rung_bbox(rk)
                if bx:
                    credited.append((bx, c, src, rk))
            so = s.get("stands_on")
            if so:
                own_lines.add(so)
        own_line_boxes = [(rung_bbox(k), k) for k in own_lines]
        own_line_boxes = [(b, k) for b, k in own_line_boxes if b]

        all_x = [bb[0], bb[2]] + [x for c in cand_keys for x in
                                   (min(lines[c]), max(lines[c]))]
        all_y = [bb[1], bb[3]] + [y for c in cand_keys for y in lines[c]]
        for bx, *_r in credited:
            all_x += [bx[0], bx[2]]
            all_y += [bx[1], bx[3]]
        for bx, _k in own_line_boxes:
            all_x += [bx[0], bx[2]]
            all_y += [bx[1], bx[3]]
        sp0 = sp[cand_keys[0]]
        cx0 = int(max(0, min(bb[0], bb[0]) - 8 * sp0))
        cx1 = int(min(im.width, max(bb[2], bb[2]) + 8 * sp0))
        cy0 = int(max(0, min(all_y) - 1.5 * sp0))
        cy1 = int(min(im.height, max(all_y) + 1.5 * sp0))
        Z = 3
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        big = big_font_cache.setdefault(
            round(sp0), ImageFont.load_default(size=max(26, int(sp0 * Z * 0.7))))
        for c, rgb, label in (
                (arm_winner, (0, 160, 60),
                 "GREEN - ARM (today) awards this note here"),
                (loser, (30, 90, 255),
                 "BLUE - other candidate staff")):
            top = (min(lines[c]) - cy0) * Z
            bot = (max(lines[c]) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=rgb + (55,))
            for ly in lines[c]:
                y = (ly - cy0) * Z
                od.line([(0, y), (crop.width, y)], fill=rgb + (220,), width=4)
            ty = max(0, top + (bot - top) / 2 - big.size / 2)
            tw = od.textlength(label, font=big)
            od.rectangle([26, ty - 4, 26 + tw + 12, ty + big.size + 6],
                         fill=(255, 255, 255, 230), outline=rgb + (255,),
                         width=3)
            od.text((32, ty), label, fill=rgb + (255,), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        dr = ImageDraw.Draw(crop)

        # the note, bracketed red
        bx0, by0 = (bb[0] - cx0) * Z, (bb[1] - cy0) * Z
        bx1, by1 = (bb[2] - cx0) * Z, (bb[3] - cy0) * Z
        arm_len = max(10, int((bx1 - bx0) * 0.45))
        for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=(220, 0, 0),
                    width=6)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=(220, 0, 0),
                    width=6)

        # credited rungs, solid magenta, labelled by source
        for bx, cstaff, src, rk in credited:
            rx0, ry0 = (bx[0] - cx0) * Z, (bx[1] - cy0) * Z
            rx1, ry1 = (bx[2] - cx0) * Z, (bx[3] - cy0) * Z
            dr.rectangle([rx0, ry0, rx1, ry1], outline=(220, 0, 220), width=5)
            lbl = f"CREDITED->{ 'ARM' if cstaff == arm_winner else 'other'} ({src})"
            dr.text((rx0, max(0, ry0 - 20)), lbl, fill=(180, 0, 180), font=font)

        # own-line (excluded) rungs, dashed grey
        for bx, rk in own_line_boxes:
            rx0, ry0 = (bx[0] - cx0) * Z, (bx[1] - cy0) * Z
            rx1, ry1 = (bx[2] - cx0) * Z, (bx[3] - cy0) * Z
            x = rx0
            while x < rx1:
                dr.line([(x, ry0), (min(x + 14, rx1), ry0)],
                        fill=(120, 120, 120), width=3)
                dr.line([(x, ry1), (min(x + 14, rx1), ry1)],
                        fill=(120, 120, 120), width=3)
                x += 28
            dr.text((rx0, ry1 + 2), "own line (excluded)",
                    fill=(90, 90, 90), font=font)

        # ruler off the ARM winner's outer line
        y = (min(lines[arm_winner]) - cy0) * Z
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (16 if k % 5 else 26, y)], fill=(0, 90, 200),
                        width=2)
            y += sp[arm_winner] * Z
            k += 1

        name = f"2.6c-reversal-{n:02d}.png"
        s_arm = sides.get(arm_winner) or {}
        s_lose = sides.get(loser) or {}
        title = [
            (f"{name}  contest #{n}  subjects {subA} / {subB}  pdf idx {p}",
             (0, 0, 0)),
            (f"BASE (pre-2.6c hard gate): {base_winner}   ARM (today, "
             f"2.6c/2.6d/2.6e): {arm_winner}  reason={v.reason}  "
             f"ledger.word={led.get('word')}", (80, 0, 120)),
            (f"{arm_winner} (GREEN): expected={s_arm.get('expected')} "
             f"found={s_arm.get('found')} toward={s_arm.get('toward')} "
             f"missing={s_arm.get('missing')} reach_sp="
             f"{s_arm.get('reach_spaces')}   {loser} (BLUE): expected="
             f"{s_lose.get('expected')} found={s_lose.get('found')} "
             f"toward={s_lose.get('toward')} reach_sp="
             f"{s_lose.get('reach_spaces')}", (0, 90, 0)),
            ("Q: UPPER / LOWER / not a note -- and are the drawn (MAGENTA) "
             "ledger lines real, reaching this head from the staff they "
             "are credited toward?", (0, 0, 0)),
        ]
        band = 22 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (t, col) in enumerate(title):
            cd.text((6, 4 + i * 22), t, fill=col, font=font)
        out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name,
            "subjects": [subA, subB],
            "page": p,
            "base_winner": base_winner,
            "arm_winner": arm_winner,
            "arm_reason": v.reason,
            "ledger_word": led.get("word"),
            "other_candidate": loser,
            "sides": sides,
            "credited_rungs": [{"bbox": [round(x, 1) for x in bx],
                                "toward": cstaff, "source": src, "key": rk}
                               for bx, cstaff, src, rk in credited],
            "own_line_rungs": [{"bbox": [round(x, 1) for x in bx], "key": rk}
                              for bx, rk in own_line_boxes],
            "head_page_box": [round(x, 1) for x in bb],
            "frame_contrast": {c: round(v2[1], 1) for c, v2 in ok.items()},
            "frame_contrast_shifted_half_space": {
                c: round(v2[1], 1) for c, v2 in broken.items()},
            "question": ("UPPER / LOWER / not a note -- and are the "
                        "MAGENTA-boxed credited ledger rungs real, "
                        "reaching this head?"),
            "VERDICT_none_yet": None,
        })

    print(f"crops {len(manifest)}  refused {len(refused)}")
    (OUT_DIR / "2.6c-reversal-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6c.3",
        "record": a.record, "pdf": a.pdf, "dpi": DPI,
        "n_contests": len(CONTESTS), "n_subjects": len(CONTESTS) * 2,
        "crops": manifest, "refused": refused}, indent=2))
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
