"""INDEPENDENT VERIFIER of lane-staff-lines-off-ink (40aab116).

Written from scratch; reads nothing from that lane's scripts. STAGED and
LEGACY share the code measured here (`preprocessing.render_page`,
`staff_detector.detect_staves`, `measure_extractor`).

Subcommands:
  extract  <doc>       record -> compact JSON (scratch); record read ONLY via
                       record_io.load_record
  control              synthetic tilt control + +3 px shift control
  measure  <doc>       every page: re-render, re-detect (claim e), measure the
                       ink row of every staff line at clear columns against
                       (a) the raw recorded line_ys and (b) the per-bar grid
                       (line_ys + `_cell_line_offset` shift, reconstructed by
                       re-running `extract_measures`, checked against the
                       record's own NOTEHEAD_STAFF_POSITION)
  summary              tables for the FINDINGS section
  sheet                out/print/verify_staff_line_offsets.png

INK ROW OF A LINE AT x (the measure). A strip `STRIP` px wide centred on x,
rows from 1.5 spaces above the recorded top line to 1.5 below the bottom one.
A row is ink when at least half the strip's pixels are ink (binary 0). The
column is CLEAR only if that window holds EXACTLY five dark runs, each no
thicker than 0.4 space, with every gap between consecutive run centres within
20% of the recorded spacing -- so no notehead, stem crossing a line (a stem
is vertical: the whole run merges), beam, ledger, slur or text lies anywhere
in the window. Then line k IS run k, and its ink row is the run's centre
((first+last)/2, pixel-row coordinates, the same coordinates line_ys use).
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SCRATCH = Path("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-notation-tile-fixes-2837c5/61ecbfe3-efe1-4b05-b3a2-0c894d475fc0/scratchpad/verify")
SHARED = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
DOCS = {
    "litolff": SHARED / "beethoven5-litolff-mvt1-whole-20261006-night-combined.record.json",
    "brahms": SHARED / "brahms1-breitkopf-mvt1-whole-20261006-night-combined.record.json",
}
STEP_SPACES = 0.5          # candidate columns every half space


# ───────────────────────────── extract ─────────────────────────────

def extract(doc: str) -> None:
    from tools.omr.staged.record_io import load_record
    r = load_record(DOCS[doc])
    args = r["provenance"]["settings"]["args"]
    out = {"pdf": args["pdf"], "dpi": args["dpi"], "pages": args["pages"],
           "commit": r["provenance"]["commit"], "dirty": r["provenance"]["dirty"],
           "staves": {}, "cells": {}, "heads": {}}
    pos = {}
    boxes = {}
    for o in r["record"]["observations"]:
        q = o["quantity"]
        s = o["subject"]
        if q == "staff_lines":
            out["staves"].setdefault(s, {})["lines"] = o["value"]
            out["staves"][s]["page_staff_index"] = o["detail"].get("page_staff_index")
        elif q == "staff_spacing":
            out["staves"].setdefault(s, {})["spacing"] = o["value"]
        elif q == "staff_extent":
            out["staves"].setdefault(s, {})["extent"] = o["value"]
        elif q == "cell_box":
            out["cells"][s] = o["value"]
        elif q == "notehead_staff_position":
            pos[s] = o["value"]
        elif q == "glyph_box" and str(o["value"][0]).startswith("notehead"):
            boxes[s] = (o["value"], o["detail"].get("y_center_page"))
    for g, p in pos.items():
        if g in boxes:
            out["heads"][g] = {"pos": p, "box": boxes[g][0], "y_page": boxes[g][1]}
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / f"{doc}.extract.json").write_text(json.dumps(out))
    print(doc, len(out["staves"]), "staves", len(out["cells"]), "cells",
          len(out["heads"]), "heads", out["pages"], out["commit"], out["dirty"])


# ───────────────────────────── the measure ─────────────────────────────

def ink_runs(binary: np.ndarray, x: int, y_lo: int, y_hi: int, strip: int):
    h, w = binary.shape
    a, b = max(0, x - strip // 2), min(w, x - strip // 2 + strip)
    y_lo, y_hi = max(0, y_lo), min(h, y_hi)
    if b <= a or y_hi <= y_lo:
        return []
    col = (binary[y_lo:y_hi, a:b] == 0).mean(axis=1) >= 0.5
    runs, start = [], None
    for i, v in enumerate(col):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((y_lo + start, y_lo + i - 1)); start = None
    if start is not None:
        runs.append((y_lo + start, y_lo + len(col) - 1))
    return runs


def measure_column(binary, x, lines, spacing, strip):
    """Five ink-row centres + thicknesses at x, or None if x is not clear."""
    lo = int(round(min(lines) - 1.5 * spacing))
    hi = int(round(max(lines) + 1.5 * spacing)) + 1
    runs = ink_runs(binary, x, lo, hi, strip)
    if len(runs) != 5:
        return None
    th = [e - s + 1 for s, e in runs]
    if max(th) > 0.4 * spacing:
        return None
    c = [(s + e) / 2.0 for s, e in runs]
    gaps = np.diff(c)
    if np.any(np.abs(gaps - spacing) > 0.2 * spacing):
        return None
    return c, th


def strip_for(spacing):
    return max(3, int(round(0.2 * spacing)))


def staff_columns(binary, lines, spacing, x0, x1):
    strip = strip_for(spacing)
    step = max(2, int(round(STEP_SPACES * spacing)))
    out = []
    for x in range(int(x0) + strip, int(x1) - strip, step):
        m = measure_column(binary, x, lines, spacing, strip)
        if m is not None:
            out.append((x, m[0], m[1]))
    return out


# ───────────────────────────── controls ─────────────────────────────

def control() -> dict:
    res = {}
    # (i) synthetic: 5 lines, spacing 20, thickness 3, tilt 12 px over 4000
    # px, plus notehead blobs, stems and a beam over parts of the staff.
    H, W = 400, 4000
    img = np.full((H, W), 255, np.uint8)
    y0, sp, tilt = 150.0, 20.0, 12.0
    true = lambda k, x: y0 + k * sp + tilt * x / W
    for x in range(W):
        for k in range(5):
            yc = true(k, x)
            r = int(round(yc))       # 3-px line, nearest-row rasterisation
            img[r - 1:r + 2, x] = 0
    rng = np.random.default_rng(0)
    for _ in range(80):     # heads + stems
        cx = int(rng.integers(50, W - 50)); cy = int(rng.integers(120, 280))
        img[cy - 8:cy + 8, cx - 11:cx + 11] = 0
        img[cy - 70:cy, cx + 10:cx + 12] = 0
    img[100:108, 1000:1600] = 0   # a beam above the staff
    flat = [y0 + k * sp + tilt / 2 for k in range(5)]   # one y per line (mid)
    cols = staff_columns(img, flat, sp, 0, W)
    errs = []
    for x, c, _ in cols:
        for k in range(5):
            errs.append((c[k] - flat[k]) - (true(k, x) - flat[k]))
    errs = np.abs(np.array(errs))
    xs = np.array([x for x, _, _ in cols], float)
    off = np.array([np.mean(np.array(c) - np.array(flat)) for _, c, _ in cols])
    b, a = np.polyfit(xs, off, 1)
    fitted_tilt = float(b * W)
    res["synthetic_tilt"] = {"n_columns": len(cols),
                             "max_point_err_px": float(errs.max()),
                             "median_point_err_px": float(np.median(errs)),
                             "true_tilt_px": tilt, "fitted_tilt_px": round(fitted_tilt, 3),
                             "fitted_intercept_px": round(float(a), 3),
                             "pass": bool(errs.max() <= 0.5 + 1e-9
                                          and abs(fitted_tilt - tilt) < 0.5)}
    # the same control must be able to FAIL: a measure that ignored the tilt
    # (offset 0 everywhere) would err by up to tilt/2
    res["synthetic_tilt"]["if_measure_ignored_tilt_max_err_px"] = tilt / 2
    print("control (i) synthetic tilt:", res["synthetic_tilt"])
    return res


def shift_control(binary, lines, spacing, extent, shift=3):
    a = staff_columns(binary, lines, spacing, *extent)
    moved = [y + shift for y in lines]
    b = staff_columns(binary, moved, spacing, *extent)
    da = {x: np.mean(np.array(c) - np.array(lines)) for x, c, _ in a}
    db = {x: np.mean(np.array(c) - np.array(moved)) for x, c, _ in b}
    common = sorted(set(da) & set(db))
    d = [da[x] - db[x] for x in common]
    return {"n_common": len(common), "n_a": len(a), "n_b": len(b),
            "median_detected_shift": float(np.median(d)) if d else None,
            "max_dev": float(np.max(np.abs(np.array(d) - shift))) if d else None}


# ───────────────────────────── measure one doc ─────────────────────────────

def parse_pages(spec):
    out = []
    for part in str(spec).split(","):
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def measure(doc: str) -> None:
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import measure_extractor as me
    from tools.omr.staged.gather import _system_local

    ex = json.loads((SCRATCH / f"{doc}.extract.json").read_text())
    pages = parse_pages(ex["pages"])
    dpi = ex["dpi"]
    rows = []           # per staff
    cell_rows = []      # per cell
    head_checks = []
    repro = {"staves": 0, "exact": 0, "mismatch": []}
    cell_repro = {"cells": 0, "box_match": 0}
    shiftctl = None
    heads_by_cell = defaultdict(list)
    for g, h in ex["heads"].items():
        heads_by_cell["cell/" + "/".join(g.split("/")[1:5])].append((g, h))
    for p in pages:
        pi = render_page(ex["pdf"], p, dpi=dpi)
        pws = detect_staves(pi)
        local = _system_local(pws.staves)
        mine = {}
        for st in pws.staves:
            sy, sl = local[st.staff_index]
            mine[f"staff/{p}/{sy}/{sl}"] = st
        rec = {k: v for k, v in ex["staves"].items() if k.split("/")[1] == str(p)}
        # (e) reproduction
        for k, v in rec.items():
            repro["staves"] += 1
            st = mine.get(k)
            if st is not None and [int(y) for y in st.line_ys] == [int(y) for y in v["lines"]] \
                    and [st.x_start, st.x_end] == list(v["extent"]):
                repro["exact"] += 1
            else:
                repro["mismatch"].append(k)
        extra = set(mine) - set(rec)
        if extra:
            repro.setdefault("extra", []).extend(sorted(extra))
        # the per-bar grid, reconstructed exactly as gather cuts it
        cells = me.extract_measures(pws)
        by_cell = {}
        for c in cells:
            sy, sl = local[c.staff_index]
            by_cell[f"cell/{p}/{sy}/{sl}/{c.measure_index}"] = c
        binary = pi.binary
        for k, v in rec.items():
            st = mine.get(k)
            if st is None:
                continue
            lines = [float(y) for y in v["lines"]]
            sp = float(v["spacing"])
            x0, x1 = v["extent"]
            cols = staff_columns(binary, lines, sp, x0, x1)
            if shiftctl is None and len(cols) > 20:
                shiftctl = {"staff": k, **shift_control(binary, lines, sp, (x0, x1))}
                print("control (ii) +3 px:", shiftctl)
            # cells of this staff
            pre = "cell/" + k[len("staff/"):] + "/"
            mycells = {ck: c for ck, c in by_cell.items() if ck.startswith(pre)}
            cell_of_x = []
            for ck, c in mycells.items():
                cell_repro["cells"] += 1
                rb = ex["cells"].get(ck)
                if rb is not None and [float(a) for a in c.bbox_page_px] == [float(a) for a in rb]:
                    cell_repro["box_match"] += 1
                prov = c.__dict__.get("line_grid_localized")
                shift = int(prov["offset_px"]) if prov else 0
                cell_of_x.append((c.bbox_page_px[0], c.bbox_page_px[2], ck, shift))
            samples = []
            for x, cen, th in cols:
                raw = [cen[i] - lines[i] for i in range(5)]
                hit = [t for t in cell_of_x if t[0] <= x < t[1]]
                ck, shift = (hit[0][2], hit[0][3]) if hit else (None, None)
                bar = [r - shift for r in raw] if hit else None
                samples.append({"x": x, "raw": raw, "bar": bar, "cell": ck,
                                "shift": shift, "th": th})
            rows.append({"staff": k, "spacing": sp, "extent": [x0, x1],
                         "lines": lines, "n_cols": len(cols), "samples": samples})
            # head-position check: every head in this staff's cells
            for ck, c in mycells.items():
                lines_c = list(c.staff_line_ys_canonical)
                unl = c.__dict__.get("staff_line_ys_canonical_unlocalized", lines_c)
                gaps = np.diff(lines_c)
                hs = float(np.mean(gaps)) / 2.0
                hs_u = float(np.mean(np.diff(unl))) / 2.0
                for g, h in heads_by_cell.get(ck, []):
                    _n, xc, yc, wc, hc = h["box"]
                    ycen = yc + hc // 2
                    mine_pos = (ycen - lines_c[0]) / hs
                    unloc_pos = (ycen - unl[0]) / hs_u
                    head_checks.append({"glyph": g, "rec": h["pos"],
                                        "pergrid": round(mine_pos, 2),
                                        "unlocalized": round(unloc_pos, 2),
                                        "shift": (c.__dict__.get("line_grid_localized") or {}).get("offset_px", 0)})
        print(f"{doc} p{p}: staves {len(rec)} repro {repro['exact']}/{repro['staves']} "
              f"cells {cell_repro['box_match']}/{cell_repro['cells']}", flush=True)
    out = {"doc": doc, "repro": repro, "cell_repro": cell_repro,
           "shift_control": shiftctl, "staves": rows, "head_checks": head_checks}
    (SCRATCH / f"{doc}.measure.json").write_text(json.dumps(out))


# ───────────────────────────── summary ─────────────────────────────

def _pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def classify(st):
    """TILT / SHIFT / WANDER / SPACING for one staff, from the per-column
    mean raw offset o(x) (mean of the five lines) and the per-column spread
    of the five lines. Own rules, stated in FINDINGS."""
    sp = st["spacing"]
    xs = np.array([s["x"] for s in st["samples"]], float)
    o = np.array([np.mean(s["raw"]) for s in st["samples"]])
    spread = np.array([max(s["raw"]) - min(s["raw"]) for s in st["samples"]])
    if len(xs) < 3:
        return "too_few", {}
    b, a = np.polyfit(xs, o, 1)
    resid = o - (a + b * xs)
    W = st["extent"][1] - st["extent"][0]
    info = {"tilt_px": float(b * W), "resid_max_px": float(np.abs(resid).max()),
            "resid_sd_px": float(resid.std()), "mean_px": float(o.mean()),
            "spread_med_px": float(np.median(spread))}
    if np.median(spread) >= 0.2 * sp:
        return "spacing", info
    if np.abs(resid).max() >= 0.2 * sp:
        return "wander", info
    if abs(b * W) >= 0.25 * sp:
        return "tilt", info
    return "shift", info


def summary() -> dict:
    from tools.omr.measure_extractor import CELL_LINE_MAX_SHIFT_SPACES
    out = {}
    for doc in ("litolff", "brahms"):
        f = SCRATCH / f"{doc}.measure.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        R = {"repro": f"{d['repro']['exact']}/{d['repro']['staves']}",
             "repro_extra": len(d["repro"].get("extra", [])),
             "cells_box_match": f"{d['cell_repro']['box_match']}/{d['cell_repro']['cells']}",
             "shift_control": d["shift_control"]}
        hc = d["head_checks"]
        e = np.array([abs(h["rec"] - h["pergrid"]) for h in hc])
        u = np.array([abs(h["rec"] - h["unlocalized"]) for h in hc])
        shifted = np.array([h["shift"] != 0 for h in hc])
        R["heads"] = {"n": len(hc), "max_err_pergrid": float(e.max()),
                      "n_err_gt_0.01": int((e > 0.01).sum()),
                      "n_in_shifted_cells": int(shifted.sum()),
                      "unlocalized_err_median_in_shifted":
                          float(np.median(u[shifted])) if shifted.any() else None}
        line_px, line_sp, signed_px, thick = [], [], [], []
        any25 = any40 = any25_line = any40_line = 0
        kinds = defaultdict(int)
        kind_info = defaultdict(list)
        worst = []
        cells = defaultdict(lambda: {"raw": [], "bar": [], "shift": None, "sp": None})
        for st in d["staves"]:
            sp = st["spacing"]
            if not st["samples"]:
                continue
            col = []
            for s in st["samples"]:
                for r in s["raw"]:
                    line_px.append(abs(r)); line_sp.append(abs(r) / sp); signed_px.append(r)
                thick += s["th"]
                col.append(np.mean(s["raw"]))
                if s["cell"] is not None:
                    c = cells[s["cell"]]
                    c["raw"].append(np.mean(s["raw"])); c["bar"].append(np.mean(s["bar"]))
                    c["shift"] = s["shift"]; c["sp"] = sp
            col = np.abs(np.array(col))
            mx_line = max(max(abs(r) for r in s["raw"]) for s in st["samples"])
            any25 += col.max() >= 0.25 * sp; any40 += col.max() >= 0.4 * sp
            any25_line += mx_line >= 0.25 * sp; any40_line += mx_line >= 0.4 * sp
            if col.max() >= 0.25 * sp:
                k, info = classify(st)
                kinds[k] += 1
                kind_info[k].append(abs(info.get("tilt_px", 0)))
            worst.append((float(col.max()), st["staff"], float(col.max() / sp)))
        lp, ls = np.array(line_px), np.array(line_sp)
        R["raw_line_samples"] = {
            "n": len(lp), "median_px": _pct(lp, 50), "p90_px": _pct(lp, 90),
            "max_px": float(lp.max()), "median_sp": _pct(ls, 50),
            "p90_sp": _pct(ls, 90), "max_sp": float(ls.max()),
            "signed_median_px": float(np.median(signed_px)),
            "signed_mean_px": float(np.mean(signed_px)),
            "thickness_median_px": float(np.median(thick))}
        R["staves_measured"] = sum(1 for st in d["staves"] if st["samples"])
        R["clear_columns_per_staff_median"] = float(np.median([st["n_cols"] for st in d["staves"]]))
        R["staves_ge_0.25sp_colmean"] = int(any25)
        R["staves_ge_0.4sp_colmean"] = int(any40)
        R["staves_ge_0.25sp_anyline"] = int(any25_line)
        R["staves_ge_0.4sp_anyline"] = int(any40_line)
        R["shape_of_flagged"] = dict(kinds)
        R["max_tilt_px_among_tilt"] = max(kind_info["tilt"]) if kind_info["tilt"] else None
        worst.sort(reverse=True)
        R["worst10"] = [{"staff": w[1], "max_px": round(w[0], 1), "max_sp": round(w[2], 2)}
                        for w in worst[:10]]
        # (b) per bar
        n2 = [c for c in cells.values() if len(c["raw"]) >= 2]

        def cnt(key, thr, stat):
            return sum(1 for c in n2 if stat(np.abs(np.array(c[key]))) >= thr * c["sp"])
        R["cells_ge2"] = len(n2)
        for thr in (0.25, 0.4):
            R[f"cells_median_ge_{thr}sp"] = {"raw": cnt("raw", thr, np.median),
                                              "bar": cnt("bar", thr, np.median)}
            R[f"cells_anypoint_ge_{thr}sp"] = {"raw": cnt("raw", thr, np.max),
                                                "bar": cnt("bar", thr, np.max)}
        within = np.array([max(c["bar"]) - min(c["bar"]) for c in n2])
        R["within_bar_range_px"] = {"median": _pct(within, 50), "p90": _pct(within, 90)}
        cm = np.array([abs(np.median(c["bar"])) for c in n2])
        R["cell_median_abs_bar_px"] = {"median": _pct(cm, 50), "p90": _pct(cm, 90)}
        bad = [(k, c) for k, c in cells.items() if len(c["raw"]) >= 2
               and abs(np.median(c["bar"])) >= 0.4 * c["sp"]]
        why = defaultdict(int)
        for k, c in bad:
            cap = int(round(CELL_LINE_MAX_SHIFT_SPACES * c["sp"]))
            if c["shift"] == 0:
                why["not_shifted"] += 1
            elif abs(c["shift"]) == cap:
                why["at_cap"] += 1
            elif np.sign(c["shift"]) != np.sign(np.median(c["raw"])):
                why["moved_wrong_way"] += 1
            else:
                why["other"] += 1
        R["bad_cells_median_ge_0.4sp"] = {
            "n": len(bad), "why": dict(why),
            "list": [{"cell": k, "shift": c["shift"],
                      "raw_med": round(float(np.median(c["raw"])), 1),
                      "bar_med": round(float(np.median(c["bar"])), 1)}
                     for k, c in sorted(bad)][:40]}
        out[doc] = R
    (SCRATCH / "summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


# ───────────────────────────── the lane's sheet selection ─────────────────────

def lane_sheet_rate() -> dict:
    """Why the lane's sheet read 8/24 red and 13/24 blue within 2 px: apply
    ITS selection (worst raw staves, x = first / worst / last clean column)
    to MY measure, then the same test on random staves at random clear x."""
    out = {}
    all_st = []
    for doc in ("litolff", "brahms"):
        d = json.loads((SCRATCH / f"{doc}.measure.json").read_text())
        all_st += [dict(st, doc=doc) for st in d["staves"] if len(st["samples"]) >= 3]

    def ok(vals):
        return max(abs(v) for v in vals) <= 2.0

    def rate(picks):
        r = sum(ok(s["raw"]) for s in picks)
        b = sum(ok(s["bar"]) for s in picks if s["bar"] is not None)
        nb = sum(1 for s in picks if s["bar"] is not None)
        return {"red": f"{r}/{len(picks)}", "blue": f"{b}/{nb}"}

    def worst(st):
        return max(abs(np.mean(s["raw"])) for s in st["samples"]) / st["spacing"]
    chosen, seen = [], set()
    for st in sorted(all_st, key=lambda s: -worst(s)):
        key = (st["doc"], st["staff"].split("/")[1])
        if key in seen:
            continue
        seen.add(key); chosen.append(st)
        if len(chosen) == 8:
            break
    picks = []
    for st in chosen:
        S = st["samples"]
        iw = int(np.argmax([abs(np.mean(s["raw"])) for s in S]))
        picks += [S[i] for i in sorted({0, iw, len(S) - 1})]
    out["lane_selection_on_my_measure"] = rate(picks)
    rng = random.Random(7)
    rp = []
    for st in rng.sample(all_st, 200):
        rp.append(rng.choice(st["samples"]))
    out["random_200_staves_one_random_clear_x"] = rate(rp)
    allp = [s for st in all_st for s in st["samples"]]
    out["every_clear_column"] = rate(allp)
    print(json.dumps(out, indent=1))
    return out


# ───────────────────────────── the crop sheet ─────────────────────────────

RED, BLUE, GREEN = (230, 0, 0), (0, 70, 255), (0, 170, 0)


def _to_tile(y, y0, scale):
    """Page row y (float, pixel-centre coordinates) -> tile row."""
    return (y - y0 + 0.5) * scale - 0.5


def _from_tile(row, y0, scale):
    return (row + 0.5) / scale - 0.5 + y0


def sheet() -> None:
    import cv2
    from tools.omr.preprocessing import render_page
    docs = {}
    for doc in ("litolff", "brahms"):
        d = json.loads((SCRATCH / f"{doc}.measure.json").read_text())
        ex = json.loads((SCRATCH / f"{doc}.extract.json").read_text())
        docs[doc] = (d, ex)
    all_st = [dict(st, doc=doc) for doc, (d, _) in docs.items()
              for st in d["staves"] if len(st["samples"]) >= 5]

    def worst(st):
        return max(abs(np.mean(s["raw"])) for s in st["samples"]) / st["spacing"]
    chosen, seen = [], set()
    for st in sorted(all_st, key=lambda s: -worst(s)):
        key = (st["doc"], st["staff"].split("/")[1])
        if key in seen:
            continue
        seen.add(key); chosen.append(("worst raw", st))
        if len(chosen) == 3:
            break
    rng = random.Random(20261006)
    pool = [st for st in all_st if st not in [c[1] for c in chosen]]
    for st in rng.sample(pool, 3):
        chosen.append(("random", st))

    HALF = 110
    rows_img, report = [], []
    pages = {}
    for n, (why, st) in enumerate(chosen, 1):
        doc = st["doc"]; d, ex = docs[doc]
        p = int(st["staff"].split("/")[1])
        if (doc, p) not in pages:
            pages[(doc, p)] = render_page(ex["pdf"], p, dpi=ex["dpi"])
        pi = pages[(doc, p)]
        sp = st["spacing"]; lines = np.array(st["lines"])
        scale = 3 if sp < 20 else 2
        S = st["samples"]
        iw = int(np.argmax([abs(np.mean(s["raw"])) for s in S]))
        idx = sorted({len(S) // 10, len(S) // 2, len(S) - 1 - len(S) // 10} if why == "random"
                     else {len(S) // 10, iw, len(S) - 1 - len(S) // 10})
        while len(idx) < 3:
            idx = sorted(set(idx) | {len(S) // 3})
        tiles = []
        for i in idx:
            s = S[i]; x = s["x"]
            shift = s["shift"] if s["shift"] is not None else 0
            ink = lines + np.array(s["raw"])
            bar = lines + shift
            y0 = int(min(lines.min(), ink.min(), bar.min()) - 1.6 * sp)
            y1 = int(max(lines.max(), ink.max(), bar.max()) + 1.6 * sp) + 1
            xa = max(0, x - HALF); xb = xa + 2 * HALF
            crop = pi.rgb[y0:y1, xa:xb].copy()
            big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            mid = int((x - xa + 0.5) * scale)
            Wt = big.shape[1]
            drawn = []
            for k in range(5):
                rr = int(round(_to_tile(lines[k], y0, scale)))
                big[rr, 0:mid - 10 * scale // 2] = RED
                rb = int(round(_to_tile(bar[k], y0, scale)))
                big[rb, mid + 10 * scale // 2:Wt] = BLUE
                rg = int(round(_to_tile(ink[k], y0, scale)))
                big[rg, mid - 4 * scale // 2:mid + 4 * scale // 2] = GREEN
                drawn.append((k, rr, rb, rg))
            # RE-MEASURE every drawn line from the tile's own pixel rows
            for k, rr, rb, rg in drawn:
                def rows_of(colour, cx):
                    col = big[:, cx]
                    hit = np.where((col == np.array(colour)).all(axis=1))[0]
                    return hit
                red_rows = rows_of(RED, 2)
                blue_rows = rows_of(BLUE, Wt - 3)
                green_rows = rows_of(GREEN, mid)
                # the k-th drawn row of each colour
                yr = _from_tile(red_rows[k], y0, scale)
                yb = _from_tile(blue_rows[k], y0, scale)
                yg = _from_tile(green_rows[k], y0, scale)
                report.append({"tile": n, "doc": doc, "staff": st["staff"], "x": x, "line": k,
                               "drawn_red_err": round(yr - lines[k], 2),
                               "drawn_blue_err": round(yb - bar[k], 2),
                               "drawn_green_err": round(yg - ink[k], 2),
                               "red_vs_ink_px": round(yr - yg, 2),
                               "blue_vs_ink_px": round(yb - yg, 2),
                               "shift": shift})
            tiles.append(big)
        h = max(t.shape[0] for t in tiles)
        tiles = [np.pad(t, ((0, h - t.shape[0]), (6, 6), (0, 0)), constant_values=255) for t in tiles]
        row = np.concatenate(tiles, axis=1)
        label = np.full((30, row.shape[1], 3), 255, np.uint8)
        xs = [S[i]["x"] for i in idx]
        cv2.putText(label, f"{n} ({why}) {doc} {st['staff']}  x={xs}  worst raw {worst(st):.2f} sp",
                    (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        rows_img.append(np.concatenate([label, row], axis=0))
    W = max(r.shape[1] for r in rows_img)
    rows_img = [np.pad(r, ((0, 8), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows_img]
    legend = np.full((70, W, 3), 255, np.uint8)
    for j, (c, t) in enumerate([(RED, "RED (left of each column): the RAW recorded staff-wide line_ys (Q.STAFF_LINES)"),
                                (BLUE, "BLUE (right): the PER-BAR grid gather uses = line_ys + this cell's _cell_line_offset shift"),
                                (GREEN, "GREEN (short tick at the column): MY measured ink centre of each line in a clear 1-staff-high column")]):
        cv2.putText(legend, t, (6, 20 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, c[::-1][::-1], 1)
    sheet = np.concatenate([legend] + rows_img, axis=0)
    outp = ROOT / "out" / "print" / "verify_staff_line_offsets.png"
    outp.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(outp), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    (SCRATCH / "sheet_report.json").write_text(json.dumps(report, indent=1))
    dr = np.array([[r["drawn_red_err"], r["drawn_blue_err"], r["drawn_green_err"]] for r in report])
    print("wrote", outp, sheet.shape)
    print("drawn-vs-intended max |err| px (red, blue, green):", np.abs(dr).max(axis=0))
    for n in range(1, len(chosen) + 1):
        rr = [r for r in report if r["tile"] == n]
        for x in sorted({r["x"] for r in rr}):
            q = [r for r in rr if r["x"] == x]
            print(n, q[0]["doc"], q[0]["staff"], "x", x, "shift", q[0]["shift"],
                  "red-ink", [r["red_vs_ink_px"] for r in q],
                  "blue-ink", [r["blue_vs_ink_px"] for r in q])


# ───────────────────────────── (c) the far-head local lines ─────────────────

FH_REF = "origin/lane-night-1005-combined"


def _fh_functions():
    """`_darkest_row` + `local_staff_lines` exactly as on the far-head branch
    (exec'd from `git show`, not copied), so what is scored is that code."""
    import subprocess
    src = subprocess.run(["git", "show", f"{FH_REF}:tools/omr/annotate/far_head_reader.py"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    a = src.index("def _darkest_row(")
    b = src.index("def frame_lines_for_head(")
    ns = {"np": np, "Optional": __import__("typing").Optional,
          "Sequence": __import__("typing").Sequence, "List": __import__("typing").List}
    exec(src[a:b], ns)
    return ns["_darkest_row"], ns["local_staff_lines"]


def farhead(doc: str) -> None:
    """Score the far-head reader's own local re-measure of the five lines
    (`_darkest_row` over a head-wide band, +-0.5 sp around each RAW line)
    against MY ink centre, at my clear columns (a band centred on x)."""
    import cv2
    from tools.omr.preprocessing import render_page
    darkest, _local = _fh_functions()
    d = json.loads((SCRATCH / f"{doc}.measure.json").read_text())
    ex = json.loads((SCRATCH / f"{doc}.extract.json").read_text())
    by_page = defaultdict(list)
    for st in d["staves"]:
        by_page[int(st["staff"].split("/")[1])].append(st)
    rows = []
    for p in sorted(by_page):
        pi = render_page(ex["pdf"], p, dpi=ex["dpi"])
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        for st in by_page[p]:
            sp = st["spacing"]; w = 1.3 * sp
            for s in st["samples"][::3]:
                x = s["x"]
                ink = [st["lines"][k] + s["raw"][k] for k in range(5)]
                got = []
                for gy in sorted(st["lines"]):
                    y = darkest(gray, int(x - w / 2), int(x + w / 2),
                                int(gy - sp * 0.5), int(gy + sp * 0.5) + 1)
                    got.append(y)
                rows.append({"raw_off_sp": float(np.max(np.abs(s["raw"]))) / sp,
                             "err": [None if g is None else g - i for g, i in zip(got, ink)],
                             "sp": sp, "th": s["th"]})
        print(doc, "p", p, len(rows), flush=True)
    out = {}
    for name, lo, hi in (("raw<0.25sp", 0, 0.25), ("0.25-0.5sp", 0.25, 0.5), ("raw>=0.5sp", 0.5, 9)):
        sel = [r for r in rows if lo <= r["raw_off_sp"] < hi]
        full = [r for r in sel if None not in r["err"]]
        e = np.array([v for r in full for v in r["err"]])
        ok2 = sum(1 for r in full if max(abs(v) for v in r["err"]) <= 2)
        far = sum(1 for r in full if max(abs(v) for v in r["err"]) >= 0.5 * r["sp"])
        out[name] = {"n": len(sel), "all5_found": len(full),
                     "signed_median_px": float(np.median(e)) if len(e) else None,
                     "abs_median_px": float(np.median(np.abs(e))) if len(e) else None,
                     "all5_within_2px": ok2, "any_line_>=0.5sp_off": far}
    out["line_thickness_median_px"] = float(np.median([t for r in rows for t in r["th"]]))
    (SCRATCH / f"{doc}.farhead.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "farhead":
        farhead(sys.argv[2])
    if cmd == "lane_sheet_rate":
        lane_sheet_rate()
    if cmd == "sheet":
        sheet()
    if cmd == "extract":
        extract(sys.argv[2])
    elif cmd == "control":
        control()
    elif cmd == "measure":
        measure(sys.argv[2])
    elif cmd == "summary":
        summary()
