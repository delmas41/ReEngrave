"""ROADMAP 2.78 Phase 2 -- the pool of NEW blind tiles: stems whose decision CHANGED, none of Sean's 14.

PATH: STAGED, GATHER + ADJUDICATE only. Reads `l278_p2_arm.py`'s output (`--out`), builds the two files
`l278_tiles.py` takes (`--pop`, `--select`), and prints the pool by cause so the choice is on the page.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_p2_tiles_pool.py \
        --arm lit_B=ARM.json --arm lit_X=ARM.json --arm brahms_X=ARM.json --out-dir DIR [--n 10]

A label is `<doc>_<tag>` (the tag keeps two records of one document apart: stem row ids restart per record).

A change is one of (a stem can be several): LEVELS (the beams/flags now read from the stem's tip), DOTS (the
stem's dot reaches a head that lacked it), BASE (a hollow head's half now holds the stem, or the reverse),
NARROWED->DECIDED, DECIDED->NARROWED, WHOLE (a whole-class box takes the stem's value). The pool is chosen
round-robin over those causes, alternating documents, then TWO controls are added: stems whose heads all agreed
before and after (one beamed, one hollow), so a judge who calls everything changed is caught.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("l278_p2_arm", os.path.join(HERE, "l278_p2_arm.py"))
arm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(arm)


def _first(s):
    v = arm._vals(s)
    return next(iter(v)) if v and len(v) == 1 else None


def causes(stem):
    out = set()
    for h in stem["heads"]:
        a, b = h["own"], h["stem_value"]
        if arm._vals(a) == arm._vals(b):
            continue
        av, bv = arm._vals(a), arm._vals(b)
        if a and a["outcome"] == "narrowed" and b and b["outcome"] == "decided":
            out.add("NARROWED_TO_DECIDED")
        if a and a["outcome"] == "decided" and b and b["outcome"] == "narrowed":
            out.add("DECIDED_TO_NARROWED")
        if "whole" in h["cls"].lower():
            out.add("WHOLE")
        if av and bv and len(av) == 1 and len(bv) == 1:
            x, y = next(iter(av)), next(iter(bv))
            if x[1] != y[1]:
                out.add("DOTS")
            if x[2] != y[2]:
                out.add("LEVELS")
            fill = lambda t: (t[0] * 2 ** t[2] / (2.0 - 2.0 ** (-t[1]))) >= 1.99
            if fill(x) != fill(y):
                out.add("BASE")
    return out


def affine(heads):
    sols = []
    for h in heads:
        if not (h.get("box_canon") and h.get("box_page")):
            continue
        cx0, cy0, cx1, cy1 = h["box_canon"]
        px0, py0, px1, py1 = h["box_page"]
        if px1 - px0 <= 0 or cx1 - cx0 <= 0:
            continue
        up = (cx1 - cx0) / (px1 - px0)
        sols.append((px0 - cx0 / up, py0 - cy0 / up, up))
    if not sols:
        return None
    return tuple(statistics.median(s[i] for s in sols) for i in range(3))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--manifest", default="out/print/2.78-review/manifest.json")
    a = ap.parse_args(argv)
    judged = set()
    for t in json.load(open(a.manifest))["tiles"]:
        judged.update(t["subject"])
    os.makedirs(a.out_dir, exist_ok=True)
    pool = {}      # cause -> [(doc, stem dict)]
    controls = []
    pops = {}
    for spec in a.arm:
        doc, path = spec.split("=", 1)
        d = json.load(open(path))
        groups = []
        for st in d["tables"]["stems"]:
            keys = {h["key"] for h in st["heads"]}
            if keys & judged:
                continue
            aff = affine(st["heads"])
            if aff is None:
                continue
            ox, oy, up = aff
            sb = st.get("stem_box")
            row = {"stem": st["stem"], "page": st["page"], "primary": "", "sub": "",
                   "heads": [{"key": h["key"], "cls": h["cls"], "box_page": h["box_page"],
                              "outcome": (h["own"] or {}).get("outcome"), "reason": (h["own"] or {}).get("reason"),
                              "vals": [list(v) for v in sorted(arm._vals(h["own"]) or ())],
                              "after": {"outcome": (h["stem_value"] or {}).get("outcome"),
                                        "reason": (h["stem_value"] or {}).get("reason"),
                                        "vals": [list(v) for v in sorted(arm._vals(h["stem_value"]) or ())]}}
                             for h in st["heads"]]}
            if sb:
                x, y, w, h_ = sb
                row["stem_box_page"] = [ox + x / up, oy + y / up, ox + (x + w) / up, oy + (y + h_) / up]
            cs = causes(st)
            row["primary"] = "changed" if st["changed"] else "unchanged"
            row["sub"] = "+".join(sorted(cs))
            groups.append(row)
            if st["changed"]:
                for c in sorted(cs) or ["OTHER"]:
                    pool.setdefault(c, []).append((doc, row))
            else:
                vals = {tuple(v) for h in row["heads"] for v in h["vals"]}
                if len(row["heads"]) >= 2 and len(vals) == 1:
                    controls.append((doc, row, next(iter(vals))))
        pops[doc] = groups
        json.dump({doc: {"groups": groups}}, open(os.path.join(a.out_dir, f"pool-{doc}.json"), "w"))
    print("changed-decision stems (none of the 14), by cause (a stem may count under several):")
    for c, items in sorted(pool.items()):
        print(f"   {c:<22}{len(items):>4}   lit {sum(1 for d, _ in items if d.startswith('lit'))}  brahms {sum(1 for d, _ in items if d.startswith('brahms'))}")
    picked, seen = [], set()
    order = ["LEVELS", "DOTS", "BASE", "NARROWED_TO_DECIDED", "DECIDED_TO_NARROWED", "WHOLE", "OTHER"]
    turn = 0
    while len(picked) < a.n and any(pool.get(c) for c in order):
        progressed = False
        for c in order:
            for doc_pref in (("lit", "brahms") if turn % 2 == 0 else ("brahms", "lit")):
                cand = [(d, r) for d, r in pool.get(c, []) if d.startswith(doc_pref) and (d, r["stem"]) not in seen]
                if cand and len(picked) < a.n:
                    d, r = cand[0]
                    seen.add((d, r["stem"]))
                    picked.append((d, r, c))
                    progressed = True
                    break
        turn += 1
        if not progressed:
            break
    sel = [{"doc": d, "stem": r["stem"], "note": f"CHANGED ({c}): " + ", ".join(
        f"{h['key'].split('/', 2)[2]} {h['cls'].replace('notehead', '')} {h['vals']} -> {h['after']['vals']}" for h in r["heads"])}
        for d, r, c in picked]
    # two controls: one beamed (levels > 0), one hollow
    for want in ("beamed", "hollow"):
        for d, r, v in controls:
            beamed = v[2] > 0
            hollow = (v[0] * 2 ** v[2] / (2.0 - 2.0 ** (-v[1]))) >= 1.99
            if (want == "beamed" and beamed) or (want == "hollow" and hollow and not beamed):
                if (d, r["stem"]) not in seen:
                    seen.add((d, r["stem"]))
                    sel.append({"doc": d, "stem": r["stem"], "note": f"CONTROL unchanged ({want}): all heads {v}"})
                    break
    json.dump(sel, open(os.path.join(a.out_dir, "selection.json"), "w"), indent=1)
    print(f"\nselection ({len(sel)}): {os.path.join(a.out_dir, 'selection.json')}")
    for s in sel:
        print("  ", s["doc"], s["stem"], s["note"][:150])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
