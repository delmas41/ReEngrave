"""ROADMAP 2.4a — 12 fresh print crops of REFUSED boxes, not in any existing
crop-pass manifest: 6 per plate, 600 dpi, corner brackets on the exact box,
frame control. For Sean to adjudicate; this job does not claim their accuracy.

⚠️ FRAME CONTROL FIRST, and it can fail (`omr-stem-crop-pass-2026-09`'s own
precedent): `Q.STAFF_LINES` rows for the target staff must be materially
darker than a half-space offset, or the render is not the frame the record's
boxes are filed in and nothing drawn on it is evidence.

⚠️ ONLY `clipped_fragment` and `too_narrow` boxes are cropped — the two rules
that SHIP. `unladdered` is measured and held back (see
`notehead_precision.py`); cropping its population is not this job's ask.

    python3 probe/crop_refused.py --record <litolff.record.json> \
        --measured out/litolff.json --label litolff --pdf <pdf> \
        --exclude-manifest ../../omr-stem-crop-pass-2026-09/out/crop-manifest-litolff.json \
        --n 6 --out-dir out/print
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record import Subject  # noqa: E402


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
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
    return (float(sum(off) / len(off) - sum(on) / len(on)) >= margin,
            float(sum(off) / len(off) - sum(on) / len(on)))


def load_manifest_subjects(paths):
    out = set()
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for t in d.get("tiles", []):
            if t.get("subject"):
                out.add(t["subject"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--measured", required=True,
                    help="measure.py's out/<label>.json")
    ap.add_argument("--label", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--exclude-manifest", nargs="*", default=[])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--frame-margin", type=float, default=8.0)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page

    measured = json.loads(Path(a.measured).read_text())
    refused = measured["refused_subjects"]        # subject -> reason
    excluded = load_manifest_subjects(a.exclude_manifest)

    shippable = {"too_narrow", "clipped_fragment"}
    candidates = [(s, r) for s, r in refused.items()
                 if r in shippable and s not in excluded]
    if not candidates:
        print("DEAD: no eligible refused/unmanifested subjects", file=sys.stderr)
        return 2
    # Mix reasons where possible, deterministic order (sorted by subject).
    by_reason: dict[str, list[str]] = {}
    for s, r in candidates:
        by_reason.setdefault(r, []).append(s)
    for r in by_reason:
        by_reason[r].sort()
    picked: list[tuple[str, str]] = []
    reasons_cycle = sorted(by_reason)
    i = 0
    while len(picked) < a.n and any(by_reason.values()):
        r = reasons_cycle[i % len(reasons_cycle)]
        if by_reason.get(r):
            picked.append((by_reason[r].pop(0), r))
        i += 1
        if i > 10000:
            break
    print(f"{a.label}: picked {len(picked)} of {len(candidates)} eligible "
         f"(excluded {len(excluded)} already-manifested subjects)",
         file=sys.stderr)

    rec = json.loads(Path(a.record).read_text())["record"]
    box_by_subject = {}
    staff_lines = {}   # staff subject key -> (line_ys, spacing)
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"] in dict(picked):
            box_by_subject[o["subject"]] = (o.get("detail") or {}).get(
                "bbox_page_px")
        if o["quantity"] == "staff_lines":
            staff_lines.setdefault(o["subject"], [None, None])[0] = o["value"]
        if o["quantity"] == "staff_spacing":
            staff_lines.setdefault(o["subject"], [None, None])[1] = o["value"]

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"label": a.label, "pdf": a.pdf, "dpi": a.dpi, "tiles": []}

    by_page: dict[int, list] = {}
    for subj, reason in picked:
        sub = Subject.from_key(subj)
        by_page.setdefault(sub.page, []).append((subj, reason, sub))

    for page, items in sorted(by_page.items()):
        print(f"rendering page {page} ...", file=sys.stderr)
        pi = render_page(a.pdf, page, dpi=a.dpi)
        arr = getattr(pi, "rgb", None)
        if arr is None:
            arr = getattr(pi, "binary")
        arr_np = np.asarray(arr)
        img = Image.fromarray(arr_np if arr_np.ndim == 3
                              else np.stack([arr_np] * 3, axis=-1))

        for subj, reason, sub in items:
            box = box_by_subject.get(subj)
            if not box:
                print(f"  SKIP {subj}: no page box", file=sys.stderr)
                continue
            staff_key = f"staff/{sub.page}/{sub.system}/{sub.staff}"
            line_ys, spacing = staff_lines.get(staff_key, (None, None))
            frame_ok, margin_val = (None, None)
            if line_ys and spacing:
                frame_ok, margin_val = _frame_ok(
                    arr_np, line_ys, spacing, margin=a.frame_margin)
            px0, py0, px1, py1 = box
            pad_x = 3.0 * (spacing or 40.0)
            pad_y = 5.0 * (spacing or 40.0)
            cx0, cy0 = max(0, int(px0 - pad_x)), max(0, int(py0 - pad_y))
            cx1 = min(img.width, int(px1 + pad_x))
            cy1 = min(img.height, int(py1 + pad_y))
            crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
            draw = ImageDraw.Draw(crop)
            bx0, by0 = px0 - cx0, py0 - cy0
            bx1, by1 = px1 - cx0, py1 - cy0
            L = max(6.0, 0.25 * (bx1 - bx0))
            # ⚠️ CORNER BRACKETS, not a box outline — the exact box's corners
            # only, so the ink inside it is not obscured.
            for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                   (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                draw.line([(x, y), (x + dx * L, y)], fill=(220, 20, 20), width=2)
                draw.line([(x, y), (x, y + dy * L)], fill=(220, 20, 20), width=2)
            tile_id = subj.replace("/", "-")
            fname = f"{a.label}-{tile_id}.png"
            crop.save(out_dir / fname)
            manifest["tiles"].append({
                "id": tile_id, "subject": subj, "reason": reason,
                "file": fname, "frame_ok": frame_ok,
                "frame_margin": margin_val,
                "box_page_px": box,
            })
            print(f"  {subj} [{reason}] frame_ok={frame_ok} "
                 f"margin={margin_val} -> {fname}", file=sys.stderr)

    (out_dir / f"crop-manifest-{a.label}.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
