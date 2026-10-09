"""ROADMAP 2.73 -- what the change moved on a small re-gather, base vs arm.

PATH: STAGED, GATHER+ADJUDICATE only. Both records are gathered from one tree
each (base = `lane-2.70-hollow-half` + main, arm = + this lane) with the same
weights, so glyph keys line up one for one; `--check-keys` says how many do
not (a detector that is not byte-deterministic would show here).

    python3 benchmarks/omr-head-fill-2026-09/population_2_73.py BASE.json ARM.json \
        [--pages 0,1] [--json out.json]

Position changes and duration changes are reported APART (CLAUDE.md: a head
that moves a half-step and a head that changes value are different claims):

  position   the notehead's staff position (ADJUDICATE `notehead_position`
             where decided, else GATHER's rounded `notehead_staff_position`),
             on heads kept in BOTH records
  duration   ADJUDICATE `duration` (beats, or narrowed/abstained) on heads
             kept in BOTH records
  kept       heads refused in one record and kept in the other
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys


def facts(run, key, readout):
    g = run.glyphs[key]
    status, why = readout.adjudicate_status(run, g)
    vs = {v["quantity"]: v for v in run.verdicts_at(key, "ADJUDICATE")}
    pos = None
    pv = vs.get("notehead_position")
    if pv and pv.get("outcome") == "decided":
        pos = pv.get("value")
    if pos is None:
        sp = run.obs_at(key, "notehead_staff_position")
        if sp:
            pos = int(round(float(sp[-1]["value"])))
    d = vs.get("duration")
    if d is None:
        dur = None
    elif d.get("outcome") == "decided" and isinstance(d.get("value"), dict):
        dur = ("decided", d["value"].get("beats"), d.get("reason"))
    else:
        dur = (d.get("outcome"), None, d.get("reason"))
    return {"status": status, "why": (why or [""])[0], "pos": pos, "dur": dur,
            "cls": g.cls, "box": g.box_page}


def main(argv=None):
    sys.path.insert(0, os.getcwd())
    from tools.omr.staged import readout
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("arm")
    ap.add_argument("--pages")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    base, arm = readout.load_run(a.base), readout.load_run(a.arm)
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    kb = {k for k, g in base.glyphs.items() if g.family == "note"
          and (pages is None or g.page in pages)}
    ka = {k for k, g in arm.glyphs.items() if g.family == "note"
          and (pages is None or g.page in pages)}
    both = sorted(kb & ka)
    out = {"base_heads": len(kb), "arm_heads": len(ka), "same_key": len(both),
           "only_base": len(kb - ka), "only_arm": len(ka - kb)}
    kept = ("kept", "narrowed", "abstained")
    pos_moved, dur_moved, newly_kept, newly_refused = [], [], [], []
    cut_rows = {k: arm.obs_at(k, "head_line_cut") for k in both}
    n_cut = sum(1 for v in cut_rows.values() if v)
    for k in both:
        fb, fa = facts(base, k, readout), facts(arm, k, readout)
        kb_, ka_ = fb["status"] in kept, fa["status"] in kept
        if kb_ and not ka_:
            newly_refused.append((k, fb, fa))
        elif ka_ and not kb_:
            newly_kept.append((k, fb, fa))
        elif kb_ and ka_:
            if fb["pos"] != fa["pos"]:
                pos_moved.append((k, fb, fa))
            if fb["dur"] != fa["dur"]:
                dur_moved.append((k, fb, fa))
    out.update({"head_line_cut_rows": n_cut,
                "newly_kept": len(newly_kept), "newly_refused": len(newly_refused),
                "position_moved": len(pos_moved), "duration_moved": len(dur_moved)})
    why_c = collections.Counter(f["why"][:60] for _k, f, _a in newly_refused)
    why_k = collections.Counter(f["why"][:60] for _k, f, _a in newly_kept)
    out["newly_refused_by_reason_now"] = collections.Counter(
        f["why"][:60] for _k, _b, f in newly_refused).most_common(8)
    out["newly_kept_were_refused_by"] = why_k.most_common(8)
    out["duration_moves"] = collections.Counter(
        f"{(b['dur'] or ('-',))[1:2]} -> {(x['dur'] or ('-',))[1:2]} [{(x['dur'] or ('-', '-', ''))[2]}]"
        for _k, b, x in dur_moved).most_common(12)
    out["position_moves"] = collections.Counter(
        f"{b['pos']} -> {x['pos']}" for _k, b, x in pos_moved).most_common(12)
    print(json.dumps(out, indent=1, default=str))
    if a.json:
        json.dump({"summary": out,
                   "newly_kept": [(k, b, x) for k, b, x in newly_kept],
                   "newly_refused": [(k, b, x) for k, b, x in newly_refused],
                   "position_moved": [(k, b, x) for k, b, x in pos_moved],
                   "duration_moved": [(k, b, x) for k, b, x in dur_moved]},
                  open(a.json, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
