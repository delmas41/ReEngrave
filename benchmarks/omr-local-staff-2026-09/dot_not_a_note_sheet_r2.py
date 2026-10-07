"""lane-dot-not-a-note ROUND 2 sheet (Sean 2026-10-07: 8 of 12 right on `dot_not_a_note.png`).  Tiles 1-4 are the four he
called wrong (round-1 tiles 5, 8, 9, 10: Litolff 12/1/6/2/9, Litolff 4/1/2/5/8, Brahms 16/1/10/4/3, Brahms 5/1/1/2/17), then
8 fresh seeded changes (not among round 1's twelve).  Same replay (flag off = BEFORE, flag on = AFTER), same drawing.

  python3 dot_not_a_note_sheet_r2.py <replay dir> [--seed 20261008]
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import dot_not_a_note_sheet as S1

OUT = HERE.parents[1] / "out/print/dot_not_a_note_r2.png"
ROUND1 = {("brahms", "glyph/7/1/0/9/9"), ("brahms", "glyph/18/1/12/6/18"), ("brahms", "glyph/5/0/1/5/32"),
          ("brahms", "glyph/10/1/2/2/7"), ("lito", "glyph/12/1/6/2/9"), ("brahms", "glyph/3/1/12/6/6"),
          ("brahms", "glyph/17/0/1/3/7"), ("lito", "glyph/4/1/2/5/8"), ("brahms", "glyph/16/1/10/4/3"),
          ("brahms", "glyph/5/1/1/2/17"), ("brahms", "glyph/5/0/2/2/13"), ("brahms", "glyph/18/0/8/5/8")}
FOUR = [("lito", "glyph/12/1/6/2/9"), ("lito", "glyph/4/1/2/5/8"), ("brahms", "glyph/16/1/10/4/3"), ("brahms", "glyph/5/1/1/2/17")]
NP_WORDS = {"is_a_dot": "refused as a dot", "on_a_barline": "refused: stray ink on a barline", "clipped_fragment": "refused: a fragment cut by the strip's edge",
            "too_narrow": "refused: too narrow to be a head"}
ROLE_WORDS = {"augmentation": "lengthens the note to its left", "staccato": "is a staccato mark on a note"}


def role_words(r):
    if not r or r.get("o") != "decided":
        why = (r or {}).get("r")
        return "is not read" + (" (it is ink on a barline)" if why == "on_a_barline" else " -- cannot tell if it lengthens a note")
    return ROLE_WORDS.get(r.get("v"), str(r.get("v")))


def capfn_for(short, kind):
    def cap(on, off, row, dk, hk, note_staff, filing, own_off, own_on):
        caps = []
        if dk is None or row["key"] not in on["dots"]:      # a notehead-class box
            a, b = row["off"], row["on"]
            na = (a["np"] or {}).get("r") if (a["np"] or {}).get("v") is True else None
            nb = (b["np"] or {}).get("r") if (b["np"] or {}).get("v") is True else None
            caps.append((f"BEFORE: this {b['cls'][4:]} box ({b['w']:.2f} x {b['h']:.2f} staff spaces) was "
                         + (NP_WORDS.get(na, f"refused ({na})") if na else "kept as a notehead") + ".", S1.RED))
            caps.append(("AFTER: it is " + (NP_WORDS.get(nb, f"refused ({nb})") if nb else "kept as a notehead") + ".", S1.GREEN))
            if own_off != own_on:
                caps.append((f"Its owner: BEFORE {S1.label(on, own_off)}, AFTER {S1.label(on, own_on)} (it follows the dot on the same ink).", S1.GREY))
        else:
            ra, rb = (off["dots"].get(dk) or {}).get("role"), (on["dots"].get(dk) or {}).get("role")
            caps.append((f"BEFORE: the dot {role_words(ra)}; it belongs to {S1.label(on, own_off)}.", S1.RED))
            caps.append((f"AFTER: the dot {role_words(rb)}; it belongs to {S1.label(on, own_on)}"
                         + (", the staff of the note it trails." if (rb or {}).get("v") == "augmentation" and own_on != filing else "."), S1.GREEN))
        caps.append(("Orange = the dot; green box = the note it trails (if any); blue box = a notehead-shaped box on the same ink; grey outline = the staff "
                     "the mark was filed on; green outline = its note's staff.", S1.GREY))
        return caps
    return cap


def changed(short, d):
    off, on = d["off"], d["on"]
    out = []
    for k, a in off["dots"].items():
        b = on["dots"][k]
        ra, rb = (a["role"] or {}), (b["role"] or {})
        if (ra.get("o"), ra.get("v")) != (rb.get("o"), rb.get("v")) or (a["own"] or {}).get("v") != (b["own"] or {}).get("v"):
            out.append(dict(doc=short, key=k, off=a, on=b))
    for k, a in off["boxes"].items():
        b = on["boxes"][k]
        if (a["np"] or {}).get("r") != (b["np"] or {}).get("r") or (a["own"] or {}).get("v") != (b["own"] or {}).get("v"):
            out.append(dict(doc=short, key=k, off=a, on=b))
    return out


def main(d, seed):
    reps = S1.Rep(d, "all")
    pool = []
    for short, rep in reps.docs.items():
        pool += [r for r in changed(short, rep) if (short, r["key"]) not in ROUND1 and int(r["key"].split("/")[1]) >= 2]
    first = []
    for short, k in FOUR:
        rep = reps.docs[short]
        it_off = rep["off"]["dots"].get(k) or rep["off"]["boxes"].get(k)
        it_on = rep["on"]["dots"].get(k) or rep["on"]["boxes"].get(k)
        first.append(dict(doc=short, key=k, off=it_off, on=it_on))
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for r in pool:
        a, b = r["off"], r["on"]
        if r["key"] in reps.docs[r["doc"]]["on"]["dots"]:
            kind = "role" if ((a["role"] or {}).get("v") != (b["role"] or {}).get("v")) else "owner"
        else:
            kind = "box_np" if (a["np"] or {}).get("r") != (b["np"] or {}).get("r") else "box_owner"
        by[kind].append(r)
    print({k: len(v) for k, v in by.items()})
    picks = []
    for kind, n in (("role", 3), ("owner", 2), ("box_np", 1), ("box_owner", 1), ("role", 1)):
        pl = by.get(kind, [])
        if pl:
            picks.append(pl.pop(rng.randrange(len(pl))))
        if kind == "role" and n > 1:
            for _ in range(n - 1):
                if by["role"]:
                    picks.append(by["role"].pop(rng.randrange(len(by["role"]))))
        if kind == "owner" and n > 1 and by["owner"]:
            picks.append(by["owner"].pop(rng.randrange(len(by["owner"]))))
    allrows = (first + picks)[:12]
    tiles, info, chk = [], [], []
    for i, row in enumerate(allrows, 1):
        short = row["doc"]
        rep = reps.docs[short]
        ov, zoom, caps, ch, meta = S1.draw(short, rep, row, i, "r2", capfn=capfn_for(short, "r2"))
        chk += ch
        W = max(ov.shape[1], zoom.shape[1])
        cl = [(ln, c) for t, c in caps for ln in S1.wrap(t, W)]
        title = ("YOU SAID WRONG (round-1 tile %s). " % {0: "5", 1: "8", 2: "9", 3: "10"}.get(i - 1, "")) if i <= 4 else "SEEDED CHANGE. "
        head = S1.wrap(f"{i}. {title}", W, 0.5)
        hh, chh = 8 + 20 * len(head), 8 + 18 * len(cl) + 20
        c = np.full((hh + ov.shape[0] + zoom.shape[0] + chh, W, 3), 255, np.uint8)
        for j, ln in enumerate(head):
            cv2.putText(c, ln, (4, 18 + 20 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        c[hh:hh + ov.shape[0], :ov.shape[1]] = ov
        c[hh + ov.shape[0]:hh + ov.shape[0] + zoom.shape[0], :zoom.shape[1]] = zoom
        y0 = hh + ov.shape[0] + zoom.shape[0]
        for j, (ln, col) in enumerate(cl):
            cv2.putText(c, ln, (6, y0 + 18 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.46, tuple(int(v * 0.8) for v in col), 1, cv2.LINE_AA)
        cv2.putText(c, f"{short} pdf page {meta['page']}  {meta['subject'].replace('glyph/', '')}", (6, y0 + chh - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (110, 110, 110), 1, cv2.LINE_AA)
        cv2.rectangle(c, (0, 0), (W - 1, c.shape[0] - 1), (190, 190, 190), 1)
        tiles.append(c)
        info.append(dict(n=i, **meta, caps=[t for t, _ in caps]))
    cols, W = 3, max(t.shape[1] for t in tiles)
    rows = []
    for k in range(0, len(tiles), cols):
        grp = tiles[k:k + cols]
        h = max(t.shape[0] for t in grp)
        grp = [np.pad(t, ((0, h - t.shape[0]), (4, 4 + W - t.shape[1]), (0, 0)), constant_values=255) for t in grp]
        while len(grp) < cols:
            grp.append(np.full((h, W + 8, 3), 255, np.uint8))
        rows.append(np.hstack(grp))
    w = max(r.shape[1] for r in rows)
    img = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    legend = np.full((120, img.shape[1], 3), 255, np.uint8)
    for j, txt in enumerate((
            "ROUND 2.  Tiles 1-4 are the four you called wrong; 5-12 are fresh seeded changes.  BEFORE = the 10-07 night record as it stands; AFTER = same record, same stages (gather + adjudicate), dot rule on.",
            "A lengthening dot sits RIGHT of its head at the head's height; a staccato sits above or below a head within its x span and is never read as lengthening.  A dot-sized mark on a barline is not a dot.",
            "ORANGE = the dot (orange ring on the whole system).  GREEN = its note.  GREY outline = the staff that boxed the mark.  GREEN outline = the staff of its note.  Staff names at the left.",
            "Thin grey/green horizontal lines in each zoom are the five staff lines of the two staves, 1 px, re-measured against the ink rows of the page.")):
        cv2.putText(legend, txt, (8, 24 + 26 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    OUT.with_suffix(".json").write_text(json.dumps(info, indent=1, default=str))
    ok = sum(1 for c in chk if c is not None and c <= 2.0)
    print(f"staff lines drawn {len(chk)}: within 2 px {ok}, further {sum(1 for c in chk if c is not None and c > 2.0)}, no ink {sum(1 for c in chk if c is None)}")
    for t in info:
        print(t["n"], t["doc"], t["subject"], "|", " || ".join(t["caps"][:2]))
    print("wrote", OUT)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261008)
