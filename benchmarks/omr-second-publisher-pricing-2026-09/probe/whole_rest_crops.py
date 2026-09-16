"""LOOK AT THE INK — every glyph `OMR_WHOLE_REST_INK` would DELETE, cropped.

This repo's own record is that no count settled a question of this shape and a
single crop repeatedly did, and the rule under test REMOVES MUSIC FROM A FILE.
So the reach probe only says where to point this.

⚠️⚠️ IT OPENS WITH A FRAME CONTROL THAT CAN FAIL, and that is the whole reason
this is a separate script rather than a `--pdf` flag on the Litolff one. A crop
is only evidence if the rendered page is the frame `Q.GLYPH_BOX.detail.
bbox_page_px` is filed in. A wrong DPI, a different rasteriser or a rotated page
moves every box by the same amount and the result LOOKS like a reading fault —
the `Q.ONSET_COLUMN` frame error, which this project has now paid for three
times, once inside a measuring instrument. So before any crop is written, each
page's `Q.STAFF_LINES` rows are checked against the ink actually under them: a
staff line is a long dark run, so the row at a claimed line must be far darker
than the row a half space off it. `--require-frame` (the default) ABORTS when it
is not, rather than writing 12 crops of the wrong place.

What is drawn on each crop:
  * this staff's five lines, from `Q.STAFF_LINES`               (blue)
  * a tick at staff step 5.5, where an engraver MUST hang a
    whole rest -- `WHOLE_REST_STEP`, imported                   (green)
  * the suspect's own detection box                             (red)
  * every other detection box filed in the same bar             (dim green)
  * the NEIGHBOUR that vouched for it, where one did            (orange)

⚠️ The neighbour is drawn because on this document it is the witness that fires,
and a reader cannot adjudicate "another bar of this staff has a whole rest at
the same height" without seeing that bar.

    python3 whole_rest_crops.py --cache C --rows out/fires.json --out-dir D
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import rhythm as R  # noqa: E402

PDF_REL = ("editions/brahms/symphony-1-op68/"
           "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")


def _default_pdf():
    """⚠️ `library/` is GITIGNORED, so a git WORKTREE has none of its own.
    `library_root()` exists precisely to resolve to the MAIN checkout from
    inside one — using it rather than a path relative to this file is what lets
    this probe run in the worktree the record was never copied into."""
    from tools.library.score_library import library_root
    return str(library_root() / PDF_REL)


def _page_image(pdf, page, dpi):
    from tools.omr.preprocessing import render_page
    pi = render_page(pdf, page, dpi=dpi)
    # ⚠️ `rgb` first: the BINARY image is what the detector saw, but a human
    # adjudicating ink wants the grey the binariser threw away -- the question
    # is whether a mark is a filled BAR or a filled OVAL, and binarisation is
    # precisely the step that can turn one into the other.
    for attr in ("rgb", "binary"):
        arr = getattr(pi, attr, None)
        if arr is not None:
            return arr
    raise SystemExit("render_page gave no image array -- schema changed")


def _frame_ok(arr, line_ys, spacing, *, margin):
    """Is the ink where `Q.STAFF_LINES` says it is?

    A staff line is a long dark run. Sample the claimed line row and the row a
    HALF SPACE off it across the staff's own width; the line must be materially
    darker. Returns (ok, contrast) where contrast is mean(off) - mean(on) in
    grey levels -- positive means the claimed row is darker, i.e. correct.
    """
    import numpy as np
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    contrast = float(sum(off) / len(off) - sum(on) / len(on))
    return contrast >= margin, contrast


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pdf", default=None)
    # ⚠️ 600 is the STAGED GATHER's own default (`staged/__main__.py --dpi`),
    # and the recipe that made this record passed no `--dpi`. It is not a
    # choice made here; changing it invalidates every box.
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--pad-spaces", type=float, default=7.0)
    ap.add_argument("--target-px", type=float, default=300.0)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--frame-margin", type=float, default=8.0,
                    help="grey levels the claimed staff row must be darker by")
    ap.add_argument("--no-require-frame", action="store_true",
                    help="write crops even if the frame control FAILS "
                         "(for diagnosing the failure, never for adjudicating)")
    a = ap.parse_args()
    if a.pdf is None:
        a.pdf = _default_pdf()
    if not Path(a.pdf).is_file():
        print(f"NO PDF AT {a.pdf} — this probe renders the page the record was "
              "gathered from and cannot substitute anything for it.",
              file=sys.stderr)
        return 2
    print(f"pdf   {a.pdf}\ndpi   {a.dpi}  (the staged gather's own default)")

    import numpy as np
    from PIL import Image, ImageDraw

    cache = json.load(open(a.cache))
    boxes, lines, spacing = {}, {}, {}
    for o in cache["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                boxes[s] = pb
        elif q == "staff_lines":
            lines[s] = o["value"]
        elif q == "staff_spacing":
            spacing[s] = o["value"]

    rows = json.load(open(a.rows))
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        print("NO ROWS TO CROP — dead instrument", file=sys.stderr)
        return 2

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_page = {}
    for r in rows:
        by_page.setdefault(r["where"]["page"], []).append(r)

    made, frame_report = 0, []
    for page, group in sorted(by_page.items()):
        arr = np.asarray(_page_image(a.pdf, page, a.dpi))
        base = Image.fromarray(arr).convert("RGB")

        # ── THE FRAME CONTROL, before a single crop of this page ───────────
        w = group[0]["where"]
        skey = "staff/%d/%d/%d" % (page, w["system"], w["staff"])
        ok, contrast = _frame_ok(arr, lines[skey], spacing[skey],
                                 margin=a.frame_margin)
        frame_report.append({"page": page, "staff": skey, "ok": ok,
                             "contrast": round(contrast, 2)})
        print(f"FRAME page {page} via {skey}: "
              f"claimed staff rows are {contrast:+.1f} grey levels darker "
              f"than a half space off -> {'OK' if ok else 'FAILED'}")
        if not ok and not a.no_require_frame:
            print("FRAME CONTROL FAILED: the render is not the frame the "
                  "boxes are filed in, so every crop would be of the wrong "
                  "place. Refusing to write crops that would be adjudicated.",
                  file=sys.stderr)
            return 2

        for r in group:
            w = r["where"]
            skey = "staff/%d/%d/%d" % (page, w["system"], w["staff"])
            ly, sp = lines.get(skey), spacing.get(skey)
            if not ly or not sp:
                continue
            pad = a.pad_spaces * sp
            pre = "glyph/%d/%d/%d/%d/" % (page, w["system"], w["staff"],
                                          w["cell"])
            here = {s: b for s, b in boxes.items() if s.startswith(pre)}
            bb = boxes[r["subject"]]
            xs = [bb[0], bb[2]] + [v for b in here.values() for v in (b[0], b[2])]
            x0, x1 = min(xs) - pad, max(xs) + pad
            # ⚠️ The crop must contain the SUSPECT, which on this document is
            # often far OUTSIDE the staff -- so the y window is the union of
            # the staff and the box, never the staff alone.
            y0 = min(min(ly), bb[1]) - pad
            y1 = max(max(ly), bb[3]) + pad
            crop = base.crop((int(x0), int(y0), int(x1), int(y1)))
            scale = max(1, int(round(a.target_px / max(1.0, (y1 - y0)))))
            crop = crop.resize((crop.width * scale, crop.height * scale),
                               Image.NEAREST)
            d = ImageDraw.Draw(crop)
            X = lambda v: (v - x0) * scale          # noqa: E731
            Y = lambda v: (v - y0) * scale          # noqa: E731

            for y in ly:
                d.line([(0, Y(y)), (crop.width, Y(y))], fill=(120, 170, 255),
                       width=1)
            rest_y = max(ly) - R.WHOLE_REST_STEP * (sp / 2.0)
            d.line([(0, Y(rest_y)), (crop.width, Y(rest_y))],
                   fill=(0, 190, 0), width=1)
            for s, b in here.items():
                if s == r["subject"]:
                    continue
                d.rectangle([X(b[0]), Y(b[1]), X(b[2]), Y(b[3])],
                            outline=(0, 160, 0), width=1)
            d.rectangle([X(bb[0]), Y(bb[1]), X(bb[2]), Y(bb[3])],
                        outline=(255, 0, 0), width=3)
            name = (f"p{page}s{w['system']}st{w['staff']}c{w['cell']}"
                    f"g{w['glyph']}-{r.get('witness') or 'na'}"
                    f"-h{r['height_spaces']:.2f}-step{r['staff_step']:+.1f}"
                    f".png")
            crop.save(out / name)
            made += 1
            print(f"  {name}  cls={r['cls']} conf={(r['conf'] or 0):.2f} "
                  f"glyphs_in_bar={len(here)}")

    json.dump(frame_report, open(out / "frame-control.json", "w"), indent=1)
    print(f"\n{made} crops -> {out}")
    return 0 if made else 2


if __name__ == "__main__":
    raise SystemExit(main())
