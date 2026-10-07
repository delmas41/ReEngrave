"""lane-brahms-1007-worse-and-slow, PART 1 (Sean: "it is possible that as we get better the worse results are actually an
improvement").  STAGED, GATHER+ADJUDICATE only, READ ONLY.  NEW = `brahms1-breitkopf-mvt1-whole-20261007-night`,
BASE = `...-20261006-night-combined`, both read through `record_io.load_record` by `brahms_1007_worse_extract.py`
(x/new.json, x/base.json: every standing verdict compact + the 10-06 per-glyph extraction).

  python3 brahms_1007_worse_cases.py <scratch dir with x/new.json x/base.json> [--seed 20261007]

Counts every kind of change in which NEW looks WORSE by our own counts (a decided answer gone, an owner moved or lost, a
position moved, a refusal added, ...), writes `out/brahms_1007_worse_counts.json`, and cuts ONE sheet of 12 seeded tiles,
2 per kind for the six biggest kinds, from the gather-frame page (`frame.render_page_matching_gather`, 600 dpi).  It does
NOT say which side is right.
"""
from __future__ import annotations
import collections, json, random, sys, textwrap
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_sheet as NF
import night_1007_sheet as S
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

DOC = "brahms1-breitkopf"
OUT = HERE.parents[1] / "out/print/brahms_1007_worse_cases.png"
COUNTS = HERE / "out/brahms_1007_worse_counts.json"
MAGENTA, LIME, RED, AZURE, ORANGE, GREY = (255, 0, 255), (0, 170, 0), (0, 0, 255), (255, 150, 0), (0, 140, 255), (110, 110, 110)
SC = 2
OWN_WORDS = {
    "ledger_note_first": "counting ledger lines outward from the note",
    "ledger_direction": "which side the ledger lines are on",
    "ledger_owner_density": "how many ledger lines each staff would need",
    "distance": "which staff is nearer",
    "staff_band": "the note lying inside a staff's band",
    "staff_band_no_box": "the note lying inside a staff's band (no box to check)",
    "range_veto": "the instrument's playable range",
    "far_no_rungs": "no ledger lines found, so no staff could be named",
    "group_owner": "the other detections of the same printed mark",
    "ladder": "the ladder of ledger lines reaching the staff",
    "hairpin_separates": "a hairpin lying between the staves",
    "tied": "two staves tied on the evidence",
    "hugs_noteheads": "the staff whose noteheads the arc hugs",
    "no_better_staff": "no other staff explaining the arc better",
}
FAR_WHY = {
    "no_rungs": "it found no ledger lines to count",
    "count_does_not_fit": "the number of ledger lines it counted did not fit any position",
    "no_line_at_the_note_box": "it found no staff or ledger line at the note's box",
    "line_at_the_box_not_a_ledger_for_this_head": "the line at the note's box was not a ledger line for this head",
    "line_not_beyond_the_staff_edge": "the line it found was not beyond the staff edge",
    "ledger_not_read": "the ledger reader could not read it",
}
EXTRA_KINDS = {}


def jl(s):
    return json.loads(s) if s not in (None, "") else None


def staff_of(subject):
    return "staff/" + "/".join(subject.split("/")[1:4])


class Ctx:
    def __init__(self, d):
        d = Path(d)
        self.N = json.loads((d / "x/new.json").read_text())
        self.B = json.loads((d / "x/base.json").read_text())
        self.an, self.ab = self.N["allv"], self.B["allv"]
        S._STATE["N"] = {DOC: self.N}
        self.gray = {}
        self.inst = {}
        for k, v in self.an.items():
            if k.startswith("instrument|") and v[0] == "decided":
                self.inst[k.split("|", 1)[1]] = (jl(v[1]) or {}).get("name")
        self.boxes = collections.defaultdict(dict)
        for s, c, b in self.N["boxes"]:
            self.boxes[R.page_of(s)][s] = (c, b)
        widths = sorted(g["box"][2] - g["box"][0] for g in self.N["glyphs"].values() if "box" in g and R.is_far(g) and "geo" in g)
        self.med_w = widths[len(widths) // 2]

    def gimg(self, page):
        if page not in self.gray:
            self.gray[page] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        return self.gray[page]

    def label(self, key):
        if not key:
            return "no staff"
        _, p, s, k = key.split("/")
        nm = self.inst.get(key) or "staff with no name read"
        return f"{nm} (system {int(s) + 1}, staff {int(k) + 1} from the top)"

    def has_twin(self, subject, box, staff_key):
        page = R.page_of(subject)
        pre = "glyph/" + "/".join(staff_key.split("/")[1:]) + "/"
        for s2, g in self.N["glyphs"].items():
            if s2.startswith(pre) and "box" in g and R.iou(box, g["box"]) > 0.3:
                return True
        return False


def count(ctx):
    N, B, an, ab = ctx.N, ctx.B, ctx.an, ctx.ab
    out = {}
    P = collections.defaultdict(list)
    far_n = lambda g: R.is_far(g)
    for s, g in N["glyphs"].items():
        bg = B["glyphs"].get(s)
        if not bg or "box" not in g:
            continue
        page = R.page_of(s)
        np_n, np_b = g.get("np"), bg.get("np")
        if np_n and np_b:
            if np_b["outcome"] == "decided" and np_n["outcome"] == "abstained":
                P["far_decided_then_abstains"].append(dict(subject=s, page=page, box=g["box"], base=int(round(float(np_b["value"]))),
                                                          why=np_n.get("reason"), lreason=(np_n.get("detail") or {}).get("ledger_reason")))
            elif np_b["outcome"] == "decided" and np_n["outcome"] == "decided" and int(round(float(np_b["value"]))) != int(round(float(np_n["value"]))):
                P["far_answer_changed"].append(dict(subject=s, page=page, box=g["box"], base=int(round(float(np_b["value"]))),
                                                    new=int(round(float(np_n["value"])))))
        if not np_n and not np_b and not (far_n(g) or far_n(bg)):
            pn, pb = R.geo_pos(g), R.geo_pos(bg)
            if pn is not None and pb is not None and pn != pb:
                P["in_staff_position_moved"].append(dict(subject=s, page=page, box=g["box"], base=pb, new=pn))
        on, ob = g.get("own"), bg.get("own")
        if on and ob and ob["outcome"] == "decided":
            if on["outcome"] == "abstained":
                P["owner_decided_then_abstains"].append(dict(subject=s, page=page, box=g["box"], base=ob["value"], why=on.get("reason"), base_why=ob.get("reason")))
            elif on["outcome"] == "decided" and on["value"] != ob["value"]:
                filing = staff_of(s)
                twin = ctx.has_twin(s, g["box"], on["value"]) if on["value"] != filing else None
                sub = "to_filing_staff" if on["value"] == filing else ("moved_off_filing_staff_twin_there" if twin else "moved_off_filing_staff_no_twin")
                P["owner_moved_to_another_staff"].append(dict(subject=s, page=page, box=g["box"], base=ob["value"], new=on["value"],
                                                              why=on.get("reason"), base_why=ob.get("reason"), sub=sub, filing=filing))
        nn, nb = g.get("nan"), bg.get("nan")
        if nn and nb and nn["outcome"] == "decided" and nb["outcome"] == "decided":
            if nb["reason"] == "notehead" and nn["reason"] != "notehead":
                P["note_newly_refused_as_not_a_note"].append(dict(subject=s, page=page, box=g["box"], why=nn["reason"]))
            elif nb["reason"] != "notehead" and nn["reason"] == "notehead":
                P["not_a_note_now_a_note"].append(dict(subject=s, page=page, box=g["box"], why=nb["reason"]))
    # non-glyph-extract quantities straight from the all-verdict maps
    for k, v in an.items():
        if k not in ab:
            continue
        w = ab[k]
        if v == w:
            continue
        q, subj = k.split("|", 1)
        box = (ctx.boxes[R.page_of(subj)].get(subj) or (None, None))[1] if subj.startswith("glyph/") else None
        row = dict(subject=subj, page=R.page_of(subj) if subj.startswith(("glyph/", "staff/")) else None, box=box, new=v, base=w)
        if q == "dot_role" and w[0] == "decided" and v[0] == "abstained":
            P["dot_no_longer_read_as_lengthening"].append(row)
        elif q == "arc_owner" and w[0] == "decided" and v[0] == "decided" and v[1] != w[1]:
            P["arc_owner_changed"].append(row)
        elif q == "tie_pair" and w[0] == "decided" and v[0] != "decided":
            P["tie_pair_lost"].append(row)
        elif q == "accidental_owner" and w[0] == "decided" and v[0] == "abstained":
            P["accidental_owner_lost"].append(row)
        elif q == "articulation_owner" and w[0] == "decided" and v[0] == "abstained":
            P["articulation_owner_lost"].append(row)
        elif q == "duration" and w[0] == "decided" and v[0] == "decided" and v[1] != w[1]:
            P["duration_changed"].append(row)
        elif q in ("meter", "clef", "key_signature", "measure_partition", "system_membership", "staff_group", "empty_bar_whole_rest") \
                and w[0] == "decided" and v[0] != "decided":
            P["bar_or_staff_fact_lost"].append(row)
    out["counts"] = {k: len(v) for k, v in sorted(P.items(), key=lambda t: -len(t[1]))}
    out["owner_moved_split"] = dict(collections.Counter(r["sub"] for r in P["owner_moved_to_another_staff"]))
    out["far_abstain_reasons"] = dict(collections.Counter((r["lreason"] or r["why"]).split(" (")[0] for r in P["far_decided_then_abstains"]))
    out["only_in_new"] = dict(collections.Counter(k.split("|")[0] for k in an if k not in ab))
    out["empty_bar_whole_rest_only_in_new"] = dict(collections.Counter(an[k][0] + ":" + str(an[k][2]) for k in an if k not in ab and k.startswith("empty_bar_whole_rest|")))
    nn = collections.Counter(), collections.Counter()
    for s, g in N["glyphs"].items():
        nn[0][(g.get("nan") or {}).get("reason")] += 1
        nn[1][(B["glyphs"][s].get("nan") or {}).get("reason")] += 1
    out["not_a_note_reasons_new"] = dict(nn[0]); out["not_a_note_reasons_base"] = dict(nn[1])
    return out, P


def y_of(lines, pos):
    sp = (lines[4] - lines[0]) / 4.0
    return lines[0] + pos * sp / 2.0, sp


def ledger_rulers(lines, positions):
    lo, hi = min(positions), max(positions)
    sp = (lines[4] - lines[0]) / 4.0
    ys = []
    if lo < 0:
        ys += [lines[0] + p * sp / 2.0 for p in range(-2, lo - 1, -2)]
    if hi > 8:
        ys += [lines[0] + p * sp / 2.0 for p in range(10, hi + 1, 2)]
    edge = lines[0] if lo < 0 else lines[4]
    return edge, ys


def nearest(lines, y):
    return min(lines, key=lambda v: abs(v - y))


def tile_lines(ctx, kind, r):
    """-> (box, staff_keys [(key, colourword)], lines [(y, colour, label, is_base)], captions [(text, colour)], staves_y)"""
    page, s, box = r["page"], r["subject"], r["box"]
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    gn, sn = S.grids(DOC, page, "new")
    parts = s.split("/")
    k3 = (int(parts[2]), int(parts[3]), int(parts[4]))
    fkey = staff_of(s)
    L, caps, staves = [], [], [fkey]
    if kind in ("far_answer_changed", "far_decided_then_abstains"):
        lines = gn.get(k3) or ctx.N["staff_lines"][fkey]
        pn, pb = r.get("new"), r["base"]
        poss = [p for p in (pn, pb) if p is not None]
        edge, rul = ledger_rulers(lines, poss)
        L.append((edge, MAGENTA, "staff edge", False))
        L += [(y, LIME, "ledger ruler", False) for y in rul]
        yb, sp = y_of(lines, pb)
        L.append((yb, AZURE, "BASE note line", True))
        caps.append(("BASE (azure): " + S.words_pos(pb) + ".", AZURE))
        if kind == "far_answer_changed":
            yn, _ = y_of(lines, pn)
            L.append((yn, RED, "NEW note line", False))
            caps.append(("NEW (red): " + S.words_pos(pn) + ".", RED))
        else:
            why = FAR_WHY.get(r["lreason"] or r["why"], str(r["lreason"] or r["why"]))
            caps.append((f"NEW: no answer; {why}.", RED))
        caps.append(("Magenta = the edge of the staff the note is filed on; green = ledger lines counted out from it.", GREY))
        sp_ = sp
    elif kind in ("owner_moved_to_another_staff", "owner_decided_then_abstains", "arc_owner_changed"):
        newk = r["new"] if kind == "owner_moved_to_another_staff" else (None if kind == "owner_decided_then_abstains" else jl(r["new"][1]))
        basek = r["base"] if kind != "arc_owner_changed" else jl(r["base"][1])
        if kind == "owner_moved_to_another_staff":
            newk, basek = r["new"], r["base"]
        sp_ = None
        for key, colour, word, isb in ((fkey, GREY, "FILED", False), (newk, RED, "NEW", False), (basek, AZURE, "BASE", True)):
            if not key:
                continue
            lines = S.seg_lines(sn, key, cx)
            if not lines:
                continue
            sp_ = sp_ or (lines[4] - lines[0]) / 4.0
            if key not in staves:
                staves.append(key)
            if key == fkey and (key == newk or key == basek):
                continue
            L.append((nearest(lines, cy), colour, f"{word} staff, line nearest the mark", isb))
        if kind == "owner_moved_to_another_staff":
            nw, bw = OWN_WORDS.get(r["why"], r["why"]), OWN_WORDS.get(r["base_why"], r["base_why"])
            caps.append((f"BASE (azure): belongs to {ctx.label(basek)}, by {bw}.", AZURE))
            caps.append((f"NEW (red): belongs to {ctx.label(newk)}, by {nw}.", RED))
            extra = {"to_filing_staff": "NEW is the staff it is filed on.",
                     "moved_off_filing_staff_twin_there": "NEW's staff holds a second box of the same mark.",
                     "moved_off_filing_staff_no_twin": "NEW's staff holds no second box of this mark."}[r["sub"]]
            caps.append((f"Grey = the staff it is filed on ({ctx.label(fkey)}). {extra}", GREY))
        elif kind == "owner_decided_then_abstains":
            caps.append((f"BASE (azure): belongs to {ctx.label(basek)}, by {OWN_WORDS.get(r['base_why'], r['base_why'])}.", AZURE))
            caps.append((f"NEW: no owner named; {OWN_WORDS.get(r['why'], r['why'])}.", RED))
            caps.append((f"Grey = the staff it is filed on ({ctx.label(fkey)}).", GREY))
        else:
            caps.append((f"BASE (azure): the arc belongs to {ctx.label(basek)}, by {OWN_WORDS.get(r['base'][2], r['base'][2])}.", AZURE))
            caps.append((f"NEW (red): the arc belongs to {ctx.label(newk)}, by {OWN_WORDS.get(r['new'][2], r['new'][2])}.", RED))
            caps.append((f"Grey = the staff it is filed on ({ctx.label(fkey)}).", GREY))
        sp_ = sp_ or 16.0
    elif kind == "in_staff_position_moved":
        gb, sb = S.grids(DOC, page, "base")
        ln, lb = gn.get(k3), gb.get(k3)
        sp_ = (ln[4] - ln[0]) / 4.0
        L += [(y, RED, f"NEW line {i + 1}", False) for i, y in enumerate(ln)]
        L += [(y, AZURE, f"BASE line {i + 1}", True) for i, y in enumerate(lb)]
        caps.append(("BASE (azure, its five staff lines for this bar): the note sits " + S.words_pos(r["base"]) + ".", AZURE))
        caps.append(("NEW (red, its five staff lines for this bar): the note sits " + S.words_pos(r["new"]) + ".", RED))
    elif kind == "dot_no_longer_read_as_lengthening":
        lines = gn.get(k3) or ctx.N["staff_lines"][fkey]
        sp_ = (lines[4] - lines[0]) / 4.0
        L.append((nearest(lines, cy), MAGENTA, "staff line nearest the dot", False))
        # the head the dot trails: nearest notehead box to its left on this page
        best = None
        for s2, (c2, b2) in ctx.boxes[page].items():
            if c2 and c2.startswith("notehead") and b2[2] <= box[0] + 3 and box[0] - b2[2] < 3.0 * sp_ and abs((b2[1] + b2[3]) / 2 - cy) < 1.0 * sp_ + 6:
                d = box[0] - b2[2]
                if best is None or d < best[0]:
                    best = (d, s2, b2)
        r["head"] = best
        db = lambda e: (jl(e[1]) or {}).get("beats") if e else None
        hb = (ctx.ab.get("duration|" + best[1]), ctx.an.get("duration|" + best[1])) if best else (None, None)
        caps.append((f"BASE (azure): the dot lengthens the note before it by half" + (f"; that note counts {db(hb[0])} beats." if hb[0] else "."), AZURE))
        caps.append((f"NEW (red): cannot tell whether the dot lengthens the note or is something else" + (f"; that note counts {db(hb[1])} beats." if hb[1] else "."), RED))
        caps.append(("Orange = the dot; green = the note head to its left; magenta = the staff line nearest the dot.", GREY))
    else:
        raise KeyError(kind)
    r["sp"] = sp_
    return cx, cy, L, caps, staves, sn


def draw(ctx, kind, r, no):
    page = r["page"]
    gray = ctx.gimg(page)
    cx, cy, L, caps, staves, sn = tile_lines(ctx, kind, r)
    box, sp = r["box"], r["sp"]
    ys = [l[0] for l in L] + [box[1], box[3]]
    st_rows = []
    for key in staves:
        lines = S.seg_lines(sn, key, cx)
        if lines:
            ys += [lines[0], lines[-1]]
            st_rows.append((key, (lines[0] + lines[-1]) / 2.0))
    # a staff far from the note still needs its label visible: include staves' own lines in the extent, never beyond 14 sp
    ya, yb = max(0, int(min(ys) - 1.2 * sp)), int(max(ys) + 1.2 * sp)
    xa, xb = max(0, int(cx - 6.0 * sp)), int(cx + 6.0 * sp)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    left = (int(box[0] - 1.0 * sp), int(box[0] - 0.1 * sp))
    side = (int(box[2] + 0.1 * sp), int(box[2] + 1.0 * sp))
    checks = []
    for (y, colour, label, isb) in L:
        yy = int(round((y - ya) * SC)) + SC // 2
        cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 1)
        peaks = [NF.remeasure(gray, y, *cols, thr) for cols in (left, side)]
        peaks = [p for p in peaks if p[0] is not None]
        off = min((abs(p[1]) for p in peaks), default=None)
        checks.append((no, label, round(float(y), 1), None if off is None else round(off, 1), isb))
    if kind == "dot_no_longer_read_as_lengthening" and r.get("head"):
        hb = r["head"][2]
        cv2.rectangle(crop, (int((hb[0] - xa) * SC), int((hb[1] - ya) * SC)), (int((hb[2] - xa) * SC), int((hb[3] - ya) * SC)), LIME, 1)
    cv2.rectangle(crop, (int((box[0] - xa) * SC), int((box[1] - ya) * SC)), (int((box[2] - xa) * SC), int((box[3] - ya) * SC)), ORANGE, 1)
    # left margin: the instrument of every staff in view, in words
    M = 250
    H, W = crop.shape[:2]
    margin = np.full((H, M, 3), 255, np.uint8)
    for key, yc in st_rows:
        _, p, s_, k = key.split("/")
        nm = ctx.inst.get(key) or "no name read"
        yy = int((yc - ya) * SC)
        cv2.putText(margin, nm[:30], (4, yy - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(margin, f"system {int(s_) + 1}, staff {int(k) + 1}", (4, yy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1, cv2.LINE_AA)
    return np.hstack([margin, crop]), caps, checks


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


TITLES = {
    "far_answer_changed": "FAR HEAD, answer changed (both runs decided, different position)",
    "owner_moved_to_another_staff": "OWNER moved to a different staff (both runs named one)",
    "far_decided_then_abstains": "FAR HEAD, decided in BASE, NEW gives no answer",
    "arc_owner_changed": "SLUR/TIE: owner staff changed (both runs named one)",
    "in_staff_position_moved": "IN-STAFF HEAD: its position moved (staff lines of the bar moved)",
    "dot_no_longer_read_as_lengthening": "DOT: BASE read it as lengthening the note, NEW cannot tell",
}


def main(d, seed):
    ctx = Ctx(d)
    cnt, P = count(ctx)
    COUNTS.parent.mkdir(parents=True, exist_ok=True)
    COUNTS.write_text(json.dumps(cnt, indent=1))
    print(json.dumps(cnt, indent=1))
    order = [k for k in cnt["counts"] if k in TITLES][:6]
    rng = random.Random(seed)
    picks = []
    for kind in order:
        pool = [r for r in P[kind] if r["page"] is not None and r["page"] >= 2]
        if kind in ("far_answer_changed", "far_decided_then_abstains"):
            pool = [r for r in pool if r["box"] and (r["box"][2] - r["box"][0]) >= 0.6 * ctx.med_w]
        if kind == "owner_moved_to_another_staff":     # one of each sub-kind first, where it exists
            subs = collections.defaultdict(list)
            for r in pool:
                subs[r["sub"]].append(r)
            chosen = []
            for sk in sorted(subs, key=lambda k: -len(subs[k])):
                if len(chosen) < 2:
                    chosen.append(rng.choice(subs[sk]))
            while len(chosen) < 2 and pool:
                chosen.append(rng.choice(pool))
            picks += [(kind, r) for r in chosen]
        else:
            picks += [(kind, r) for r in rng.sample(pool, min(2, len(pool)))]
    print("tiles:", len(picks), "pools:", {k: len(P[k]) for k in order})
    tiles, allchecks, info = [], [], []
    for i, (kind, r) in enumerate(picks, 1):
        try:
            img, caps, ch = draw(ctx, kind, r, i)
        except Exception as e:
            print("tile failed", kind, r["subject"], repr(e)); raise
        allchecks += ch
        tiles.append((kind, r, img, caps, i))
        info.append(dict(n=i, kind=kind, subject=r["subject"], page=r["page"], caps=[c[0] for c in caps]))
    W = max(t[2].shape[1] for t in tiles)
    cells = []
    for kind, r, img, caps, i in tiles:
        title = f"{i}. {TITLES[kind]}  [{cnt['counts'][kind]} on Brahms]"
        head_lines = wrap(title, W, 0.5)
        cap_lines = []
        for text, col in caps:
            for j, ln in enumerate(wrap(text, W)):
                cap_lines.append((ln, col))
        hh = 8 + 20 * len(head_lines)
        ch_ = 8 + 18 * len(cap_lines) + 22
        H = img.shape[0]
        c = np.full((hh + H + ch_, W, 3), 255, np.uint8)
        for j, ln in enumerate(head_lines):
            cv2.putText(c, ln, (4, 18 + 20 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        c[hh:hh + H, :img.shape[1]] = img
        for j, (ln, col) in enumerate(cap_lines):
            cv2.putText(c, ln, (6, hh + H + 18 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.46, tuple(int(v * 0.75) for v in col), 1, cv2.LINE_AA)
        cv2.putText(c, f"brahms pdf page {r['page']}  {r['subject'].replace('glyph/', '')}", (6, hh + H + ch_ - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (110, 110, 110), 1, cv2.LINE_AA)
        cv2.rectangle(c, (0, 0), (W - 1, c.shape[0] - 1), (190, 190, 190), 1)
        cells.append(c)
    cols = 3
    rows = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, W + 8, 3), 255, np.uint8))
        rows.append(np.hstack(grp))
    w = max(r_.shape[1] for r_ in rows)
    img = np.vstack([np.pad(r_, ((6, 6), (0, w - r_.shape[1]), (0, 0)), constant_values=255) for r_ in rows])
    legend = np.full((150, img.shape[1], 3), 255, np.uint8)
    for j, (txt, col) in enumerate((
            ("Brahms 1 mvt 1 (Breitkopf), 12 changes where NEW (10-07) looks worse than BASE (10-06) by our own counts; NOT judged -- Sean decides which is right.", (0, 0, 0)),
            ("ORANGE box = the mark the question is about.  Every coloured line is 1 px, drawn at the page's own coordinates, and was re-measured against the ink rows (below).", ORANGE),
            ("AZURE = what BASE says.   RED = what NEW says.   MAGENTA = the staff edge / staff line the answer is counted from.   GREEN = ledger lines counted out from the edge, or the head a dot trails.", AZURE),
            ("GREY = the staff the mark is filed on (where the pipeline first put it).  Staff names at the left of each tile are the instrument the record names for that staff.", GREY))):
        cv2.putText(legend, txt, (8, 24 + 26 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.58, col if col != AZURE else (0, 0, 0), 1, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), np.vstack([legend, img]))
    OUT.with_suffix(".json").write_text(json.dumps(info, indent=1, default=str))
    new_checks = [c for c in allchecks]
    hidden = [c for c in new_checks if c[3] is None]
    bad = [c for c in new_checks if c[3] is not None and c[3] > 2.0]
    # ledger rulers and note lines in a SPACE are not expected on ink; staff/edge/five-line checks are
    core = [c for c in new_checks if ("ruler" not in c[1] and "note line" not in c[1])]
    cbad = [c for c in core if c[3] is not None and c[3] > 2.0]
    chid = [c for c in core if c[3] is None]
    print(f"drawn lines {len(new_checks)}: within 2 px of an ink row {len(new_checks) - len(bad) - len(hidden)}, off by >2 px {len(bad)}, no ink beside the head {len(hidden)}")
    print(f"  staff/edge/five-line/nearest-line subset {len(core)}: within 2 px {len(core) - len(cbad) - len(chid)}, >2 px {len(cbad)} {cbad}, no ink {len(chid)} {chid}")
    print("  all >2px:", bad)
    print("  all no-ink:", [(c[0], c[1]) for c in hidden])
    for t in info:
        print(t["n"], t["kind"], t["subject"], "|", " || ".join(t["caps"]))
    print("wrote", OUT)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
