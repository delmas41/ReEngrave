"""lane-owner-by-ledgers (2026-10-05): ONE sheet of 12 seeded CHANGES of owner, read off the ledgers.

A change = the ledger witness names a staff other than the one the recorded `glyph_owner` named (the filing staff
where the recorded verdict abstained). Each tile draws BOTH staves' edges at the head's x (BLUE = the old owner,
CYAN = the new owner), the note's box (orange), the ledgers the reader counted toward the NEW staff (solid green),
the note's own line (red), what it saw toward the OLD staff (dashed), and says in words why the note moved. Every
drawn line is re-measured against pixel rows.

  python3 farhead_owner_by_ledgers_sheet.py litolff.json brahms.json out.png [seed]
"""
from __future__ import annotations
import collections, json, random, sys, textwrap
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import truth_set_2_44c as ts
import farhead_note_first_oos as OOS
from farhead_note_first_sheet import remeasure
from farhead_owner_by_ledgers import redecide
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

BLUE, CYAN, GREEN, RED, ORANGE, GREY = (255, 80, 0), (230, 200, 0), (0, 150, 0), (0, 0, 255), (0, 140, 255), (130, 130, 130)
TW = 372


def effective_old(r):
    return r["old_value"] if r["old_outcome"] == "decided" else r["own"]


def is_change(r):
    return r["owner"] is not None and r["owner"] != effective_old(r)


def staff_words(key):
    p, s, st = key.split("/")[1:4]
    return f"staff {st} of system {s} (page {p})"


def new_words(r):
    c = r["cands"][r["owner"]]
    if c["how"] == "geometry":
        return (f"the head lies on the lines of {staff_words(r['owner'])}, or in the first space outside them "
                f"(half-step {c['pos']} from its top line), so no ledger is needed there")
    k = c.get("k")
    n = len(c.get("between") or [])
    kind = "on" if c.get("kind") == "on" else "in the space beyond"
    return (f"the note's own line is {kind} ledger {k} of the new staff; {n} ledger(s) counted between it and the "
            f"staff edge, every gap one ledger apart")


def old_words(r):
    old = effective_old(r)
    c = r["cands"].get(old)
    if c is None:
        return "the old staff was not read"
    rs = (c.get("reason") or "").split(" (")[0]
    gaps = c.get("gaps")
    return {"no_rungs": "no ledger line is found toward it",
            "no_line_at_the_note_box": "no line touches the note on the way to it",
            "line_at_the_box_not_a_ledger_for_this_head": "the line at the note is not a ledger for it",
            "count_does_not_fit": "the ledgers toward it do not make a chain" + (
                " (gaps " + ", ".join(f"{g:.1f}" for g in gaps) + " sp)" if gaps else "")}.get(
        rs, rs or "no chain of ledgers reaches it")


def words(r):
    return (f"moved from {staff_words(effective_old(r))} to {staff_words(r['owner'])} because {new_words(r)}; "
            f"toward the old staff: {old_words(r)}.")


def local_edge(gray, lines, box):
    ls = FH.frame_lines_for_head(gray, lines, tuple(box))
    cy = (box[1] + box[3]) / 2.0
    return (max(ls) if cy > max(ls) else min(ls) if cy < min(ls) else (max(ls) if cy > (min(ls) + max(ls)) / 2 else min(ls))), \
        (max(ls) - min(ls)) / 4.0


def tile(r, gray, lines_of, no, checks):
    box = r["cands"][r["owner"]].get("box_used") or r["cands"][r["own"]].get("box_used") or r["box"]
    old, new = effective_old(r), r["owner"]
    e_old, sp = local_edge(gray, lines_of[old], r["box"])
    e_new, sp_n = local_edge(gray, lines_of[new], r["box"])
    sp = (sp + sp_n) / 2.0
    cn, co = r["cands"][new], r["cands"].get(old) or {}
    ys = [e_old, e_new, r["box"][1], r["box"][3]]
    cx = (r["box"][0] + r["box"][2]) / 2.0
    ya, yb = int(min(ys) - 1.4 * sp), int(max(ys) + 1.4 * sp)
    S = min(24.0 / sp, 520.0 / max(1, yb - ya))
    xa, xb = max(0, int(cx - 7.0 * sp)), int(cx + 7.0 * sp)
    ya = max(0, ya)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    W = crop.shape[1]
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    left = (int(r["box"][0] - 1.0 * sp), int(r["box"][0] - 0.1 * sp))
    right = (int(r["box"][2] + 0.1 * sp), int(r["box"][2] + 1.0 * sp))
    broad = ((int(r["box"][0] - 4.0 * sp), int(r["box"][0] - 0.1 * sp)), (int(r["box"][2] + 0.1 * sp), int(r["box"][2] + 4.0 * sp)))

    def Y(y):
        return int(round((y - ya) * S))

    def measure(y, label):
        for cols in ((left, right), broad):
            peaks = [remeasure(gray, y, *c, thr) for c in cols]
            peaks = [p for p in peaks if p[0] is not None]
            if peaks:
                off = min(abs(p[1]) for p in peaks)
                checks.append((no, label, round(float(y), 1), round(off, 1)))
                return off
        checks.append((no, label, round(float(y), 1), None))
        return None

    def line(y, colour, label, dashed=False, text=None, thick=2):
        yy = Y(y)
        if dashed:
            for x in range(0, W, 12):
                cv2.line(crop, (x, yy), (min(W - 1, x + 6), yy), colour, thick)
        else:
            cv2.line(crop, (0, yy), (W - 1, yy), colour, thick)
        off = measure(y, label)
        if text:
            t = text + (" (hidden)" if off is None else f" (!{off:.0f}px)" if off > 2 else "")
            cv2.putText(crop, t, (3, yy - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.34, colour if colour != CYAN else (160, 140, 0), 1, cv2.LINE_AA)

    line(e_old, BLUE, "old staff edge", text="old owner's edge", thick=3)
    line(e_new, CYAN, "new staff edge", text="new owner's edge", thick=3)
    # what each staff's chain looked like
    for c, solid, who in ((co, False, "old"), (cn, True, "new")):
        for i, b in enumerate(c.get("between") or []):
            line(b, GREEN, f"{who} ledger {i + 1}", dashed=not solid, text=f"{who} ledger {i + 1}", thick=2)
        if c.get("line_y") is not None:
            line(c["line_y"], RED, f"{who} note line", dashed=not solid, text=f"{who}: note's line", thick=1)
    b = r["box"]
    cv2.rectangle(crop, (int((b[0] - xa) * S), int((b[1] - ya) * S)), (int((b[2] - xa) * S), int((b[3] - ya) * S)), ORANGE, 2)
    return crop


def sheet(picks, grays, lines_of, out):
    checks, cells = [], []
    for no, r in picks:
        crop = tile(r, grays[(r["doc"], r["page"])], lines_of[r["doc"]], no, checks)
        H = crop.shape[0]
        wrap = textwrap.wrap(words(r), 58)[:7]
        cap_h = 20 + 14 * len(wrap)
        canvas = np.full((H + cap_h, TW, 3), 255, np.uint8)
        w = min(TW, crop.shape[1])
        canvas[:H, :w] = crop[:, :w]
        cv2.putText(canvas, f"{no}", (4, H + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
        cv2.putText(canvas, f"{r['doc']} {r['subject'].replace('glyph/', '')}", (30, H + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        for i, t in enumerate(wrap):
            cv2.putText(canvas, t, (4, H + 30 + 14 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (0, 0, 150), 1, cv2.LINE_AA)
        cells.append(canvas)
    cols, rows_img = 4, []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, TW + 8, 3), 255, np.uint8))
        rows_img.append(np.hstack(grp))
    w = max(r.shape[1] for r in rows_img)
    body = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows_img])
    leg = ["ORANGE box: the note.  BLUE line: the OLD owner's staff edge (measured at the note).  CYAN line: the NEW owner's staff edge.",
           "GREEN solid: a ledger counted toward the new staff.  GREEN dashed: a ledger seen toward the old staff.  RED: the note's own line (dashed = toward the old staff).",
           "Every drawn line was re-measured against pixel rows; '(hidden)' = the head covers it, '(!Npx)' = more than 2 px from the ink row.  NOT yet adjudicated by Sean."]
    legend = np.full((24 * len(leg) + 6, w, 3), 255, np.uint8)
    for i, t in enumerate(leg):
        cv2.putText(legend, t, (8, 18 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack([legend, body]))
    return checks


def main(paths, out, seed):
    rng = random.Random(seed)
    by_doc = {}
    for p in paths:
        rows = [redecide(r) for r in json.loads(Path(p).read_text())]
        by_doc[rows[0]["doc"]] = rows
    picks, need = [], collections.defaultdict(set)
    import os
    chosen = os.environ.get("SHEET_SUBJECTS")        # "brahms:glyph/5/1/2/3/20,litolff:..." -- a look at named heads
    if chosen:
        for spec in chosen.split(","):
            doc, sub = spec.split(":")
            r = next(x for x in by_doc[doc] if x["subject"] == sub)
            r = dict(r, owner=r["owner"] or r["neighbour"] or r["own"])
            picks.append(r)
            need[doc].update([effective_old(r), r["owner"]])
    for doc in (() if chosen else ("litolff", "brahms")):
        import statistics
        med_w = statistics.median(r["box"][2] - r["box"][0] for r in by_doc[doc])
        allchg = [r for r in by_doc[doc] if is_change(r)]
        # a box narrower than 0.6 x the document's median far-head width is a barline / stem sliver the product
        # refuses elsewhere (CLAUDE.md §10: Breitkopf SHATTERS); the sample is drawn from the real-sized boxes
        pool = sorted((r for r in allchg if (r["box"][2] - r["box"][0]) >= 0.6 * med_w), key=lambda r: r["subject"])
        print(doc, "changes", len(allchg), "of", len(by_doc[doc]), "| real-sized boxes (sampled from):", len(pool))
        for r in rng.sample(pool, 6):
            picks.append(r)
            need[doc].update([effective_old(r), r["owner"]])
    lines_of, grays = {}, {}
    for doc, keys in need.items():
        d, fname = OOS.RECORDS[doc]
        rec = EXP.Record(load_record(OOS.SHARED / fname))
        lines_of[doc] = {k: [float(v) for v in rec.obs(Q.STAFF_LINES, k)[-1]["value"]] for k in keys}
        del rec
    for r in picks:
        k = (r["doc"], r["page"])
        if k not in grays:
            cfg = ts.DOCS[OOS.RECORDS[r["doc"]][0]]
            grays[k] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    ordered = list(enumerate(picks, 1))
    checks = sheet(ordered, grays, lines_of, out)
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    hid = [c for c in checks if c[3] is None]
    print("drawn lines", len(checks), "| within 2 px of an ink row:", len(checks) - len(bad) - len(hid),
          "| off by more than 2 px:", bad, "| hidden by the head (no ink row beside it):", len(hid))
    for no, r in ordered:
        print(no, r["doc"], r["subject"], "p", r["page"], "|", words(r))


if __name__ == "__main__":
    main(sys.argv[1:3], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 20261005)
