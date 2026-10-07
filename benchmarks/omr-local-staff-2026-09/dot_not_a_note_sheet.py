"""lane-dot-not-a-note (ROADMAP 2.59): ONE sheet for Sean.  Tiles 1-3 are his three (Brahms 7/1/0/9/9, 18/1/12/6/18,
5/0/1/5/32); 4-12 are seeded changes the rule makes on pages it was not written on.  GATHER+ADJUDICATE only, replayed
from the 10-07 night records with `OMR_DOT_FOLLOWS_NOTE` off (BEFORE) and on (AFTER) -- same tree, same record.

  python3 dot_not_a_note_sheet.py <replay dir> [--seed 20261007]

<replay dir> holds `<doc>_<tag>_off.json` / `_on.json` from `dot_not_a_note_replay.py` (docs: brahms, lito).
Each tile: the WHOLE system (staff names at the left; the dot's own staff outlined grey, its note's staff outlined green;
the dot orange, its note green) and a zoom of the dot at 2x with the five lines of both staves drawn 1 px and
re-measured against the pixel rows of the page.  Words, not numbers, under each tile.
"""
from __future__ import annotations
import collections, glob, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import night_1007_sheet as S
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/dot_not_a_note.png"
DOCNAME = {"brahms": "brahms1-breitkopf", "lito": "beethoven5-litolff"}
ORANGE, GREEN, GREY, RED, BLUE = (0, 140, 255), (0, 170, 0), (120, 120, 120), (0, 0, 255), (255, 120, 0)
SC = 2
WORDS = {"ledger_note_first": "counting ledger lines outward from the note", "distance": "which staff is nearer",
         "ledger_direction": "which side the ledger lines are on", "dot_follows_note": "the note the dot trails",
         "group_owner": "the other detections of the same printed mark", "staff_band": "the note lying inside a staff's band",
         "ledger_owner_density": "how many ledger lines each staff would need", "tied": "two staves tied"}
TITLES = {
    "role_read": "DOT: its note belongs to another staff, so it could not find its note",
    "owner_moved": "DOT: owner moved from the strip that boxed it to its note's staff",
    "newly_refused": "BOX of a dot's size, called a (hollow) notehead",
    "twin_moved": "DOT boxed twice, once as a notehead: the notehead box follows the dot",
}


class Rep:
    def __init__(self, d, tag):
        self.docs = {}
        for short in DOCNAME:
            fs = {m: Path(d) / f"{short}_{tag}_{m}.json" for m in ("off", "on")}
            if all(f.exists() for f in fs.values()):
                self.docs[short] = {m: json.loads(f.read_text()) for m, f in fs.items()}


def label(R, key):
    if not key:
        return "no staff"
    _, p, s, k = key.split("/")
    nm = R["inst"].get(key) or "a staff with no name read"
    return f"{nm} (system {int(s) + 1}, staff {int(k) + 1} from the top)"


def pick_all(reps):
    """-> dict kind -> [row]; one row per changed item, doc/page/subject/off/on."""
    P = collections.defaultdict(list)
    for short, d in reps.docs.items():
        off, on = d["off"], d["on"]
        for k, a in off["dots"].items():
            b = on["dots"].get(k)
            if not b:
                continue
            ra, rb = (a["role"] or {}), (b["role"] or {})
            oa, ob = (a["own"] or {}), (b["own"] or {})
            if ra.get("v") != rb.get("v") and rb.get("v") == "augmentation":
                P["role_read"].append(dict(doc=short, key=k, off=a, on=b))
            elif oa.get("v") != ob.get("v") and ob.get("r") == "dot_follows_note":
                P["owner_moved"].append(dict(doc=short, key=k, off=a, on=b))
        for k, a in off["boxes"].items():
            b = on["boxes"].get(k)
            if not b:
                continue
            if (a["np"] or {}).get("v") is not True and (b["np"] or {}).get("v") is True:
                P["newly_refused"].append(dict(doc=short, key=k, off=a, on=b))
            elif ((b["own"] or {}).get("r") == "dot_follows_note") and (a["own"] or {}).get("v") != (b["own"] or {}).get("v"):
                P["twin_moved"].append(dict(doc=short, key=k, off=a, on=b))
    return P


_GRAY = {}


def gray(doc, page):
    if (doc, page) not in _GRAY:
        _GRAY[(doc, page)] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
    return _GRAY[(doc, page)]


def wrap(text, px, scale=0.46):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > px - 12 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def find_dot_and_head(rep, row):
    """-> (dot_key, dot_box, head_key|None, head_box|None, sliver_box|None).  For a notehead-class box the dot is its twin."""
    on = rep["on"]
    k = row["key"]
    sliver = None
    if k in on["dots"]:
        dk = k
    else:
        sliver = on["boxes"][k]["box"]
        dk = None
        best = 0
        for kk, d in on["dots"].items():
            if kk.split("/")[1] != k.split("/")[1] or not d["box"] or not sliver:
                continue
            a, b = sliver, d["box"]
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            if ix * iy > best:
                best, dk = ix * iy, kk
    if dk is None:
        return None, None, None, None, sliver
    role = (on["dots"][dk]["role"] or {})
    hk = (role.get("d") or {}).get("head")
    hb = (on["boxes"].get(hk) or {}).get("box") if hk else None
    return dk, on["dots"][dk]["box"], hk, hb, sliver


def draw(short, rep, row, no, kind):
    doc = DOCNAME[short]
    on, off = rep["on"], rep["off"]
    dk, dbox, hk, hbox, sliver = find_dot_and_head(rep, row)
    if dbox is None:
        dbox = row["on"]["box"]
    page = int(row["key"].split("/")[1])
    gimg = gray(doc, page)
    S._STATE["N"] = {doc: {"staff_lines": on["staff_lines"]}}
    gn, sn = S.grids(doc, page, "new")
    parts = (dk or row["key"]).split("/")
    sysi = int(parts[3 - 1 + 0]) if False else int(parts[2])
    sys_staves = sorted([k for k in on["staff_lines"] if k.startswith(f"staff/{page}/{sysi}/")], key=lambda k: int(k.split("/")[3]))
    cx = (dbox[0] + dbox[2]) / 2.0
    cy = (dbox[1] + dbox[3]) / 2.0
    # who owns what, BEFORE (flag off) and AFTER (flag on)
    item_off = off["dots"].get(dk) or off["boxes"].get(row["key"])
    item_on = on["dots"].get(dk) or on["boxes"].get(row["key"])
    filing = "staff/" + "/".join((row["key"]).split("/")[1:4])
    own_off = (row["off"]["own"] or {}).get("v") or filing
    own_on = (row["on"]["own"] or {}).get("v") or filing
    note_staff = own_on if kind in ("owner_moved", "twin_moved") else None
    if hk:
        hv = (on["boxes"].get(hk) or {}).get("own") or {}
        hs = hv.get("v") if hv else None
        hf = "staff/" + "/".join(hk.split("/")[1:4])
        note_staff = hs if (hs and hv.get("o") == "decided") else hf
    note_staff = note_staff or own_on
    sp = None
    lines_of = {}
    for key in set([filing, note_staff]):
        ln = S.seg_lines(sn, key, cx) or on["staff_lines"].get(key)
        if ln:
            lines_of[key] = ln
            sp = sp or (ln[4] - ln[0]) / 4.0
    sp = sp or 27.0
    # ---------------- zoom ----------------
    ys = [dbox[1], dbox[3]] + ([hbox[1], hbox[3]] if hbox else [])
    for ln in lines_of.values():
        ys += [ln[0], ln[4]]
    ya, yb = max(0, int(min(ys) - 1.0 * sp)), int(max(ys) + 1.0 * sp)
    xa, xb = max(0, int(cx - 7.0 * sp)), int(cx + 5.0 * sp)
    zoom = cv2.cvtColor(gimg[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    zoom = cv2.resize(zoom, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gimg[ya:yb, xa:xb], 25) + 40), 140)
    cols = ((int(dbox[0] - 3 * sp), int(dbox[0] - 1.2 * sp)), (int(dbox[2] + 0.4 * sp), int(dbox[2] + 3 * sp)))
    checked = []
    for key, colour in ((filing, GREY), (note_staff, GREEN)):
        ln = lines_of.get(key)
        if not ln:
            continue
        for y in ln:
            yy = int(round((y - ya) * SC)) + SC // 2
            cv2.line(zoom, (0, yy), (zoom.shape[1] - 1, yy), colour, 1)
            peaks = [NF.remeasure(gimg, y, *c, thr) for c in cols]
            peaks = [p for p in peaks if p[0] is not None]
            checked.append(None if not peaks else min(abs(p[1]) for p in peaks))
        yt, yb2 = int((ln[0] - 0.6 * sp - ya) * SC), int((ln[4] + 0.6 * sp - ya) * SC)
        cv2.rectangle(zoom, (1, yt), (zoom.shape[1] - 2, yb2), colour, 2 if key == note_staff else 1)
    rect = lambda img, b, col, w=1, ox=xa, oy=ya, s=SC: cv2.rectangle(img, (int((b[0] - ox) * s), int((b[1] - oy) * s)), (int((b[2] - ox) * s), int((b[3] - oy) * s)), col, w)
    if hbox:
        rect(zoom, hbox, GREEN, 2)
    if sliver is not None:
        rect(zoom, sliver, BLUE, 1)
    rect(zoom, dbox, ORANGE, 2)
    # ---------------- whole system ----------------
    all_lines = [on["staff_lines"][k] for k in sys_staves]
    ytop = max(0, int(min(l[0] for l in all_lines) - 3 * sp))
    ybot = min(gimg.shape[0], int(max(l[4] for l in all_lines) + 3 * sp))
    xl, xr = 0, gimg.shape[1]
    ink_cols = np.where((gimg[ytop:ybot] <= 140).sum(axis=0) > 3)[0]
    if len(ink_cols):
        xl, xr = int(ink_cols[0]), int(ink_cols[-1]) + 1
    TILE_W = zoom.shape[1]
    scale = (TILE_W - 0) / float(xr - xl)
    ov = cv2.cvtColor(gimg[ytop:ybot, xl:xr], cv2.COLOR_GRAY2BGR)
    ov = cv2.resize(ov, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    for k in sys_staves:
        ln = on["staff_lines"][k]
        t, b = int((ln[0] - 1.0 * sp - ytop) * scale), int((ln[4] + 1.0 * sp - ytop) * scale)
        if k == note_staff:
            cv2.rectangle(ov, (1, t), (ov.shape[1] - 2, b), GREEN, 2)
        elif k == filing:
            cv2.rectangle(ov, (1, t), (ov.shape[1] - 2, b), GREY, 2)
    ox, oy = int((cx - xl) * scale), int((cy - ytop) * scale)
    cv2.circle(ov, (ox, oy), 9, ORANGE, 2)
    if hbox:
        cv2.circle(ov, (int(((hbox[0] + hbox[2]) / 2 - xl) * scale), int(((hbox[1] + hbox[3]) / 2 - ytop) * scale)), 9, GREEN, 2)
    M = 210
    margin = np.full((ov.shape[0], M, 3), 255, np.uint8)
    for k in sys_staves:
        ln = on["staff_lines"][k]
        yy = int(((ln[0] + ln[4]) / 2 - ytop) * scale)
        nm = (on["inst"].get(k) or "no name read")[:24]
        col = (0, 120, 0) if k == note_staff else ((90, 90, 90) if k == filing else (0, 0, 0))
        cv2.putText(margin, nm, (3, yy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)
    ov = np.hstack([margin, ov])
    zoom = np.hstack([np.full((zoom.shape[0], M, 3), 255, np.uint8), zoom])
    # ---------------- words ----------------
    caps = []
    role_off, role_on = (item_off or {}).get("role") or {}, (item_on or {}).get("role") or {}
    nm_note = (on["inst"].get(note_staff) or "unnamed-staff")
    if kind == "newly_refused":
        caps.append((f"BEFORE: this box, {round(row['on']['w'], 2)} x {round(row['on']['h'], 2)} staff spaces, was kept as a {row['on']['cls']} notehead.", RED))
        caps.append(("AFTER: it is refused as a dot (a notehead is about 1.3 spaces wide, a dot 0.5).", GREEN))
    else:
        if dk is not None and role_off.get("v") != role_on.get("v"):
            caps.append(("BEFORE: the dot's note belongs to another staff, so the dot could not find it -- "
                         "\"cannot tell\" whether it lengthens a note.", RED))
            caps.append((f"AFTER: it lengthens the note to its left, a note of the {nm_note} staff.", GREEN))
        oo = (row["off"].get("own") if kind == "twin_moved" else (item_off or {}).get("own")) or {}
        on_ = (item_on or {}).get("own") or {}
        if sliver is not None:
            caps.append((f"BEFORE: the notehead-shaped box (blue) was given to {label(on, own_off)}, by {WORDS.get(oo.get('r'), oo.get('r'))}.", RED))
            caps.append((f"AFTER: it goes with the dot it overlaps, to {label(on, own_on)}.", GREEN))
        elif (row["off"]["own"] or {}).get("v") != (row["on"]["own"] or {}).get("v"):
            caps.append((f"BEFORE: the dot belongs to {label(on, own_off)}, by {WORDS.get(oo.get('r'), oo.get('r'))}.", RED))
            caps.append((f"AFTER: it belongs to {label(on, own_on)}, the staff of the note it trails.", GREEN))
    caps.append(("Orange = the dot; green box = its note; blue box = a notehead-shaped box on the same ink; grey outline = the staff the dot was filed on; "
                 "green outline = its note's staff.", GREY))
    return ov, zoom, caps, checked, dict(doc=short, page=page, subject=row["key"], dot=dk, head=hk)


def main(d, seed):
    reps = Rep(d, "tiles"), Rep(d, "all")
    # tiles 1-3 are the three of Sean's, from the tile-page replay; the rest are seeded from the whole-document replays
    tile_rep = reps[0].docs.get("brahms")
    all_reps = reps[1]
    rng = random.Random(seed)
    first = []
    for k in ("glyph/7/1/0/9/9", "glyph/18/1/12/6/18", "glyph/5/0/1/5/32"):
        src = tile_rep["on"]
        item_on = src["dots"].get(k) or src["boxes"].get(k)
        item_off = tile_rep["off"]["dots"].get(k) or tile_rep["off"]["boxes"].get(k)
        kind = "twin_moved" if k in src["boxes"] else ("role_read" if (item_off["role"] or {}).get("v") != (item_on["role"] or {}).get("v") else "owner_moved")
        first.append((kind, "brahms", tile_rep, dict(doc="brahms", key=k, off=item_off, on=item_on)))
    P = pick_all(all_reps)
    print({k: len(v) for k, v in P.items()})
    quota = [("role_read", 3), ("owner_moved", 3), ("newly_refused", 1), ("twin_moved", 2)]
    picks = []
    for kind, n in quota:
        pool = [r for r in P[kind] if int(r["key"].split("/")[1]) >= 2 and r["key"] not in [f[3]["key"] for f in first]]
        docs = collections.defaultdict(list)
        for r in pool:
            docs[r["doc"]].append(r)
        chosen = []
        order = sorted(docs)
        i = 0
        while len(chosen) < n and any(docs.values()):
            dname = order[i % len(order)]
            i += 1
            if docs[dname]:
                chosen.append(docs[dname].pop(rng.randrange(len(docs[dname]))))
        picks += [(kind, r["doc"], all_reps.docs[r["doc"]], r) for r in chosen]
    picks = (first + picks)[:12]
    tiles, info, allchk = [], [], []
    for i, (kind, short, rep, row) in enumerate(picks, 1):
        ov, zoom, caps, chk, meta = draw(short, rep, row, i, kind)
        allchk += chk
        W = max(ov.shape[1], zoom.shape[1])
        cap_lines = []
        for t, col in caps:
            for ln in wrap(t, W):
                cap_lines.append((ln, col))
        head = wrap(f"{i}. {TITLES[kind]}", W, 0.5)
        hh = 8 + 20 * len(head)
        ch = 8 + 18 * len(cap_lines) + 20
        c = np.full((hh + ov.shape[0] + zoom.shape[0] + ch, W, 3), 255, np.uint8)
        for j, ln in enumerate(head):
            cv2.putText(c, ln, (4, 18 + 20 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        c[hh:hh + ov.shape[0], :ov.shape[1]] = ov
        c[hh + ov.shape[0]:hh + ov.shape[0] + zoom.shape[0], :zoom.shape[1]] = zoom
        y0 = hh + ov.shape[0] + zoom.shape[0]
        for j, (ln, col) in enumerate(cap_lines):
            cv2.putText(c, ln, (6, y0 + 18 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.46, tuple(int(v * 0.8) for v in col), 1, cv2.LINE_AA)
        cv2.putText(c, f"{short} pdf page {meta['page']}  {meta['subject'].replace('glyph/', '')}", (6, y0 + ch - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (110, 110, 110), 1, cv2.LINE_AA)
        cv2.rectangle(c, (0, 0), (W - 1, c.shape[0] - 1), (190, 190, 190), 1)
        tiles.append(c)
        info.append(dict(n=i, kind=kind, **meta, caps=[t for t, _ in caps]))
    cols = 3
    rows = []
    W = max(t.shape[1] for t in tiles)
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
            "A dot belongs to the note immediately to its LEFT, and so to that note's staff.  A dot-sized box is never a notehead.  Tiles 1-3 are the three you judged; 4-12 are seeded changes.",
            "BEFORE = the 10-07 night record as it stands; AFTER = the same record, the same stages (gather + adjudicate), with the dot rule on.  NOT judged -- you decide.",
            "ORANGE = the dot (orange ring on the whole system).  GREEN = its note.  GREY outline = the staff that boxed the dot.  GREEN outline = the staff of its note.  Staff names at the left.",
            "Thin grey/green horizontal lines in each zoom are the five staff lines of the two staves, 1 px, re-measured against the ink rows of the page (count printed by the script).")):
        cv2.putText(legend, txt, (8, 24 + 26 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    OUT.with_suffix(".json").write_text(json.dumps(info, indent=1, default=str))
    ok = sum(1 for c in allchk if c is not None and c <= 2.0)
    print(f"staff lines drawn {len(allchk)}: within 2 px of an ink row {ok}, further {sum(1 for c in allchk if c is not None and c > 2.0)}, no ink to measure {sum(1 for c in allchk if c is None)}")
    for t in info:
        print(t["n"], t["kind"], t["doc"], t["subject"], "|", " || ".join(t["caps"][:2]))
    print("wrote", OUT)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
