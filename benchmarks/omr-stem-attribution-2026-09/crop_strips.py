#!/usr/bin/env python3
"""Render one FULL-WIDTH STAFF STRIP per pre-registered pair, for the print.

⚠️⚠️ A STRIP, NOT A TILE, AND IT IS AN INSTRUCTION RATHER THAN A PREFERENCE.
`docs/handoff-2026-09-18-three-lanes-and-the-print.md` §3: *"at tile
magnification the adjudicator read two heads WRONG and a wide strip corrected
both — a numeral and a dotted half note each read as a hollow head with no
stem. A crop centred on a head cannot tell you the head is a NUMERAL. Any
future crop pass here uses a full-width strip."* So every crop here is the
whole staff across the marked bar, and the head under question is marked in
the MARGIN rather than over the ink.

⚠️ THE MARK IS OUTSIDE THE MUSIC. Two ticks in the top and bottom margin bands
give the head's x, and nothing is drawn on the staff itself — an annotation
over the ink is an annotation over the evidence, and this pass exists
precisely because a box was in the wrong place.

⚠️ THE FRAME CONTROL CAN FAIL AND IS CHECKED PER STRIP. If the five staff
lines are not darker than the spaces beside them by a margin, the crop is not
the staff it claims to be — a wrong page, a wrong y, a wrong dpi — and the
strip is REFUSED rather than written. A crop pass whose frame is wrong
produces confident verdicts about the wrong ink.

⚠️ IDS ARE OPAQUE. The manifest maps id -> subject and stratum and is written
to a SEPARATE file, so the adjudication can be genuinely blind: the person
looking at the strips must not be able to see which stratum a strip was drawn
from, or the answer is in the question.

    python3 benchmarks/omr-stem-attribution-2026-09/crop_strips.py \
        --sample out/sample-litolff.json --record <shared record> \
        --pdf <pdf> --out-dir out/strips-litolff \
        --manifest out/manifest-litolff.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

#: How far above and below the staff the strip reaches, in staff spaces. ⚠️ A
#: stem is ~3.5 spaces and a ledger note can sit 4 above, so this is the reach
#: that shows a stroke's BOTH ENDS for any note on the staff — the one thing
#: the strip has to show for the question to be answerable at all.
PAD_Y_SPACES = 6.0
#: The margin band the tick marks live in, as a fraction of the strip height.
MARGIN_FRAC = 0.10
#: The frame control's floor, in grey levels between a staff line and the
#: space beside it. ⚠️ Inherited from `omr-stem-crop-pass-2026-09`, where it
#: passed at +133 to +229 on these same two plates.
FRAME_MARGIN = 40.0
#: One staff space, in output pixels. ⚠️ THE SIBLING PASS'S CONVENTION,
#: imported as a number rather than re-argued: at this plate's native 16 px per
#: staff space a strip is 186x256 and a stem cannot be traced by eye. The
#: resampling is NEAREST because the plates are `bpc: 1` and genuinely bitonal
#: -- an interpolating filter would invent grey that is not on the plate, and
#: this pass exists to look at ink.
PX_PER_SPACE = 100.0
#: The reach either side of the MARKED HEAD, in staff spaces, that the strip
#: guarantees whatever its bar's width. ⚠️ A stroke's far end can stand a
#: notehead's width away horizontally and several spaces vertically; what this
#: buys is the NEIGHBOURS, which is the whole question -- "does this stroke
#: belong to another note" cannot be answered without seeing the other notes.
CONTEXT_X_SPACES = 8.0


def _page_image(pdf, page, dpi):
    from tools.omr.preprocessing import render_page
    pi = render_page(pdf, page, dpi=dpi)
    for attr in ("rgb", "binary"):
        arr = getattr(pi, attr, None)
        if arr is not None:
            return arr
    raise SystemExit("render_page gave no image array -- schema changed")


def _frame_ok(a, line_ys, spacing, *, margin=FRAME_MARGIN):
    """Are the five staff lines actually darker than the spaces beside them?

    ⚠️⚠️ ASKED OF THE WHOLE PAGE ROW, NOT OF THE STRIP, AND THE FIRST VERSION
    GOT THIS WRONG AND REFUSED 38 OF 40 CROPS. The question the control exists
    to answer is *are these five y values the staff lines on this page* — a
    property of the page's geometry, which is what can be wrong (a wrong page,
    a wrong dpi, a deskew we did not apply). Measured inside a ONE-BAR-WIDE
    strip of dense orchestral music the test collapses for a reason that has
    nothing to do with the geometry: the spaces in that bar are FULL OF INK, so
    the line-minus-space contrast goes to zero or inverts. Litolff p2 staff 0
    reads **+12.2 in the bar and +69.7 across the page**, and its neighbours
    −25.6 / +100.9 and +19.7 / +89.7.

    ⚠️ The control was not RELAXED to make the crops pass — it was asked of the
    right raster. Refusing 38 of 40 was the control working; believing it about
    the geometry would have been the error.
    """
    h, w = a.shape[:2]
    g = a if a.ndim == 2 else a.mean(axis=2)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    half = max(1, int(round(spacing / 2.0)))
    on, off = [], []
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(g[y, x0:x1].mean())
        off.append((g[y - half, x0:x1].mean() + g[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    d = float(sum(off) / len(off) - sum(on) / len(on))
    return d >= margin, d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image

    sample = json.load(open(a.sample))
    rows = sample["rows"]
    print(f"{sample['label']}: {len(rows)} pre-registered pairs", flush=True)

    # ── the geometry each strip needs, off the RECORD ───────────────────────
    print("  reading staff geometry from the record...", flush=True)
    doc = json.load(open(a.record))
    lines_of, spacing_of, cellbox_of = {}, {}, {}
    for o in doc["record"]["observations"]:
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            try:
                spacing_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp and len(bp) == 4:
                cellbox_of.setdefault(
                    "/".join(o["subject"].split("/")[:5]).replace(
                        "glyph/", "cell/", 1), []).append([float(x)
                                                           for x in bp])

    pages = sorted({int(r["subject"].split("/")[1]) for r in rows})
    imgs = {p: _page_image(a.pdf, p, a.dpi) for p in pages}
    print(f"  rendered pages {pages}", flush=True)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles, refused = [], []
    for r in rows:
        parts = r["subject"].split("/")        # glyph/page/sys/staff/cell/i
        page, sysx, stx, cellx = (int(parts[1]), int(parts[2]),
                                  int(parts[3]), int(parts[4]))
        staff_key = f"staff/{page}/{sysx}/{stx}"
        cell_key = f"cell/{page}/{sysx}/{stx}/{cellx}"
        lines = lines_of.get(staff_key)
        sp = spacing_of.get(staff_key)
        if not lines or not sp:
            refused.append({"subject": r["subject"], "why": "no staff geometry"})
            continue
        boxes = cellbox_of.get(cell_key) or []
        if not boxes:
            refused.append({"subject": r["subject"], "why": "no page boxes"})
            continue
        # the BAR's own x-extent, from every page box gathered in that cell
        bx0 = min(b[0] for b in boxes)
        bx1 = max(b[2] for b in boxes)
        # ⚠️ THE BAR, WIDENED, AND THE MARKED HEAD KEPT AWAY FROM THE EDGE.
        # The bar is the musical unit -- its barlines are what let a reader
        # place the strip on the page by eye -- but on a dense orchestral
        # plate a bar can be narrow enough that the marked head lands against
        # the frame, and a stroke whose other end is outside the crop cannot
        # be adjudicated at all. So the window is the bar plus a margin, UNION
        # a fixed reach either side of the head itself.
        hp_pre = r.get("head_page_box")
        hcx = ((hp_pre[0] + hp_pre[2]) / 2.0) if hp_pre else (bx0 + bx1) / 2.0
        pad_x = 4.0 * sp
        x0 = max(0, int(min(bx0 - pad_x, hcx - CONTEXT_X_SPACES * sp)))
        x1 = int(max(bx1 + pad_x, hcx + CONTEXT_X_SPACES * sp))
        y0 = max(0, int(min(lines) - PAD_Y_SPACES * sp))
        y1 = int(max(lines) + PAD_Y_SPACES * sp)

        arr = imgs[page]
        crop = arr[y0:y1, x0:x1]
        if crop.size == 0:
            refused.append({"subject": r["subject"], "why": "empty crop"})
            continue
        # ⚠️ THE FULL PAGE, not `crop` — see `_frame_ok`'s own docstring.
        ok, d = _frame_ok(arr, lines, sp)
        if not ok:
            refused.append({"subject": r["subject"],
                            "why": f"frame control failed (delta {d:.1f})"})
            continue

        img = (crop if crop.ndim == 3
               else np.stack([crop] * 3, axis=-1)).astype(np.uint8)
        scale = PX_PER_SPACE / sp
        pil = Image.fromarray(img).resize(
            (max(1, int(img.shape[1] * scale)),
             max(1, int(img.shape[0] * scale))), Image.NEAREST)
        img = np.asarray(pil).copy()
        h, w = img.shape[:2]
        # the two margin ticks, in the OUTER band only
        hp = r.get("head_page_box")
        if not hp:
            refused.append({"subject": r["subject"],
                            "why": "the head row carries no page box"})
            continue
        # ⚠️ PAGE pixels, CORNERS -- never `head_box`, which is canonical-cell
        # and put every mark outside its own bar on this lane's first run.
        hx = int(((hp[0] + hp[2]) / 2.0 - x0) * (PX_PER_SPACE / sp))
        band = max(2, int(h * MARGIN_FRAC))
        if 0 <= hx < w:
            tw = max(2, int(PX_PER_SPACE * 0.06))
            img[0:band, max(0, hx - tw):hx + tw] = [255, 0, 0]
            img[h - band:h, max(0, hx - tw):hx + tw] = [255, 0, 0]
        else:
            refused.append({"subject": r["subject"],
                            "why": "the marked head is outside its own bar"})
            continue

        tid = hashlib.sha1(
            f"{sample['seed']}|{r['subject']}|{r['stem']}".encode()
        ).hexdigest()[:10]
        Image.fromarray(img).save(out_dir / f"{tid}.png")
        tiles.append({"id": tid, "subject": r["subject"], "stem": r["stem"],
                      "stratum": r["stratum"], "frame_delta": round(d, 1)})

    man = {"label": sample["label"], "seed": sample["seed"],
           "question": sample["question"],
           "verdicts_allowed": sample["verdicts_allowed"],
           "dpi": a.dpi, "pad_y_spaces": PAD_Y_SPACES,
           "px_per_space": PX_PER_SPACE, "resample": "NEAREST",
           "written": len(tiles), "refused": refused, "tiles": tiles}
    Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
    json.dump(man, open(a.manifest, "w"), indent=1)

    print(f"  wrote {len(tiles)} strips, refused {len(refused)}")
    for x in refused[:5]:
        print(f"    refused {x['subject']}: {x['why']}")
    if not tiles:
        print("⚠️ DEAD: no strip was written.", file=sys.stderr)
        return 2
    print(f"  manifest -> {a.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
