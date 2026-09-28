"""ROADMAP 2.15: crops of refused duplicate-rest boxes for Sean, both boxes
drawn, the staff drawn, `VERDICT_none_yet` sidecars. Reads each record ONCE
(record_io.load_record -- geometry and the specific glyph boxes named by
`r215_price.py`'s pricing output, nothing else), renders straight off the
PDF -- no detector, no re-gather, no re-adjudication.

    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/r215_crops.py \
        --pricing-dir <dir with r215-pricing-<label>.json> \
        --record litolff=<path> --pdf litolff=<path> \
        --record brahms=<path> --pdf brahms=<path> \
        --out-dir out/print/r215-<date>

Picks up to 4 examples per document (the ROADMAP-named example first when
present, then a mix of the two refusal kinds -- collapse and disagree).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import record_io  # noqa: E402

NAMED_EXAMPLE_PREFIX = "glyph/2/1/0/7/"  # the ROADMAP 2.15 example (Brahms)


def cell_key_of(subject: str) -> str:
    parts = subject.split("/")
    return "cell/" + "/".join(parts[1:5])


def staff_key_of(subject: str) -> str:
    parts = subject.split("/")
    return "staff/" + "/".join(parts[1:4])


def pick_examples(pricing_path: Path, n: int = 4):
    d = json.loads(pricing_path.read_text())
    changed = d["changed"]
    collapse = [c for c in changed if "duplicate_of" in (c["detail"] or {})]
    disagree = [c for c in changed
               if "duplicate_disagrees_with" in (c["detail"] or {})]
    named = [c for c in collapse if c["subject"].startswith(NAMED_EXAMPLE_PREFIX)]
    out = []
    if named:
        out.append(named[0])
        collapse = [c for c in collapse if c is not named[0]]
    half = max(1, n // 2)
    out.extend(collapse[:max(0, half - len(out))])
    out.extend(disagree[:n - len(out)])
    return out[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pricing-dir", required=True,
                    help="directory holding r215-pricing-<label>.json")
    ap.add_argument("--record", action="append", default=[],
                    metavar="label=path", help="repeatable")
    ap.add_argument("--pdf", action="append", default=[],
                    metavar="label=path", help="repeatable")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--per-doc", type=int, default=4)
    a = ap.parse_args()

    records = dict(kv.split("=", 1) for kv in a.record)
    pdfs = dict(kv.split("=", 1) for kv in a.pdf)
    pricing_dir = Path(a.pricing_dir)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import numpy as np
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page

    manifest = []
    for label, record_path in records.items():
        pdf_path = pdfs.get(label)
        pricing_path = pricing_dir / f"r215-pricing-{label}.json"
        if pdf_path is None or not pricing_path.exists():
            print(f"[{label}] missing --pdf or {pricing_path}, skipping",
                 file=sys.stderr)
            continue
        examples = pick_examples(pricing_path, a.per_doc)
        if not examples:
            print(f"[{label}] no refused duplicates to crop", file=sys.stderr)
            continue
        print(f"[{label}] {len(examples)} examples", file=sys.stderr)

        print(f"[{label}] loading record ...", file=sys.stderr)
        data = record_io.load_record(record_path)
        rec = data.get("record", data)
        glyph_box_by_subject, glyph_box_by_obsid = {}, {}
        staff_lines, staff_spacing, cell_box = {}, {}, {}
        for o in rec["observations"]:
            q = o.get("quantity")
            if q == "glyph_box":
                glyph_box_by_subject[o["subject"]] = o
                glyph_box_by_obsid[o["id"]] = o
            elif q == "staff_lines":
                staff_lines[o["subject"]] = o["value"]
            elif q == "staff_spacing":
                staff_spacing[o["subject"]] = o["value"]
            elif q == "cell_box":
                cell_box[o["subject"]] = o["value"]
        del rec, data
        print(f"[{label}] loaded", file=sys.stderr)

        page_cache: dict = {}
        cut = 0
        for e in examples:
            subj = e["subject"]
            det = e["detail"] or {}
            a_row = glyph_box_by_subject.get(subj)
            if a_row is None:
                print(f"  SKIP {subj}: no glyph_box row", file=sys.stderr)
                continue
            sib_ids = (list(det.get("duplicate_of") and [det["duplicate_of"]] or [])
                      or list(det.get("duplicate_disagrees_with") or []))
            sib_rows = [glyph_box_by_obsid[i] for i in sib_ids
                       if i in glyph_box_by_obsid]
            if not sib_rows:
                print(f"  SKIP {subj}: no sibling box found", file=sys.stderr)
                continue
            b_row = sib_rows[0]

            box = cell_box.get(cell_key_of(subj))
            line_ys = staff_lines.get(staff_key_of(subj))
            spacing = staff_spacing.get(staff_key_of(subj)) or 40.0
            pa = (a_row.get("detail") or {}).get("bbox_page_px")
            pb = (b_row.get("detail") or {}).get("bbox_page_px")
            if not box or not line_ys or not pa or not pb:
                print(f"  SKIP {subj}: missing geometry", file=sys.stderr)
                continue

            page = int(subj.split("/")[1])
            if page not in page_cache:
                print(f"  rendering page {page} ...", file=sys.stderr)
                pi = render_page(pdf_path, page, dpi=600)
                arr = getattr(pi, "rgb", None)
                if arr is None:
                    arr = getattr(pi, "binary")
                arr_np = np.asarray(arr)
                page_cache[page] = Image.fromarray(
                    arr_np if arr_np.ndim == 3 else np.stack([arr_np] * 3, axis=-1))
            img = page_cache[page]

            px0, py0, px1, py1 = box
            cx0 = int(max(0, min(px0, pa[0], pb[0]) - 1.5 * spacing))
            cx1 = int(min(img.width, max(px1, pa[2], pb[2]) + 1.5 * spacing))
            cy0 = int(max(0, min(line_ys) - 3.5 * spacing))
            cy1 = int(min(img.height, max(line_ys) + 2.0 * spacing))

            crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
            UP = 6
            crop = crop.resize((crop.width * UP, crop.height * UP), Image.NEAREST)
            draw = ImageDraw.Draw(crop)
            for ly in line_ys:
                y = (ly - cy0) * UP
                draw.line([(0, y), (crop.width, y)], fill=(70, 130, 220),
                         width=max(1, UP // 3))
            bx0, by0 = (px0 - cx0) * UP, (py0 - cy0) * UP
            bx1, by1 = (px1 - cx0) * UP, (py1 - cy0) * UP
            draw.rectangle([(bx0, by0), (bx1, by1)], outline=(120, 120, 120),
                          width=max(1, UP // 4))

            ax0, ay0, ax1, ay1 = pa
            bxx0, byy0, bxx1, byy1 = pb
            draw.rectangle([((ax0 - cx0) * UP, (ay0 - cy0) * UP),
                           ((ax1 - cx0) * UP, (ay1 - cy0) * UP)],
                          outline=(220, 20, 20), width=max(2, UP // 3))
            draw.rectangle([((bxx0 - cx0) * UP, (byy0 - cy0) * UP),
                           ((bxx1 - cx0) * UP, (byy1 - cy0) * UP)],
                          outline=(20, 160, 20), width=max(2, UP // 3))

            kind = "collapse" if "duplicate_of" in det else "disagree"
            tile_id = subj.replace("/", "-")
            fname = f"r215-{label}-{kind}-{tile_id}.png"
            label_line = (f"{label} {subj} [{kind}] class(A)={a_row['value'][0]} "
                         f"class(B)={b_row['value'][0]}")
            draw.rectangle([(2, 2), (crop.width - 2, 40)], fill=(255, 255, 255))
            draw.text((6, 6), label_line, fill=(0, 0, 0))
            crop.save(out_dir / fname)

            sidecar = {
                "subject": subj, "sibling": b_row["subject"],
                "cause": "rest_is_a_duplicate_box", "kind": kind,
                "reason": e["reason"], "detail": det,
                "class_a": a_row["value"][0], "class_b": b_row["value"][0],
                "score_a": a_row.get("score"), "score_b": b_row.get("score"),
                "bbox_page_px_a": pa, "bbox_page_px_b": pb,
                "file": fname,
                "VERDICT_none_yet": None,
            }
            (out_dir / fname.replace(".png", ".json")).write_text(
                json.dumps(sidecar, indent=2))
            manifest.append(sidecar)
            cut += 1
            print(f"  [{cut}] {subj} -> {fname}", file=sys.stderr)

    (out_dir / "r215-crop-manifest.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
