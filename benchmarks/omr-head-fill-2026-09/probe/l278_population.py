"""ROADMAP 2.78 Phase 1 -- ONE STEM, ONE VALUE: how many stems carry heads whose
written values disagree TODAY.

PATH: STAGED, GATHER + ADJUDICATE only (CLAUDE.md §6b). Reads a record ONLY
through `readout.load_run` (-> `record_io.load_record`). Reads no raster, no
EVALUATE/INFER/EXPORT verdict, never the reference encoding.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_population.py RECORD.json \
        [--pages 0,1,2,3] [--count-page 3] [--json out.json] [--label NAME]

THE JOIN. No verdict in the record says "these heads share a stem". The only
statements of it are (1) `Q.NOTEHEAD_STEM_CROSS_INK.detail.stem` (GATHER, one
row per head that overlaps a stem, the FIRST stem in row order, and none where
the head leaves no area on one side) and (2) `Q.STACKED_HEAD_FIT.detail.stem`
(only heads on the SAME side of a stem). ADJUDICATE re-derives the join as a
bare box overlap, with no tolerance, privately, in three places
(`rhythm._stems_on`, `notehead_precision._stem_rows_on`,
`gather._stacked_boxes_overlap`). This probe uses the same test
(`rhythm._boxes_overlap` on `Q.GLYPH_BOX` vs `Q.STEM` rows of the head's own
cell) and cross-checks it against (1).

WHAT COUNTS AS A HEAD. A notehead-family box (`g.family == "note"`) whose
ADJUDICATE status is kept / narrowed / abstained. A box ADJUDICATE REFUSED (not a
notehead: a slash, a duplicate, ...) or GAVE AWAY to another staff is not a head
and is not counted -- that is the population the rule would otherwise have to
refuse.

A HEAD'S WRITTEN VALUE is the standing ADJUDICATE `duration` verdict: DECIDED
-> one `(written, dots, fill)`; NARROWED -> its candidates; ABSTAINED -> unread.
`fill` is `hollow` where the head's own base value is >= 2 beats, derived as
written * 2**beam_levels / (2 - 2**-dots).

THE PARTITION, mutually exclusive, in this order, over every stem carrying
>= 2 kept heads (a head on two stems is counted on each; identical head-sets
from two duplicate stem rows are counted once):

  agree   every head DECIDED, one value                          (the control)
  (a)     >= 2 DECIDED heads disagree on FILL (hollow vs filled)
  (b)     decided heads agree on fill, disagree on DOTS
  (c)     decided heads (>= 1) all agree; another head is NARROWED or ABSTAINED
            c1 narrowed, and the decided value is among its candidates
            c2 narrowed, and its candidates EXCLUDE the decided value
            c3 abstained (unread)           [and mixes, named]
  (d)     anything else
            d1a decided heads, same fill and dots, a WHOLE-class box and a
                HALF-class box (head base differs)
            d1b decided heads differ only in beam/flag level
            d2 no head decided: all narrowed IDENTICALLY (agreement in
               ignorance) / narrowed with a common candidate / narrowed with
               disjoint candidates / all abstained / narrowed and abstained

and, as an overlapping count, "stems with >= 1 head whose value is unread".
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys

KEPT = ("kept", "narrowed", "abstained")


# ───────────────────────────── the join ─────────────────────────────

def _overlap(a, b):
    """`rhythm._boxes_overlap`, restated: (x, y, w, h), no tolerance."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax <= bx + bw and ax + aw >= bx and ay <= by + bh and ay + ah >= by


def stem_index(run):
    """cell key -> [(row id, (x, y, w, h))] from the `stem` observations."""
    out = collections.defaultdict(list)
    for o in run.observations:
        if o["quantity"] != "stem":
            continue
        v = o.get("value")
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            out[o["subject"]].append((o["id"], tuple(float(x) for x in v[:4])))
    return out


def cell_space(run, cell_key):
    rows = run.obs_at(cell_key, "cell_staff_space")
    try:
        return float(rows[-1]["value"]) if rows else None
    except (TypeError, ValueError):
        return None


# ───────────────────────────── readings ─────────────────────────────

def triple(value):
    """(written, dots, fill, base, levels) from a duration value dict. `base`
    is the head's own beats before any beam/flag/dot (4 whole, 2 half, 1 black);
    `fill` is derived from it."""
    written = float(value["written"])
    dots = int(value.get("dots") or 0)
    levels = int(value.get("beam_levels") or 0)
    base = written * (2 ** levels) / (2.0 - 2.0 ** (-dots))
    return (round(written, 4), dots, "hollow" if base >= 1.99 else "filled",
            round(base, 3), levels)


def reading(run, key):
    v = run.standing(key, "duration", "ADJUDICATE")
    if v is None:
        return {"outcome": "none", "reason": None, "vals": []}
    oc = v["outcome"]
    if oc == "decided" and isinstance(v.get("value"), dict) \
            and "written" in v["value"]:
        vals = [triple(v["value"])]
    elif oc == "narrowed":
        vals = [triple(c["value"]) for c in (v.get("candidates") or [])
                if isinstance(c.get("value"), dict) and "written" in c["value"]]
    else:
        vals = []
        if oc == "decided":
            oc = "none"
    return {"outcome": oc, "reason": v.get("reason"), "vals": vals}


def fill_word(t):
    return t[2]


# ───────────────────────────── classification ─────────────────────────────

def classify(heads):
    """(primary, sub) for one stem's kept heads. See the module docstring."""
    dec = [h for h in heads if h["read"]["outcome"] == "decided"]
    nar = [h for h in heads if h["read"]["outcome"] == "narrowed"]
    unread = [h for h in heads
              if h["read"]["outcome"] not in ("decided", "narrowed")]
    dec_vals = {h["read"]["vals"][0] for h in dec}
    if len(dec_vals) >= 2:
        fills = {t[2] for t in dec_vals}
        dots = {t[1] for t in dec_vals}
        if len(fills) >= 2:
            return "a_fill", ("fill+dots" if len(dots) >= 2 else "fill")
        if len(dots) >= 2:
            return "b_dots", "dots"
        if len({t[3] for t in dec_vals}) >= 2:
            # both hollow (or both filled), same dots, different head base:
            # a WHOLE-class box and a HALF-class box on one stem
            return "d_other", "d1a_whole_vs_half_class"
        return "d_other", "d1b_beam_or_flag_level_only"
    if len(dec_vals) == 1:
        v = next(iter(dec_vals))
        if not nar and not unread:
            return "agree", ""
        subs = set()
        for h in nar:
            subs.add("c1_narrowed_holds_it" if v in set(h["read"]["vals"])
                     else "c2_narrowed_excludes_it")
        if unread:
            subs.add("c3_unread")
        return "c_decided_vs_unsettled", "+".join(sorted(subs))
    # no head decided
    if nar and not unread:
        sets = [frozenset(h["read"]["vals"]) for h in nar]
        common = frozenset.intersection(*sets)
        if len(set(sets)) == 1:
            return "d_other", "d2_all_narrowed_identical"
        return "d_other", ("d2_narrowed_common_candidate" if common
                           else "d2_narrowed_disjoint")
    if unread and not nar:
        return "d_other", "d2_all_unread"
    return "d_other", "d2_narrowed_and_unread"


# ───────────────────────────── per-cell affine (canonical -> page) ─────────

def cell_affine(heads):
    """(ox, oy, up, max_residual_px): page = origin + canonical / up, solved
    from each head that carries both frames, median-combined. The residual is
    the control: every head's own page box re-predicted from the median."""
    sols = []
    for h in heads:
        g = h["g"]
        if g.box_canon is None or g.box_page is None:
            continue
        cx0, cy0, cx1, cy1 = g.box_canon
        px0, py0, px1, py1 = g.box_page
        if px1 - px0 <= 0:
            continue
        up = (cx1 - cx0) / (px1 - px0)
        if up <= 0:
            continue
        sols.append((px0 - cx0 / up, py0 - cy0 / up, up))
    if not sols:
        return None
    ox = statistics.median(s[0] for s in sols)
    oy = statistics.median(s[1] for s in sols)
    up = statistics.median(s[2] for s in sols)
    res = 0.0
    for h in heads:
        g = h["g"]
        if g.box_canon is None or g.box_page is None:
            continue
        cx0, cy0, cx1, cy1 = g.box_canon
        px0, py0, px1, py1 = g.box_page
        pred = (ox + cx0 / up, oy + cy0 / up, ox + cx1 / up, oy + cy1 / up)
        res = max(res, max(abs(pred[0] - px0), abs(pred[1] - py0),
                           abs(pred[2] - px1), abs(pred[3] - py1)))
    return ox, oy, up, res


# ───────────────────────────── the measurement ─────────────────────────────

def collect(run, pages=None, shift_stems_heads=0.0, shift_y_heads=0.0):
    """Every kept head, joined to every stem its box overlaps.

    `shift_stems_heads` > 0 is the NEGATIVE CONTROL: it slides every stem box
    right by that many head widths before the join, which must collapse the
    multi-head stems (a join that survives it is not a join)."""
    stems = stem_index(run)
    heads = []
    status_counts = collections.Counter()
    for key, g in run.glyphs.items():
        if g.family != "note" or (pages is not None and g.page not in pages):
            continue
        status, _why = _status(run, g)
        status_counts[status] += 1
        if status not in KEPT or g.box_canon is None:
            continue
        x0, y0, x1, y1 = g.box_canon
        heads.append({"key": key, "g": g, "status": status,
                      "box": (x0, y0, x1 - x0, y1 - y0),
                      "read": reading(run, key), "stems": []})
    by_stem = collections.defaultdict(list)
    for h in heads:
        w = h["box"][2]
        for sid, sb in stems.get(h["g"].cell_key, ()):
            sb2 = (sb[0] + shift_stems_heads * w,
                   sb[1] + shift_y_heads * h["box"][3], sb[2], sb[3])
            if _overlap(sb2, h["box"]):
                h["stems"].append((sid, sb))
                by_stem[sid].append(h)
    return heads, by_stem, status_counts


_RD = None


def _status(run, g):
    return _RD.adjudicate_status(run, g)


def enrich(run, stem_id, stem_box, hs):
    """The per-head evidence ADJUDICATE already holds, for the tile choice and
    the proposal (never used to classify)."""
    cell_key = hs[0]["g"].cell_key
    sp = cell_space(run, cell_key)
    sx, sy, sw, sh = stem_box
    slash = 0
    for o in run.obs_at(cell_key, "stem_slash"):
        if (o.get("detail") or {}).get("stem_row_id") == stem_id:
            try:
                slash = int(o.get("value") or 0)
            except (TypeError, ValueError):
                slash = 0
    out = []
    for h in hs:
        g = h["g"]
        x, y, w, hh = h["box"]
        cy = y + hh / 2.0
        end = min(cy - sy, (sy + sh) - cy) / hh if hh > 0 else None
        ink = run.obs_at(h["key"], "notehead_ink")
        center = ring = None
        if ink:
            d = (ink[-1].get("detail") or {})
            raw = d.get("ink_raw") or {}
            win = raw.get("windows") or {}
            center, ring = win.get("center"), win.get("ring")
        # where the stem's centre line stands across the head's own width:
        # a stem is flush with a head's SIDE (CLAUDE.md §10: up -> right edge,
        # down -> left edge), so 0 or 1 is attached and ~0.5 is a stem passing
        # through the head's body (a neighbour's stem, or a through-stem)
        frac = ((sx + sw / 2.0) - x) / w if w > 0 else None
        out.append({
            "stem_x_frac": round(frac, 2) if frac is not None else None,
            "key": h["key"], "cls": g.cls, "status": h["status"],
            "outcome": h["read"]["outcome"], "reason": h["read"]["reason"],
            "vals": [list(t) for t in h["read"]["vals"]],
            "w_sp": round(w / sp, 2) if sp else None,
            "h_sp": round(hh / sp, 2) if sp else None,
            "end_dist_heads": round(end, 2) if end is not None else None,
            "ink_center": center, "ink_ring": ring,
            "box_page": list(g.box_page) if g.box_page else None,
            "n_stems": len(h["stems"]),
        })
    return out, slash


def population(run, pages=None, shift=0.0, with_detail=True, shift_y=0.0):
    heads, by_stem, status_counts = collect(run, pages, shift, shift_y)
    stems = stem_index(run)
    sbox = {sid: sb for cell in stems.values() for sid, sb in cell}
    seen_sets = {}
    dup_stem_rows = 0
    groups = []
    for sid, hs in by_stem.items():
        if len(hs) < 2:
            continue
        hset = frozenset(h["key"] for h in hs)
        if hset in seen_sets:
            dup_stem_rows += 1
            continue
        seen_sets[hset] = sid
        primary, sub = classify(hs)
        row = {"stem": sid, "cell": hs[0]["g"].cell_key,
               "page": hs[0]["g"].page, "n_heads": len(hs),
               "primary": primary, "sub": sub,
               "any_unread": any(h["read"]["outcome"] not in
                                 ("decided", "narrowed") for h in hs)}
        if with_detail:
            ev, slash = enrich(run, sid, sbox[sid], hs)
            row["heads"] = ev
            row["slash_rows_on_stem"] = slash
            aff = cell_affine(hs)
            if aff is not None:
                ox, oy, up, res = aff
                x, y, w, h_ = sbox[sid]
                row["stem_box_page"] = [round(ox + x / up, 1),
                                        round(oy + y / up, 1),
                                        round(ox + (x + w) / up, 1),
                                        round(oy + (y + h_) / up, 1)]
                row["affine_residual_px"] = round(res, 2)
        groups.append(row)
    return heads, groups, status_counts, dup_stem_rows


def crosscheck_filed_join(run, heads):
    """Our first-overlapping-stem vs the stem GATHER filed on the head
    (`notehead_stem_cross_ink.detail.stem`), where it filed one."""
    n = agree = 0
    miss_ours = 0
    for h in heads:
        rows = run.obs_at(h["key"], "notehead_stem_cross_ink")
        if not rows:
            continue
        filed = (rows[-1].get("detail") or {}).get("stem")
        n += 1
        if not h["stems"]:
            miss_ours += 1
        elif h["stems"][0][0] == filed:
            agree += 1
    return {"heads_with_filed_join": n, "first_overlap_equals_filed": agree,
            "filed_but_no_overlap_here": miss_ours}


def event_relation(run, heads, groups):
    """How the existing chord verdict (`Q.EVENT`, an x-cluster of heads, never
    stems) relates to the stem groups: do the heads of one stem land in one
    event, and how many multi-head events stand on no shared stem."""
    cells = {h["g"].cell_key for h in heads}
    ev_of = {}          # (cell, glyph ordinal) -> event index
    events = {}         # cell -> [event dict]
    for c in cells:
        v = run.standing(c, "event", "ADJUDICATE")
        if not v or v.get("outcome") != "decided":
            continue
        evs = (v.get("value") or {}).get("events") or []
        events[c] = evs
        for i, e in enumerate(evs):
            for gi in e.get("glyphs", ()):
                ev_of[(c, gi)] = i
    kept = {(h["g"].cell_key, h["g"].index) for h in heads}
    same = split = nover = 0
    in_group = set()
    for g in groups:
        idx = []
        for h in g["heads"]:
            k = h["key"]
            cell = g["cell"]
            gi = int(k.rsplit("/", 1)[1])
            idx.append(ev_of.get((cell, gi)))
            in_group.add((cell, gi))
        if any(i is None for i in idx):
            nover += 1
        elif len(set(idx)) == 1:
            same += 1
        else:
            split += 1
    multi_events = no_stem_group = 0
    for c, evs in events.items():
        for e in evs:
            ks = [(c, gi) for gi in e.get("glyphs", ()) if (c, gi) in kept]
            if len(ks) < 2:
                continue
            multi_events += 1
            # a stem group holding two of this event's heads?
            held = sum(1 for k in ks if k in in_group)
            if held < 2:
                no_stem_group += 1
    return {"stem_groups": len(groups), "heads_all_in_one_event": same,
            "heads_split_across_events": split, "head_without_event": nover,
            "events_with_2plus_kept_heads": multi_events,
            "of_those_with_no_shared_stem": no_stem_group}


def tally(groups):
    c = collections.Counter(g["primary"] for g in groups)
    subs = collections.Counter((g["primary"], g["sub"]) for g in groups)
    return c, subs


def report(label, run, pages, count_page, out):
    heads, groups, status_counts, dups = population(run, pages)
    n_by_page = collections.Counter(h["g"].page for h in heads)
    print(f"\n=== {label}  pages {sorted(pages) if pages else 'all'} ===")
    print("notehead boxes by ADJUDICATE status:",
          dict(sorted(status_counts.items())))
    print(f"kept heads {len(heads)}; with >=1 stem "
          f"{sum(1 for h in heads if h['stems'])}; on 2+ stems "
          f"{sum(1 for h in heads if len(h['stems']) > 1)}; "
          f"no stem {sum(1 for h in heads if not h['stems'])}")
    # reach first (rule: print the population before any accuracy claim)
    print(f"stems carrying >=2 kept heads: {len(groups)} "
          f"(duplicate stem rows with the same head-set, counted once: {dups})")
    if not groups:
        print("DEAD: no multi-head stem in this record.")
    sizes = collections.Counter(g["n_heads"] for g in groups)
    print("  by head count:", dict(sorted(sizes.items())))
    for scope, sel in (("all gathered pages", groups),
                       (f"count page {count_page}",
                        [g for g in groups if g["page"] == count_page])):
        c, subs = tally(sel)
        print(f"-- {scope}: {len(sel)} multi-head stems")
        order = ["agree", "a_fill", "b_dots", "c_decided_vs_unsettled",
                 "d_other"]
        for p in order:
            print(f"   {p:<24}{c.get(p, 0):>6}")
            for (pp, s), n in sorted(subs.items()):
                if pp == p and s:
                    print(f"        {s:<40}{n:>5}")
        print(f"   stems with >=1 head UNREAD (abstained / no verdict): "
              f"{sum(1 for g in sel if g['any_unread'])}")
    for p in sorted({g['page'] for g in groups}):
        c, _ = tally([g for g in groups if g["page"] == p])
        print(f"  page {p}: kept heads {n_by_page[p]}, multi-head stems "
              f"{sum(c.values())}  " + "  ".join(
                  f"{k.split('_')[0]}={v}" for k, v in sorted(c.items())))
    # what the 'agree' control is made of (so it cannot be all one value)
    ag = [g for g in groups if g["primary"] == "agree"]
    vals = collections.Counter(tuple(g["heads"][0]["vals"][0]) for g in ag)
    print("-- the agree control by value (written, dots, fill):",
          dict(sorted(vals.items())))
    dotted = [g for g in groups
              if any(v[1] > 0 for h in g["heads"] for v in h["vals"])]
    print(f"-- multi-head stems with a dot read on any head: {len(dotted)} "
          f"(dot disagreement needs this population; (b) is only a result "
          f"where it is nonzero)")
    single = collections.Counter()
    for h in heads:
        single[len(h["stems"])] += 1
    print("-- kept heads by number of stem rows overlapped:",
          dict(sorted(single.items())))
    off = [h for g in groups for h in g["heads"]
           if h["stem_x_frac"] is not None and 0.25 < h["stem_x_frac"] < 0.75]
    print(f"-- group heads whose stem centre stands in the MIDDLE half of the "
          f"head ({len(off)} of {sum(len(g['heads']) for g in groups)}): a "
          f"stem is flush with a head's side, so these are loose joins")
    print("-- Q.EVENT (x-cluster chords) vs stem groups:",
          event_relation(run, heads, groups))
    # controls
    print("-- controls")
    print("  filed-join cross-check:", crosscheck_filed_join(run, heads))
    res = [g.get("affine_residual_px") for g in groups
           if g.get("affine_residual_px") is not None]
    if res:
        print(f"  cell affine residual px over groups: max {max(res):.2f}, "
              f"median {statistics.median(res):.2f}  (a COMPUTATION, not a "
              f"control: GATHER derives each page box from the canonical one "
              f"by this same affine; the frame control is `frame_control` on "
              f"the render, run by l278_tiles.py)")
    _h, g_shift, _s, _d = population(run, pages, shift=10.0, with_detail=False)
    print(f"  NEGATIVE control (stems slid 10 head-widths right): "
          f"multi-head stems {len(groups)} -> {len(g_shift)}  (a nonzero floor "
          f"is the slid stem landing on a NEIGHBOUR chord on a dense plate)")
    _h, g_shy, _s, _d = population(run, pages, shift_y=12.0, with_detail=False)
    print(f"  NEGATIVE control (stems slid 12 head-heights down): "
          f"multi-head stems {len(groups)} -> {len(g_shy)}")
    cols = []
    for g in groups:
        xs = [(h["box_page"][0] + h["box_page"][2]) / 2.0 for h in g["heads"]
              if h["box_page"]]
        sps = [h["w_sp"] for h in g["heads"] if h["w_sp"]]
        if xs and sps:
            cols.append((max(xs) - min(xs), statistics.mean(
                [(h["box_page"][2] - h["box_page"][0]) for h in g["heads"]
                 if h["box_page"]])))
    if cols:
        within = sum(1 for dx, w in cols if dx <= 1.2 * w)
        print(f"  POSITIVE control: heads of one stem share a column "
              f"(centre spread <= 1.2 head widths): {within} of {len(cols)}")
    out[label] = {"pages": sorted(pages) if pages else None,
                  "status_counts": dict(status_counts),
                  "kept_heads": len(heads), "groups": groups,
                  "duplicate_stem_rows": dups,
                  "filed_join_check": crosscheck_filed_join(run, heads)}
    return groups


def main(argv=None):
    global _RD
    sys.path.insert(0, os.getcwd())
    from tools.omr.staged import readout
    _RD = readout
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pages", help="comma list of page indexes (default all)")
    ap.add_argument("--count-page", type=int, required=True)
    ap.add_argument("--json")
    ap.add_argument("--label", default=None)
    a = ap.parse_args(argv)
    run = readout.load_run(a.record)
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    out = {"record": a.record,
           "provenance": run.provenance.get("commit"),
           "dirty": run.provenance.get("dirty")}
    print("record", a.record, "commit", out["provenance"], "dirty", out["dirty"])
    report(a.label or os.path.basename(a.record), run, pages, a.count_page, out)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print("wrote", a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
