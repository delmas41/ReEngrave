"""Why did the candidate finder not box a printed direction word? ONE page per run (2026-10-08).

    python3 direction_miss_diag.py <pdf> <page> <tag> <outdir> [points.json]

Runs the real staged GATHER (--through gather), and at `gather_direction_words` replaces it with a DIAGNOSIS that runs
NO OCR: it recomputes `direction_text`'s own steps (bands, subtraction, letter components, clusters) and
  * writes `diag_<tag>.png`: one column, per system: cyan = band limits, red tint = ink the subtraction erased
    (labelled with the detection category), blue box = candidate, and (if `<outdir>/data_<tag>.json` exists) green = word found;
  * for each point in points.json -- [{"system": s, "x": px, "y": px, "text": "dim."}, ...] in the PNG's own strip
    coordinates of `page_<tag>.png` (same layout) -- reports the step that dropped it:
      no_band | found | subtracted:<cat,...> | letter_filter | cluster | merged
Points are PAGE-INDEPENDENT of OCR so this can be run on any tree.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
import cv2
import numpy as np

WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
W = 1400


def layout(pws):
    """Per system: (system_index, x0, y0, x1, y1, k, strip_top_in_png) -- the SAME geometry as direction_cap_heldout.draw."""
    page = pws.page.rgb
    sp = float(np.median([s.line_ys[4] - s.line_ys[0] for s in pws.staves])) / 4.0
    systems = {}
    for s in pws.staves:
        systems.setdefault(s.system_index, []).append(s)
    out = []
    top = 46
    for si, sts in sorted(systems.items()):
        y0 = max(0, int(min(s.line_ys[0] for s in sts) - 6 * sp)); y1 = min(page.shape[0], int(max(s.line_ys[4] for s in sts) + 6 * sp))
        x0 = max(0, int(min(s.x_start for s in sts) - 2 * sp)); x1 = min(page.shape[1], int(max(s.x_end for s in sts) + 2 * sp))
        k = W / float(x1 - x0)
        h = max(1, int((y1 - y0) * k))
        out.append(dict(system=si, x0=x0, y0=y0, x1=x1, y1=y1, k=k, img_top=top + 40, h=h, staff_ids={s.staff_index for s in sts}))
        top += 40 + h + 14
    return out


def diagnose(pt, lay, pws, page_dict, raw, blank, cands, bands, cfg, DT, sp):
    L = [l for l in lay if l["system"] == pt["system"]][0]
    px = L["x0"] + pt["x"] / L["k"]; py = L["y0"] + (pt["y"] - L["img_top"]) / L["k"]
    rx, ry = int(2.2 * sp), int(0.9 * sp)
    ys0, ys1, xs0, xs1 = int(py - ry), int(py + ry), int(px - rx), int(px + rx)
    res = {"text": pt.get("text"), "page_xy": [int(px), int(py)]}
    band = [b for b in bands if b[2] <= py <= b[3] and b[0].x_start <= px <= b[0].x_end]
    res["band"] = [(b[0].staff_index, b[1], b[2], b[3]) for b in band]
    win_raw = raw[ys0:ys1, xs0:xs1] > 0; win_blank = blank[ys0:ys1, xs0:xs1] > 0
    n_raw = int(win_raw.sum()); n_left = int(win_blank.sum())
    res["ink_px"] = n_raw; res["ink_left_after_subtraction"] = n_left
    cats = {}
    for system in page_dict["systems"]:
        for staff in system["staves"]:
            for m in staff["measures"]:
                for d in m.get("detections", []):
                    x, y, w, h = [int(v) for v in d["bbox_page"]]
                    if x < xs1 and x + w > xs0 and y < ys1 and y + h > ys0:
                        blanked = w <= cfg.max_blank_width_spaces * sp
                        cats[d.get("category")] = cats.get(d.get("category"), 0) + 1
                        res.setdefault("detections", []).append([d.get("category"), x, y, w, h, "blanked" if blanked else "span-not-blanked"])
    hit = [c for c in cands if c.bbox_page[0] < xs1 and c.bbox_page[2] > xs0 and c.bbox_page[1] < ys1 and c.bbox_page[3] > ys0]
    if hit:
        c = hit[0]
        big = (c.bbox_page[2] - c.bbox_page[0]) > 3 * max(1, 2 * rx) / 2 * 2.5 or (c.bbox_page[3] - c.bbox_page[1]) > 3.2 * sp
        res["candidate_bbox_sp"] = [round((c.bbox_page[2] - c.bbox_page[0]) / sp, 1), round((c.bbox_page[3] - c.bbox_page[1]) / sp, 1)]
        res["step"] = "found_candidate(" + ("MERGED?" if (c.bbox_page[3] - c.bbox_page[1]) > 3.2 * sp else "ok") + ")"
        return res
    if not band:
        res["step"] = "no_band"
        res["staves_near_sp"] = [(s.staff_index, "below_staff_bottom=%.1fsp" % ((py - s.bottom_y) / sp), "above_staff_top=%.1fsp" % ((s.top_y - py) / sp))
                                 for s in pws.staves if -1 < (py - s.bottom_y) / sp < 9 or -1 < (s.top_y - py) / sp < 9]
        res["band_edges_near"] = [(b[0].staff_index, b[1], b[2], b[3]) for b in bands if abs(b[2] - py) < 8 * sp or abs(b[3] - py) < 8 * sp]
        return res
    if n_raw and n_left < 0.5 * n_raw:
        res["step"] = "subtracted:" + ",".join(sorted(cats)); return res
    # letter components in the window of the subtracted mask
    sub = blank.copy()
    n, _lab, stats, _c = cv2.connectedComponentsWithStats(sub[ys0:ys1, xs0:xs1], 8)
    comps = [tuple(int(v) for v in stats[i, :5]) for i in range(1, n)]
    ok = DT._letter_components(sub[ys0:ys1, xs0:xs1], sp, cfg)
    res["components_in_window"] = len(comps); res["pass_letter_filter"] = len(ok)
    if len(ok) < cfg.min_components:
        res["step"] = "letter_filter" if len(ok) < len(comps) or not comps else "cluster"
        res["comp_sizes_sp"] = [[round(c[2] / sp, 2), round(c[3] / sp, 2), round(c[4] / max(1, c[2] * c[3]), 2)] for c in comps][:8]
    else:
        res["step"] = "cluster"
        res["ok_comps_sp"] = [[round(c[0] / sp, 2), round(c[1] / sp, 2), round(c[2] / sp, 2), round(c[3] / sp, 2)] for c in ok]
        for (st, plc, yt, yb) in band:
            x0s, x1s = max(0, int(st.x_start)), min(blank.shape[1], int(st.x_end))
            bm = blank[yt:yb, x0s:x1s]
            ws = DT._cluster_into_words(DT._letter_components(bm, DT._spacing(st), cfg), DT._spacing(st), cfg)
            res["band_words_near"] = [[x0s + w[0], yt + w[1], x0s + w[2], yt + w[3], w[4]] for w in ws
                                      if x0s + w[0] < xs1 and x0s + w[2] > xs0 and yt + w[1] < ys1 and yt + w[3] > ys0]
        res["clusters_of_window_comps"] = [[round(v / sp, 2) for v in w[:4]] + [w[4]] for w in DT._cluster_into_words(ok, sp, cfg)]
    return res


def main():
    pdf, page, tag, outdir = sys.argv[1:5]
    pts = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else []
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged import gather as G
    from tools.omr import staff_labels_surya as SU
    from tools.omr import direction_text as DT
    R = {"tag": tag}

    def hook(log, pws, cells, local, detections):
        cfg = DT.DEFAULT_BAND_CONFIG
        pd = G._direction_page_dict(pws, cells, local, detections)
        sp = float(np.median([DT._spacing(s) for s in pws.staves]))
        raw = DT._page_ink(pws.page); blank = DT._blank_detections(raw, pd, sp, cfg)
        cands = DT.find_candidates(pws, pd); bands = DT._bands_for_page(pws, cfg)
        lay = layout(pws)
        found = []
        dj = outdir / f"data_{tag}.json"
        if dj.exists():
            found = [(w[0], w[1], w[2]) for w in json.load(open(dj)).get("on_words", [])]
        byxy = {(c.staff_index, c.measure_index, c.x_page): c for c in cands}
        page_rgb = pws.page.rgb
        strips = []
        for L in lay:
            img = np.ascontiguousarray(page_rgb[L["y0"]:L["y1"], L["x0"]:L["x1"]]).copy()
            ov = img.copy()
            red = (raw[L["y0"]:L["y1"], L["x0"]:L["x1"]] > 0) & ~(blank[L["y0"]:L["y1"], L["x0"]:L["x1"]] > 0)
            ov[red] = (255, 0, 0)
            img = cv2.addWeighted(ov, 0.55, img, 0.45, 0)
            img = cv2.resize(img, (W, L["h"]), interpolation=cv2.INTER_AREA)
            k = L["k"]
            for (s, plc, yt, yb) in bands:
                if s.staff_index in L["staff_ids"]:
                    cv2.line(img, (0, int((yt - L["y0"]) * k)), (W, int((yt - L["y0"]) * k)), (0, 190, 190), 1)
                    cv2.line(img, (0, int((yb - L["y0"]) * k)), (W, int((yb - L["y0"]) * k)), (0, 190, 190), 1)
            for c in cands:
                if c.staff_index in L["staff_ids"]:
                    a, b, c2, d = c.bbox_page
                    isf = (c.staff_index, c.measure_index, c.x_page) in found
                    cv2.rectangle(img, (int((a - L["x0"]) * k) - 3, int((b - L["y0"]) * k) - 3), (int((c2 - L["x0"]) * k) + 3, int((d - L["y0"]) * k) + 3),
                                  (0, 160, 0) if isf else (0, 0, 255), 3 if isf else 2)
            head = np.full((40, W, 3), 255, np.uint8)
            cv2.putText(head, f"system {L['system']}", (6, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
            strips += [head, img, np.full((14, W, 3), 128, np.uint8)]
        top = np.full((46, W, 3), 255, np.uint8)
        cv2.putText(top, f"{tag}: red tint=erased by subtraction, cyan=band limits, blue=candidate, green=found", (6, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 160), 2)
        cv2.imwrite(str(outdir / f"diag_{tag}.png"), cv2.cvtColor(np.vstack([top] + strips), cv2.COLOR_RGB2BGR))
        R["n_candidates"] = len(cands); R["n_found_in_data"] = len(found)
        R["points"] = [diagnose(p, lay, pws, pd, raw, blank, cands, bands, cfg, DT, sp) for p in pts]
        (outdir / f"diag_{tag}.json").write_text(json.dumps(R, indent=1, default=str))
    G.gather_direction_words = hook
    from tools.omr.staged.__main__ import main as staged_main
    staged_main([pdf, "--pages", page, "--weights", WEIGHTS, "--through", "gather"])


if __name__ == "__main__":
    main()
