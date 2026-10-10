#!/usr/bin/env python3
"""l281_score: the 2.81 bare-stem population on Sean's hand-labeled page, scored.

For every member of the population (see `l281_population.py`) on PDF page 0 of Brahms
317803, find the truth notehead it is (the scorer's own matcher, `hand_truth.score.match_boxes`,
boxes by overlap and never by the cell the record filed them under) and read the head's
written value off Sean's boxes (`l281_truth.py`). The candidate rule: *filled head, bare
stem, tip seen clean -> level 0 (a quarter; a dotted quarter with a dot)*.

A member is judged
  right         the truth head is FILLED, stands on a truth stem, and no truth beam or flag is on
                that stem (levels 0): the rule's level-0 answer is the print's
  wrong_beam    the truth head carries beam/flag level >= 1 (the rule would say quarter; the print
                says eighth or shorter)
  wrong_fill    the truth head is hollow (a half or whole; level 0 is a quarter, not the print's)
  no_truth_stem the truth head has no stem box under it: Sean's page does not say (92 of 339 heads
                on this page; stems are CV-only and Sean boxed only some) -- NEVER counted
  no_truth_head no truth notehead overlaps the record's box: the member is not a head in the
                truth (a false head; reported, never counted as right or wrong)
  unscored      the member's centre is in no fully labeled cell

The point estimate is right / (right + wrong_*) with its count and a 95% Wilson interval, per
tip status and for every judged member together. Dots are compared separately: the rule does not
choose the dot count (every candidate carries ours), so a dot disagreement is a second fault and
reported beside, never folded in.

    python3 l281_score.py --tag brahms-quick --ext DIR [--json out.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_population import build, wilson  # noqa: E402
from l281_truth import Truth, in_full_cell  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402

PAGE = 0

#: Heads judged `right` by Sean's boxes whose crop (out/print/2.81-hand-truth-check/) shows a printed flag his
#: page does not box. Agent-read; the crop is there for Sean to overrule.
PRINT_CHECK_UNBOXED_MARK = {"glyph/0/0/9/2/2"}


def fmt_ci(k, n):
    if n == 0:
        return "n=0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.3f}  (95% Wilson {lo:.3f}-{hi:.3f})"


def match_all(T, heads_page):
    """record head key -> (truth head idx, iou) over every record head on the page."""
    truth = [(h.idx, h.rect, h.cls) for h in T.heads]
    read = [(i, tuple(h["page"]), h["cls"]) for i, (k, h) in enumerate(heads_page.items())
            if h["page"]]
    keys = [k for k, h in heads_page.items() if h["page"]]
    pairs, only_t, only_r = S.match_boxes(truth, read)
    out = {}
    for t_idx, (r_i, iou) in pairs.items():
        out[keys[r_i]] = (t_idx, iou)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ext", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Truth()
    d, pop, n_heads, _sc = build(a.ext, a.tag)
    heads_page = {k: h for k, h in d["obs"]["heads"].items() if int(k.split("/")[1]) == PAGE}
    match = match_all(T, heads_page)
    by_idx = {h.idx: h for h in T.heads}
    members = [m for m in pop if m["page"] == PAGE]
    print(f"== {a.tag} (record {d['prov'].get('commit')}); page-{PAGE} heads {len(heads_page)}; "
          f"population members on the page {len(members)}")
    rows = []
    for m in members:
        tip2 = m["tip"]
        if tip2 == "clean":
            tip2 = {False: "clean_nostroke", True: "clean_stroke"}.get(m["at_tip"], "clean_unasked")
        row = {"key": m["key"], "tip": tip2, "dots_read": m["dots"], "cls": m["cls"],
               "final_stage": m["final_stage"], "final_outcome": m["final_outcome"],
               "page_box": m["page_box"], "ink_why": m["ink_why"]}
        fv = m["final_value"]
        row["final_level"] = fv.get("beam_levels") if isinstance(fv, dict) else None
        row["final_written"] = fv.get("written") if isinstance(fv, dict) else None
        box = m["page_box"]
        if not box:
            row["judge"] = "unscored"
            rows.append(row)
            continue
        cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
        cell = in_full_cell(T.full, [cx, cy, cx, cy])
        if cell is None:
            row["judge"] = "unscored"
            rows.append(row)
            continue
        hit = match.get(m["key"])
        if hit is None:
            row["judge"] = "no_truth_head"
            rows.append(row)
            continue
        th = by_idx[hit[0]]
        dv = T.derive(th)
        row.update(truth_cls=th.cls, truth_status=dv["status"], truth_levels=dv.get("levels"),
                   truth_dots=dv.get("dots"), truth_base=dv.get("base"), iou=round(hit[1], 2),
                   truth_written=dv.get("written"), truth_tremolo=dv.get("tremolo"),
                   truth_rect=dv["rect"], truth_id=dv["id"], cell=cell.id,
                   truth_stem_rect=dv.get("stem_rect"), truth_tip_end=dv.get("tip_end"),
                   truth_levels_beam=dv.get("levels_beam"), truth_levels_flag=dv.get("levels_flag"),
                   truth_tremolo_n=dv.get("tremolo"), truth_stem_id=dv.get("stem"),
                   truth_beam_ids=dv.get("beam_ids"), truth_flag_ids=dv.get("flag_ids"))
        if dv["status"] != "ok":
            mk = dv.get("marks_near") or {}
            row["marks_near"] = mk
            row["judge"] = ("no_stem_box_marked" if (mk.get("flags") or mk.get("beams"))
                            else "no_truth_stem")
        elif dv["base"] != 1.0:
            row["judge"] = "wrong_fill"
        elif dv["levels"] == 0:
            row["judge"] = "right"
        else:
            row["judge"] = "wrong_beam"
        rows.append(row)
    print("judge:", dict(collections.Counter(r["judge"] for r in rows)))
    judged = [r for r in rows if r["judge"] in ("right", "wrong_beam", "wrong_fill")]
    # THE PRINT CHECK (agent-read, NOT Sean's): every head judged `right` was looked at on a crop big
    # enough to show its stem's far end (out/print/2.81-hand-truth-check/); a head whose print shows a
    # flag or beam Sean's page does not box is `right` BY HIS BOXES and wrong by the print.
    corrected = collections.Counter()
    for r in judged:
        if r["judge"] == "right" and r["key"] in PRINT_CHECK_UNBOXED_MARK:
            corrected[r["tip"]] += 1
    cj = [dict(r, judge=("wrong_print" if (r["judge"] == "right" and r["key"] in PRINT_CHECK_UNBOXED_MARK)
                         else r["judge"])) for r in judged]
    print(f"\nPRINT CHECK: {sum(corrected.values())} head(s) right by Sean's boxes, a flag/beam on the print "
          f"his page does not box: {dict(corrected)}; {sorted(PRINT_CHECK_UNBOXED_MARK)}")
    print("  with the correction (agent-read):  all", fmt_ci(sum(r["judge"] == "right" for r in cj), len(cj)))
    for tip in ("clean_nostroke", "clean_stroke", "occupied", "no_stem"):
        sub = [r for r in cj if r["tip"] == tip]
        if sub:
            print(f"    tip {tip:14s}", fmt_ci(sum(r["judge"] == "right" for r in sub), len(sub)))
    # SENSITIVITY: a head Sean did not box a stem for, but whose flag/beam box is plainly its own, is
    # evidence it is not level 0 -- counted here as WRONG (never as right) to bound the strict figure.
    bounded = judged + [r for r in rows if r["judge"] == "no_stem_box_marked"]
    print("\nBOUNDED (heads with an unboxed stem but THEIR flag/beam box counted wrong; never counted right):")
    print("  all:             ", fmt_ci(sum(r["judge"] == "right" for r in bounded), len(bounded)))
    for tip in ("clean_nostroke", "clean_stroke", "occupied", "no_stem"):
        sub = [r for r in bounded if r["tip"] == tip]
        if sub:
            print(f"  tip {tip:11s}: ", fmt_ci(sum(r["judge"] == "right" for r in sub), len(sub)))
    csub = [r for r in bounded if r["tip"].startswith("clean")]
    print("  tip clean (window) any:", fmt_ci(sum(r["judge"] == "right" for r in csub), len(csub)))
    print("  UNJUDGEABLE (stem unboxed, no mark of his near):",
          dict(collections.Counter(r["tip"] for r in rows if r["judge"] == "no_truth_stem")))
    print("  FALSE HEADS (no truth head under the box):",
          dict(collections.Counter(r["tip"] for r in rows if r["judge"] == "no_truth_head")))
    print("\nPRECISION OF 'level 0 = the head's own value' over judged members:")
    print("  all judged:      ", fmt_ci(sum(r["judge"] == "right" for r in judged), len(judged)))
    clean = [r for r in judged if r["tip"].startswith("clean")]
    print("  tip clean (window) any:", fmt_ci(sum(r["judge"] == "right" for r in clean), len(clean)))
    for tip in ("clean_nostroke", "clean_stroke", "clean_unasked", "occupied", "hook_seen", "no_stem",
                "left_inked", "no_side", "other_abst"):
        sub = [r for r in judged if r["tip"] == tip]
        if sub:
            print(f"  tip {tip:11s}: ", fmt_ci(sum(r["judge"] == "right" for r in sub), len(sub)))
    print("\nby tip status x judge:")
    c = collections.Counter((r["tip"], r["judge"]) for r in rows)
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")
    # dots
    dj = [r for r in judged if r.get("truth_dots") is not None]
    dd = collections.Counter((r["dots_read"], r["truth_dots"]) for r in dj)
    print("\nour dots vs truth dots (judged members):", dict(dd))
    # INDEPENDENCE: heads that share a stem (a chord) or a beam stand or fall together -- one refused beam
    # makes every head under it wrong. The sampling unit is the stem/beam GROUP, not the head.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a_, b_):
        parent[find(a_)] = find(b_)
    for r in judged:
        find(r["key"])
        if r.get("truth_stem_id"):
            union(r["key"], "stem:" + r["truth_stem_id"])
        for b in (r.get("truth_beam_ids") or []):
            union(r["key"], "beam:" + b)
        for f in (r.get("truth_flag_ids") or []):
            union(r["key"], "flag:" + f)
    groups = collections.defaultdict(list)
    for r in judged:
        groups[find(r["key"])].append(r)
    g_wrong = [g for g in groups.values() if any(x["judge"] != "right" for x in g)]
    g_right = [g for g in groups.values() if all(x["judge"] == "right" for x in g)]
    print(f"\nINDEPENDENT UNITS (heads sharing a stem, beam or flag counted once): {len(groups)} groups over "
          f"{len(judged)} heads; {len(g_right)} groups all right, {len(g_wrong)} groups with a wrong head "
          f"(mixed groups: {sum(1 for g in g_wrong if any(x['judge'] == 'right' for x in g))})")
    print("  by group:   ", fmt_ci(len(g_right), len(groups)))
    print("  wrong groups by what his boxes show:",
          dict(collections.Counter(
              "beam" if any(x.get("truth_levels_beam") for x in g) else "flag" for g in g_wrong)),
          "; heads per wrong group:", sorted(len(g) for g in g_wrong))
    ious = [r["iou"] for r in judged if r.get("iou") is not None]
    print(f"  match quality (the frame): IoU >= 0.99 on {sum(1 for v in ious if v >= 0.99)} of {len(ious)} judged heads; "
          f"min {min(ious):.2f}")
    wrong = [r for r in judged if r["judge"] != "right"]
    print("\nwrong cases by what Sean's boxes show on the stem:",
          dict(collections.Counter(
              ("beam" if r.get("truth_levels_beam") else "flag") + f" level {r.get('truth_levels')}"
              for r in wrong)))
    print("\nwrong cases:")
    for r in wrong:
        print(f"  {r['key']} tip={r['tip']} {r['judge']} truth_levels={r['truth_levels']} "
              f"truth_cls={r['truth_cls']} cell={r['cell']} truth {r['truth_id']}")
    print("\nfinal state of the judged members (what the later stages did):")
    fc = collections.Counter((r["judge"], r["final_stage"], r["final_outcome"], r["final_level"])
                             for r in judged)
    for k, v in sorted(fc.items(), key=lambda kv: str(kv[0])):
        print(f"  {k}: {v}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
