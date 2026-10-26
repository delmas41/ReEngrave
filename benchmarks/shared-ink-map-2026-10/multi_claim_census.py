"""ROADMAP 2.205 cause study (read-only; no gather): how often is ONE stroke claimed by detector boxes of DIFFERENT families, and which pairs?

usage: multi_claim_census.py REPORT_OUT_DIR OUT.json [--arm on]
   REPORT_OUT_DIR = a lane_report out dir whose work/<plate>.<arm>.gathered.record.json was gathered with OMR_STROKE_MAP (the 2.202 milestone:
   .claude/worktrees/lane-2.202/out/lane-report/2.202m).

Streams each gathered record once (ijson). Per cell: the `Q.STROKE` rows, the `Q.GLYPH_BOX` + `Q.GLYPH_STROKES` rows (which strokes each box
covers, share >= 0.5, and partly covers), the `Q.CLAIMED_AREA` rows (page px areas), the `Q.STEM` finder rows. Then:

  1. raw coverage: strokes covered by 0 / 1 / >= 2 boxes, by >= 2 FAMILIES (`stroke_owner.family_of`), and the family pairs, by stroke kind;
  2. the consumers' exposure: strokes the 2.202 rule gives a beam role (`beam_strokes.role_of`: beam / beam_stub / hook / hook_or_stub) and
     vertical strokes <= 8 sp that coincide with a finder `Q.STEM` -- how many of them a CLAIMANT family's box covers (or partly covers), by family;
  3. `stroke_owner.own_strokes` itself on every cell: strokes by state, contested by family pair, refused claims by family;
  4. PARITY (plan section 5 step 5): every head / rest / accidental box an old PAIR RULE refused in the record's own verdicts
     (`PAIR_REASONS`), set against `stroke_owner.box_verdict` for that box: refused / contested (narrowed) / merged (same family, 2.186's) /
     owns / no_ink -- and the boxes ownership would refuse that no old pair rule refused, by what the record decided for them.
"""
import collections
import json
import pathlib
import sys

import ijson

sys.path.insert(0, ".")
from tools.omr.staged import beam_strokes as BS          # noqa: E402
from tools.omr.staged import stroke_owner as SO          # noqa: E402

BASE = 375000
#: (decision quantity, reason) of the pair rules plan section 3 lists for rests and heads; `rest_is_a_duplicate_box` counts only its
#: different-class branch (detail `duplicate_disagrees_with`).
PAIR_REASONS = {
    ("rest_is_not_a_rest", "rest_has_a_stem"), ("rest_is_not_a_rest", "rest_stroke_into_a_head"), ("rest_is_not_a_rest", "rest_is_a_barline"),
    ("rest_is_not_a_rest", "rest_is_a_slashed_stem"), ("rest_is_not_a_rest", "rest_is_a_duplicate_box"),
    ("notehead_is_not_a_notehead", "is_a_rest_twin"), ("notehead_is_not_a_notehead", "on_a_rest"),
    ("notehead_is_not_a_notehead", "is_a_beam_piece"), ("notehead_is_not_a_notehead", "head_cut_piece"),
    ("notehead_is_not_a_notehead", "tremolo_slash_crosses_stem"), ("accidental_owner", "on_a_rest"),
}
BOX_DECISIONS = {"rest_is_not_a_rest": "rest", "notehead_is_not_a_notehead": "head", "accidental_owner": "accidental"}


def old_verdicts(path):
    """`{(quantity, glyph key): (outcome, reason, different_class)}` for the three box decisions, the live (last) verdict per subject."""
    out = {}
    with open(path, "rb") as f:
        for v in ijson.items(f, "record.verdicts.item", use_float=True):
            q = v["quantity"]
            if q not in BOX_DECISIONS:
                continue
            d = v.get("detail") or {}
            out[(q, v["subject"])] = (v.get("outcome"), v.get("reason"), bool(d.get("duplicate_disagrees_with")), v.get("value"))
    return out


def cell_of(subject):
    """`p/s/st/c` of a glyph subject `glyph/p/s/st/c/n` (the key `Q.STEM` rows -- `cell/p/s/st/c` -- and the area claims share)."""
    return subject[len("glyph/"):].rsplit("/", 1)[0]


def stream(path):
    cells = collections.defaultdict(lambda: {"strokes": {}, "boxes": {}, "gs": {}, "stems": []})
    areas = collections.defaultdict(list)
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            q = o["quantity"]
            s = o["subject"]
            if q == "stroke":
                d = o["detail"]
                c = cells[cell_of(s)]
                c["strokes"][int(s.rsplit("/", 1)[1]) - BASE] = (o["value"], tuple(d["stroke_box"][:4]), float(d.get("length_spaces") or 0),
                                                                float(d.get("thickness_spaces") or 0), float(d.get("sagitta_spaces") or 0),
                                                                float(d.get("angle_deg") or 0),
                                                                tuple((int(a), float(b)) for a, b in d.get("touches") or ()),
                                                                float(d.get("staff_space_local_px") or 0), tuple(d.get("bbox_page_px") or ()),
                                                                o["id"], float(d.get("fill") or 0))
            elif q == "glyph_box" and s.startswith("glyph/"):
                cells[cell_of(s)]["boxes"][s] = (o["value"][0], (o.get("detail") or {}).get("category"))
            elif q == "glyph_strokes":
                d = o.get("detail") or {}
                cells[cell_of(s)]["gs"][s] = (tuple(int(v) for v in o["value"]), tuple((int(a), float(b)) for a, b in d.get("partial") or ()), o["id"])
            elif q == "stem" and s.startswith("cell/"):
                cells[s[5:]]["stems"].append(tuple(o["value"][:4]))
            elif q == "claimed_area":
                d = o.get("detail") or {}
                if d.get("unit") == "area" and d.get("standing", "READ") == "READ":
                    areas["%s/%s" % (s[6:], d.get("cell"))].append((d.get("owner"), tuple(o["value"][:4]), o["id"]))
    return cells, areas


def area_sp2(t):
    sp = t[7]
    return t[10] * t[1][2] * t[1][3] / (sp * sp) if sp > 0 else 0.0


def run(path):
    cells, areas = stream(path)
    boxv = {}
    raw = collections.Counter()
    pairs = collections.Counter()
    pairs_kind = collections.Counter()
    expo = collections.Counter()
    states = collections.Counter()
    contested = collections.Counter()
    refused = collections.Counter()
    decided_fam = collections.Counter()
    for ck, c in cells.items():
        if not c["strokes"]:
            continue
        fam_of_box = {k: SO.family_of(cls, cat) for k, (cls, cat) in c["boxes"].items()}
        cover = collections.defaultdict(set)      # ordinal -> {(box, family)}
        part = collections.defaultdict(set)
        claims = []
        for k, (cov, partial, rid) in c["gs"].items():
            fam = fam_of_box.get(k)
            if fam is None:
                continue
            for o in cov:
                cover[o].add((k, fam))
            for o, sh in partial:
                if sh >= SO.ATTACH_SHARE_MIN:
                    part[o].add((k, fam))
            claims.append(SO.Claim(k, fam, c["boxes"][k][0], cov, partial, rid))
        # area claims: the strokes whose page-px centre stands in the area
        for owner, (x0, y0, x1, y1), rid in areas.get(ck, ()):
            inside = []
            for o, t in c["strokes"].items():
                pb = t[8]
                if len(pb) == 4 and x0 <= (pb[0] + pb[2]) / 2 <= x1 and y0 <= (pb[1] + pb[3]) / 2 <= y1:
                    inside.append(o)
            if owner in SO.AREA_OWNERS and inside:
                claims.append(SO.Claim(rid, owner, owner, tuple(inside), (), rid, area=True))
        views = [BS.StrokeView(o, t[0], tuple(float(v) for v in t[1]), t[2], t[3], t[4], t[5], t[6], t[7], t[9]) for o, t in c["strokes"].items()]
        role = BS.roles(views)
        finder = set()
        for o, t in c["strokes"].items():
            kind = t[0]
            fams = {f for _k, f in cover.get(o, ())}
            raw["strokes"] += 1
            nb = len(cover.get(o, ()))
            raw["boxes=%s" % (nb if nb < 2 else ">=2")] += 1
            claimant = {f for f in fams if f not in SO.CONSUMERS}
            if len(fams) >= 2:
                raw["families>=2"] += 1
                if len(claimant) >= 2:
                    raw["claimant_families>=2"] += 1
                fl = sorted(fams)
                for i in range(len(fl)):
                    for j in range(i + 1, len(fl)):
                        pairs[(fl[i], fl[j])] += 1
                        pairs_kind[(fl[i], fl[j], kind)] += 1
            # consumer exposure
            r = role[o]["role"]
            cons = None
            if r in ("beam", "beam_stub", "hook", "hook_or_stub"):
                cons = "beam_role:" + r
            elif kind == "vertical" and t[2] <= BS.STEM_MAX_SPACES:
                bx, by, bw, bh = t[1]
                for sx, sy, sw, sh in c["stems"]:
                    if bx <= sx + sw + 0.35 * t[7] and bx + bw >= sx - 0.35 * t[7] and min(by + bh, sy + sh) - max(by, sy) > 0.5 * min(bh, sh):
                        cons = "finder_stem"
                        finder.add(o)
                        break
            if cons:
                expo[(cons, "total")] += 1
                if claimant:
                    expo[(cons, "covered_by_claimant")] += 1
                    for f in claimant:
                        expo[(cons, "covered_by:" + f)] += 1
                elif {f for _k, f in part.get(o, ()) if f not in SO.CONSUMERS}:
                    expo[(cons, "partly_covered_by_claimant")] += 1
        inks = [SO.Ink(o, t[0], tuple(float(v) for v in t[1]), t[2], t[3], area_sp2(t), t[7], t[6], t[9], t[5]) for o, t in c["strokes"].items()]
        own = SO.own_strokes(inks, claims)
        by_ink = {i.ordinal: i for i in inks}
        for cl in claims:
            if cl.family in ("head", "rest", "accidental") and not cl.area:
                bv = SO.box_verdict(cl, own, by_ink)
                if bv["verdict"] == "owns" and all(len(own[o].owners) > 1 for o in cl.covers if o in own and cl.key in own[o].owners):
                    bv = {"verdict": "merged", "lost": []}
                boxv[cl.key] = (cl.family, cl.cls, bv["verdict"], [(o, st, fam, why) for o, st, fam, why in bv["lost"]][:4])
        for o, w in own.items():
            states[w.state] += 1
            if w.family:
                decided_fam[w.family] += 1
            if w.state == "contested":
                contested["|".join(sorted({str(x["family"]) for x in w.candidates if x["fit"] != "no"})) + "|" + by_ink[o].kind] += 1
            if w.state == "refused_claims":
                for x in w.candidates:
                    refused["%s:%s:%s" % (x["family"], str(x["why"]).split(":")[0], by_ink[o].kind)] += 1
            if o in finder:
                states["finder_stem:%s" % (w.family or w.state)] += 1
            r = role[o]["role"]
            if r in ("beam", "beam_stub", "hook", "hook_or_stub") and w.claimed:
                states["beam_role_claimed:%s:%s" % (r, w.family or w.state)] += 1
    return {"raw": dict(raw), "pairs": {"|".join(k): v for k, v in pairs.most_common()},
            "pairs_by_kind": {"|".join(k): v for k, v in pairs_kind.most_common(40)},
            "exposure": {"|".join(k): v for k, v in sorted(expo.items())},
            "own_states": dict(states.most_common()), "owned_by_family": dict(decided_fam.most_common()),
            "contested_pairs": dict(contested.most_common()), "refused_claims": dict(refused.most_common(30))}, boxv


def parity(boxv, old):
    """The parity table (module doc, 4) and the named differences."""
    tab = collections.Counter()
    diffs = collections.defaultdict(list)
    new = collections.Counter()
    new_ex = collections.defaultdict(list)
    for (q, key), (outcome, reason, diffcls, value) in old.items():
        fam = BOX_DECISIONS[q]
        bv = boxv.get(key)
        own = bv[2] if bv and bv[0] == fam else "no_strokes_row"
        pair = (q, reason) in PAIR_REASONS and (reason != "rest_is_a_duplicate_box" or diffcls)
        if pair:
            name = reason + (":different_class" if reason == "rest_is_a_duplicate_box" else "")
            tab[(name, own)] += 1
            if own not in ("refused", "contested"):
                diffs[name + "/" + own].append([key, bv[1] if bv else None, bv[3] if bv else None])
        elif own in ("refused", "contested") and (q != "accidental_owner"):
            refused_old = (value is True) if q != "accidental_owner" else outcome != "decided"
            new[(fam, own, "old_refused:" + str(reason) if refused_old else "old_kept:" + str(reason))] += 1
            if not refused_old:
                new_ex["%s/%s" % (fam, own)].append([key, bv[1], bv[3]])
    return ({"|".join(k): v for k, v in sorted(tab.items())}, {k: v[:12] for k, v in diffs.items()}, {k: len(v) for k, v in diffs.items()},
            {"|".join(k): v for k, v in new.most_common(40)}, {k: v[:12] for k, v in new_ex.items()})


def main():
    rep = pathlib.Path(sys.argv[1])
    arm = sys.argv[sys.argv.index("--arm") + 1] if "--arm" in sys.argv else "on"
    res = {}
    for plate in ("litolff", "brahms"):
        path = rep / "work" / ("%s.%s.gathered.record.json" % (plate, arm))
        res[plate], boxv = run(path)
        tab, ex, nd, new, new_ex = parity(boxv, old_verdicts(path))
        res[plate]["parity"] = {"table": tab, "differences_n": nd, "differences_examples": ex, "ownership_only": new, "ownership_only_examples": new_ex}
        r = res[plate]
        print("  parity", tab)
        print("  ownership-only", list(new.items())[:14])
        print(plate, r["raw"])
        print("  pairs", list(r["pairs"].items())[:12])
        print("  exposure", r["exposure"])
        print("  own", r["own_states"])
        print("  contested", list(r["contested_pairs"].items())[:10])
        print("  refused", list(r["refused_claims"].items())[:10])
    json.dump(res, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
