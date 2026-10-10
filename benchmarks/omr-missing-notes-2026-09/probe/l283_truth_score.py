#!/usr/bin/env python3
"""l283_truth_score: Sean's hand-truth page (Brahms 317803 pdf 0) scored against BASE and ARM records, GATHER+ADJUDICATE only
(CLAUDE.md 6b), for ROADMAP 2.83.

Heads: each truth BLACK head in a fully labeled cell with a derived written value (`l281_truth.Truth.derive`: the stem box it
stands on, the beams and flags of his on that stem, tremolo slashes excluded) is matched to a record head by box overlap
(`hand_truth.score.match_boxes`, never by the cell the record filed it under). The standing ADJUDICATE `Q.DURATION` verdict
of that head, in each record, is classed against his level L:

  right      DECIDED at level L
  narrowed+  NARROWED and L is one of the candidates (the right answer is still on the table)
  narrowed-  NARROWED and L is NOT a candidate (the right answer was dropped)
  wrong      DECIDED at another level
  abstained  no verdict / abstained / the head refused or given to another staff

Sean's flags: each of his `flag*` boxes -> the stem it hangs from -> the black head(s) on that stem; "read" = the head's
verdict acknowledges a flag (decided level >= 1, or narrowed with no level-0 candidate), and the head's own-stem tip row
(`Q.STEM_TIP_INK`, the end the stem points away from) says True. The 2.81 population's wrong heads (the 22 of FINDINGS 17.3)
are the truth heads of level >= 1 that base left as level 0 or narrowed over 0: they are reported by name.

    python3 l283_truth_score.py --base base.record.json --arm arm.record.json [--json out.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth, hbase, in_full_cell  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

PAGE = 0


def verdict_class(run, key, level):
    g = run.glyphs.get(key)
    if g is None:
        return "abstained", None
    status, _ = RD.adjudicate_status(run, g)
    if status in ("refused", "given_away"):
        return "abstained", status
    v = run.standing(key, Q.DURATION, "ADJUDICATE")
    if v is None or v["outcome"] == "abstained":
        return "abstained", v["outcome"] if v else "none"
    if v["outcome"] == "decided":
        val = v.get("value") or {}
        lv = val.get("beam_levels")
        return ("right" if lv == level else "wrong"), (v.get("reason"), lv)
    lvs = set()
    for c in v.get("candidates") or []:
        val = c.get("value") if isinstance(c, dict) else None
        if isinstance(val, dict):
            lvs.add(val.get("beam_levels"))
    return ("narrowed+" if level in lvs else "narrowed-"), (v.get("reason"), sorted(x for x in lvs if x is not None))


def tip_state(run, key):
    """The Q.STEM_TIP_INK rows of this head's cell for the stem its HEAD_STEM verdict names: 'flag'/'none' per end, or the
    abstention reason. Returns the end the stem points AWAY from the head (the tip) only when the stem direction is decided."""
    v = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
    if v is None or v["outcome"] != "decided" or not v.get("value"):
        return "no_stem"
    sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
    if sd is None or sd["outcome"] != "decided" or sd.get("value") not in ("up", "down"):
        return "no_side"
    end = "top" if sd["value"] == "up" else "bottom"
    g = run.glyphs[key]
    cell = g.cell_key
    out = None
    for o in run.obs_at(cell, Q.STEM_TIP_INK):
        d = o.get("detail") or {}
        if d.get("stem_row_id") == v["value"] and d.get("end") == end:
            out = "flag" if o["value"] else "none"
    if out is None:
        for s, k, a in run.rows_at(cell):
            if k == "abstention" and a["quantity"] == Q.STEM_TIP_INK:
                d = a.get("detail") or {}
                if d.get("stem_row_id") == v["value"] and d.get("end") == end:
                    out = "abstained:" + a["reason"] + ((":" + d["why"]) if d.get("why") else "")
    return out or "no_row"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Truth()
    runs = {"base": RD.load_run(a.base), "arm": RD.load_run(a.arm)}
    for k, r in runs.items():
        print(f"{k}: {r.provenance.get('commit')} dirty={r.provenance.get('dirty')} {r.path}")
    truth_heads = [(h.idx, h.rect, h.cls) for h in T.heads]
    match = {}
    for tag, run in runs.items():
        keys = [k for k, g in run.glyphs.items() if g.page == PAGE and g.box_page and (g.cls or "").startswith("notehead")]
        read = [(i, tuple(run.glyphs[k].box_page), run.glyphs[k].cls) for i, k in enumerate(keys)]
        pairs, _ot, _or = S.match_boxes(truth_heads, read)
        match[tag] = {t_idx: keys[r_i] for t_idx, (r_i, _iou) in pairs.items()}
    by_idx = {h.idx: h for h in T.heads}
    rows = []
    for h in T.heads:
        if hbase(h.cls) != 1.0 or in_full_cell(T.full, h.rect) is None:
            continue
        d = T.derive(h)
        if d["status"] != "ok" or d["tremolo"]:
            continue
        L = d["levels"]
        row = {"truth": h.id, "level": L, "kind": "beam" if d["levels_beam"] else ("flag" if d["levels_flag"] else "bare")}
        for tag, run in runs.items():
            key = match[tag].get(h.idx)
            row[tag + "_key"] = key
            if key is None:
                row[tag] = ("unmatched", None)
                row[tag + "_tip"] = None
            else:
                row[tag] = verdict_class(run, key, L)
                row[tag + "_tip"] = tip_state(run, key)
        rows.append(row)
    print(f"\ntruth black heads judged: {len(rows)}  by kind: {dict(collections.Counter(r['kind'] for r in rows))}")
    for kind in ("flag", "beam", "bare"):
        sub = [r for r in rows if r["kind"] == kind]
        b = collections.Counter(r["base"][0] for r in sub)
        c = collections.Counter(r["arm"][0] for r in sub)
        print(f"\n== truth {kind} (n={len(sub)})")
        print("   base:", dict(b))
        print("   arm: ", dict(c))
        tr = collections.Counter((r["base"][0], r["arm"][0]) for r in sub)
        for (x, y), n in sorted(tr.items(), key=lambda kv: -kv[1]):
            print(f"     {x:10s} -> {y:10s} {n}")
    print("\n== tip row of the true tip end (flag heads), base -> arm")
    tr = collections.Counter((r["base_tip"], r["arm_tip"]) for r in rows if r["kind"] == "flag")
    for (x, y), n in sorted(tr.items(), key=lambda kv: -kv[1]):
        print(f"   {str(x):40s} -> {str(y):40s} {n}")
    print("\n== GUARD: tip rows at the true tip of heads whose stem carries NO flag (bare + beam), arm")
    g = collections.Counter(r["arm_tip"] for r in rows if r["kind"] in ("bare", "beam"))
    for k_, n in sorted(g.items(), key=lambda kv: -kv[1]):
        print(f"   {str(k_):45s} {n}")
    newly = [r for r in rows if r["kind"] in ("bare", "beam") and r["arm_tip"] == "flag" and r["base_tip"] != "flag"]
    print(f"   NEWLY read as a flag where his boxes show none: {len(newly)}", [r["truth"] for r in newly])
    # wrong-in-2.81 eighths: level>=1 heads base left as quarter / narrowed
    wrong81 = [r for r in rows if r["level"] >= 1 and r["base"][0] in ("wrong", "narrowed+", "narrowed-", "abstained")
               and r["base"][0] != "right"]
    print(f"\n== his level>=1 heads that base does not decide right ({len(wrong81)}), base -> arm")
    for r in sorted(wrong81, key=lambda r: (r["kind"], r["truth"])):
        print(f"   {r['truth']:8s} {r['kind']:5s} L={r['level']}  base {r['base'][0]:10s} {r['base'][1]}  ->  arm {r['arm'][0]:10s} {r['arm'][1]}"
              f"   tip {r['base_tip']} -> {r['arm_tip']}")
    wrong_now = [r for r in rows if r["arm"][0] == "wrong" and r["base"][0] != "wrong"]
    print(f"\n== NEWLY WRONG (decided at another level than his, where base was not): {len(wrong_now)}")
    for r in wrong_now:
        print("  ", r["truth"], r["kind"], "L=", r["level"], "base", r["base"], "arm", r["arm"], r["arm_tip"])
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
