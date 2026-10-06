"""night 2026-10-06: ONE sheet for Sean, 12 seeded-random NEW far-head decisions on pages the rules were NOT written on
(Litolff pp.4-16, Brahms pp.2-26), 6 per document, favouring heads where NEW differs from BASE (4 differ + 2 agree per
document = 8 + 4). NEW = `...20261006-night-combined`, BASE = `...20261004-farhead-all`.

Each tile: orange = the note's box, blue = the staff's edge, green = each ledger counted between the edge and the note's
line, red = the note's own line; under it the answer in WORDS, NEW then BASE. Every drawn line is re-measured against the
pixel rows of the page (`farhead_note_first_sheet.remeasure`); a line more than 2 px off ink, or with no ink beside the
head to measure, is printed (and the tile says so). CONTROL that can fail: only heads whose replay reproduces the
recorded position are eligible, so a tile always shows what the record holds.

  python3 night_1006_sheet.py <scratch dir with x/*.json> [--seed 20261006]
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/ledgers/night_1006_sample.png"
NEWTAG, BASETAG = "20261006-night-combined", "20261004-farhead-all"
PAGES = {"beethoven5-litolff": range(4, 17), "brahms1-breitkopf": range(2, 27)}
SHORT = {"beethoven5-litolff": "litolff", "brahms1-breitkopf": "brahms"}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n):
    return ORD.get(n, f"{n}th")


def words_pos(p):
    """A position (half-steps, 0 = top staff line, 8 = bottom) in words."""
    if p is None:
        return "no answer (abstained)"
    p = int(p)
    if p < 0:
        if p == -1:
            return "in the first space above the staff"
        if p % 2 == 0:
            return f"on the {ordinal(-p // 2)} ledger above"
        return f"in the space above the {ordinal((-p - 1) // 2)} ledger"
    if p > 8:
        if p == 9:
            return "in the first space below the staff"
        if p % 2 == 0:
            return f"on the {ordinal((p - 8) // 2)} ledger below"
        return f"in the space below the {ordinal((p - 9) // 2)} ledger"
    return ("on staff line %d" % (p // 2 + 1)) if p % 2 == 0 else ("in staff space %d" % (p // 2 + 1))


def build_pool(d, doc):
    N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
    B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
    rn = json.loads((d / "x" / f"rep_new_{SHORT[doc]}.json").read_text())["heads"]
    bybox = R.by_page(B["glyphs"])
    widths = sorted(g["box"][2] - g["box"][0] for g in N["glyphs"].values() if "box" in g and R.is_far(g) and "geo" in g)
    med_w = widths[len(widths) // 2]
    pool = []
    for s, g in N["glyphs"].items():
        if not (R.is_far(g) and "geo" in g and "box" in g and "fh" in g):
            continue
        if R.page_of(s) not in PAGES[doc] or (g.get("np") or {}).get("outcome") != "decided":
            continue
        m = rn.get(s)
        if not m or not m.get("repro") or m.get("edge_y") is None or m.get("line_y") is None or m.get("between") is None:
            continue
        if g["box"][2] - g["box"][0] < 0.6 * med_w:      # slivers (barline / stem pieces): not a fair tile
            continue
        mb, v = R.best_match(g["box"], R.page_of(s), bybox)
        bpos = R.decided_pos(mb[1]) if mb else None
        bstat = "none" if mb is None else ("abstained" if bpos is None else "decided")
        newpos = int(round(float(g["np"]["value"])))
        differs = (mb is not None) and (bpos != newpos)
        pool.append(dict(doc=doc, subject=s, page=R.page_of(s), geometry=R.geo_pos(g), base_subject=mb[0] if mb else None,
                         base_pos=bpos, base_status=bstat, differs=differs, new_pos=newpos,
                         new=dict(pos=newpos, box_used=m["box_used"], lines=m["lines"], edge_y=m["edge_y"],
                                  line_y=m["line_y"], between=m["between"], kind=m["kind"], k=m["k"], how=m["how"],
                                  seen=m["seen"]),
                         old=dict(pos=bpos), run2_recorded=bpos))
    return pool


def main(d, seed):
    d = Path(d)
    rng = random.Random(seed)
    picks = []
    stats = {}
    for doc in ("beethoven5-litolff", "brahms1-breitkopf"):
        pool = build_pool(d, doc)
        diff_both = [r for r in pool if r["differs"] and r["base_status"] == "decided"]
        diff_abs = [r for r in pool if r["differs"] and r["base_status"] == "abstained"]
        agree = [r for r in pool if not r["differs"]]
        stats[doc] = dict(pool=len(pool), differ_both_decided=len(diff_both), differ_base_abstained=len(diff_abs), agree=len(agree))
        # favour a visible difference: BASE decided something else; fall back to BASE abstained only if short
        diff = rng.sample(diff_both, min(4, len(diff_both)))
        if len(diff) < 4:
            diff += rng.sample(diff_abs, min(4 - len(diff), len(diff_abs)))
        ag = rng.sample(agree, 2)
        picks += diff + ag
    print("pools:", stats)
    # shuffle once so the numbers 1-12 do not group by document or by agree/differ
    rng.shuffle(picks)
    grays = {}
    for r in picks:
        key = (r["doc"], r["page"])
        if key not in grays:
            cfg = ts.DOCS[r["doc"]]
            grays[key] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    tiles, allchecks = [], []
    for i, r in enumerate(picks, 1):
        crop, ch = NF.tile(r, grays[(r["doc"], r["page"])], i)
        allchecks += ch
        tiles.append((crop, i, r))
    W = max(t[0].shape[1] for t in tiles)
    cells = []
    for crop, i, r in tiles:
        cap_h = 88
        H = crop.shape[0]
        canvas = np.full((H + cap_h, W, 3), 255, np.uint8)
        canvas[:H, :crop.shape[1]] = crop
        short = r["subject"].replace("glyph/", "")
        cv2.putText(canvas, f"{i}", (6, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(canvas, f"{SHORT[r['doc']][:4]} p{r['page']} {short}", (34, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        cv2.putText(canvas, "NEW: " + words_pos(r["new_pos"]), (6, H + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (0, 0, 200), 1)
        btxt = "BASE: " + (words_pos(r["base_pos"]) if r["base_status"] != "none" else "no matching box")
        cv2.putText(canvas, btxt, (6, H + 62), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (150, 0, 150), 1)
        tag = "differs from BASE" if r["differs"] else "same as BASE"
        if not r["new"].get("seen"):
            tag += "  [no full stub beside head]"
        cv2.putText(canvas, tag, (6, H + 82), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1)
        cells.append(canvas)
    cols = 4
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        rowsimg.append(np.hstack(grp))
    w = max(r.shape[1] for r in rowsimg)
    img = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rowsimg])
    legend = np.full((92, img.shape[1], 3), 255, np.uint8)
    for j, (txt, col) in enumerate((("ORANGE box = the note the reader was asked about.", (0, 120, 230)),
                                    ("BLUE line = the edge of the staff the note is filed on (its outer line, nearest the note).", (200, 70, 0)),
                                    ("GREEN lines = each ledger line the reader counted between the staff edge and the note's line.", (0, 140, 0)),
                                    ("RED line = the line the note sits on, or sits just beyond (drawn full width).", (0, 0, 220)))):
        cv2.putText(legend, txt, (8, 20 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    (OUT.with_suffix(".json")).write_text(json.dumps(
        [{k: r[k] for k in ("doc", "subject", "page", "geometry", "new_pos", "base_pos", "base_status", "differs", "new")} for r in picks], default=str))
    hidden = [c for c in allchecks if c[3] is None]
    bad = [c for c in allchecks if c[3] is not None and c[3] > 2.0]
    print("drawn lines", len(allchecks), "| within 2 px of a flanking ink row:", len(allchecks) - len(bad) - len(hidden),
          "| off by more than 2 px:", len(bad), bad, "| no flanking ink beside the head:", len(hidden))
    for i, r in enumerate(picks, 1):
        print(i, r["doc"][:6], r["subject"], "| NEW", words_pos(r["new_pos"]), "| BASE", words_pos(r["base_pos"]),
              "| geometry", r["geometry"], "|", "DIFF" if r["differs"] else "same", r["new"]["how"])
    print("wrote", OUT)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261006)
