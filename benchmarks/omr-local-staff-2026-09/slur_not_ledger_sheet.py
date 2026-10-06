"""lane-slur-not-ledger (Sean 2026-10-06): the out-of-sample read and ONE sheet. READ ONLY.

Input: `slur_not_ledger_oos.py` output for both documents (the 10-06 night-combined records, rule OFF vs ON per far
head; OFF must reproduce the record -- the control that can fail). Prints: heads replayed, OFF reproduces the record,
decisions changed (and how), owners changed, Sean's confirmed-right tiles (must keep their answers), then writes the sheet
of up to 12 seeded changes (tile 6 of the night sheet first): rejected rung = RED dashes, counted ledgers = GREEN,
note box = ORANGE, staff edge = BLUE; the answer and the owner in words, before and after; every drawn line re-measured
against the pixel rows of the page.

  python3 slur_not_ledger_sheet.py <oos_lito.json> <oos_brah.json> [--seed 20261006]
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import night_1006_sheet as NS
import slur_not_ledger_sean_tiles as SEAN
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/ledgers/slur_not_ledger.png"
TILE6 = ("beethoven5-litolff", "glyph/16/0/0/0/2")
SCALE = 3
RED, GREEN, ORANGE, BLUE = NF.RED, NF.GREEN, NF.ORANGE, NF.BLUE


def owner_words(o, own):
    if o is None:
        return "no ownership read"
    ow = o["owner"]
    if ow is None:
        return "no owner (silent: %s)" % o["word"]
    if ow == own:
        return "this staff (%s)" % own.replace("staff/", "")
    return "the OTHER staff (%s)" % ow.replace("staff/", "")


def changed(r):
    pos = r["off"]["pos"] != r["on"]["pos"]
    oo, no = (r["off"]["owner"] or {}).get("owner"), (r["on"]["owner"] or {}).get("owner")
    return pos, (oo != no)


def dashed(img, yy, colour):
    for x in range(0, img.shape[1], 14):
        cv2.line(img, (x, yy), (min(x + 8, img.shape[1] - 1), yy), colour, 2)


def tile(r, gray, no):
    box = r["box"]
    off, on = r["off"], r["on"]
    edge = off["edge_y"] if off["edge_y"] is not None else on["edge_y"]
    line_y = off["line_y"] or on["line_y"]
    kept = list(on["between"] or [])
    gone = [y for y in (off["between"] or []) if all(abs(y - k) > 1.0 for k in kept)]
    gone += [x["y"] for x in (on["refused"] or []) if all(abs(x["y"] - g) > 1.0 for g in gone)]
    sp = 15.75 if edge is None else max(14.0, (box[3] - box[1]) * 0.9)
    ys = [v for v in [edge, line_y, box[1], box[3]] + kept + gone if v is not None]
    cx = (box[0] + box[2]) / 2.0
    xa, xb = max(0, int(cx - 3.2 * sp)), int(cx + 3.2 * sp)
    ya, yb = max(0, int(min(ys) - 1.2 * sp)), int(max(ys) + 1.2 * sp)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    cols = ((int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp)), (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp)))
    checks = []

    def draw(y, colour, label, dash=False):
        yy = int(round((y - ya) * SCALE))
        if dash:
            dashed(crop, yy, colour)
        else:
            cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 2)
        pk = [NF.remeasure(gray, y, *c, thr) for c in cols]
        pk = [p for p in pk if p[0] is not None]
        checks.append((no, label, round(float(y), 1), min((abs(p[1]) for p in pk), default=None)))
    if edge is not None:
        draw(edge, BLUE, "staff edge")
    for i, y in enumerate(kept):
        draw(y, GREEN, f"counted ledger {i + 1}")
    for y in gone:
        draw(y, RED, "rejected rung", dash=True)
    cv2.rectangle(crop, (int((box[0] - xa) * SCALE), int((box[1] - ya) * SCALE)),
                  (int((box[2] - xa) * SCALE), int((box[3] - ya) * SCALE)), ORANGE, 1)
    return crop, checks, gone


def pos_words(p):
    return NS.words_pos(p)


def main(lito, brah, seed):
    rows = []
    stats = {}
    for path in (lito, brah):
        d = json.loads(Path(path).read_text())
        stats[d["doc"]] = d["stats"]
        rows += d["rows"]
    n = len(rows)
    repro = sum(r["repro"] for r in rows)
    print(f"far heads replayed {n}; OFF reproduces the recorded position on {repro} (mismatch {n - repro}); {stats}")
    by_key = {(r["doc"], r["subject"]): r for r in rows}
    ok = [r for r in rows if r["repro"]]
    dec = collections.Counter()
    ch_pos, ch_own = [], []
    for r in ok:
        p, o = changed(r)
        if p:
            a, b = r["off"]["pos"], r["on"]["pos"]
            kind = ("decided->abstain" if b is None else "abstain->decided" if a is None else "decided->other decided")
            dec[kind] += 1
            agree = (b is not None and b == r["geo"])
            r["_kind"], r["_agree_geo"] = kind, agree
            ch_pos.append(r)
        if o:
            ch_own.append(r)
    print(f"decisions changed {len(ch_pos)} of {len(ok)}: {dict(dec)}")
    print("   of them agree with geometry after:", sum(1 for r in ch_pos if r.get("_agree_geo")), "| disagreed with geometry before:",
          sum(1 for r in ch_pos if r['off']['pos'] is not None and r['off']['pos'] != r['geo']))
    oc = collections.Counter()
    for r in ch_own:
        a, b = (r["off"]["owner"] or {}).get("owner"), (r["on"]["owner"] or {}).get("owner")
        own = r["off"]["owner"]["own"]
        oc[("own" if a == own else "silent" if a is None else "OTHER") + "->" + ("own" if b == own else "silent" if b is None else "OTHER")] += 1
    print(f"owners changed {len(ch_own)}: {dict(oc)}")
    refd = sum(1 for r in ok if r["on"]["refused"] and any("not_straight" in x["why"] or "arc_box" in x["why"] for x in r["on"]["refused"]))
    print("heads where the rule refused a counted rung:", refd, "| rung refusals by kind:",
          dict(collections.Counter(x["why"] for r in ok for x in (r["on"]["refused"] or []) if "not_straight" in x["why"] or "arc_box" in x["why"])))
    # Sean's confirmed-right tiles
    keep_bad = 0
    print("Sean's confirmed-right tiles (position / owner OFF -> ON):")
    for w, s, tag in SEAN.tiles():
        doc = "beethoven5-litolff" if w == "litolff" else "brahms1-breitkopf"
        r = by_key.get((doc, s))
        if r is None:
            print(f"   {tag} {w} {s}: not a far head in the 10-06 record")
            continue
        p, o = changed(r)
        keep_bad += p or o
        print(f"   {tag:7s} {w:7s} {s:18s} pos {r['off']['pos']} -> {r['on']['pos']} | owner {(r['off']['owner'] or {}).get('owner')} -> {(r['on']['owner'] or {}).get('owner')} {'CHANGED' if (p or o) else 'same'}")
    print("   tiles whose answer changed:", keep_bad)
    # the sheet: tile 6 first, then 11 seeded changes
    pool = [r for r in ok if (changed(r)[0] or changed(r)[1])]
    t6 = by_key[TILE6]
    rng = random.Random(seed)
    rest = [r for r in pool if (r["doc"], r["subject"]) != TILE6]
    pick = [t6] + rng.sample(rest, min(11, len(rest)))
    grays, tiles, allchecks = {}, [], []
    for r in pick:
        k = (r["doc"], r["page"])
        if k not in grays:
            grays[k] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[r["doc"]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
    W = 0
    cells = []
    for i, r in enumerate(pick, 1):
        crop, ch, gone = tile(r, grays[(r["doc"], r["page"])], i)
        allchecks += ch
        own = (r["off"]["owner"] or {}).get("own") or "staff/" + "/".join(r["subject"].split("/")[1:4])
        H = crop.shape[0]
        cap = 118
        cv = np.full((H + cap, crop.shape[1], 3), 255, np.uint8)
        cv[:H] = crop
        lines = [(f"{i}  {'lito' if 'beeth' in r['doc'] else 'brah'} p{r['page']} {r['subject'].replace('glyph/', '')}", (0, 0, 0)),
                 ("BEFORE: " + pos_words(r["off"]["pos"]), (150, 0, 150)),
                 ("   owner: " + owner_words(r["off"]["owner"], own), (150, 0, 150)),
                 ("AFTER:  " + pos_words(r["on"]["pos"]), (0, 0, 200)),
                 ("   owner: " + owner_words(r["on"]["owner"], own), (0, 0, 200)),
                 (f"rejected {len(gone)} rung(s); geometry says {pos_words(r['geo'])}", (90, 90, 90))]
        for j, (t, c) in enumerate(lines):
            cv2.putText(cv, t[:62], (4, H + 18 + 19 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.43, c, 1, cv2.LINE_AA)
        cells.append(cv)
        W = max(W, cv.shape[1])
    cols = 4
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, W - c.shape[1] + 4), (0, 0)), constant_values=255) for c in grp]
        rowsimg.append(np.hstack(grp))
    w = max(x.shape[1] for x in rowsimg)
    img = np.vstack([np.pad(x, ((6, 6), (0, w - x.shape[1]), (0, 0)), constant_values=255) for x in rowsimg])
    legend = np.full((92, img.shape[1], 3), 255, np.uint8)
    for j, (t, c) in enumerate((("ORANGE box = the note the reader was asked about.     BLUE line = the edge of the staff it is filed on.", ORANGE),
                                ("GREEN lines = each ledger the reader still counts between the staff edge and the note's line.", GREEN),
                                ("RED DASHES = a rung the slur rule refused (a slur / tie / far-too-long stroke is not a ledger).", RED),
                                ("Tile 1 is Sean's slur tile (night sheet tile 6); 2-12 are seeded random changes (seed %d)." % seed, (0, 0, 0)))):
        cv2.putText(legend, t, (8, 20 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    hidden = [c for c in allchecks if c[3] is None]
    bad = [c for c in allchecks if c[3] is not None and c[3] > 2.0]
    print("drawn lines", len(allchecks), "| within 2 px of an ink row:", len(allchecks) - len(bad) - len(hidden),
          "| off by more than 2 px:", len(bad), bad, "| no ink beside the head to measure:", len(hidden))
    for i, r in enumerate(pick, 1):
        print(i, r["doc"][:6], r["subject"], "| BEFORE", pos_words(r["off"]["pos"]), "|", owner_words(r["off"]["owner"], "x"),
              "| AFTER", pos_words(r["on"]["pos"]), "|", owner_words(r["on"]["owner"], "x"))
    print("wrote", OUT, "pool of changes", len(pool))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261006)
