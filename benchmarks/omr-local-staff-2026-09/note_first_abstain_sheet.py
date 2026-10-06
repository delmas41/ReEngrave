"""lane-note-first-abstain-sheet (2026-10-05): WHY the note-first far-head reader abstains. READ ONLY -- no reader code
changed, no gather. Re-runs the reader exactly as `farhead_note_first_oos.py` does (the 10-04 run-2 records, the page
re-rendered in the gather's own deskewed frame at 600 dpi), then

  * counts the abstentions by reason (and checks they equal the committed oos json: a control that can fail);
  * for count_does_not_fit: the ledgers FOUND against the ledgers the distance EXPECTS, and which gap broke the rule;
  * for every abstaining far head: is its box INSIDE, or TOUCHING, another staff of the page (a hint it belongs to it);
  * ONE sheet: for each of the top three reasons, 4 seeded-random examples (2 Litolff, 2 Brahms), 12 tiles.
    Colours: orange = the note's box; blue = the staff's edge; green = a line the reader counted; grey dashed = a
    line it saw in the gap and rejected (with why); red bracket = the place it looked for the note's own line; a
    red thin line = the note's line, where it found one. Every drawn line is re-measured against pixel rows.

  python3 note_first_abstain_sheet.py out.png [seed]
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
from farhead_note_first_sheet import remeasure
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

RANGES = {"litolff": (4, 16), "brahms": (2, 26)}
REASONS = [("no_line_at_the_note_box", "couldn't find a line at the note"),
           ("no_rungs", "no ledger lines found"),
           ("count_does_not_fit", "the ledger count didn't fit the gap")]
BLUE, GREEN, RED, ORANGE, GREY = (255, 80, 0), (0, 150, 0), (0, 0, 255), (0, 140, 255), (130, 130, 130)
PITCH = 1.05      # a ledger pitch in staff spaces (Litolff ~1.1, Brahms ~1.0), to turn a distance into an expected count


def key(reason):
    return OOS.reason_key(reason)


def other_staves(rec):
    lines, ext = {}, {}
    for o in rec.observations:
        q = o["quantity"]
        if q == Q.STAFF_LINES and o["subject"].startswith("staff/") and o.get("value"):
            lines[o["subject"]] = [float(v) for v in o["value"]]
        elif q == Q.STAFF_EXTENT and o["subject"].startswith("staff/") and o.get("value"):
            ext[o["subject"]] = [float(v) for v in o["value"]]
    by_page = collections.defaultdict(list)
    for sk, gl in lines.items():
        if len(gl) >= 2 and sk in ext:
            by_page[int(sk.split("/")[1])].append((sk, min(gl), max(gl), ext[sk][0], ext[sk][1]))
    return by_page


def vs_other_staff(row, by_page):
    """'inside' = the box centre is within another staff's lines (and its x extent); 'touching' = the box overlaps
    that staff's band (a quarter space of slack) without its centre being inside; else None."""
    x0, y0, x1, y1 = row["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    own = "staff/" + "/".join(row["subject"].split("/")[1:4])
    best = (None, None)
    for sk, top, bot, ex0, ex1 in by_page.get(row["page"], []):
        if sk == own or not (ex0 <= cx <= ex1):
            continue
        slack = 0.25 * (bot - top) / 4.0
        if top <= cy <= bot:
            return "inside", sk
        if y1 >= top - slack and y0 <= bot + slack:
            best = ("touching", sk)
    return best


def nearest_other_staff(row, by_page):
    """(distance of the box centre to the nearest OTHER staff's band, in that staff's spaces; distance of the box
    centre to its own staff's band, in its own spaces). A head nearer another staff than its own is a hint it is that
    staff's."""
    x0, y0, x1, y1 = row["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    own = "staff/" + "/".join(row["subject"].split("/")[1:4])
    d_other = None
    d_own = None
    for sk, top, bot, ex0, ex1 in by_page.get(row["page"], []):
        sp = (bot - top) / 4.0
        if sp <= 0:
            continue
        d = max(top - cy, cy - bot, 0.0) / sp
        if sk == own:
            d_own = d
        elif ex0 - 2 * sp <= cx <= ex1 + 2 * sp and (d_other is None or d < d_other):
            d_other = d
    return d_other, d_own


def run_doc(which, want, results_out, grays_out):
    p0, p1 = RANGES[which]
    doc, fname = OOS.RECORDS[which]
    cfg = ts.DOCS[doc]
    print("loading", fname, flush=True)
    rec = EXP.Record(load_record(OOS.SHARED / fname))
    by_page = other_staves(rec)
    glyphs = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            glyphs[int(o["subject"].split("/")[1])].append(
                (o["subject"], o["value"][0], tuple(float(v) for v in pb),
                 float(o.get("score") if o.get("score") is not None else 1.0)))
    ctxs, pool = {}, []
    for page in range(p0, p1 + 1):
        if page not in glyphs:
            continue
        heads, staff_lines, page_boxes = OOS.page_inputs(rec, page, glyphs[page])
        far = [h for h in heads if lg.far_head_needs_ledger_read(h["pos"])]
        if not far:
            continue
        pi = render_page_matching_gather(cfg["pdf"], page, 600)
        gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
        ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
        pool.extend(ctx.samples)
        ctxs[page] = (ctx, far)
        print(which, "page", page, "far", len(far), flush=True)
    pooled = FH.pooled_shape(pool)
    last, orig = {}, lg.derive_note_first_step

    def wrapped(gray, head_box, edge, sign, spacing, items, **kw):
        nf = orig(gray, head_box, edge, sign, spacing, items, **kw)
        last.clear()
        last.update(items=[float(v) for v in items], sign=sign, spacing=spacing, head_box=tuple(head_box), nf=nf)
        return nf
    lg.derive_note_first_step = wrapped
    FH.READER_KEYWORDS["note_first"] = True
    rows = []
    try:
        for page, (ctx, far) in ctxs.items():
            if ctx.shape is None and pooled is not None:
                ctx.adopt(pooled, f"document pool n={len(pool)}")
            for h in far:
                last.clear()
                r = ctx.read(h["subject"], h["box"], h["cls"], h["global_lines"])
                det = r.get("detail") or {}
                nf = det.get("note_first") or {}
                row = dict(doc=which, subject=h["subject"], page=page, box=list(h["box"]), pos=r["pos"],
                           reason=r["reason"], edge_y=det.get("edge_y"),
                           line_y=nf.get("line_y"), between=nf.get("between") or [], gaps=nf.get("gaps") or [],
                           box_used=r.get("box_used"))
                row["other_staff"], row["other_staff_key"] = vs_other_staff(row, by_page)
                row["d_other"], row["d_own"] = nearest_other_staff(row, by_page)
                if h["subject"] in want:
                    row["rungs"] = last.get("items")
                    row["sign"], row["spacing"] = last.get("sign"), last.get("spacing")
                    row["head_box"] = last.get("head_box")
                    assert last.get("nf") and r["reason"].startswith(last["nf"]["reason"]), "captured the wrong call"
                    grays_out[(which, page)] = ctx.gray
                rows.append(row)
    finally:
        lg.derive_note_first_step = orig
    results_out[which] = rows
    del rec


def stats(which, rows, json_path):
    ab = [r for r in rows if r["pos"] is None]
    c = collections.Counter(key(r["reason"]) for r in ab)
    print(f"== {which}: far heads {len(rows)}; decided {len(rows) - len(ab)}; abstained {len(ab)}")
    for k, v in c.most_common():
        print(f"   {v:5d}  {k}")
    old = json.loads(Path(json_path).read_text())
    oc = collections.Counter(key(r["new"]["reason"]) for r in old if r["new"]["pos"] is None)
    print("   control: re-run reasons equal the committed oos json:", c == oc, "(json:", dict(oc), ")")
    cnf = [r for r in ab if key(r["reason"]) == "count_does_not_fit"]
    tab, kinds = collections.Counter(), collections.Counter()
    for r in cnf:
        d = sum(r["gaps"])
        found = len(r["between"])
        expected = max(0, int(round(d / PITCH)) - 1)
        tab[(found, expected)] += 1
        wide = any(g > lg.NOTE_GAP_MAX_SPACES for g in r["gaps"])
        narrow = any(g < lg.NOTE_GAP_MIN_SPACES for g in r["gaps"])
        kinds["a gap too wide (a ledger missed)" if wide and not narrow else
              "a gap too narrow (two marks of one)" if narrow and not wide else "both"] += 1
    print(f"   count_does_not_fit {len(cnf)}: which gap broke the rule:", dict(kinds))
    print("   found-between vs expected-between (expected = round(distance/1.05 sp) - 1):")
    for (f, e), v in sorted(tab.items()):
        print(f"      found {f} expected {e}: {v}")
    print("   found fewer than expected", sum(v for (f, e), v in tab.items() if f < e),
          "| equal", sum(v for (f, e), v in tab.items() if f == e),
          "| more", sum(v for (f, e), v in tab.items() if f > e))
    print("   inside / touching ANOTHER staff, by reason (abstaining), and the decided far heads as a control:")
    for k, _ in REASONS:
        sub = [r for r in ab if key(r["reason"]) == k]
        io = collections.Counter(r["other_staff"] for r in sub)
        print(f"      {k:26s} n={len(sub):5d} inside {io['inside']:4d} touching {io['touching']:4d}")
    def nearer(sub):
        return sum(1 for r in sub if r["d_other"] is not None and r["d_own"] is not None and r["d_other"] < r["d_own"])
    print("   box centre NEARER another staff than its own:",
          {k: f"{nearer([r for r in ab if key(r['reason']) == k])}/{sum(1 for r in ab if key(r['reason']) == k)}"
           for k, _ in REASONS},
          "| all abstaining", f"{nearer(ab)}/{len(ab)}",
          "| decided (control)", f"{nearer([r for r in rows if r['pos'] is not None])}/{len(rows) - len(ab)}")
    dec = [r for r in rows if r["pos"] is not None]
    io = collections.Counter(r["other_staff"] for r in dec)
    print(f"      decided (control)          n={len(dec):5d} inside {io['inside']:4d} touching {io['touching']:4d}")
    io = collections.Counter(r["other_staff"] for r in ab)
    print(f"      ALL abstaining             n={len(ab):5d} inside {io['inside']:4d} touching {io['touching']:4d}")


def why(row):
    """(y, plain-words label, colour) for every candidate line the reader saw, in the gap."""
    sign, sp, edge, line_y = row["sign"], row["spacing"], row["edge_y"], row["line_y"]
    hb = row["head_box"]
    near_y = hb[3] if sign < 0 else hb[1]
    out = []
    for r in sorted(row["rungs"], key=lambda v: sign * v):
        if any(abs(r - b) < 1.5 for b in row["between"]):
            out.append((r, "counted", GREEN))
        elif sign * (r - edge) <= lg.NOTE_BETWEEN_MIN_SPACES * sp:
            out.append((r, "too near the staff", GREY))
        elif line_y is not None and abs(r - line_y) < lg.NOTE_BETWEEN_MIN_SPACES * sp:
            out.append((r, "the note's own line", GREY))
        elif line_y is not None and sign * (r - line_y) > 0:
            out.append((r, "beyond the note's line", GREY))
        elif line_y is not None:
            out.append((r, "too near the previous", GREY))
        else:
            out.append((r, f"{abs(sign * (r - near_y) / sp):.1f} sp from the note", GREY))
    for b in row["between"]:
        if not any(abs(b - r) < 1.5 for r in row["rungs"]):
            out.append((b, "found by a closer look", GREEN))
    return out


def tile(row, gray, no, checks):
    sp, sign, edge = row["spacing"], row["sign"], row["edge_y"]
    box = row["box_used"] or row["box"]
    S = 36.0 / sp
    line_y = row["line_y"]
    cands = why(row)
    near_y = box[3] if sign < 0 else box[1]
    lo, hi = lg.NOTE_LINE_NEAR_BAND_SPACES
    band = sorted([near_y + sign * lo * sp, near_y + sign * hi * sp])
    mid = (box[1] + box[3]) / 2.0
    ys = [edge, box[1], box[3]] + [c[0] for c in cands] + ([line_y] if line_y is not None else [])
    cx = (box[0] + box[2]) / 2.0
    xa, xb = int(cx - 4.5 * sp), int(cx + 4.5 * sp)
    ya, yb = int(min(ys) - 1.3 * sp), int(max(ys) + 1.3 * sp)
    xa, ya = max(0, xa), max(0, ya)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    left = (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp))
    right = (int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp))
    W = crop.shape[1]

    def Y(y):
        return int(round((y - ya) * S))

    def X(x):
        return int(round((x - xa) * S))

    broad = ((int(box[0] - 4.0 * sp), int(box[0] - 0.1 * sp)), (int(box[2] + 0.1 * sp), int(box[2] + 4.0 * sp)))

    def measure(y, label):
        """offset in px between the drawn row and the nearest pixel ink row (flanks of the head, then a broader band
        either side); None where no row within 6 px is inked there (the line is hidden behind the head)."""
        for cols in ((left, right), broad):
            peaks = [remeasure(gray, y, *c, thr) for c in cols]
            peaks = [p for p in peaks if p[0] is not None]
            if peaks:
                off = min(abs(p[1]) for p in peaks)
                checks.append((no, label, round(float(y), 1), round(off, 1)))
                return off
        checks.append((no, label, round(float(y), 1), None))
        return None

    def put(text, y, colour):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
        x = W - tw - 14
        cv2.rectangle(crop, (x - 2, y - th - 2), (W - 12, y + 3), (255, 255, 255), -1)
        cv2.putText(crop, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, colour, 1, cv2.LINE_AA)

    cv2.line(crop, (0, Y(edge)), (W - 1, Y(edge)), BLUE, 2)
    measure(edge, "staff edge")
    labels_y = []
    for r, why_, colour in cands:
        if line_y is not None and why_ == "the note's own line":
            continue                     # drawn once, as the red line
        yy = Y(r)
        if colour == GREEN:
            cv2.line(crop, (0, yy), (W - 1, yy), colour, 2)
        else:
            for x in range(0, W, 14):
                cv2.line(crop, (x, yy), (min(W - 1, x + 7), yy), colour, 2)
        off = measure(r, f"line ({why_})")
        if off is None:
            why_ += " (hidden)"
        elif off > 2.0:
            why_ += f" (!{off:.0f}px off)"
        ty = yy - 3
        while any(abs(ty - t) < 11 for t in labels_y):
            ty += 11
        labels_y.append(ty)
        put(why_, ty, colour if colour == GREEN else (90, 90, 90))
    if line_y is not None:
        cv2.line(crop, (0, Y(line_y)), (W - 1, Y(line_y)), RED, 1)
        measure(line_y, "note's line")
    for (a, b, xx, d) in ((band[0], band[1], 3, 1),
                          (mid - lg.NOTE_LINE_MIDDLE_BAND_SPACES * sp, mid + lg.NOTE_LINE_MIDDLE_BAND_SPACES * sp, W - 4, -1)):
        cv2.line(crop, (xx, Y(a)), (xx, Y(b)), RED, 2)
        cv2.line(crop, (xx, Y(a)), (xx + 7 * d, Y(a)), RED, 2)
        cv2.line(crop, (xx, Y(b)), (xx + 7 * d, Y(b)), RED, 2)
    cv2.rectangle(crop, (X(box[0]), Y(box[1])), (X(box[2]), Y(box[3])), ORANGE, 2)
    ink = float((gray[int(box[1]):int(box[3]), int(box[0]):int(box[2])] <= thr).mean())
    checks.append((no, "box holds ink (fraction)", round(ink, 2), 0.0 if ink >= 0.25 else 99.0))
    return crop


def sheet(picks, grays, out):
    checks, cells = [], []
    TW = 330
    for no, r in picks:
        crop = tile(r, grays[(r["doc"], r["page"])], no, checks)
        H = crop.shape[0]
        canvas = np.full((H + 56, TW, 3), 255, np.uint8)
        w = min(TW, crop.shape[1])
        canvas[:H, :w] = crop[:, :w]
        short = r["subject"].replace("glyph/", "")
        cv2.putText(canvas, f"{no}", (4, H + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(canvas, f"{r['doc']} p{r['page']}  glyph {short}", (30, H + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        if key(r["reason"]) == "count_does_not_fit":
            line2 = f"gaps {' + '.join(f'{g:.2f}' for g in r['gaps'])} sp; {len(r['between'])} counted"
        else:
            line2 = f"{len(r['rungs'] or [])} line(s) seen on this side"
        osd = {"inside": "INSIDE another staff", "touching": "touches another staff"}.get(r["other_staff"], "clear of other staves")
        if r.get("d_other") is not None and r.get("d_own") is not None:
            osd += f" | next staff {r['d_other']:.1f} sp, own {r['d_own']:.1f} sp"
        cv2.putText(canvas, line2, (4, H + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 160), 1)
        cv2.putText(canvas, osd, (4, H + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 0, 0) if r["other_staff"] else (90, 90, 90), 1)
        cells.append((canvas, no))
    rows_img = []
    for ri, (rk, title) in enumerate(REASONS):
        grp = [c for c, no in cells if (no - 1) // 4 == ri]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        row = np.hstack(grp)
        head = np.full((34, row.shape[1], 3), 235, np.uint8)
        cv2.putText(head, f"{title.upper()}  --  tiles {ri * 4 + 1}-{ri * 4 + 4}", (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2)
        rows_img += [head, row]
    w = max(r.shape[1] for r in rows_img)
    body = np.vstack([np.pad(r, ((3, 3), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows_img])
    legend_lines = ["ORANGE box: the note's head, as the reader boxed it.   BLUE line: the staff's edge, measured locally at the note.",
                    "GREEN line: a ledger line the reader saw and counted.   GREY dashed: a line it saw in the gap and did not count (why, in 2-3 words).",
                    "RED bracket: where it looked for the note's own line (box edge on the staff side, left; box middle, right).  RED thin line: the note's line, where it found one."]
    legend = np.full((26 * len(legend_lines) + 6, w, 3), 255, np.uint8)
    for i, t in enumerate(legend_lines):
        cv2.putText(legend, t, (8, 20 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack([legend, body]))
    return checks


def main(out, seed):
    old = {w: json.loads((HERE / f"farhead_note_first_oos_{w}.json").read_text()) for w in RANGES}
    rng = random.Random(seed)
    picks, want = [], set()
    for rk, title in REASONS:
        for w in ("litolff", "brahms"):
            pool = sorted(r["subject"] for r in old[w] if r["new"]["pos"] is None and key(r["new"]["reason"]) == rk)
            for s in rng.sample(pool, 2):
                picks.append((w, s)); want.add(s)
    results, grays = {}, {}
    cache = Path(os.environ["NFA_CACHE"]) if os.environ.get("NFA_CACHE") else None
    if cache and cache.exists():
        results = json.loads(cache.read_text())
        for w in results:
            stats(w, results[w], HERE / f"farhead_note_first_oos_{w}.json")
            for r in results[w]:
                if r["subject"] in want and (w, r["page"]) not in grays:
                    cfg = ts.DOCS[OOS.RECORDS[w][0]]
                    grays[(w, r["page"])] = cv2.cvtColor(
                        render_page_matching_gather(cfg["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    else:
        for w in ("litolff", "brahms"):
            run_doc(w, want, results, grays)
            stats(w, results[w], HERE / f"farhead_note_first_oos_{w}.json")
        if cache:
            cache.write_text(json.dumps(results))
    index = {(r["doc"], r["subject"]): r for w in results for r in results[w]}
    ordered = [(i + 1, index[p]) for i, p in enumerate(picks)]
    checks = sheet(ordered, grays, out)
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    hid = [c for c in checks if c[3] is None]
    print("drawn lines", len(checks), "| within 2 px of a pixel ink row:", len(checks) - len(bad) - len(hid),
          "| off by more than 2 px:", bad, "| no ink row found:", hid)
    for no, r in ordered:
        print(no, r["doc"], r["subject"], "page", r["page"], key(r["reason"]), "| other staff:", r["other_staff"],
              "| lines seen:", len(r["rungs"] or []), "| gaps", [round(g, 2) for g in r["gaps"]])


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20261005)
