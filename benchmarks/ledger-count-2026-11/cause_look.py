"""ROADMAP 2.312 Part 0c -- the cause tally of far heads whose ledger count refused, and the crop look.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/ledger-count-2026-11/cause_look.py tally HEADS.json PLATE
    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/ledger-count-2026-11/cause_look.py sheets HEADS.json PLATE OUTDIR [N=40] [SEED=2312]

`HEADS.json` is `far_heads_rerun.py`'s file. A far head = the geometry puts it two or more half-steps outside the staff (position <= -2 or >= 10),
and the far-head owner did not move it to another staff. `tally` counts the refusals by the ledger reader's own reason word and by what was written.
`sheets` draws N seeded random refused heads as crops of the page as scanned (grey), the staff and its ledger lines, one thin orange box, the case
number and reason word under each; 20 to a sheet. Our own look at them is written in FINDINGS.md (ours, not truth).
"""
from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def is_far(h):
    g = int(round(h["geom"]))
    return g <= -2 or g >= 10


def reason_of(h):
    r = ((h.get("ledger_refusal") or {}).get("detail") or {}).get("ledger_reason") or (h.get("ledger_refusal") or {}).get("reason") or "?"
    return r.split(" (")[0]


def moved(h):
    return ((h.get("pitch") or {}).get("reason") or "") in ("reowned", "reowned_by_ledger_reading")


def refused(h):
    """the count refused and the head stays on its own staff (a head the ledger lines moved to the other staff is that staff's note, not a refusal)"""
    return is_far(h) and h["ledger_row"] is None and h.get("ledger_refusal") is not None and not moved(h)


def how_written(h):
    w = h["written"]
    nan = h.get("not_a_note")
    if w is None:
        return "not written" + (" (refused as a head)" if nan and nan[1] is True else "")
    return "written blue" if w["blue"] else "written plain"


def tally(heads):
    far = [h for h in heads if is_far(h)]
    ref = [h for h in far if refused(h)]
    print("far heads", len(far), "| ledger count read", sum(1 for h in far if h["ledger_row"] is not None), "| refused", len(ref))
    c = collections.Counter((reason_of(h), how_written(h)) for h in ref)
    by = collections.Counter(reason_of(h) for h in ref)
    for r, n in by.most_common():
        print("  %-48s %4d   %s" % (r, n, "  ".join("%s %d" % (w, c[(r, w)]) for w in ("written blue", "written plain", "not written") if c[(r, w)])))
    print("  written, all refused:", collections.Counter(how_written(h) for h in ref))
    unrefused_nofar = [h for h in far if h["ledger_row"] is None and h.get("ledger_refusal") is None]
    print("  far by geometry but no ledger row and no refusal (owner moved / never asked):", len(unrefused_nofar),
          collections.Counter(how_written(h) for h in unrefused_nofar))
    return ref


def sheets(heads, plate, outdir, n=40, seed=2312):
    from checksheet import page_image
    from ledger_heights import load
    staff_lines = load(plate)[0]["staff_lines"]
    ref = [h for h in heads if refused(h)]
    ref.sort(key=lambda h: h["key"])
    pick = random.Random(seed).sample(ref, min(n, len(ref)))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    W, PXSP = 420, 34.0
    tiles, key = [], []
    for i, h in enumerate(pick, 1):
        p, s, st, c, g = (int(x) for x in h["key"].split("/")[1:])
        b = h["box"]
        sl = staff_lines.get("staff/%d/%d/%d" % (p, s, st))
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        # the staff spacing from the geometry: the box height is about one space; use the reader's own `lines_used` if kept, else 1 space = box height
        sp = (sl["value"][4] - sl["value"][0]) / 4.0 if sl else (b[3] - b[1])
        im = page_image(plate, p)
        k = PXSP / sp
        half = (W / k) / 2
        up = 9.0 if h["geom"] < 4 else 2.0
        dn = 2.0 if h["geom"] < 4 else 9.0
        x0, x1 = int(cx - half), int(cx + half)
        y0, y1 = int(cy - up * sp), int(cy + dn * sp)
        crop = im.crop((x0, y0, x1, y1)).convert("RGB")
        d = ImageDraw.Draw(crop)
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
        crop = crop.resize((W, max(1, int(crop.height * k))))
        t = Image.new("RGB", (W, crop.height + 30), "white")
        t.paste(crop, (0, 0))
        dd = ImageDraw.Draw(t)
        dd.text((6, crop.height + 4), "%d  p%d %s" % (i, p, reason_of(h)[:46]), fill=(0, 0, 0))
        dd.text((6, crop.height + 16), "%s  %s" % (how_written(h), h["key"]), fill=(80, 80, 80))
        tiles.append(t)
        key.append(dict(i=i, key=h["key"], reason=reason_of(h), written=how_written(h)))
    per = 20
    for si in range(0, len(tiles), per):
        grp = tiles[si:si + per]
        cols = 4
        rows = (len(grp) + cols - 1) // cols
        rh = [max(t.height for t in grp[r * cols:(r + 1) * cols]) for r in range(rows)]
        sh = Image.new("RGB", (cols * (W + 6) + 6, sum(rh) + 6 * (rows + 1)), "white")
        y = 6
        for r in range(rows):
            for cc, t in enumerate(grp[r * cols:(r + 1) * cols]):
                sh.paste(t, (6 + cc * (W + 6), y))
            y += rh[r] + 6
        sh.save(outdir / ("sheet_%s_%d.png" % (plate, si // per + 1)))
    json.dump(key, open(outdir / ("key_%s.json" % plate), "w"), indent=1)
    print("wrote", len(tiles), "crops")


if __name__ == "__main__":
    cmd, f, plate = sys.argv[1:4]
    heads = json.load(open(f))
    if cmd == "tally":
        tally(heads)
    else:
        sheets(heads, plate, sys.argv[4], *(int(a) for a in sys.argv[5:7]))
