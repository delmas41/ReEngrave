"""Bar 2: the beam-family narrowed heads of the sample pages -- would the group reading give ONE value? (and check it against Sean's judged answers)

usage: python3 probe/2.278-micro/heads.py out/2.278-micro/brahms.pkl [out.json] [--pages 0,5]

Decision per narrowed beam-family head (plan section 3 step 6):
  no stem row                      -> undecided, counted as a STEM problem (2.204/M6), never a beam problem
  stem beamed at its FAR end       -> beam_levels = levels read (undecided if the levels are UNREAD)
  stem beamed only at the head end -> undecided (conflict)
  stem owned by no beam            -> beam_levels 0 only if the claim-aware tip window is clean; else undecided (flag/other ink)
  the reading must equal exactly one of the verdict's OWN candidates (never a value outside them); else undecided with the reason.
"""
import sys, pickle, json, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import groups as G

BEAM_FAMILY = ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined")


def head_geom(h):
    b = h.get("bbox")
    return b


def far_end(h, sg):
    b = h["bbox"]
    cy = (b[1] + b[3]) / 2.0
    mid = (sg["top"] + sg["bot"]) / 2.0
    return "top" if cy > mid else "bottom"


def tip_clean(P, s, end, h, sg):
    """claim-aware tip window: no ink that is not claimed, not the stem, not the head, within 1.0 sp across and from 0.5 sp past the tip to 3.3 sp in."""
    sp = sg["sp"]
    tip = sg["top"] if end == "top" else sg["bot"]
    y0, y1 = (tip - 0.5 * sp, tip + 3.3 * sp) if end == "top" else (tip - 3.3 * sp, tip + 0.5 * sp)
    x0, x1 = sg["x"] - 1.0 * sp, sg["x"] + 1.0 * sp
    hb = h["bbox"]
    hx0, hy0, hx1, hy1 = hb[0] - 0.5 * sp, hb[1] - 0.5 * sp, hb[2] + 0.5 * sp, hb[3] + 0.5 * sp
    ink = []
    for o, k in P["strokes"].items():
        if o == s or k["kind"] in ("barline", "vertical") or o in P["claimed"]:
            continue
        b = k["bbox"]
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if hx0 <= cx <= hx1 and hy0 <= cy <= hy1:
            continue
        ink.append(o)
    return not ink, ink


def tip_clean_landed(P, res, s, end, claim_aware):
    """POST-HOC variant B (changed AFTER the first run, disclosed in FINDINGS): the LANDED `beam_strokes.tip_clean` (2.202d/2.146: no non-blob stroke touching or
    within 0.5 sp of the stem in the tip window), once as the record's M4a row has it (claim_aware False: the stored `PAGE_BEAM_TIP.tip_clean`) and once with
    the strokes an earlier claim owns removed (claim_aware True)."""
    side = "up" if end == "top" else "down"
    sv = res["V_all"][s]
    near = [v for o, v in res["V_all"].items() if o != s and not (claim_aware and o in P["claimed"])
            and v.box[0] < sv.box[0] + sv.box[2] + 2.5 * sv.space_px and v.box[0] + v.box[2] > sv.box[0] - 2.5 * sv.space_px
            and v.box[1] < sv.box[1] + sv.box[3] + 2.5 * sv.space_px and v.box[1] + v.box[3] > sv.box[1] - 2.5 * sv.space_px]
    import tools.omr.staged.beam_strokes as BS
    return BS.tip_clean(near, sv, side)


def decide(P, res, h, plain=True, window="A"):
    """-> (status, levels, why, detail)"""
    ref = h.get("stem_ref")
    if not ref or ref[0] != h["page"]:
        return "undecided", None, "no_stem_row", {}
    s = ref[1]
    if s not in res["rows"]:
        return "undecided", None, "no_stem_row", {}
    sg = res["SG"][s]
    row = res["rows"][s]
    fe = far_end(h, sg)
    ne = "top" if fe == "bottom" else "bottom"
    e = row["ends"].get(fe)
    if e and e["levels"]:
        if e["unread"]:
            return "undecided", None, "levels_unread:" + e["unread"], dict(stem=s, strokes=e["strokes"])
        return "beam", e["levels"], None, dict(stem=s, strokes=e["strokes"], end=fe)
    if row["ends"].get(ne) and row["ends"][ne]["levels"]:
        return "undecided", None, "beam_only_at_head_end", dict(stem=s)
    if plain:
        if window == "A":
            ok, ink = tip_clean(P, s, fe, h, sg)
        else:
            ok, ink = tip_clean_landed(P, res, s, fe, window == "B2"), []
        if ok:
            return "plain", 0, None, dict(stem=s, end=fe)
        return "undecided", None, "tip_not_clean", dict(stem=s, end=fe, ink=ink[:6])
    return "undecided", None, "owned_by_no_beam", dict(stem=s)


def match_candidate(h, L):
    c = [x for x in h.get("cands", []) if x[1] == L]
    if len(c) == 1:
        return c[0], None
    if not c:
        return None, "outside_candidates"
    return None, "dots_open"


def run(D, pages, plain=True, window="A", **kw):
    out = []
    reads = {p: G.read_page(D["pages"][p], **kw) for p in pages}
    for sub, h in D["heads"].items():
        if h["page"] not in pages or h.get("outcome") != "narrowed" or h.get("reason") not in BEAM_FAMILY:
            continue
        if h.get("not_a_notehead") is not False or not h.get("bbox"):
            continue
        st, L, why, det = decide(D["pages"][h["page"]], reads[h["page"]], h, plain=plain, window=window)
        cand = None
        if st != "undecided":
            cand, why2 = match_candidate(h, L)
            if cand is None:
                st, why = "undecided", why2
        out.append(dict(sub=sub, page=h["page"], reason=h["reason"], status=st, levels=L, why=why, cand=cand, bbox=h["bbox"], det=det, cands=h.get("cands")))
    return out


if __name__ == "__main__":
    D = pickle.load(open(sys.argv[1], "rb"))
    pages = sorted(D["pages"]) if "--pages" not in sys.argv else [int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")]
    win = sys.argv[sys.argv.index("--window") + 1] if "--window" in sys.argv else "A"
    print("tip window variant", win)
    out = run(D, pages, window=win)
    n = len(out)
    c = collections.Counter(o["status"] for o in out)
    print("narrowed beam-family heads (notehead, not open):", n, dict(c))
    print("decided share:", round((c["beam"] + c["plain"]) / max(1, n), 3), "| beam-owned", c["beam"], "plain", c["plain"])
    print("undecided by why:", collections.Counter(o["why"] for o in out if o["status"] == "undecided").most_common(10))
    byp = collections.defaultdict(collections.Counter)
    for o in out:
        byp[o["page"]][o["status"]] += 1
    print({p: dict(v) for p, v in sorted(byp.items())})
    byr = collections.defaultdict(collections.Counter)
    for o in out:
        byr[o["reason"]][o["status"]] += 1
    print({p: dict(v) for p, v in byr.items()})
    if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        json.dump(out, open(sys.argv[2], "w"), default=str)
