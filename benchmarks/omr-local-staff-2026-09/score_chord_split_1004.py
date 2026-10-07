#!/usr/bin/env python3
"""lane-chord-blob-split (2026-10-04): arm E4 = E3 + the chord-blob split
(`ledger_grid.split_chord_blob`, a pure function; the harness decides where to
call it) scored on the 2.44c truth sets, STAFF POSITION against the reference,
exactly as `score_combined_1004.py`.

  E4raw  every far head whose blob is laid over by exactly TWO detector boxes
         and whose ink run is > 1.6 standard heads takes the split box (the
         trigger as first specified)
  E4     E4raw + the boxes-must-overprint gate (pre-set 0.2 sp; two standard
         heads a third apart abut at ~0.05 sp, so detector boxes that overlap
         more are oversize boxes on one blob)

The partner's entry in the page box list is replaced too (it is the partner's
exclusion / third-stack input).  Every other head is the E3 read, byte for
byte.  Also: how often the split fires on every in-staff head of the two pages
and on every far head, per gate variant.

    python3 benchmarks/omr-local-staff-2026-09/score_chord_split_1004.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_combined_1004 as c  # noqa: E402
import score_exclusion as se  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OVERPRINT_SP = 0.2   # pre-set: two standard heads a third apart abut (~0.05 sp)


THROUGH = dict(through_head_on_rung=True)


def same_staff(a, b):
    """glyph/<page>/<system>/<staff>/<cell>/<i>: the first four fields."""
    return a.split("/")[:4] == b.split("/")[:4]


def blob_for(h, D, overprint=None):
    """(subjects, cluster boxes, split result) for a far head."""
    page = h["page"]
    shp = D["shapes"][page]
    others = [(s, b) for (s, b) in D["nh"].get(page, [])
              if s != h["subject"] and same_staff(s, h["subject"])]
    cl = lg.chord_blob_cluster(h["box"], [b for (_s, b) in others])
    clset = set(cl[1:])
    subs = [h["subject"]] + [s for (s, b) in others if tuple(b) in clset]
    res = lg.split_chord_blob(h["gray"], cl, h["spacing"], shp["width_sp"],
                              shp["height_sp"], shp["tilt_deg"],
                              exclude_boxes=[b for (s, b) in others if s not in subs],
                              staff_span=(min(h["lines"]), max(h["lines"])),
                              min_box_overprint_sp=overprint)
    return subs, cl, res


def e4_reads(D, e3_boxes, overprint=None, **extra):
    """{subject: dict(pos, reason, v, box, split)} for every far head."""
    out = {}
    for h in D["far"]:
        subs, cl, res = blob_for(h, D, overprint)
        base = dict(h, box=tuple(e3_boxes[h["subject"]]))   # the E3 box unless split
        split = None
        if res.get("split") and len(cl) == 2:
            order = sorted(range(2), key=lambda i: (cl[i][1] + cl[i][3]) / 2.0)
            mine = order.index(0)
            new = {subs[order[0]]: res["boxes"][0], subs[order[1]]: res["boxes"][1]}
            base["box"] = tuple(res["boxes"][mine])
            # the blob's other head is part of THIS head's own ink: its ledgers
            # (a bar through its bottom edge) are shared, so it is not blanked
            base["boxes"] = [(s, b) for (s, b) in h["boxes"] if s not in new]
            base["_kw"] = dict(chord_split_rungs_y=res["rungs_y"])
            split = dict(rung_y=round(res["rung_y"], 1), confirmed=res["rung_confirmed"],
                         source=res["rung_source"],
                         extent_sp=round(res["extent_sp"], 2), partner=subs[1])
        elif res.get("split"):
            split = dict(declined="cluster_of_%d_boxes" % len(cl))
        pos, reason = se.read(base, **{**c.EXC, **extra, **base.pop("_kw", {})})
        out[h["subject"]] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                 box=[round(float(v), 1) for v in base["box"]], split=split)
    return out


VARIANTS = {   # name -> (staff gate, overprint gate)
    "raw (trigger as specified: ink run > 1.6 std heads)": (False, None),
    "far only": (True, None),
    "far + boxes overprint >= %.2f sp" % OVERPRINT_SP: (True, OVERPRINT_SP),
}


def trigger_census(D):
    """(fired, n, rows) per (population, variant): how often the split FIRES
    over every in-staff head of the page set and every far head."""
    out = {}
    for key, heads in (("in_staff", D["heads_in"]), ("far", D["far"])):
        for vname, (gate, ov) in VARIANTS.items():
            n, fired, rows = 0, 0, []
            for h in heads:
                page = h["page"]
                shp = D["shapes"][page]
                lines = h.get("lines") or h.get("global_lines")
                sp = h.get("spacing") or (max(lines) - min(lines)) / 4.0
                others = [b for (s, b) in D["nh"].get(page, [])
                          if s != h["subject"] and same_staff(s, h["subject"])]
                cl = lg.chord_blob_cluster(h["box"], others)
                res = lg.split_chord_blob(
                    D["pages"].get(page), cl, sp, shp["width_sp"], shp["height_sp"],
                    shp["tilt_deg"], staff_span=(min(lines), max(lines)) if gate else None,
                    min_box_overprint_sp=ov)
                n += 1
                if res.get("split"):
                    fired += 1
                    rows.append((h["subject"], len(cl), round(res["extent_sp"], 2)))
            out[(key, vname)] = (fired, n, rows)
    return out


def through_head_census(D):
    """How often `through_head_on_rung_evidence` WOULD fire on every in-staff
    head of the page (the reader asks it for far heads only; here it is asked
    of each staff line crossing the box, on both sides -- an UPPER bound of
    the heads it could ever claim). Returns (fired, n, rows)."""
    fired, n, rows = 0, 0, []
    for h in D["heads_in"]:
        lines = h.get("lines") or h.get("global_lines")
        gray = h.get("gray")
        if gray is None:
            gray = D["pages"].get(h["page"])
        sp = h.get("spacing") or (max(lines) - min(lines)) / 4.0
        x0, y0, x1, y1 = h["box"]
        n += 1
        hit = None
        for y in (yy for yy in lines if y0 <= yy <= y1):
            for sg in (-1.0, 1.0):
                ev = lg.through_head_on_rung_evidence(gray, y, h["box"], sg, sp)
                if ev["ok"]:
                    hit = (h["subject"], round(y), sg, round(ev["frac_stf"], 3))
        if hit:
            fired += 1
            rows.append(hit)
    return fired, n, rows


def main():
    base_res = c.run()[1]
    arms = {"E4raw": None, "E4": OVERPRINT_SP, "E5": OVERPRINT_SP}
    e4, census, through_census = {}, {}, {}
    for d in ts.DOCS:
        D = c.sb.build(d)
        e3b = {s: r["reads"]["E3"]["box"] for s, r in base_res[d].items()}
        e4[d] = {a: e4_reads(D, e3b, ov, **(THROUGH if a == "E5" else {}))
                 for a, ov in arms.items()}
        census[d] = trigger_census(D)
        through_census[d] = through_head_census(D)
    print("== E3 (control) vs E4raw vs E4")
    for d in ts.DOCS:
        print(f"E3    {d:20} {ec.tally([r['reads']['E3']['v'] for r in base_res[d].values()])}")
        for a in arms:
            print(f"{a:5} {d:20} {ec.tally([e4[d][a][s]['v'] for s in base_res[d]])}")
    for a in ["E3"] + list(arms):
        def g(s, a=a):
            return base_res[c.LIT][s]["reads"]["E3"]["pos"] if a == "E3" else e4[c.LIT][a][s]["pos"]
        print(f"vs Sean (3/0/0/6/2=-6) {a}:",
              ec.tally([ec.verdict(g(s), c.SEAN.get(s, base_res[c.LIT][s]["truth"]))
                        for s in base_res[c.LIT]]))
    for a in arms:
        print(f"\n-- {a}: every head whose read differs from E3, or that was split")
        broken = []
        for d in ts.DOCS:
            for s, r in base_res[d].items():
                o, n = r["reads"]["E3"], e4[d][a][s]
                if (o["pos"], o["v"]) != (n["pos"], n["v"]) or n["split"]:
                    print(f"{d[:6]} {s:18} {o['pos']!s:>4} {o['v']:7} -> {n['pos']!s:>4} {n['v']:7} "
                          f"ref={r['truth']} split={n['split']} | {n['reason'][:90]}")
                if o["v"] == "right" and n["v"] != "right":
                    broken.append(s)
        print(f"{a} right heads broken vs E3:", broken)
    print("\n== through-head rule: in-staff heads it could fire on (upper bound), and far heads it DID fire on")
    for d in ts.DOCS:
        f, n, rows = through_census[d]
        print(f"{d[:8]} in-staff: {f} / {n}")
        for r in rows[:15]:
            print("      ", r)
        fired = [s for s, r in e4[d]["E5"].items() if "runs through the head" in r["reason"]]
        print(f"{d[:8]} far heads where the rule fired: {fired}")
    print("\n== trigger census: split fires / heads")
    for d in ts.DOCS:
        for (key, vname), (fired, n, rows) in census[d].items():
            print(f"{d[:8]} {key:9} [{vname}]: {fired} / {n}")
            if key == "far" or (fired and fired < 12):
                for r in rows:
                    print("      ", r)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(dict(e4=e4, census={d: {f"{k[0]}|{k[1]}": v for k, v in cs.items()}
                                           for d, cs in census.items()}), indent=1, default=str))


if __name__ == "__main__":
    main()
