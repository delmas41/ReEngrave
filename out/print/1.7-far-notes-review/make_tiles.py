"""Far-note review tiles for Sean's phone (ROADMAP 1.7; Sean 2026-10-10: "I should take a look at the far notes
just to verify that we are connecting them to the correct staff").

    python3 out/print/1.7-far-notes-review/make_tiles.py \
        --page /Users/seanjohnson/Desktop/ReEngrave-handtruth/data/hand-truth/pages/imslp317803/0.json \
        --record <brahms1-breitkopf-p1.record.json> --pdf <imslp317803.pdf>

One image per FAR head (a notehead in a fully labeled cell with no staff within 1.1 spaces: Sean's page has 92):
the head in red corner brackets, the staff WE connect it to in orange (the record's `glyph_owner` verdict if decided,
else the staff the box is filed on), the nearest staff on the OTHER side of the head in grey. Nothing else of ours is
drawn: no pitch, no duration, no record boxes. Sean's page is only read. Not product code.

Order: disagreements first (we and the ledger-line reference connect it to different staves), then heads the
reference could not place (no ledger boxes), then the rest in page order.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import phone_tile as P  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.hand_truth import store  # noqa: E402
from tools.omr.hand_truth.score_crops import truth_frame_control  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

HALF_WIDTH_SPACES = 5.5   # the crop is 11 staff spaces wide, centred on the head
MARGIN_SPACES = 1.7       # air above the upper staff / below the lower one, for the labels


def band_at(bands, key, cx):
    """The five lines of staff ``key`` as measured in the cell that holds ``cx`` (local, never page-wide)."""
    mine = [b for b in bands if (b.system, b.staff) == key]
    inside = [b for b in mine if b.rect[0] <= cx <= b.rect[2]]
    return inside[0] if inside else min(mine, key=lambda b: abs((b.rect[0] + b.rect[2]) / 2 - cx))


def instrument_name(run, key):
    v = run.standing(f"staff/0/{key[0]}/{key[1]}", "instrument", "ADJUDICATE")
    if v and v["outcome"] == "decided" and isinstance(v.get("value"), dict):
        return v["value"].get("name")
    return None


def connection(copies):
    """(primary glyph, our staff, how) -- the kept copy if there is one, else the best-overlapping copy."""
    if not copies:
        return None, None, "the record has no box on this head"
    kept = [g for g in copies if g.status not in S.KEPT_STATUSES_DROPPED]
    g = (kept or copies)[0]
    if g.owner_outcome == "decided" and g.owner is not None:
        return g, g.owner, f"record glyph_owner verdict (decided: {g.owner_reason})"
    if g.owner_outcome == "uncontested":
        return g, g.filed_staff, "filed on this staff; the record has no glyph_owner verdict for the head"
    return g, g.filed_staff, (f"filed on this staff; glyph_owner {g.owner_outcome} ({g.owner_reason}) -- "
                              "the pipeline would not place it")


def other_staff(bands, staves, ours_key, ours_band, cx, cy):
    """The nearest staff on the opposite side of the head from the staff we connect it to."""
    side = "above" if cy < ours_band.lines[0] else "below" if cy > ours_band.lines[-1] else "inside"
    cands = []
    for k in staves:
        if k == ours_key:
            continue
        b = band_at(bands, k, cx)
        if side == "above" and b.lines[-1] <= cy:
            cands.append((cy - b.lines[-1], k, b))
        elif side == "below" and b.lines[0] >= cy:
            cands.append((b.lines[0] - cy, k, b))
        elif side == "inside":
            cands.append((min(abs(cy - b.lines[0]), abs(cy - b.lines[-1])), k, b))
    if not cands:
        return side, None, None
    _, k, b = min(cands, key=lambda c: c[0])
    return side, k, b


def build(args):
    page = store.load(args.page)
    run = RO.load_run(str(args.record))
    items = S.truth_items(page, derive=True)
    full = S.Scope(S.fully_labeled(page))
    far = [it for it in items if it.family == "notehead" and full.holds(it.rect) and it.derived_how != "staff"]
    heads = [g for g in S.read_glyphs(run, page.pdf_page_index) if g.family == "notehead"]
    bands = S.staff_bands(page)
    staves = sorted({(b.system, b.staff) for b in bands})
    ledgers = [it for it in items if it.family == "ledger_line"]
    rows = []
    for it in far:
        copies = sorted((g for g in heads if S._iou(g.rect, it.rect) >= S.MIN_IOU),
                        key=lambda g: -S._iou(g.rect, it.rect))
        g, ours, how = connection(copies)
        derived = it.derived_owner
        if ours is None:
            group = 0
        elif derived is None:
            group = 1
        else:
            group = 0 if tuple(ours) != tuple(derived) else 2
        cx, cy = S._cx(it.rect), S._cy(it.rect)
        near_led = [l for l in ledgers if l.rect[2] >= it.rect[0] - 32 and l.rect[0] <= it.rect[2] + 32
                    and abs(S._cy(l.rect) - cy) <= 6 * 32]
        rows.append({"item": it, "copies": copies, "glyph": g, "ours": ours, "how": how, "derived": derived,
                     "group": group, "cx": cx, "cy": cy, "ledgers": near_led})
    rows.sort(key=lambda r: (r["group"], (r["ours"] or (0, 99)), r["cx"]))
    return page, run, rows, bands, staves


def render_tile(img, n, total, row, bands, staves, run):
    it = row["item"]
    cx, cy = row["cx"], row["cy"]
    sp = float(np.median([b.space for b in bands]))
    ours_key = tuple(row["ours"])
    ob = band_at(bands, ours_key, cx)
    side, ok, otb = other_staff(bands, staves, ours_key, ob, cx, cy)
    tops = [ob.lines[0], it.rect[1] - 0.8 * sp] + ([otb.lines[0]] if otb else [])
    bots = [ob.lines[-1], it.rect[3] + 0.8 * sp] + ([otb.lines[-1]] if otb else [])
    box = (cx - HALF_WIDTH_SPACES * sp, min(tops) - MARGIN_SPACES * sp,
           cx + HALF_WIDTH_SPACES * sp, max(bots) + MARGIN_SPACES * sp)
    body, scale, (x0, y0) = P.crop_scaled(img, box)
    d = ImageDraw.Draw(body)
    thick = max(8, int(round(2.9 * scale)))
    toY = lambda y: (y - y0) * scale  # noqa: E731
    if otb:
        P.staff_lines(d, [toY(y) for y in otb.lines], body.width, P.GREY, thick)
    P.staff_lines(d, [toY(y) for y in ob.lines], body.width, P.ORANGE, thick)

    def nm(k):
        n_ = instrument_name(run, k)
        return n_ if n_ else "name not read"

    ours_name = instrument_name(run, ours_key)
    ours_txt = f"Staff {ours_key[1] + 1}" + (f", {ours_name}" if ours_name else "")
    d_label_x = 10
    P.staff_label(d, d_label_x, int(toY(ob.lines[0])) - 14, f"STAFF {ours_key[1] + 1}", nm(ours_key), P.ORANGE)
    runs = [(f"orange = staff we connect it to ({ours_txt}); ", P.ORANGE)]
    if otb:
        P.staff_label(d, d_label_x, int(toY(otb.lines[0])) - 14, f"Staff {ok[1] + 1}", f"{nm(ok)} (other)", P.GREY)
        runs.append(("grey = the other staff", P.GREY))
    else:
        runs.append(("grey = other staff (none on that side)", P.GREY))
    pad = 0.28 * sp * scale
    r = ((it.rect[0] - x0) * scale - pad, toY(it.rect[1]) - pad, (it.rect[2] - x0) * scale + pad,
         toY(it.rect[3]) + pad)
    P.corner_brackets(d, r)
    top = P.banner(body.width, n, f"Far note {n} of {total}", runs)
    return P.compose(top, body), (ok, side)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True, type=Path)
    ap.add_argument("--record", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    page, run, rows, bands, staves = build(a)
    img = np.asarray(render_page(str(a.pdf), page.pdf_page_index, dpi=page.dpi).rgb).copy()
    frame = truth_frame_control(img, page)
    total = len(rows)
    manifest = {
        "what": "Far-note review tiles: for each far head, which staff we connect it to (orange) and the nearest staff "
                "on the other side (grey). Staff numbers count from the top of the page (1 = top staff); "
                "`record_staff_index` is the record/page-store index (0 = top staff).",
        "truth_page": f"{page.edition}:{page.pdf_page_index}", "truth_state": page.state,
        "record": {"path": str(a.record), "commit": run.provenance.get("commit"), "dirty": run.provenance.get("dirty"),
                   "weights": S.record_weights(run), "dpi": run.dpi},
        "frame_check_staff_lines_on_ink": round(frame, 1),
        "tiles_total": total, "tiles": []}
    ims = []
    for n, row in enumerate(rows, 1):
        if row["ours"] is None:
            raise SystemExit(f"far head {row['item'].id} has no staff we connect it to: handle before drawing")
        im, (other, side) = render_tile(img, n, total, row, bands, staves, run)
        fn = f"tile_{n:02d}.png"
        P.save_small(im, a.out / fn, colors=48)
        ims.append((n, im))
        it, g = row["item"], row["glyph"]
        manifest["tiles"].append({
            "tile": n, "file": fn,
            "subject": {"truth_box": it.id, "cell": it.cell_id, "class": it.cls, "origin": it.origin,
                        "page_rect": [round(v, 1) for v in it.rect]},
            "head_is": side + " the staff we connect it to",
            "our_owner": {"record_staff_index": row["ours"][1], "staff_number_from_top": row["ours"][1] + 1,
                          "instrument": instrument_name(run, tuple(row["ours"]))},
            "how_decided": row["how"],
            "record_copies_of_this_head": [
                {"glyph": c.key, "adjudicate_status": c.status, "filed_staff_index": c.staff,
                 "glyph_owner": c.owner_outcome,
                 "glyph_owner_staff_index": (c.owner[1] if c.owner else None), "reason": c.owner_reason}
                for c in row["copies"]],
            "ledger_reference_owner": ({"record_staff_index": row["derived"][1],
                                         "staff_number_from_top": row["derived"][1] + 1}
                                        if row["derived"] else None),
            "ledger_reference_how": ("derived from Sean's ledger-line boxes under the head (the reference has no "
                                     "owner label of his; it is derived, not his)" if row["derived"] else
                                     "none: no ledger-line box of Sean's leads from this head to a staff"),
            "reference_agrees": (None if row["derived"] is None else tuple(row["ours"]) == tuple(row["derived"])),
            "group": ["DISAGREE", "NO_REFERENCE", "agree"][row["group"]],
            "other_staff_drawn_grey": ({"record_staff_index": other[1], "staff_number_from_top": other[1] + 1,
                                        "instrument": instrument_name(run, tuple(other))} if other else None),
            "sean_ledger_boxes_near_the_head": [
                {"box": l.id, "origin": l.origin, "page_rect": [round(v, 1) for v in l.rect]} for l in row["ledgers"]],
        })
    counts = {k: sum(1 for t in manifest["tiles"] if t["group"] == k) for k in ("DISAGREE", "NO_REFERENCE", "agree")}
    manifest["agreement"] = {**counts, "note": "agree = the staff we connect it to is the staff Sean's ledger-line "
                                                "boxes lead to (derived reference, not his label)"}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    # contact sheets (desktop use): 12 per sheet, the same tiles reduced
    per = 12
    cols, w = 4, 480
    for s in range(0, total, per):
        chunk = ims[s:s + per]
        small = [(n, im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)) for n, im in chunk]
        rows_ = [small[i:i + cols] for i in range(0, len(small), cols)]
        head = 150
        H = head + sum(max(t.height for _, t in r_) + 12 for r_ in rows_)
        sheet = Image.new("RGB", (cols * (w + 12) + 12, H), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        d.text((14, 12), f"Far notes {chunk[0][0]}-{chunk[-1][0]} of {total} (sheet {s // per + 1} of {-(-total // per)})",
               font=P.font(46), fill=P.INK)
        d.text((14, 74), "orange lines = the staff we connect the note to   grey lines = the other staff   "
                         "red corners = the note", font=P.font(34, False), fill=P.INK)
        d.text((14, 114), "Tell me the numbers that are wrong, e.g. \"all right except 7, 23\".",
               font=P.font(30, False), fill=P.GREY)
        y = head
        for r_ in rows_:
            x = 12
            for _, t in r_:
                sheet.paste(t, (x, y))
                x += w + 12
            y += max(t.height for _, t in r_) + 12
        P.save_small(sheet, a.out / f"sheet_{s // per + 1:02d}.png", colors=48)
    print(json.dumps({"tiles": total, **counts, "frame_check": round(frame, 1)}))


if __name__ == "__main__":
    main()
