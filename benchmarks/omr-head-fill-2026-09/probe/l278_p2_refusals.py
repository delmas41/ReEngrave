"""ROADMAP 2.78 Phase 2 -- which per-box witnesses ALREADY sit on the record for the boxes Sean says are not notes.

PATH: STAGED, GATHER + ADJUDICATE only, on a re-adjudicated saved record (see l278_p2_arm.py). Measures
only; nothing here refuses a box. Sean (DECISIONS 2026-10-09): a head that may not be a head is refused ONLY
with a per-box witness (a slash crossing it, or a duplicate of another head at the same position), never by
fill alone. Three candidate witnesses, each counted over every KEPT notehead box:

  (a) TWIN of a refused slash: the box lies (>= 0.8 of the SMALLER box) inside a box this tree already refused
      as `tremolo_slash_crosses_stem` -- it is the same ink the slash refusal already named.
  (b) SLASH, BLOCKED ONLY BY POSITION: the 2.49 shape and crossing tests both pass and only the "away from both
      stem ends" test fails (a slash near the TIP, which a head cannot occupy).
  (c) CROSS-CLASS DUPLICATE: another box of a different class lies on the same stem at IoU >= 0.5.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_p2_refusals.py DOC RECORD.json
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location(
    "l278_p2_arm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "l278_p2_arm.py"))
arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arm)


def _box(g):
    x0, y0, x1, y1 = g.box_canon
    return (x0, y0, x1 - x0, y1 - y0)


def _inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def main(argv=None):
    from tools.omr.staged import readout
    doc, rec = argv[0], argv[1]
    judged = {}
    man = json.load(open("out/print/2.78-review/manifest.json"))
    answers = json.load(open("out/print/2.78-review/answers.json"))
    for t in man["tiles"]:
        for h in t["subject"]:
            judged[h] = (t["n"], answers[str(t["n"])])
    run_old, run_new, _ = arm.readjudicate(rec)
    notes = {k: g for k, g in run_new.glyphs.items() if g.family == "note" and g.box_canon}
    kept = {k: g for k, g in notes.items() if arm._kept(run_new, g)}
    refused_slash = {}
    for k, g in notes.items():
        v = run_new.standing(k, "notehead_is_not_a_notehead", "ADJUDICATE")
        if v and v["outcome"] == "decided" and v.get("value") is True \
                and v["reason"] == "tremolo_slash_crosses_stem":
            refused_slash[k] = g
    twins, blocked, cross = [], [], []
    for k, g in kept.items():
        b = _box(g)
        for rk, rg in refused_slash.items():
            if rg.cell_key != g.cell_key or rk == k:
                continue
            rb = _box(rg)
            small = min(b[2] * b[3], rb[2] * rb[3])
            if small > 0 and _inter(b, rb) / small >= 0.8:
                twins.append((k, rk))
                break
        v = run_new.standing(k, "notehead_is_not_a_notehead", "ADJUDICATE")
        sig = ((v or {}).get("detail") or {}).get("tremolo_slash_signal") or {}
        if sig.get("shape_ok") and sig.get("crossing_ok") and sig.get("position_ok") is False:
            blocked.append(k)
        sv = run_new.standing(k, "head_stem", "ADJUDICATE")
        stem = sv.get("value") if sv and sv["outcome"] == "decided" else None
        if stem:
            for ok, og in kept.items():
                if ok == k or og.cell_key != g.cell_key or og.cls == g.cls:
                    continue
                ov = run_new.standing(ok, "head_stem", "ADJUDICATE")
                if not ov or ov["outcome"] != "decided" or ov.get("value") != stem:
                    continue
                ob = _box(og)
                inter = _inter(b, ob)
                union = b[2] * b[3] + ob[2] * ob[3] - inter
                if union > 0 and inter / union >= 0.5 and k < ok:
                    cross.append((k, ok))
    def tag(k):
        j = judged.get(k)
        return f"T{j[0]}" if j else "-"
    print(f"{doc}: kept notehead boxes {len(kept)}; refused-as-slash boxes {len(refused_slash)}")
    print(f"  (a) twins of a refused slash box: {len(twins)}:", [(k, tag(k)) for k, _ in twins])
    print(f"  (b) slash shape+crossing pass, ONLY position fails: {len(blocked)}:", [(k, tag(k)) for k in blocked])
    print(f"  (c) cross-class duplicates on one stem (IoU >= 0.5): {len(cross)}:",
          [(a, b, tag(a), tag(b)) for a, b in cross])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
