import sys, json
import numpy as np
import cv2

REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)
from tools.omr.preprocessing import render_page, deskew
from tools.omr.staff_detector import detect_staves
from tools.omr import measure_extractor as me
from tools.library.score_library import library_root

OUT = REPO + "/benchmarks/omr-local-staff-2026-09/out/print/bias"
import os
os.makedirs(OUT, exist_ok=True)

DOCS = {
    "litolff": dict(
        pdf=str(library_root()) + "/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        page=3,
        record=REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json",
    ),
    "brahms": dict(
        pdf=str(library_root()) + "/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        page=1,
        record=REPO + "/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json",
    ),
}


def load_rec(path):
    return json.loads(open(path).read())["record"]


def noteheads_of(rec):
    return [o for o in rec["observations"]
           if o["quantity"] == "glyph_box" and o["value"]
           and str(o["value"][0]).startswith("notehead")]


def staff_lines_of(rec, staff_key):
    for o in rec["observations"]:
        if o["subject"] == staff_key and o["quantity"] == "staff_lines":
            return [float(y) for y in o["value"]]
    return None


def is_open(class_name):
    return "Half" in class_name or "Whole" in class_name


def main():
    for doc, cfg in DOCS.items():
        page = render_page(cfg["pdf"], cfg["page"], dpi=600)
        rgb, binary, skew = deskew(page.rgb, page.binary)
        page.rgb, page.binary, page.skew_correction_deg = rgb, binary, skew
        pws = detect_staves(page)
        cells = me.extract_measures(pws)
        cell_by_key = {(c.page_index, c.system_index, c.staff_index, c.measure_index): c
                      for c in cells}
        rec = load_rec(cfg["record"])
        heads = noteheads_of(rec)

        # group by (staff_key, cell_idx)
        from collections import defaultdict
        by_cell = defaultdict(list)
        for o in heads:
            parts = o["subject"].split("/")
            page_idx, system, staff, cell_idx, gi = (int(x) for x in parts[1:6])
            by_cell[(page_idx, system, staff, cell_idx)].append(o)

        clean = []
        for key, group in by_cell.items():
            page_idx, system, staff, cell_idx = key
            staff_key = f"staff/{page_idx}/{system}/{staff}"
            lines = staff_lines_of(rec, staff_key)
            if lines is None:
                continue
            spacing = (max(lines) - min(lines)) / 4.0
            for o in group:
                box = o["detail"]["bbox_page_px"]
                cy = (box[1] + box[3]) / 2.0
                others = [g for g in group if g is not o]
                near = [g for g in others
                       if abs(((g["detail"]["bbox_page_px"][1] + g["detail"]["bbox_page_px"][3]) / 2.0) - cy)
                       < 1.5 * spacing]
                if near:
                    continue  # has a chord-mate
                # not merged: no other box heavily overlapping
                bx0, by0, bx1, by1 = box
                overlap = False
                for g in others:
                    gx0, gy0, gx1, gy1 = g["detail"]["bbox_page_px"]
                    ix0, iy0 = max(bx0, gx0), max(by0, gy0)
                    ix1, iy1 = min(bx1, gx1), min(by1, gy1)
                    if ix1 > ix0 and iy1 > iy0:
                        overlap = True
                        break
                if overlap:
                    continue
                area = max(1.0, (bx1 - bx0) * (by1 - by0))
                ink = binary[int(by0):int(by1), int(bx0):int(bx1)] == 0
                frac = float(ink.mean()) if ink.size else 0.0
                if not (0.12 <= frac <= 0.85):
                    continue  # not a measurable ink outline
                cell = cell_by_key.get(key)
                clean.append(dict(sub=o["subject"], box=box, lines=lines, spacing=spacing,
                                  class_name=o["value"][0], cell=cell, staff_key=staff_key,
                                  page_idx=page_idx, system=system, staff=staff, cell_idx=cell_idx))
        print(f"{doc}: {len(clean)} clean single noteheads qualified")

        # ─ line bias ─
        line_diffs_base = []
        line_diffs_comb = []
        for h in clean:
            cell = h["cell"]
            box = h["box"]
            hx0, hy0, hx1, hy1 = box
            head_w = hx1 - hx0
            gap = head_w
            bands = [(int(hx0 - gap - head_w), int(hx0 - gap)),
                    (int(hx1 + gap), int(hx1 + gap + head_w))]
            spacing = h["spacing"]
            thickness_px = max(2.0, 0.12 * spacing)
            for ly in h["lines"]:
                flank_vals = []
                for bx0, bx1 in bands:
                    found = me._measure_line_run_mid(binary, bx0, bx1,
                                                      ly - 0.3 * spacing, ly + 0.3 * spacing,
                                                      max_thickness_px=1.6 * thickness_px)
                    if found is not None:
                        flank_vals.append(found[0])
                if flank_vals:
                    ink_centre = sum(flank_vals) / len(flank_vals)
                    line_diffs_base.append(ly - ink_centre)
            if cell is not None and getattr(cell, "local_line_paths_px", None) is not None:
                cx0, paths = cell.local_line_paths_px
                col = min(len(paths[0]) - 1, max(0, int((hx0 + hx1) / 2.0) - cx0))
                comb_ys = [p[col] for p in paths]
                for ly, cy_line in zip(h["lines"], comb_ys):
                    for bx0, bx1 in bands:
                        found = me._measure_line_run_mid(binary, bx0, bx1,
                                                          ly - 0.3 * spacing, ly + 0.3 * spacing,
                                                          max_thickness_px=1.6 * thickness_px)
                        if found is not None:
                            line_diffs_comb.append(cy_line - found[0])

        def stats(arr):
            a = np.array(arr)
            return len(a), (float(a.mean()) if len(a) else float("nan")), \
                  (float(a.std()) if len(a) else float("nan"))

        n, m, s = stats(line_diffs_base)
        print(f"  LINE BIAS (base grid - ink centre): n={n} mean={m:+.3f}px std={s:.3f}px")
        n2, m2, s2 = stats(line_diffs_comb)
        print(f"  LINE BIAS (comb - ink centre):       n={n2} mean={m2:+.3f}px std={s2:.3f}px")

        # ─ head bias ─
        head_diffs_all, head_diffs_open, head_diffs_filled = [], [], []
        head_diffs_online, head_diffs_inspace = [], []
        for h in clean:
            bx0, by0, bx1, by1 = h["box"]
            box_cy = (by0 + by1) / 2.0
            ink = binary[int(by0):int(by1), int(bx0):int(bx1)] == 0
            if ink.sum() == 0:
                continue
            spacing = h["spacing"]
            mask_half = 0.18 * spacing
            rows = np.arange(int(by0), int(by1))
            keep = np.ones(len(rows), dtype=bool)
            for ly in h["lines"]:
                keep &= np.abs(rows - ly) > mask_half
            ink_masked = ink[keep, :]
            rows_masked = rows[keep]
            if ink_masked.sum() == 0:
                ink_masked, rows_masked = ink, rows  # nothing left -- fall back unmasked
            row_counts = ink_masked.sum(axis=1).astype(float)
            ink_cy = float((rows_masked * row_counts).sum() / row_counts.sum())
            diff = box_cy - ink_cy
            head_diffs_all.append(diff)
            (head_diffs_open if is_open(h["class_name"]) else head_diffs_filled).append(diff)
            (head_diffs_online if "OnLine" in h["class_name"] else head_diffs_inspace).append(diff)

        n, m, s = stats(head_diffs_all)
        print(f"  HEAD BIAS (box centre - ink centre): n={n} mean={m:+.3f}px std={s:.3f}px")
        for label, arr in [("open", head_diffs_open), ("filled", head_diffs_filled),
                           ("on-line", head_diffs_online), ("in-space", head_diffs_inspace)]:
            n, m, s = stats(arr)
            print(f"    {label}: n={n} mean={m:+.3f}px std={s:.3f}px")

        # ─ save a few crops ─
        n_crops = 0
        for h in clean:
            if n_crops >= 3:
                break
            bx0, by0, bx1, by1 = h["box"]
            cx0, cy0 = int(bx0) - 550, int(by0) - 150
            cx1, cy1 = int(bx1) + 550, int(by1) + 150
            cx0, cy0 = max(0, cx0), max(0, cy0)
            cx1, cy1 = min(page.rgb.shape[1], cx1), min(page.rgb.shape[0], cy1)
            crop = page.rgb[cy0:cy1, cx0:cx1].copy()
            crop = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR) if crop.ndim == 3 else cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            for ly in h["lines"]:
                yy = int(round(ly)) - cy0
                if 0 <= yy < crop.shape[0]:
                    cv2.line(crop, (0, yy), (crop.shape[1], yy), (0, 140, 255), 1)
            cell = h["cell"]
            if cell is not None and getattr(cell, "local_line_paths_px", None) is not None:
                ccx0, paths = cell.local_line_paths_px
                for p in paths:
                    pts = [(x + ccx0 - cx0, int(round(y)) - cy0) for x, y in enumerate(p)
                          if 0 <= int(round(y)) - cy0 < crop.shape[0] and 0 <= x + ccx0 - cx0 < crop.shape[1]]
                    if len(pts) > 1:
                        cv2.polylines(crop, [np.array(pts, dtype=np.int32)], False, (0, 220, 0), 1)
            bxm, bym = int((bx0 + bx1) / 2) - cx0, int((by0 + by1) / 2) - cy0
            cv2.drawMarker(crop, (bxm, bym), (255, 0, 255), cv2.MARKER_CROSS, 20, 2)
            cv2.rectangle(crop, (int(bx0) - cx0, int(by0) - cy0), (int(bx1) - cx0, int(by1) - cy0), (0, 0, 255), 1)
            out_path = f"{OUT}/{doc}_{h['sub'].replace('/', '_')}.png"
            big = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST) if crop.shape[1] < 500 else crop
            cv2.imwrite(out_path, big)
            print(f"  crop: {out_path}  size={big.shape[1]}x{big.shape[0]}")
            n_crops += 1


if __name__ == "__main__":
    main()
