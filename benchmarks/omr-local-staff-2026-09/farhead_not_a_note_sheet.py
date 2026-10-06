"""lane-farhead-not-a-note (2026-10-05): ONE sheet of 12 seeded refusals of the not-a-note gate, out of sample (the
10-04 run-2 records; Sean's own tiles 1,5,7,8 and 2,12 are excluded from the draw). Each tile: the box the detector
called a notehead (ORANGE), the evidence that refused it drawn in MAGENTA, and the reason in words under it.

  magenta vertical line  = the measure cut (barline) the record measured, runs through / beside the box
  magenta rectangle      = the text / dynamic box lying over the head, or (tremolo) the head box with a slash across its stem
  magenta bracket below  = the box's width against one staff space (too narrow)
  magenta horizontal     = the edge of the measure cell the box is cut off by (clipped sliver)

Every drawn MAGENTA barline is re-measured against the pixel COLUMNS (the nearest tall dark run over the staff rows);
the offsets are printed. A cell edge, a text box and a width bracket are not ink lines: they are checked for what they
are (the box holds ink; the text box really overlaps; the width is the box's own).

  python3 farhead_not_a_note_sheet.py out.png [seed] [all]      # `all` = no quotas: print every refusal's evidence
"""
from __future__ import annotations
import collections, json, os, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
import farhead_note_first_oos as OOS
import farhead_not_a_note_eval as E
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

MAGENTA, ORANGE = (255, 0, 255), (0, 140, 255)
QUOTA = [("on_a_barline", 4), ("tremolo_slash", 2), ("on_text", 2), ("too_narrow", 2), ("clipped_fragment", 2)]
if os.environ.get("NAN_QUOTA"):           # diagnostic only: NAN_QUOTA=on_a_barline:12
    QUOTA = [(a.split(":")[0], int(a.split(":")[1])) for a in os.environ["NAN_QUOTA"].split(",")]
EXCLUDE = {s for (_d, s, _w) in E.SEAN.values()}
TILE_PX_PER_SP = 36.0


def barline_columns(gray, x, y0, y1, sp, thr):
    """nearest tall dark run of columns to x (within 1.2 sp): (centre, offset) or (None, None). A column is dark where
    >= 85% of the rows y0..y1 (the staff's own height) are ink."""
    lo, hi = max(0, int(x - 1.2 * sp)), min(gray.shape[1], int(x + 1.2 * sp))
    band = gray[int(y0):int(y1), lo:hi] <= thr
    if band.size == 0:
        return None, None
    cols = np.where(band.mean(axis=0) >= 0.85)[0]
    if len(cols) == 0:
        return None, None
    runs, cur = [], [cols[0]]
    for c in cols[1:]:
        if c == cur[-1] + 1:
            cur.append(c)
        else:
            runs.append(cur); cur = [c]
    runs.append(cur)
    best = min(runs, key=lambda r: abs(lo + np.mean(r) - x))
    centre = lo + float(np.mean(best))
    return centre, centre - x


def tile(row, gray, no, checks):
    box, sp, lines = row["box"], row["spacing"], row["lines"]
    r = row["now"]
    S = TILE_PX_PER_SP / sp
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    xa, xb = int(cx - 4.5 * sp), int(cx + 4.5 * sp)
    ya, yb = int(cy - 3.5 * sp), int(cy + 3.5 * sp)
    xa, ya = max(0, xa), max(0, ya)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    X = lambda x: int(round((x - xa) * S))
    Y = lambda y: int(round((y - ya) * S))
    for kind, g in r["drawn"]:
        if kind == "barline":
            cv2.line(crop, (X(g), 0), (X(g), crop.shape[0] - 1), MAGENTA, 2)
            c, off = barline_columns(gray, g, min(lines), max(lines), sp, thr)
            checks.append((no, "barline x", round(float(g), 1), None if off is None else round(off, 1)))
        elif kind == "text":
            cv2.rectangle(crop, (X(g[0]), Y(g[1])), (X(g[2]), Y(g[3])), MAGENTA, 2)
            ox = min(box[2], g[2]) - max(box[0], g[0]); oy = min(box[3], g[3]) - max(box[1], g[1])
            frac = ox * oy / ((box[2] - box[0]) * (box[3] - box[1])) if ox > 0 and oy > 0 else 0.0
            checks.append((no, "text box overlap", round(frac, 2), 0.0 if frac >= FH.TEXT_OVERLAP_MIN else 99.0))
        elif kind == "slash":
            cv2.rectangle(crop, (X(g[0]) - 4, Y(g[1]) - 4), (X(g[2]) + 4, Y(g[3]) + 4), MAGENTA, 2)
            cross = row["cross"]
            checks.append((no, "slash: angle/elong/fill/shares", (cross.get("angle_deg"), cross.get("elongation"),
                           cross.get("fill"), cross.get("left_share"), cross.get("right_share")), 0.0))
        elif kind == "box":
            y = Y(box[3]) + 10
            cv2.line(crop, (X(box[0]), y), (X(box[2]), y), MAGENTA, 3)
            cv2.line(crop, (X(box[0]), y - 5), (X(box[0]), y + 5), MAGENTA, 3)
            cv2.line(crop, (X(box[2]), y - 5), (X(box[2]), y + 5), MAGENTA, 3)
            w = (box[2] - box[0]) / sp
            cv2.line(crop, (X(box[0]), y + 14), (X(box[0] + sp), y + 14), (120, 120, 120), 3)   # one staff space, grey
            checks.append((no, "box width (sp)", round(w, 2), 0.0 if w < 1.0 else 99.0))
        elif kind == "cell_edge":
            cv2.line(crop, (0, Y(g)), (crop.shape[1] - 1, Y(g)), MAGENTA, 2)
            near = min(abs(box[1] - g), abs(box[3] - g))
            checks.append((no, "box edge to cell edge (px)", round(float(near), 1), 0.0 if near <= 1.0 else 99.0))
    cv2.rectangle(crop, (X(box[0]), Y(box[1])), (X(box[2]), Y(box[3])), ORANGE, 2)
    ink = float((gray[int(box[1]):int(box[3]), int(box[0]):int(box[2])] <= thr).mean())
    checks.append((no, "box holds ink (fraction)", round(ink, 2), 0.0 if ink >= 0.25 else 99.0))
    return crop


def build_rows():
    rows_by_doc = {}
    for which in ("litolff", "brahms"):
        doc, fname = OOS.RECORDS[which]
        rec = EXP.Record(load_record(OOS.SHARED / fname))
        refused = json.loads((HERE / f"farhead_not_a_note_oos_{which}.json").read_text())["refused"]
        rows_by_doc[which] = (doc, rec, refused)
    return rows_by_doc


def main(out, seed, show_all=False):
    rows_by_doc = build_rows()
    rng = random.Random(seed)
    pools = collections.defaultdict(list)
    for which, (doc, rec, refused) in rows_by_doc.items():
        for s, reason, also in refused:
            if s in EXCLUDE:
                continue
            if os.environ.get("NAN_ONLY_SOLE") and also:      # diagnostic: only refusals NO other reason also makes
                continue
            pools[reason].append((which, s))
    picks = []
    for reason, n in QUOTA:
        pool = sorted(pools[reason])
        chosen = pool if show_all else rng.sample(pool, min(n * (3 if os.environ.get("NAN_ONLY_UNDECIDED") else 1), len(pool)))
        picks += [(w, s, reason) for (w, s) in chosen]
    # one page raster per (doc, page); evidence per record
    grays, rows = {}, []
    cache = {}
    for which, s, reason in picks:
        doc, rec, _ = rows_by_doc[which]
        page = int(s.split("/")[1])
        if which not in cache:
            cache[which] = (E.evidence_index(rec), {})
        get, gl = cache[which]
        if not gl:
            for o in rec.observations:
                if o["quantity"] == Q.GLYPH_BOX and o.get("value"):
                    pb = (o.get("detail") or {}).get("bbox_page_px")
                    if pb:
                        gl.setdefault(int(o["subject"].split("/")[1]), []).append(
                            (o["subject"], o["value"][0], tuple(float(v) for v in pb), 1.0))
        heads, staff_lines, page_boxes = OOS.page_inputs(rec, page, gl[page])
        h = [x for x in heads if x["subject"] == s][0]
        if (which, page) not in grays:
            cfg = ts.DOCS[doc]
            grays[(which, page)] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        gray = grays[(which, page)]
        lines = FH.frame_lines_for_head(gray, h["global_lines"], h["box"])
        sp = (max(lines) - min(lines)) / 4.0
        text = [tuple(b) for (_s, c, b) in page_boxes if lg.is_text_class(c)]
        ev = get(s)
        evd = E.evidence_index(rec, with_verdict=True)(s)
        now = FH.not_a_note_reason(h["box"], h["cls"], sp, cell_box=ev["cell_box"], cross=ev.get("cross"),
                                   barline_xs=ev["barline_xs"], text_boxes=text)
        rows.append(dict(doc=which, subject=s, page=page, box=h["box"], cls=h["cls"], spacing=sp, lines=lines,
                         want=reason, now=now, cross=ev.get("cross") or {}, decided=evd.get("decided"),
                         gray_key=(which, page)))
    # control that can fail: the refusal on the rendered page, with the LOCAL spacing, must be the one the
    # out-of-sample count (global spacing) named
    same = sum(1 for r in rows if r["now"] and r["now"]["reason"] == r["want"])
    print(f"refusal re-derived on the rendered page (local spacing) names the same reason: {same}/{len(rows)}")
    for r in rows:
        if not r["now"] or r["now"]["reason"] != r["want"]:
            print("   DIFFERS", r["subject"], r["want"], "->", r["now"] and r["now"]["reason"])
    rows = [r for r in rows if r["now"]]
    if os.environ.get("NAN_ONLY_UNDECIDED"):
        rows = [r for r in rows if not r["decided"]]
    if show_all:
        for i, r in enumerate(rows, 1):
            print(i, r["doc"], r["subject"], r["now"]["reason"], r["now"]["also"], "| record verdict:", r["decided"])
        return
    checks, cells = [], []
    TW = 330
    for no, r in enumerate(rows, 1):
        crop = tile(r, grays[r["gray_key"]], no, checks)
        H = crop.shape[0]
        canvas = np.full((H + 74, TW, 3), 255, np.uint8)
        w = min(TW, crop.shape[1])
        canvas[:H, :w] = crop[:, :w]
        short = r["subject"].replace("glyph/", "")
        cv2.putText(canvas, f"{no}", (4, H + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(canvas, f"{r['doc']} p{r['page']}  glyph {short}", (30, H + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        words = r["now"]["words"]
        for li, chunk in enumerate([words[:48], words[48:96]]):
            if chunk:
                cv2.putText(canvas, chunk, (4, H + 36 + 15 * li), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 0, 160), 1)
        extra = ("record already says: " + r["decided"]) if r["decided"] else "record has NOT called this a non-note"
        cv2.putText(canvas, extra, (4, H + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)
        cells.append(canvas)
    rows_img = []
    for k in range(0, len(cells), 4):
        grp = cells[k:k + 4]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < 4:
            grp.append(np.full((h, TW + 8, 3), 255, np.uint8))
        rows_img.append(np.hstack(grp))
    w = max(r.shape[1] for r in rows_img)
    body = np.vstack([np.pad(r, ((4, 4), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows_img])
    lines_ = ["ORANGE box: what the detector called a notehead.   MAGENTA: the evidence from the record that refused it (the barline",
              "the record measured, the text box lying over it, the slash across its stem, the width against one staff space [grey], the cell edge).",
              "Each tile says in words WHY, and whether the record's own not-a-notehead verdict already said so."]
    legend = np.full((26 * len(lines_) + 6, w, 3), 255, np.uint8)
    for i, t in enumerate(lines_):
        cv2.putText(legend, t, (8, 20 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack([legend, body]))
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    hid = [c for c in checks if c[3] is None]
    print("drawn / checked", len(checks), "| within 2 px (or true):", len(checks) - len(bad) - len(hid),
          "| off by more than 2 px:", bad, "| no ink column found:", hid)
    for no, r in enumerate(rows, 1):
        print(no, r["doc"], r["subject"], "page", r["page"], r["now"]["reason"], "| also", r["now"]["also"],
              "| record verdict:", r["decided"])
    for c in checks:
        print("   check", c)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20261005, len(sys.argv) > 3 and sys.argv[3] == "all")
