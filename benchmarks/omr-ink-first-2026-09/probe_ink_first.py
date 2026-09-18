"""INK-FIRST: for every piece of ink on Brahms 1 / Breitkopf p2, what explains it?

The honest version of the test
`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §7 got wrong: that one ran
BOX-FIRST — every row started from a detector box and asked what ink was under
it — which is the arrangement §1-§5 argue against, so it inherited the defect it
was meant to examine. This asks from the INK.

READ-ONLY. Refuses to report unless every control passes.

CONVENTION ASSUMED, and it is Sean's own (2026-09-18):
  *"Since all stems are connected to note heads, it will be incredibly helpful
  to have a strong reading of note heads to be able to determine later if a
  line in a box was a stem or something else."*
  A STEM HAS A NOTEHEAD AT ONE OF ITS ENDS, BY DEFINITION. A BARLINE HAS NONE.
WHAT WOULD FALSIFY IT: a near-vertical ink run with no notehead at either end
  that the print shows IS a stem — i.e. the notehead was simply missed. This
  probe measures exactly that as the veto's COST.
NOT CONFIRMED WITH SEAN beyond the quoted sentence.

⚠️ TWO BOX CONVENTIONS IN ONE RECORD (the bug that produced a clean believable
   zero on 100 of 106 rows last night):
     glyph_box.value              = [name, x, y, w, h]      (width/height)
     ink.detail.ink_bbox_canonical = [x0, y0, x1, y1]        (corners)
   Control B asserts each against the row's own stated width_spaces.

⚠️ A SUBJECT'S LAST COORDINATE IS A POSITIONAL INDEX into the detector's output
   list, so subject keys COLLIDE ACROSS RECORDS. Control E class-matches every
   cross-record join before using one.
"""
import sys
import json
import math
import statistics
import collections

sys.path.insert(0, "benchmarks/omr-ledger-extrapolation-2026-09")
from recordstream import stream_array  # noqa: E402

# ⚠️ DEFAULTS TO THE GATHER-ONLY DUMP. Every quantity below is a GATHER
# observation, and the full CLI writes its record only after ADJUDICATE (whose
# glyph_owner step this repo records taking >40 min on this document). Pass the
# full record as argv[1] to re-run against it -- the observation rows are the
# same call's output, which is the control.
REC = ("benchmarks/omr-ink-first-2026-09/out/"
       "brahms1-breitkopf-p2.gather.json")
_pos = [a for a in sys.argv[1:] if not a.startswith("--")]
if _pos:
    REC = _pos[0]
HAND = "data/user-labeled/v18-2026-09-03-complete-breitkopf"
MANIFEST = ("benchmarks/omr-labeling-survey-2026-09/phase3-merged/breitkopf/"
            "breitkopf-cells.json")
CROP = "benchmarks/omr-stem-crop-pass-2026-09"
CATALOG = "data/user-labeled/catalog-214.yaml"

PAGE = 1                      # 0-based PDF page index; the labelling tag is "p2"
NOTEHEAD_PREFIX = "notehead"

# A near-vertical run: taller than it is wide by this much, and at least this
# tall. Both are STATED rather than fitted -- a stem is >= 2 staff spaces by
# engraving convention (the crop pass's own "too SHORT (h < 2.0 spaces)" bucket
# uses the same number, so it is inherited rather than invented), and 2.0 for
# the aspect is the loosest thing that still means "vertical".
RUN_MIN_H_SPACES = 2.0
RUN_MIN_ASPECT = 2.0

# An end of a run "has a notehead" if a notehead box's centre lies within this
# many staff spaces of the run's top or bottom end, horizontally within this
# much of the run's own x. A stem stands at the SIDE of its notehead (CLAUDE.md,
# measured at 0.35-0.47 notehead widths), so the x window must admit a head
# offset by about one head width; a head is ~1.3 spaces wide on this plate.
END_DY_SPACES = 1.0
END_DX_SPACES = 1.6

# ⚠️⚠️ THE HAND CORPUS CARRIES NO STRUCTURAL CLASS, BY PROJECT POLICY, AND
# WITHOUT THIS SPLIT THE PARTITION IS MEANINGLESS. CLAUDE.md's labelling
# instructions say in terms: "SKIP classical-CV structural elements -- staff
# lines (`staff`), stems (`stem`), beams (`beam`)", because a human cannot box
# a thin line. Verified against this version's own vocabulary: 35 classes, not
# one of them structural.
#
# So a detector BEAM box sitting on beam ink lands in "detector only" and would
# be read as an INVENTION, and every stem and every scrap of staff residue
# lands in "neither" and would be read as MISSED MUSIC. Both are artefacts of
# what the hand pass was chartered not to draw. Split out and reported apart.
STRUCTURAL = ("stem", "beam", "staff", "ledgerLine", "brace", "barline")


def load_class_names():
    names, on = [], False
    for line in open(CATALOG):
        if line.startswith("names:"):
            on = True
            continue
        if on:
            if line.startswith("- "):
                names.append(line[2:].strip())
            elif line.strip() and not line.startswith(" "):
                break
    return names


def cell_of(subject):
    """The CELL subject key a glyph subject belongs to.

    ⚠️ `subject.rsplit("/", 1)[0]` IS NOT IT, and reading it that way is a
    clean believable zero waiting to happen. `record.glyph(1,0,2,4,13)` is
    `glyph/1/0/2/4/13`, whose parent renders `glyph/1/0/2/4` -- while
    `record.cell(1,0,2,4)` is `cell/1/0/2/4`. The KIND word differs, so a
    dict keyed one way and looked up the other misses every time and reports
    an empty join as an empty page. `Q.CELL_STAFF_SPACE` is filed on the cell
    and `Q.INK` / `Q.GLYPH_BOX` on glyphs, so this probe needs both in one
    key space. Checked against `record.py`, not assumed.
    """
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5])


def iou(a, b):
    """Corner boxes."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1])
    ub = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (ua + ub - inter) if (ua + ub - inter) > 0 else 0.0


def overlap_frac_of_first(a, b):
    """How much of *a* lies inside *b*."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1])
    return inter / ua if ua > 0 else 0.0


def main():
    names = load_class_names()
    manifest = {e["cell_id"]: e for e in json.load(open(MANIFEST))}
    meta = json.load(open(f"{HAND}/metadata.json"))
    hand_cells = [e["cell_id"] for e in meta["per_cell"]
                  if "-p2-" in e["cell_id"]]

    # ── the record ───────────────────────────────────────────────────────────
    glyph_box = {}                                   # subject -> (cls, corners)
    ink = collections.defaultdict(list)              # cell -> [row]
    sp_by_cell, halfstep_by_cell = {}, {}
    pos_by_glyph = {}
    conv_err_ink, conv_err_glyph = [], []
    n_rows = 0
    for row in stream_array(REC, "observations"):
        n_rows += 1
        q, sub = row.get("quantity"), row.get("subject") or ""
        if q == "glyph_box":
            v = row.get("value") or []
            if len(v) == 5:
                x, y, w, h = (float(t) for t in v[1:])
                glyph_box[sub] = (v[0], (x, y, x + w, y + h))
        elif q == "ink":
            d = row.get("detail") or {}
            bb = d.get("ink_bbox_canonical")
            if not bb or len(bb) != 4:
                continue
            cell = cell_of(sub)
            bb = [float(t) for t in bb]
            sp = d.get("cell_staff_space_px")
            ws, hs = d.get("width_spaces"), d.get("height_spaces")
            if sp:
                sp_by_cell[cell] = float(sp)
                if ws is not None:
                    conv_err_ink.append(
                        abs((bb[2] - bb[0]) / float(sp) - float(ws)))
            ink[cell].append({
                "subject": sub, "box": bb,
                "w_sp": ws, "h_sp": hs,
                "fill": d.get("ink_fill"),
                "n_comp": d.get("ink_n_components"),
                "share": d.get("ink_share_of_cell"),
                "cov": d.get("ink_detector_coverage"),
                "by": d.get("ink_explained_by") or [],
                "area": d.get("ink_area_px"),
            })
        elif q == "cell_staff_space":
            d = row.get("detail") or {}
            if d.get("half_step"):
                halfstep_by_cell[sub] = float(d["half_step"])
        elif q == "notehead_staff_position":
            pos_by_glyph[sub] = float(row.get("value"))

    # top_y of each cell's grid, INVERTED from the position formula
    # pos = (y_center - top_y) / half_step   =>   top_y = y_center - pos*hs
    top_y_by_cell = {}
    spread = []
    tmp = collections.defaultdict(list)
    for g, pos in pos_by_glyph.items():
        cell = cell_of(g)
        hs = halfstep_by_cell.get(cell)
        gb = glyph_box.get(g)
        if hs is None or gb is None:
            continue
        yc = (gb[1][1] + gb[1][3]) / 2.0
        tmp[cell].append(yc - pos * hs)
    for cell, vals in tmp.items():
        top_y_by_cell[cell] = statistics.median(vals)
        if len(vals) > 1:
            spread.append(max(vals) - min(vals))

    # ── staves per system, to convert the manifest's PAGE-WIDE staff index ──
    sys_staves = collections.defaultdict(set)
    for cell in ink:
        p = cell.split("/")
        sys_staves[int(p[2])].add(int(p[3]))
    n_sys0 = len(sys_staves.get(0, ()))
    offset = {0: 0, 1: n_sys0}

    def record_cell(entry):
        s_page_wide = int(entry["staff_index"])
        sysi = int(entry["system_index"])
        st = s_page_wide - offset.get(sysi, 0)
        return f"cell/{PAGE}/{sysi}/{st}/{int(entry['measure_index'])}"

    # ── CONTROLS ────────────────────────────────────────────────────────────
    print("=" * 78)
    print("REACH FIRST")
    print("=" * 78)
    print(f"record rows read                     : {n_rows}")
    print(f"cells carrying Q.INK rows            : {len(ink)}")
    print(f"Q.INK rows on page {PAGE}                 : "
          f"{sum(len(v) for v in ink.values())}")
    print(f"glyph_box rows                       : {len(glyph_box)}")
    print(f"staves in system 0 / system 1        : "
          f"{n_sys0} / {len(sys_staves.get(1, ()))}")
    print(f"hand-labelled cells on this page     : {len(hand_cells)}")
    if not ink or not hand_cells:
        sys.exit("DEAD: zero reach -- no ink rows or no hand cells")

    print()
    print("=" * 78)
    print("CONTROLS (all must pass)")
    print("=" * 78)

    cB = statistics.median(conv_err_ink) if conv_err_ink else 9.9
    print(f"B  ink corners reproduce their own width_spaces : "
          f"median err {cB:.4f} spaces (n={len(conv_err_ink)})")

    # glyph convention, independently: a notehead is ~1 space TALL by
    # convention (CLAUDE.md: 0.61-1.12 spaces), which only holds if [x,y,w,h]
    # is read as width/height rather than as corners.
    nh_h = []
    for s, (cls, bx) in glyph_box.items():
        if not str(cls).startswith(NOTEHEAD_PREFIX):
            continue
        cell = cell_of(s)
        sp = sp_by_cell.get(cell)
        if sp:
            nh_h.append((bx[3] - bx[1]) / sp)
    cB2 = statistics.median(nh_h) if nh_h else -1
    print(f"B2 notehead box median HEIGHT                   : "
          f"{cB2:.2f} spaces (convention: ~1.0; n={len(nh_h)})")

    # frame join
    frame_rows, frame_bad = [], []
    for cid in hand_cells:
        e = manifest.get(cid)
        if not e:
            frame_bad.append((cid, "no manifest entry"))
            continue
        rc = record_cell(e)
        ys = [float(y) for y in e["staff_line_ys_canonical"]]
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        man_sp = sum(gaps) / len(gaps)
        rec_sp = sp_by_cell.get(rc)
        rec_top = top_y_by_cell.get(rc)
        if rec_sp is None:
            frame_bad.append((cid, f"{rc} has no ink/spacing row"))
            continue
        d_sp = abs(rec_sp - man_sp)
        d_top = abs(rec_top - ys[0]) if rec_top is not None else None
        frame_rows.append((cid, rc, man_sp, rec_sp, ys[0], rec_top,
                           d_sp, d_top))
    print()
    print(f"C  frame join, {len(frame_rows)} of {len(hand_cells)} cells resolved"
          f"  ({len(frame_bad)} unresolved)")
    for cid, rc, ms, rs, mt, rt, dsp, dtop in frame_rows:
        print(f"   {cid:<28s} -> {rc:<18s} space {ms:7.2f}/{rs:7.2f} "
              f"(d={dsp:5.2f})  top {mt:7.1f}/"
              f"{'None' if rt is None else format(rt, '7.1f')} "
              f"(d={'n/a' if dtop is None else format(dtop, '6.1f')})")
    for cid, why in frame_bad:
        print(f"   UNRESOLVED {cid}: {why}")
    if spread:
        print(f"   top_y inversion self-consistency: max within-cell spread "
              f"{max(spread):.2f} px over {len(spread)} cells")

    sp_ok = [r for r in frame_rows if r[6] <= 1.0]
    top_ok = [r for r in frame_rows if r[7] is not None and r[7] <= 5.0]
    print(f"   spacing agrees (<=1.0 px) : {len(sp_ok)} of {len(frame_rows)}")
    print(f"   grid top agrees (<=5.0 px): {len(top_ok)} of "
          f"{len([r for r in frame_rows if r[7] is not None])}")

    # ── hand boxes into canonical px, per cell ──────────────────────────────
    hand = collections.defaultdict(list)
    n_hand = 0
    for cid in hand_cells:
        e = manifest.get(cid)
        if not e:
            continue
        rc = record_cell(e)
        W = float(e["cell_canonical_w"])
        H = float(e["cell_canonical_h"])
        try:
            lines = open(f"{HAND}/labels/{cid}.txt").read().split("\n")
        except FileNotFoundError:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            p = ln.split()
            ci, cx, cy, w, h = int(p[0]), *[float(t) for t in p[1:5]]
            x0 = (cx - w / 2) * W
            x1 = (cx + w / 2) * W
            y0 = (cy - h / 2) * H
            y1 = (cy + h / 2) * H
            hand[rc].append({"cls": names[ci] if ci < len(names) else str(ci),
                             "box": (x0, y0, x1, y1), "cell_id": cid})
            n_hand += 1
    print()
    print(f"D  hand boxes placed into canonical px : {n_hand} "
          f"over {len(hand)} cells")

    # BEHAVIOURAL control: hand noteheads should land on detector noteheads
    hit, miss, tot = 0, 0, 0
    for rc, hs_ in hand.items():
        dets = [(c, b) for s, (c, b) in glyph_box.items()
                if cell_of(s) == rc]
        for h in hs_:
            if not h["cls"].startswith(NOTEHEAD_PREFIX):
                continue
            tot += 1
            best = max((iou(h["box"], b) for c, b in dets
                        if str(c).startswith(NOTEHEAD_PREFIX)), default=0.0)
            if best >= 0.3:
                hit += 1
            else:
                miss += 1
    rate = hit / tot if tot else 0.0
    print(f"E  hand NOTEHEADS landing on a detector notehead (IoU>=0.3): "
          f"{hit} of {tot} = {rate:.3f}")

    # cross-record class match for the crop-pass print verdicts
    adj = {r["id"]: r["verdict"] for r in
           json.load(open(f"{CROP}/ADJUDICATION-breitkopf.json"))["rows"]}
    tiles = {t["id"]: t for t in
             json.load(open(f"{CROP}/out/crop-manifest-breitkopf.json"))["tiles"]}
    print_rows = []
    cls_ok = cls_bad = 0
    for tid, verdict in adj.items():
        t = tiles.get(tid)
        if not t or t["where"]["page"] != PAGE:
            continue
        sub = t["subject"]
        got = glyph_box.get(sub)
        if got is None:
            cls_bad += 1
            continue
        if got[0] == t.get("cls"):
            cls_ok += 1
            print_rows.append({"id": tid, "subject": sub, "verdict": verdict,
                               "bucket": t["bucket"], "cls": got[0],
                               "box": got[1]})
        else:
            cls_bad += 1
    print(f"F  crop-pass print verdicts on page {PAGE}: {cls_ok} class-matched, "
          f"{cls_bad} refused (index collision guard)")

    fail = []
    if cB > 0.05:
        fail.append("B: ink box convention not confirmed")
    if not (0.5 <= cB2 <= 1.6):
        fail.append(f"B2: notehead height {cB2:.2f} spaces is not ~1 space -- "
                    "glyph box convention not confirmed")
    if len(sp_ok) < len(frame_rows):
        fail.append(f"C: only {len(sp_ok)}/{len(frame_rows)} cells agree on "
                    "staff spacing -- FRAMES DISAGREE")
    if rate < 0.5:
        fail.append(f"E: hand noteheads land on detector noteheads only "
                    f"{rate:.3f} of the time -- FRAMES DISAGREE")
    if fail:
        print()
        print("REFUSED -- controls did not pass:")
        for f in fail:
            print("  *", f)
        sys.exit(2)
    print()
    print("ALL CONTROLS PASS")

    # ── PAGE-WIDE INK COMPOSITION, against CLAUDE.md's committed figures ───
    print()
    print("=" * 78)
    print("PAGE-WIDE INK COMPOSITION  (all cells, not just the 19)")
    print("=" * 78)
    allink = [r for v in ink.values() for r in v]
    percell = {c: (v[0]["n_comp"] if v and v[0]["n_comp"] else len(v))
               for c, v in ink.items()}
    specks = [r for r in allink
              if (r["w_sp"] or 9) < 0.2 and (r["h_sp"] or 9) < 0.2]
    big = [r for r in allink if (r["share"] or 0) >= 0.30]
    tot_a = sum(r["area"] or 0 for r in allink) or 1
    print(f"  ink rows                          : {len(allink)}")
    print(f"  cells                             : {len(ink)}")
    print(f"  components per cell, median       : "
          f"{statistics.median(list(percell.values())):.1f}  "
          f"(min {min(percell.values())}, max {max(percell.values())})")
    print(f"  SPECKS (<0.2 x 0.2 spaces)        : {len(specks)} = "
          f"{len(specks)/len(allink):.1%} of pieces, "
          f"{sum(r['area'] or 0 for r in specks)/tot_a:.2%} of area")
    print(f"  pieces holding >=30% of their cell: {len(big)} = "
          f"{len(big)/len(allink):.1%} of pieces, "
          f"{sum(r['area'] or 0 for r in big)/tot_a:.1%} of area")
    print(f"  largest share_of_cell             : "
          f"{max((r['share'] or 0) for r in allink):.4f}")
    print("  CLAUDE.md records this plate as the one that SHATTERS -- 56% of")
    print("  Breitkopf's rows specks, 5.6 components per cell against")
    print("  Litolff's 30. Compare the two lines above.")

    # ── THE INK-FIRST PARTITION ─────────────────────────────────────────────
    print()
    print("=" * 78)
    print("THE INK-FIRST PARTITION  (only the 19 hand-labelled cells)")
    print("=" * 78)
    HAND_HIT = 0.25       # a hand box explains this much of the ink piece
    DET_HIT = 0.25

    buckets = collections.Counter()
    rows = []
    for rc in sorted(hand):
        sp = sp_by_cell.get(rc)
        if not sp:
            continue
        dets = [(c, b) for s, (c, b) in glyph_box.items()
                if cell_of(s) == rc]
        hs_ = hand[rc]
        for r in ink.get(rc, []):
            b = r["box"]
            h_ov = [(h["cls"], overlap_frac_of_first(b, h["box"])) for h in hs_]
            d_ov = [(c, overlap_frac_of_first(b, bb)) for c, bb in dets]
            by_hand = [c for c, f in h_ov if f >= HAND_HIT]
            by_det = [c for c, f in d_ov if f >= DET_HIT]
            # ⚠️ STRUCTURAL classes are separated FIRST. The hand pass was
            # chartered not to draw them, so calling a detector `beam` box on
            # beam ink an "invention" would be scoring the corpus's own
            # policy.
            struct = [c for c in by_det
                      if any(str(c).startswith(t) for t in STRUCTURAL)]
            symbolic = [c for c in by_det if c not in struct]
            if by_hand and symbolic:
                k = "1 REAL MARK, detector agrees"
            elif symbolic and not by_hand:
                k = "2 DETECTOR INVENTION (a SYMBOL class, hand says no)"
            elif by_hand and not symbolic:
                k = "3 MISSED MARK (hand only)"
            elif struct:
                k = "2s STRUCTURAL ink (detector calls it stem/beam/staff)"
            else:
                k = "4 UNEXPLAINED (neither)"
            buckets[k] += 1
            rows.append({**r, "cell": rc, "sp": sp, "bucket": k,
                         "by_hand": by_hand, "by_det": by_det})
    tot_ink = len(rows)
    tot_area = sum(r["area"] or 0 for r in rows) or 1
    print(f"{'bucket':<36s} {'n':>6s} {'share':>7s} {'area share':>11s}")
    for k in sorted(buckets):
        n = buckets[k]
        a = sum(r["area"] or 0 for r in rows if r["bucket"] == k)
        print(f"{k:<36s} {n:>6d} {n/tot_ink:>7.1%} {a/tot_area:>11.1%}")
    print(f"{'TOTAL':<36s} {tot_ink:>6d}")

    # ── SHAPE AND SIZE SPLIT of the unexplained bucket ─────────────────────
    print()
    print("=" * 78)
    print("THE UNEXPLAINED BUCKET, SPLIT BY SHAPE AND SIZE")
    print("=" * 78)
    un = [r for r in rows if r["bucket"].startswith("4")]
    if not un:
        print("EMPTY")
    else:
        def shape(r):
            w, h = r["w_sp"] or 0, r["h_sp"] or 0
            if w < 0.2 and h < 0.2:
                return "a SPECK (<0.2 x 0.2 spaces)"
            if h >= RUN_MIN_H_SPACES and w > 0 and h / w >= RUN_MIN_ASPECT:
                return "a VERTICAL RUN (h>=2sp, h/w>=2)"
            if w >= 2.0 and h > 0 and w / h >= 3.0:
                return "a HORIZONTAL RUN (w>=2sp, w/h>=3)"
            if 0.2 <= w <= 2.0 and 0.2 <= h <= 2.0:
                return "MARK-SIZED (0.2-2.0 spaces both ways)"
            return "OTHER / large blob"
        sh = collections.Counter(shape(r) for r in un)
        un_area = sum(r["area"] or 0 for r in un) or 1
        print(f"{'shape':<38s} {'n':>5s} {'of unexpl':>10s} "
              f"{'of its area':>12s} {'med w':>7s} {'med h':>7s} "
              f"{'max area':>9s} {'med area':>9s}")
        for k in sorted(sh):
            g = [r for r in un if shape(r) == k]
            a = sum(r["area"] or 0 for r in g)
            ar = sorted((r["area"] or 0) for r in g)
            print(f"{k:<38s} {len(g):>5d} {len(g)/len(un):>10.1%} "
                  f"{a/un_area:>12.1%} "
                  f"{statistics.median([r['w_sp'] or 0 for r in g]):>7.2f} "
                  f"{statistics.median([r['h_sp'] or 0 for r in g]):>7.2f} "
                  f"{ar[-1]:>9d} {ar[len(ar)//2]:>9d}")
        print(f"\nunexplained ink as a share of all ink in these cells: "
              f"{len(un)/tot_ink:.1%} of pieces, "
              f"{un_area/tot_area:.1%} of area")

    # ── SEAN'S DISCRIMINATOR ───────────────────────────────────────────────
    print()
    print("=" * 78)
    print("SEAN'S RULE: a stem has a NOTEHEAD at one of its ends; a BARLINE has none")
    print("=" * 78)

    def ends_have_head(r, heads):
        """Does a notehead centre sit at the TOP or BOTTOM end of this run?"""
        x0, y0, x1, y1 = r["box"]
        sp = r["sp"]
        out = []
        for cls, b in heads:
            hx = (b[0] + b[2]) / 2.0
            hy = (b[1] + b[3]) / 2.0
            if abs(hx - (x0 + x1) / 2.0) > END_DX_SPACES * sp:
                continue
            if abs(hy - y0) <= END_DY_SPACES * sp:
                out.append(("top", cls))
            elif abs(hy - y1) <= END_DY_SPACES * sp:
                out.append(("bottom", cls))
        return out

    def is_run(r):
        return ((r["h_sp"] or 0) >= RUN_MIN_H_SPACES
                and (r["w_sp"] or 0) > 0
                and (r["h_sp"] or 0) / (r["w_sp"] or 1) >= RUN_MIN_ASPECT)

    all_runs = [r for r in rows if is_run(r)]
    runs = [r for r in un if is_run(r)]
    # ⚠️ REACH, BOTH WAYS, because the unexplained bucket is NOT the whole
    # stem population. A stem FUSED to its own notehead is one component that
    # overlaps a hand notehead box, so it lands in bucket 1 by construction --
    # the veto's domain is specifically the DETACHED vertical run.
    print(f"REACH: vertical runs over ALL ink in these cells : {len(all_runs)}"
          f" of {tot_ink} ink rows")
    by_b = collections.Counter(r["bucket"] for r in all_runs)
    for k in sorted(by_b):
        print(f"        {k:<36s} {by_b[k]:>5d}")
    print(f"REACH: vertical runs in the UNEXPLAINED bucket   : {len(runs)}"
          f"  <- the veto's domain")
    if not runs:
        print("DEAD: no vertical runs in the unexplained bucket")
    else:
        det_heads = collections.defaultdict(list)
        for s, (c, b) in glyph_box.items():
            if str(c).startswith(NOTEHEAD_PREFIX):
                det_heads[cell_of(s)].append((c, b))

        # ⚠️⚠️ THE POSITIVE CONTROL FOR THE COST COUNTER, AND IT IS NOT
        # OPTIONAL. The measured cost is ZERO, and a counter that reads zero
        # and has never been shown able to read anything else is this repo's
        # own "clean, believable zero" -- the failure mode of every probe in
        # this thread. `--drop-det-heads` deletes the detector's noteheads
        # from every cell, which is exactly the world the veto is dangerous
        # in: the print carries heads and the reading does not. If the cost
        # does NOT rise under it, the zero above is measuring the instrument
        # and not the page.
        if "--drop-det-heads" in sys.argv:
            print()
            print("  ⚠️ POSITIVE CONTROL ACTIVE: every detector notehead "
                  "removed. The cost MUST rise.")
            det_heads = collections.defaultdict(list)
        hand_heads = collections.defaultdict(list)
        for rc, hs_ in hand.items():
            for h in hs_:
                if h["cls"].startswith(NOTEHEAD_PREFIX):
                    hand_heads[rc].append((h["cls"], h["box"]))

        tab = collections.Counter()
        cost_rows = []
        for r in runs:
            d = bool(ends_have_head(r, det_heads.get(r["cell"], [])))
            t = bool(ends_have_head(r, hand_heads.get(r["cell"], [])))
            tab[(d, t)] += 1
            if not d and t:
                cost_rows.append(r)
        print()
        print("  notehead at an end, by whose reading:")
        print(f"{'':<4s}{'detector':>10s}{'hand truth':>13s}{'n':>7s}")
        for (d, t), n in sorted(tab.items(), key=lambda kv: (-kv[1],)):
            print(f"{'':<4s}{str(d):>10s}{str(t):>13s}{n:>7d}")
        no_head_either = tab[(False, False)]
        print()
        print(f"  VETO REACH  (no head at either end, by BOTH readings): "
              f"{no_head_either} of {len(runs)} runs = "
              f"{no_head_either/len(runs):.1%}")
        print(f"  VETO COST   (detector says no head, HAND TRUTH SAYS THERE IS "
              f"ONE): {len(cost_rows)} of {len(runs)} = "
              f"{len(cost_rows)/len(runs):.1%}")
        print(f"              -> these are runs the veto would delete as "
              f"'not a stem' where the print carries a head the detector "
              f"missed.")
        print()
        print(f"  POSITIVE HALF (INFER-shaped, NOT proposed for EVALUATE): "
              f"runs WITH a head at an end, by hand truth: "
              f"{tab[(True, True)] + tab[(False, True)]}")

        # ⚠️ THE SAME TABLE OVER ALL 68 RUNS, because 7 is too thin to score a
        # rule on and the veto's SAFETY is a property of the discriminator, not
        # of one bucket. If the rule works, runs the hand pass vouches for
        # should carry a head at an end and runs nothing vouches for should
        # not.
        print()
        print("-" * 78)
        print("  THE DISCRIMINATOR OVER ALL 68 VERTICAL RUNS, BY BUCKET")
        print("-" * 78)
        print(f"  {'bucket':<52s}{'n':>4s}{'head@end det':>14s}"
              f"{'head@end hand':>15s}")
        for k in sorted(set(r["bucket"] for r in all_runs)):
            g = [r for r in all_runs if r["bucket"] == k]
            nd = sum(1 for r in g
                     if ends_have_head(r, det_heads.get(r["cell"], [])))
            nh = sum(1 for r in g
                     if ends_have_head(r, hand_heads.get(r["cell"], [])))
            print(f"  {k:<52s}{len(g):>4d}{nd:>14d}{nh:>15d}")
        # the cost over the whole run population
        cost_all = [r for r in all_runs
                    if not ends_have_head(r, det_heads.get(r["cell"], []))
                    and ends_have_head(r, hand_heads.get(r["cell"], []))]
        no_head_all = [r for r in all_runs
                       if not ends_have_head(r, det_heads.get(r["cell"], []))
                       and not ends_have_head(r, hand_heads.get(r["cell"], []))]
        print()
        print(f"  OVER ALL 68 RUNS -- veto would fire on {len(no_head_all)}; "
              f"its COST (hand head, no detector head) is {len(cost_all)}")
        for r in cost_all:
            print(f"    COST: {r['subject']} {r['w_sp']}x{r['h_sp']} sp "
                  f"bucket={r['bucket']}")

        # the seven unexplained runs, named
        print()
        print("  THE SEVEN UNEXPLAINED VERTICAL RUNS, NAMED:")
        for r in sorted(runs, key=lambda z: -(z["area"] or 0)):
            d = ends_have_head(r, det_heads.get(r["cell"], []))
            t = ends_have_head(r, hand_heads.get(r["cell"], []))
            print(f"    {r['subject']:<26s} {r['w_sp']:>6}x{r['h_sp']:<7} sp "
                  f"area {r['area']:>7} fill {r['fill']} "
                  f"ncomp {r['n_comp']}  det={bool(d)} hand={bool(t)}")

        # the largest unexplained pieces, because 84.9% of the area is a
        # handful of merges and a median hides that
        print()
        print("  THE FIVE LARGEST UNEXPLAINED PIECES (84.9% of the area is a "
              "few merges):")
        for r in sorted(un, key=lambda z: -(z["area"] or 0))[:5]:
            print(f"    {r['subject']:<26s} {r['w_sp']:>7}x{r['h_sp']:<7} sp "
                  f"area {r['area']:>7} share_of_cell {r['share']} "
                  f"ncomp {r['n_comp']}")

        # against the print-settled too TALL population
        print()
        print("-" * 78)
        print("  AGAINST THE PRINT-SETTLED `too TALL` POPULATION")
        print("-" * 78)
        tall = [p for p in print_rows if p["bucket"].startswith("too TALL")]
        print(f"  REACH: `too TALL` print verdicts on page {PAGE}: {len(tall)}")
        if not tall:
            print("  DEAD: no `too TALL` tile on this page in the crop sample")
        else:
            for p in tall:
                cell = cell_of(p["subject"])
                sp = sp_by_cell.get(cell)
                hd = det_heads.get(cell, [])
                hh = hand_heads.get(cell, [])
                # the ink piece that this box sits on
                best, bestf = None, 0.0
                for r in ink.get(cell, []):
                    f = overlap_frac_of_first(p["box"], r["box"])
                    if f > bestf:
                        best, bestf = r, f
                if best is None or not sp:
                    print(f"  {p['id']} {p['subject']}  verdict={p['verdict']}"
                          f"  -- no ink row under the box")
                    continue
                rr = {**best, "cell": cell, "sp": sp}
                d = ends_have_head(rr, hd)
                t = ends_have_head(rr, hh)
                # ⚠️ "hand=False" IS VACUOUS WHERE THE CELL HAS NO HAND
                # LABELS AT ALL -- the crop sample and the labelling batch
                # chose different cells, so most print verdicts land outside
                # the 19. Say which, or this column reads as hand truth
                # DISAGREEING when it was never asked.
                has_hand = "yes" if hh else "NO HAND TRUTH IN THIS CELL"
                print(f"  {p['id']} {p['subject']}  print={p['verdict']:<18s}"
                      f" ink {best['w_sp']}x{best['h_sp']} sp"
                      f"  head-at-end det={bool(d)}"
                      f"  hand={bool(t) if hh else 'n/a'} ({has_hand})")

    # dump for the write-up
    out = {
        "record": REC,
        "page": PAGE,
        "reach": {"ink_rows_page": sum(len(v) for v in ink.values()),
                  "hand_cells": len(hand_cells), "hand_boxes": n_hand,
                  "ink_rows_in_hand_cells": tot_ink,
                  "print_verdicts_page": len(print_rows)},
        "controls": {"ink_conv_median_err_spaces": cB,
                     "notehead_box_median_height_spaces": cB2,
                     "cells_frame_agree": len(sp_ok),
                     "cells_resolved": len(frame_rows),
                     "hand_notehead_on_detector_rate": rate,
                     "print_verdicts_class_matched": cls_ok,
                     "print_verdicts_refused": cls_bad},
        "partition": dict(buckets),
        "unexplained_n": len(un),
        "runs_n": len(runs) if un else 0,
    }
    with open("benchmarks/omr-ink-first-2026-09/out/ink-first-summary.json",
              "w") as f:
        json.dump(out, f, indent=1)
    print()
    print("wrote out/ink-first-summary.json")


if __name__ == "__main__":
    main()
