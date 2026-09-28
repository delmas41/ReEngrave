"""ROADMAP 2.7 — the gate's print check: one crop per DECIDED accidental owner
in the declared window, plus abstained controls, UNLABELLED which is which.

The window is the cleanup count's own declared sample (`benchmarks/
omr-cleanup-count-2026-09/counts/README.md`): Litolff pdf index 3, the four
string staves (staff 7 Violino I, 8 Violino II, 9 Viola, 10 Violoncello e
Basso) of bars 49-56 — system 0, cells 0-7 (system 0 has 16 cells = bars
49-64, verified off `Q.CELL_BOX`; `works.json`'s window row prints 49 over
system 1 and 65 over system 2).

⚠️ REUSES `omr-infer-duration-print-2026-09/probe/crop_inferred.py`'s frame
control, IMPORTED by path and not copied: the staff's own `Q.STAFF_LINES`
must be materially darker than a half-space off them on the render, or the
render is not the record's raster and the crop is REFUSED, not cropped with a
caveat. `--break-frame` shifts the lines by half a space to watch it fail.

⚠️ EACH CROP NAMES THE STAFF THE RECORD FILED THE GLYPH ON AND DRAWS THAT
STAFF'S FIVE LINES (Sean, 2026-09-23: a crop between two staves commits to
neither). The accidental glyph gets RED corner brackets, the notehead in
question BLUE ones, both on the EXACT boxes (`Q.GLYPH_BOX`'s own
`bbox_page_px`, the gather's 600-dpi page frame), never a margin tick.

⚠️ BLIND. The caption gives the glyph's detector class and the head's staff
letter-and-octave BEFORE any accidental (`Q.PITCH` off position + clef — the
same kind of fact for a decided owner and a control), never the decision or
the written sound. The crop files are numbered in a shuffled order; the key is
in the manifest (`reading`), which is for AFTER the adjudication. For a
control the blue head is the one the decision could not choose against
(`ambiguous_height`: its best candidate) or the nearest head to the glyph's
right in the bar (`no_candidate`).

    python3 benchmarks/omr-accidental-2026-09/probe/crop_accidentals.py \\
        --arm <arm.record.json> --pdf <litolff.pdf> --out-dir <...>/out/print
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402

_CI = ROOT / "benchmarks/omr-infer-duration-print-2026-09/probe/crop_inferred.py"
_spec = importlib.util.spec_from_file_location("crop_inferred", _CI)
crop_inferred = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crop_inferred)

STAFF_NAMES = {7: "Violino I", 8: "Violino II", 9: "Viola",
               10: "Violoncello e Basso"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--staves", default="7,8,9,10")
    ap.add_argument("--cells", default="0-7")
    ap.add_argument("--first-bar", type=int, default=49)
    ap.add_argument("--controls", type=int, default=3)
    ap.add_argument("--seed", type=int, default=27)
    ap.add_argument("--break-frame", action="store_true")
    ap.add_argument("--fate", default=None,
                    help="owner_fate.py --out JSON: adds, to the manifest KEY "
                         "only, whether the owned head reached the file")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=20)

    staves = {int(x) for x in a.staves.split(",")}
    c0, c1 = (int(x) for x in a.cells.split("-"))

    d = load_record(a.arm)
    rec = d["record"]
    obs = {}
    for o in rec["observations"]:
        if o["quantity"] in ("glyph_box", "staff_lines", "staff_spacing",
                             "notehead_staff_position"):
            obs[(o["quantity"], o["subject"])] = o
    superseded = {v.get("supersedes") for v in rec["verdicts"]
                  if v.get("supersedes")}
    standing = {}
    for v in rec["verdicts"]:
        if v["id"] in superseded:
            continue
        standing[(v["quantity"], v["subject"])] = v

    def in_window(sub):
        _, p, s, st, c, _gi = sub.split("/")
        return (int(p) == a.page and int(s) == a.system
                and int(st) in staves and c0 <= int(c) <= c1)

    owners = sorted((v for (q, s), v in standing.items()
                     if q == "accidental_owner" and in_window(s)),
                    key=lambda v: v["subject"])
    decided = [v for v in owners if v["outcome"] == "decided"]
    abstained = [v for v in owners if v["outcome"] != "decided"]
    print(f"window: {len(owners)} accidental_owner verdicts, "
          f"{len(decided)} decided, {len(abstained)} abstained "
          f"{sorted({v['reason'] for v in abstained})}")

    def nearest_right_head(acc_sub):
        cell = acc_sub.rsplit("/", 1)[0]
        ab = obs[("glyph_box", acc_sub)]["detail"]["bbox_page_px"]
        best = None
        for (q, s), o in obs.items():
            if q != "glyph_box" or not s.startswith(cell + "/"):
                continue
            if (o.get("detail") or {}).get("category") != "notehead":
                continue
            hb = o["detail"].get("bbox_page_px")
            if not hb or hb[2] < ab[2]:
                continue
            dx = max(0.0, hb[0] - ab[2])
            dy = abs((hb[1] + hb[3]) / 2 - (ab[1] + ab[3]) / 2)
            key = (dx + dy, s)
            if best is None or key < best:
                best = key
        return best[1] if best else None

    # controls: ambiguous first (a real contest), then no_candidate cases that
    # still have a head to their right, so every crop carries a blue bracket
    rng = random.Random(a.seed)
    pool_amb = [v for v in abstained if v["reason"] == "ambiguous_height"]
    pool_nc = [v for v in abstained if v["reason"] == "no_candidate"
               and nearest_right_head(v["subject"])]
    rng.shuffle(pool_amb)
    rng.shuffle(pool_nc)
    controls = (pool_amb + pool_nc)[:a.controls]

    jobs = []
    for v in decided:
        jobs.append(("decided", v, v["value"]))
    for v in controls:
        if v["reason"] == "ambiguous_height":
            head = (v.get("detail") or {}).get("candidates", [None])[0]
        else:
            head = nearest_right_head(v["subject"])
        jobs.append(("control", v, head))
    rng.shuffle(jobs)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pm = doc[a.page].get_pixmap(dpi=a.dpi)
    im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples) \
        if pm.n >= 3 else Image.frombytes(
            "L", (pm.width, pm.height), pm.samples).convert("RGB")
    arr = np.asarray(im.convert("L"), dtype=float)

    head_fate = (json.loads(Path(a.fate).read_text())["head_fate"]
                 if a.fate else {})
    manifest, refused = [], []
    for n, (kind, v, head) in enumerate(jobs, 1):
        acc = v["subject"]
        _, p, s, st, c, gi = acc.split("/")
        staff = f"staff/{p}/{s}/{st}"
        lines = obs[("staff_lines", staff)]["value"]
        spacing = float(obs[("staff_spacing", staff)]["value"])
        if a.break_frame:
            lines = [y + spacing / 2.0 for y in lines]
        ok, contrast = crop_inferred._frame_ok(arr, lines, spacing)
        if not ok:
            refused.append({"subject": acc, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue
        ab = obs[("glyph_box", acc)]["detail"]["bbox_page_px"]
        hb = (obs[("glyph_box", head)]["detail"]["bbox_page_px"]
              if head and ("glyph_box", head) in obs else None)
        xs = [ab[0], ab[2]] + ([hb[0], hb[2]] if hb else [])
        ys = [ab[1], ab[3], lines[0], lines[-1]] + ([hb[1], hb[3]] if hb else [])
        pad = 8.0 * spacing
        cx0, cx1 = int(max(0, min(xs) - pad)), int(min(im.width, max(xs) + pad))
        cy0 = int(max(0, min(ys) - 2.5 * spacing))
        cy1 = int(min(im.height, max(ys) + 2.5 * spacing))
        Z = 4
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)
        for ly in lines:
            y = (ly - cy0) * Z
            dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)
        step = spacing * Z
        y, k = (lines[0] - cy0) * Z, 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 22, y)],
                        fill=(0, 90, 200), width=1)
            y += step
            k += 1

        def brackets(box, colour):
            bx0, by0 = (box[0] - cx0) * Z, (box[1] - cy0) * Z
            bx1, by1 = (box[2] - cx0) * Z, (box[3] - cy0) * Z
            arm = max(6, int((bx1 - bx0) * 0.35))
            for (x, yy, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                    (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                dr.line([(x, yy), (x + dx * arm, yy)], fill=colour, width=3)
                dr.line([(x, yy), (x, yy + dy * arm)], fill=colour, width=3)

        brackets(ab, (220, 0, 0))
        if hb:
            brackets(hb, (0, 60, 230))

        cls = obs[("glyph_box", acc)]["value"][0]
        pitch_v = standing.get(("pitch", head)) if head else None
        # ⚠️ the letter and octave BEFORE any accidental: the restated pitch
        # is written by `restate_pitch`/`move_glyph` and carries no `#`/`b`
        # (alterations live on `Q.ACCIDENTAL`), so it reads the same for a
        # decided owner and a control.
        staff_pitch = pitch_v["value"] if pitch_v else "no pitch"
        bar = a.first_bar + int(c)
        band_h = 84
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        name = f"acc-{n:02d}"
        cd.text((6, 4), f"{name}   page idx {p}, system {int(s) + 1}, "
                        f"bar {bar}", fill=(0, 0, 0), font=font)
        cd.text((6, 28), f"FILED ON staff {st} = {STAFF_NAMES.get(int(st), '?')}"
                         f"   (its 5 lines are drawn GREEN)", fill=(0, 120, 45),
                font=font)
        cd.text((6, 54), f"RED = the glyph, detector class {cls}   |   "
                         f"BLUE = the notehead, staff pitch {staff_pitch} "
                         f"(before any accidental)", fill=(140, 0, 0), font=font)
        out_im.save(out_dir / f"{name}.png")
        acc_v = standing.get(("accidental", head)) if head else None
        manifest.append({
            "file": f"{name}.png",
            "question": ("Does the RED glyph alter the BLUE notehead, and is "
                         "the glyph the class the caption names?"),
            "accidental_glyph": acc, "notehead": head,
            "staff": int(st), "staff_name": STAFF_NAMES.get(int(st)),
            "bar": bar, "detector_class": cls,
            "staff_pitch_before_accidental": staff_pitch,
            "glyph_page_box": [round(x, 1) for x in ab],
            "head_page_box": [round(x, 1) for x in hb] if hb else None,
            "frame_contrast": round(contrast, 2),
            # ⚠️ THE KEY. Read only after adjudicating the crops.
            "reading": {
                "kind": kind, "outcome": v["outcome"], "reason": v["reason"],
                "alteration": (v.get("detail") or {}).get("alteration"),
                "written_alteration_on_head": (acc_v or {}).get("value"),
                "written_by": (acc_v or {}).get("decider"),
                "printed_flag": ((acc_v or {}).get("detail") or {})
                .get("printed"),
                "dx_spaces": (v.get("detail") or {}).get("dx_spaces"),
                "dy_positions": (v.get("detail") or {}).get("dy_positions"),
                "head_fate_in_file": (head_fate.get(head)
                                      if kind == "decided" else None),
            },
            "VERDICT_none_yet": None,
        })
    Path(out_dir / "crop-manifest.json").write_text(json.dumps({
        "window": {"page": a.page, "system": a.system,
                   "staves": sorted(staves), "cells": [c0, c1],
                   "bars": [a.first_bar + c0, a.first_bar + c1]},
        "owners_in_window": len(owners), "decided": len(decided),
        "abstained_by_reason": {r: sum(1 for v in abstained if v["reason"] == r)
                                for r in sorted({v["reason"] for v in abstained})},
        "controls": len(controls), "seed": a.seed, "dpi": a.dpi,
        "arm_record": a.arm,
        "crops": manifest, "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops ({len(decided)} decided + "
          f"{len(controls)} controls), refused {len(refused)}")
    for r in refused[:5]:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
