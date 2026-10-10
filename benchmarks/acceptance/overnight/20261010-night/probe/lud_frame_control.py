#!/usr/bin/env python3
"""lud_frame_control: do the record's page-pixel boxes sit on the rendered print?

Three controls, each with a version that MUST fail:

  1. staff lines (the frame control readout.html uses): mean darkness ON the
     five line rows minus mean darkness half a space off them. Positive = the
     lines land on ink. The same number with every line moved half a space
     must collapse to ~0 or below.
  2. clef boxes (a box we KNOW is a clef): share of dark pixels inside the
     box, against the same box moved 1.5 box-widths to the right. True boxes
     must hold far more ink than the moved ones.
  3. the note boxes the images draw: same share, against the box moved
     1.5 box-widths to the right.

Also draws one control crop: the leftmost clef of the system, its box in
green and the moved box in red.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lud_bars  # noqa: E402
from lud_render import font  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402


def dark(arr):
    g = arr.mean(axis=2) if arr.ndim == 3 else arr
    return (g < 128).astype(np.float32)


def share(D, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    H, W = D.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return float(D[y0:y1, x0:x1].mean())


def staff_contrast(D, staves, page, shift=0.0):
    on, off = [], []
    for k, v in staves.items():
        m = re.match(r"^staff/(\d+)/", k)
        if not m or int(m.group(1)) != page or not v["ext"]:
            continue
        ys = v["ys"]
        sp = (ys[-1] - ys[0]) / (len(ys) - 1)
        x0, x1 = int(max(0, v["ext"][0])), int(min(D.shape[1], v["ext"][1]))
        for y in ys:
            for yy, bucket in ((y + shift * sp, on), (y + shift * sp + sp / 2, off)):
                r = int(round(yy))
                if 0 <= r < D.shape[0]:
                    bucket.append(float(D[r, x0:x1].mean()))
    return float(np.mean(on) - np.mean(off)) if on and off else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--extract", required=True)
    ap.add_argument("--systems", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    ex = json.load(open(a.extract))
    diff = json.load(open(lud_bars.COMPARE / f"{a.doc}-first-two-stages.json"))
    changed = {}
    for p in diff["changed_pairs"]:
        if p["family"] == "note" and tuple(p["status"]) in (("kept", "narrowed"), ("narrowed", "kept")):
            changed[p["b"]] = p
    # GATHER boxes identical between the nights: every note pair matched with the same subject
    notes = [p for p in diff["changed_pairs"] if p["family"] == "note"]
    same = sum(1 for p in notes if p["a"] == p["b"])
    ious = [p["iou"] for p in notes]
    print(f"[{a.doc}] diff note pairs: {len(notes)}; a-subject == b-subject on {same}; min IoU {min(ious):.3f}")
    lines = []
    for spec in a.systems.split(","):
        page, sysi = (int(x) for x in spec.split("/"))
        img = render_page(ex["prov"]["pdf"], page, dpi=ex["prov"]["dpi"]).rgb
        D = dark(img)
        c0 = staff_contrast(D, ex["staves"], page)
        c1 = staff_contrast(D, ex["staves"], page, shift=0.5)
        # clefs on this page
        cl_true, cl_moved, n_gt = [], [], 0
        for k, b in ex["boxes"].items():
            m = re.match(r"^glyph/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$", k)
            if not m or int(m.group(1)) != page or not b[0].lower().startswith("clef"):
                continue
            box = b[1:5]
            w = box[2] - box[0]
            t = share(D, box)
            mv = share(D, [box[0] + 1.5 * w, box[1], box[2] + 1.5 * w, box[3]])
            if t is None or mv is None:
                continue
            cl_true.append(t)
            cl_moved.append(mv)
            n_gt += t > mv
        nt, nm, ngt2 = [], [], 0
        for k, p in changed.items():
            m = re.match(r"^glyph/(\d+)/(\d+)/", k)
            if not m or (int(m.group(1)), int(m.group(2))) != (page, sysi) or k not in ex["boxes"]:
                continue
            box = ex["boxes"][k][1:5]
            w = box[2] - box[0]
            t = share(D, box)
            mv = share(D, [box[0] + 1.5 * w, box[1], box[2] + 1.5 * w, box[3]])
            if t is None or mv is None:
                continue
            nt.append(t)
            nm.append(mv)
            ngt2 += t > mv
        lines.append(f"[{a.doc}] page {page} (system {sysi}): staff-line contrast {c0:.3f} on the lines; "
                     f"{c1:.3f} with every line moved half a space (control must collapse)")
        if cl_true:
            lines.append(f"    clef boxes on the page: {len(cl_true)}; median dark share inside {np.median(cl_true):.2f} vs "
                         f"{np.median(cl_moved):.2f} moved 1.5 widths right; true > moved on {n_gt} of {len(cl_true)}")
        if nt:
            lines.append(f"    drawn note boxes on the system: {len(nt)}; median dark share inside {np.median(nt):.2f} vs "
                         f"{np.median(nm):.2f} moved 1.5 widths right; true > moved on {ngt2} of {len(nt)}")
        # the control crop: the leftmost clef of this system
        cands = []
        for k, b in ex["boxes"].items():
            m = re.match(r"^glyph/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$", k)
            if m and (int(m.group(1)), int(m.group(2))) == (page, sysi) and b[0].lower().startswith("clef"):
                cands.append((b[1], k, b))
        if cands:
            _, k, b = sorted(cands)[0]
            box = b[1:5]
            sp = float(np.median([(v["ys"][-1] - v["ys"][0]) / 4 for kk, v in ex["staves"].items()
                                  if kk.startswith(f"staff/{page}/{sysi}/")]))
            sc = 3 if sp < 20 else 2
            x0, y0, x1, y1 = box[0] - 4 * sp, box[1] - 3 * sp, box[2] + 16 * sp, box[3] + 3 * sp
            crop = Image.fromarray(img[int(y0):int(y1), int(x0):int(x1)]).resize(
                (int((x1 - x0) * sc), int((y1 - y0) * sc)), Image.BICUBIC)
            d = ImageDraw.Draw(crop)
            w = box[2] - box[0]
            d.rectangle([(box[0] - x0) * sc, (box[1] - y0) * sc, (box[2] - x0) * sc, (box[3] - y0) * sc],
                        outline=(0, 160, 60), width=4)
            d.rectangle([(box[0] + 1.5 * w - x0) * sc, (box[1] - y0) * sc, (box[2] + 1.5 * w - x0) * sc, (box[3] - y0) * sc],
                        outline=(230, 0, 0), width=4)
            f = font(sp * sc * 0.75)
            d.text((6, 6), f"{k}: {b[0]}", fill=(0, 140, 50), font=f, stroke_width=2, stroke_fill=(255, 255, 255))
            d.text((6, 6 + sp * sc * 1.1), "green: the record box (a clef).  red: same box moved right, must NOT be on the clef.",
                   fill=(200, 0, 0), font=f, stroke_width=2, stroke_fill=(255, 255, 255))
            out = Path(a.out_dir) / f"control_clef_{a.tag}_p{page}_s{sysi}.png"
            crop.save(out, optimize=True)
            lines.append(f"    control crop: {out}  (clef {k}, dark share {share(D, box):.2f} in the box, "
                         f"{share(D, [box[0] + 1.5 * w, box[1], box[2] + 1.5 * w, box[3]]):.2f} moved)")
    txt = "\n".join(lines)
    print(txt)
    (Path(a.out_dir) / f"frame_control_{a.tag}.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
