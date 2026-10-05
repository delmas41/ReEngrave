#!/usr/bin/env python3
"""lane-standard-box-hollow (2026-10-04): S2 (control) vs S2H = S2 with the
head's white counter FILLED (open ring closed first) before the template's
free search and before the fit gate's IoU. The reader still reads the ORIGINAL
page; only the BOX (and the gate) change. Filled heads: the same `gray`
object, so S2H == S2 on them by construction -- checked below (box + read
identical for every head with no pocket).

    python3 benchmarks/omr-local-staff-2026-09/score_standard_box_hollow.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
import score_standard_box as S  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
import edge_census as ec  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402
from tools.omr.annotate import standard_head_box as shb  # noqa: E402

SEAN = {"glyph/3/0/0/6/2": [-6]}      # Sean 2026-10-04 (the reference says -4)


def standard_hollow(h, D):
    """Like `S.standard_for`, on the counter-filled page."""
    shp, tm = D["shapes"][h["page"]], D["tmpl"][h["page"]]
    thick = D["thick"][h["page"]]
    gray_f, info = shb.fill_counter(h["gray"], h["box"], h["spacing"], thick,
                                    shp["height_sp"], shp["width_sp"], h["kind"] == "hollow")
    others = [b for (s, b) in D["nh"].get(h["page"], []) if s != h["subject"]] \
        + [b for (_s, b) in D["acc"].get(h["page"], [])]
    st = shb.standard_head_box(gray_f, h["box"], h["spacing"], tm, shp, h["kind"], others)
    poly = ht.geometry_outline_poly(st["centre"][0], st["centre"][1], h["spacing"],
                                    shp["tilt_deg"], shp["width_sp"], shp["height_sp"])
    chk = S.r7.oval_vs_ink(gray_f, h["box"], h["spacing"], thick, list(h["lines"]), poly,
                           st["centre"][0], st["centre"][1])
    iou, off = chk["iou_open"], chk["offset_open_sp"]
    st["fit"] = dict(iou_open=iou, offset_open_sp=off)
    st["pass"] = bool(st["placed"] and off is not None and iou >= shb.FIT_IOU_MIN
                      and off <= shb.FIT_OFFSET_MAX_SPACES)
    st["pockets"] = info["pockets"]
    st["filled_same_object"] = gray_f is h["gray"]
    st["info"] = {k: info[k] for k in ("close_diameter", "r_cap", "r_floor") if k in info}
    return st


def main():
    res, Ds = {}, {}
    for d in ts.DOCS:
        D = S.build(d)
        Ds[d] = D
        out = {}
        for h in D["far"]:
            s2 = S.standard_for(h, D)
            s2h = standard_hollow(h, D)
            row = dict(s2=s2, s2h=s2h, truth=h["truth"], kind=h["kind"], cls=h["cls"], reads={})
            for arm, box in (("S0", h["box"]),
                             ("S2", s2["box"] if s2["pass"] else h["box"]),
                             ("S2H", s2h["box"] if s2h["pass"] else h["box"])):
                pos, reason = S.read(h, box, **S.READER)
                row["reads"][arm] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                         box=[round(float(v), 2) for v in box])
            out[h["subject"]] = row
        res[d] = out
    for excl, label in ((set(), "n=44/11"), (S.WRONG_REFERENCE, "n=43/11 (3/0/0/6/2 out)")):
        print("==", label)
        for arm in ("S0", "S2", "S2H"):
            for d in ts.DOCS:
                vs = [r["reads"][arm]["v"] for s, r in res[d].items() if s not in excl]
                print(f"{arm:4}{d:20} {ec.tally(vs)} n={len(vs)}")
    # against Sean's own readings
    print("== against Sean (3/0/0/6/2 = -6), n=44")
    for arm in ("S0", "S2", "S2H"):
        vs = []
        for s, r in res["beethoven5-litolff"].items():
            tr = SEAN.get(s, r["truth"])
            vs.append(ec.verdict(r["reads"][arm]["pos"], tr))
        print(arm, ec.tally(vs))
    print("\n-- S2H vs S2: every changed head --")
    for d in ts.DOCS:
        for s, r in res[d].items():
            o, n = r["reads"]["S2"], r["reads"]["S2H"]
            if (o["pos"], o["v"], o["box"]) != (n["pos"], n["v"], n["box"]):
                print(f"{d[:6]} {s:17} {o['pos']!s:>5} {o['v']:7} -> {n['pos']!s:>5} {n['v']:7} ref={r['truth']}"
                      f" kind={r['kind']} fit {r['s2']['fit']['iou_open']}/{r['s2']['fit']['offset_open_sp']}"
                      f" -> {r['s2h']['fit']['iou_open']}/{r['s2h']['fit']['offset_open_sp']} pass {r['s2']['pass']}->{r['s2h']['pass']}"
                      f" pockets={[p['area'] for p in r['s2h']['pockets']]} | {n['reason'][:90]}")
        print(d[:6], "right broken S2H vs S2:", [s for s, r in res[d].items()
              if r["reads"]["S2"]["v"] == "right" and r["reads"]["S2H"]["v"] != "right"],
              "| right broken S2H vs S0:", [s for s, r in res[d].items()
              if r["reads"]["S0"]["v"] == "right" and r["reads"]["S2H"]["v"] != "right"])
    print("\n-- heads with a pocket (counter found) --")
    for d in ts.DOCS:
        for s, r in res[d].items():
            if r["s2h"]["pockets"]:
                print(d[:6], s, r["cls"][-14:], r["kind"], r["s2h"]["pockets"], r["s2h"]["info"],
                      f"fit {r['s2']['fit']['iou_open']}/{r['s2']['fit']['offset_open_sp']} -> {r['s2h']['fit']['iou_open']}/{r['s2h']['fit']['offset_open_sp']}",
                      "pass", r["s2"]["pass"], "->", r["s2h"]["pass"])
    print("\n-- filled-head invariance: heads with NO pocket must equal S2 exactly --")
    bad = []
    n = 0
    for d in ts.DOCS:
        for s, r in res[d].items():
            if not r["s2h"]["pockets"]:
                n += 1
                same = (r["s2h"]["filled_same_object"]
                        and r["s2h"]["box"] == r["s2"]["box"] and r["s2h"]["pass"] == r["s2"]["pass"]
                        and r["reads"]["S2H"] == r["reads"]["S2"])
                if not same:
                    bad.append(s)
    print(f"no-pocket heads {n}, not identical: {bad}")
    gp = {d: (sum(r["s2h"]["pass"] for r in res[d].values()), len(res[d])) for d in ts.DOCS}
    print("gate pass S2H:", gp, "| S2:", {d: sum(r["s2"]["pass"] for r in res[d].values()) for d in ts.DOCS})
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(S._clean(res), indent=1, default=str))
    return Ds, res


if __name__ == "__main__":
    main()
