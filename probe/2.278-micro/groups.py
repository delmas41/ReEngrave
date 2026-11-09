"""2.278 MICRO TEST prototype: the beam GROUP read once on the page (STAGED GATHER-side, offline, reads only what the record already holds).

    docs/plan-2026-11-08-beam-flag-reading.md section 3 steps 2-5, section 4.  Rules pre-registered in probe/2.278-micro/RULES.md.

INPUT per page (from the saved sample record, OMR_PAGE_BEAMS + OMR_PAGE_CLAIM_NAMES on, through adjudicate; `prep.py`):
  strokes   the page stroke map (Q.PAGE_STROKE rows): kind, box, centre-line ends, thickness profile
  claimed   stroke ordinal -> owner of every stroke an EARLIER claim names (barline, bracket, clef/key/meter, word/dynamic, hairpin, arc)
  tips      one row per stem END of each stem stroke a Q.STEM row lands on (the stems the page has; their ordinals)
Nothing is read from the raster; no landed cut-off is invented: join distances and thickness cuts are the landed beam_strokes constants.

THE RULE (no per-stroke thickness test, no vote):
  step 2  a stroke (horizontal / curve, NOT claimed by an earlier claim) is a BEAM iff >= 2 distinct stems END on it (join: the stem end lies within
          FACE_JOIN_MAX_SPACES of the stroke's band at the stem's x, the stroke on the stem's outer side) and no barline stands between the stems it joins.
          Certain or absent: no 'possible'.
  step 3  it OWNS every stem that joins it (the same join), including a stem with only broken ink to the face.
  step 4  levels of a stem = the certified strokes stacked at its tip (STACK constants), a fused slab counts 2 by the LOCAL thickness
          (FUSED_LOCAL_MIN_SPACES .. FUSED_MAX_THICKNESS_SPACES); a ONE-stem stroke at the stem within STACK_GAP of the last level is a partial beam
          that cannot be shown: the stem's levels are UNREAD (reported, not decided).
  step 5  a stem no beam owns is 'plain' only if its beam-side tip window holds no ink that is not claimed (claim-aware window).

CONTROLS (can fail): shift_px moves every certified stroke before joining (the 12 px control); two_stem=False admits any single-stem stroke.
"""
import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import beam_strokes as BS

JOIN = BS.FACE_JOIN_MAX_SPACES          # 1.0 sp
XSLACK = BS.STEM_MATCH_X_SLACK_SPACES   # 0.35 sp
STACK_FIRST = BS.STACK_FIRST_SPACES     # 1.0
STACK_GAP = BS.STACK_GAP_SPACES         # 0.75
HOOK_MAX = BS.HOOK_MAX_SPACES           # 1.6
BEAM_KINDS = ("horizontal", "curve")


def view(o, k):
    bx0, by0, bx1, by1 = k["bbox"]
    return BS.StrokeView(ordinal=o, kind=k["kind"], box=(bx0, by0, bx1 - bx0, by1 - by0), length=k["length"] or 0.0, thickness=k["thick"] or 0.0,
                         sagitta=k["sagitta"], angle=k["angle"] or 0.0, touches=tuple(tuple(t) for t in (k["touches"] or ())), space_px=k["sp"] or 32.0,
                         profile=tuple(k["profile"] or ()), ends=tuple(k["ends"] or ()))


def band_at(v, x, shift=0.0):
    """(lo, hi, centre) of the stroke's band at page-x `x`, or None outside its run (+/- XSLACK)."""
    sp = v.space_px
    if len(v.ends) >= 4:
        x0, y0, x1, y1 = v.ends[:4]
        if not (min(x0, x1) - XSLACK * sp <= x <= max(x0, x1) + XSLACK * sp):
            return None
        yc = y0 if x1 == x0 else y0 + (y1 - y0) * (min(max(x, min(x0, x1)), max(x0, x1)) - x0) / (x1 - x0)
    else:
        if not (v.box[0] - XSLACK * sp <= x <= v.box[0] + v.box[2] + XSLACK * sp):
            return None
        yc = v.box[1] + v.box[3] / 2.0
    yc += shift
    t = BS.local_thickness(v, x) * sp
    return yc - t / 2.0, yc + t / 2.0, yc


def stem_geom(P, o):
    k = P["strokes"][o]
    x0, y0, x1, y1 = k["bbox"]
    return dict(x=(x0 + x1) / 2.0, top=y0, bot=y1, sp=k["sp"] or 32.0, staff=k["staff"])


def join_gap(v, sg, end, shift=0.0):
    """Staff spaces between the stem's `end` ('top'/'bottom') and the stroke's band at the stem's x; None if the stroke is not on the stem's outer side
    at that end or the stem is outside the stroke's run."""
    b = band_at(v, sg["x"], shift)
    if b is None:
        return None
    lo, hi, yc = b
    ye = sg["top"] if end == "top" else sg["bot"]
    ymid = (sg["top"] + sg["bot"]) / 2.0
    if end == "top" and not yc < ymid:
        return None
    if end == "bottom" and not yc > ymid:
        return None
    d = 0.0 if lo <= ye <= hi else min(abs(ye - lo), abs(ye - hi))
    return d / sg["sp"]


def barlines(P):
    return [k["bbox"] for k in P["strokes"].values() if k["kind"] == "barline"]


def read_page(P, shift_px=0.0, two_stem=True, shift_only=None, shift_x=0.0, use_claims=True):
    strokes, claimed = P["strokes"], (P["claimed"] if use_claims else {})
    stems = sorted({t["stem"] for t in P["tips"]})
    SG = {o: stem_geom(P, o) for o in stems}
    # position index of stems by x for speed
    order = sorted(stems, key=lambda o: SG[o]["x"])
    xs = [SG[o]["x"] for o in order]
    import bisect
    bars = barlines(P)
    cand = []
    for o, k in strokes.items():
        if k["kind"] not in BEAM_KINDS or o in claimed:
            continue
        cand.append(o)
    V = {o: view(o, strokes[o]) for o in cand}
    if shift_px or shift_x:       # CONTROL: move the stroke itself (centre line, box) before anything reads it
        import dataclasses
        for o in cand:
            if shift_only is not None and o not in shift_only:
                continue
            v = V[o]
            e = v.ends
            if len(e) >= 4:
                e = (e[0] + shift_x, e[1] + shift_px, e[2] + shift_x, e[3] + shift_px)
            V[o] = dataclasses.replace(v, ends=tuple(e), box=(v.box[0] + shift_x, v.box[1] + shift_px, v.box[2], v.box[3]))
    joins = {}          # stroke -> [(stem, end, gap)]
    for o in cand:
        v = V[o]
        sp = v.space_px
        lo = bisect.bisect_left(xs, v.box[0] - XSLACK * sp - 1)
        hi = bisect.bisect_right(xs, v.box[0] + v.box[2] + XSLACK * sp + 1)
        sh = 0.0
        js = []
        for s in order[lo:hi]:
            sg = SG[s]
            for end in ("top", "bottom"):
                g = join_gap(v, sg, end, sh)
                if g is not None and g <= JOIN:
                    js.append((s, end, g))
        if js:
            joins[o] = js
    # bars between joined stems: split into runs, certify run with >= 2 distinct stems
    certified = {}      # stroke -> list of runs (each a list of (stem,end,gap))
    uncertified = {}    # stroke -> joins (1 stem, or cut by barline)
    cut_by_bar = 0
    for o, js in joins.items():
        v = V[o]
        js = sorted(js, key=lambda t: SG[t[0]]["x"])
        runs, cur = [], []
        for j in js:
            if cur:
                xa, xb = SG[cur[-1][0]]["x"], SG[j[0]]["x"]
                sep = any(xa < (b[0] + b[2]) / 2.0 < xb and b[1] <= v.box[1] + v.box[3] and b[3] >= v.box[1] for b in bars)
                if sep:
                    runs.append(cur); cur = []; cut_by_bar += 1
            cur.append(j)
        if cur:
            runs.append(cur)
        okruns = [r for r in runs if len({t[0] for t in r}) >= (2 if two_stem else 1)]
        if okruns:
            certified[o] = okruns
        else:
            uncertified[o] = js
    # ownership: stem -> {strokes joined}, per end
    own = collections.defaultdict(lambda: collections.defaultdict(list))   # stem -> end -> [(gapdist, stroke)]
    for o, runs in certified.items():
        for r in runs:
            for (s, end, g) in r:
                own[s][end].append((g, o))
    weak = collections.defaultdict(lambda: collections.defaultdict(list))
    for o, js in uncertified.items():
        for (s, end, g) in js:
            weak[s][end].append((g, o))
    rows = {}
    for s in stems:
        r = dict(owned=False, ends={}, levels=None, unread=None)
        for end, lst in own.get(s, {}).items():
            sg = SG[s]
            ye = sg["top"] if end == "top" else sg["bot"]
            # stack: outer-most first = largest distance outward
            def outer_edge(o):
                b = band_at(V[o], sg["x"])
                return (b[0] if end == "top" else b[1], b)
            items = []
            for g, o in lst:
                oe, b = outer_edge(o)
                inner = b[1] if end == "top" else b[0]
                items.append((o, oe, inner, b))
            # sort from the tip outward: the first level's outer edge lies within STACK_FIRST of the tip
            # order by distance of outer edge from the tip going outward-most first: for 'top', smaller y = further out
            items.sort(key=lambda t: t[1] if end == "top" else -t[1])
            levels, unread, last_inner = 0, None, None
            sp = sg["sp"]
            for (o, oe, inner, b) in items:
                if last_inner is None:
                    if abs(oe - ye) / sp > STACK_FIRST + 0.5 and abs(inner - ye) / sp > STACK_FIRST + 0.5:
                        continue
                else:
                    gap = (oe - last_inner) / sp if end == "top" else (last_inner - oe) / sp
                    if gap > STACK_GAP or gap < -0.5:
                        continue
                loc = BS.local_thickness(V[o], sg["x"])
                if loc >= BS.FUSED_LOCAL_MIN_SPACES:
                    if loc <= BS.FUSED_MAX_THICKNESS_SPACES:
                        levels += 2
                    else:
                        unread = "fused_slab_too_thick"; levels += 1
                else:
                    levels += 1
                last_inner = inner
            # a ONE-stem short stroke at this stem within STACK_GAP of the last level = a partial beam that cannot be shown
            if levels and last_inner is not None:
                for g, o in weak.get(s, {}).get(end, []):
                    v = V[o]
                    b = band_at(v, sg["x"])
                    if b is None or v.length > HOOK_MAX:
                        continue
                    oe = b[0] if end == "top" else b[1]
                    gap = (oe - last_inner) / sp if end == "top" else (last_inner - oe) / sp
                    if -0.5 <= gap <= STACK_GAP:
                        unread = "partial_beam_stroke_not_two_stems"
            r["ends"][end] = dict(levels=levels, strokes=[o for o, *_ in items], unread=unread)
            if levels:
                r["owned"] = True
        rows[s] = r
    return dict(certified=certified, uncertified=uncertified, rows=rows, SG=SG, V=V, cut_by_bar=cut_by_bar, cand=len(cand), claimed_skipped=sum(1 for o, k in strokes.items() if k["kind"] in BEAM_KINDS and o in claimed))
