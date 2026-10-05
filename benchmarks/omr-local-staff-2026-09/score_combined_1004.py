#!/usr/bin/env python3
"""lane-farhead-combined-1004 (2026-10-04): today's far-head pieces COMBINED on
one tree, scored together on the 2.44c truth sets (Litolff n=44, Brahms n=11;
`glyph/1/0/10/14/1` excluded by the loader).  STAFF POSITION against the
reference; `glyph/3/0/0/6/2`'s reference (-4) is wrong -- Sean says -6 -- so
every Litolff tally is printed as scored AND "vs Sean".

Arms (cumulative; every piece is a default-OFF keyword):
  M0  main: near_edge_ledgers + restore_masked_near_edge + far_side_ledger,
      detector box                                   (control: 32/10/2, 11/0/0)
  E1  M0 + exclusion rules: connected_continuation + same-ink-other-staff +
      one-sided jut + drop-rungs-beyond-head          (control: 36/6/2, 11/0/0)
  E2  E1 + the STANDARD head box where its pre-set fit gate passes (S2)
  E3  E2 with the counter filled before the template search/gate (S2H)
                                       (S2H alone, on M0: 36/7/1, 11/0/0)

    python3 benchmarks/omr-local-staff-2026-09/score_combined_1004.py [--json f]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_exclusion as se  # noqa: E402
import score_standard_box as sb  # noqa: E402
import score_standard_box_hollow as sbh  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

SEAN = {"glyph/3/0/0/6/2": [-6]}
EXC = se.ARMS["conn+same+one+drop"]
ARMS = ["M0", "E1", "E2", "E3"]
LIT = "beethoven5-litolff"


def kw_of(arm):
    return {} if arm == "M0" else EXC


def box_of(arm, h, s2, s2h):
    if arm in ("M0", "E1"):
        return tuple(h["box"])
    st = s2 if arm == "E2" else s2h
    return tuple(st["box"]) if st["pass"] else tuple(h["box"])


def run():
    res, Ds = {}, {}
    for d in ts.DOCS:
        D = sb.build(d)
        Ds[d] = D
        res[d] = {}
        for h in D["far"]:
            s2 = sb.standard_for(h, D)
            s2h = sbh.standard_hollow(h, D)
            row = dict(truth=h["truth"], kind=h["kind"], cls=h["cls"], s2=s2, s2h=s2h, reads={})
            for arm in ARMS:
                box = box_of(arm, h, s2, s2h)
                pos, reason = se.read(dict(h, box=box), **kw_of(arm))
                row["reads"][arm] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                         box=[round(float(v), 2) for v in box],
                                         std_used=box != tuple(h["box"]))
            res[d][h["subject"]] = row
    return Ds, res


def tallies(res):
    out = {}
    for arm in ARMS:
        for d in ts.DOCS:
            vs = [r["reads"][arm]["v"] for r in res[d].values()]
            out[(arm, d)] = (ec.tally(vs), len(vs))
    return out


def sean_tally(res, arm):
    vs = []
    for s, r in res[LIT].items():
        vs.append(ec.verdict(r["reads"][arm]["pos"], SEAN.get(s, r["truth"])))
    return ec.tally(vs)


def main():
    Ds, res = run()
    print("== step tables (as scored; n=44 / n=11)")
    for arm in ARMS:
        for d in ts.DOCS:
            vs = [r["reads"][arm]["v"] for r in res[d].values()]
            print(f"{arm}  {d:20} {ec.tally(vs)} n={len(vs)}")
        print(f"{arm}  vs Sean (3/0/0/6/2 = -6), Litolff n=44: {sean_tally(res, arm)}")
    print()
    for a, b in zip(ARMS, ARMS[1:]):
        print(f"--- {b} vs {a}: every changed head")
        for d in ts.DOCS:
            for s, r in res[d].items():
                o, n = r["reads"][a], r["reads"][b]
                if (o["pos"], o["v"], o["box"]) != (n["pos"], n["v"], n["box"]):
                    why = ""
                    if b in ("E2", "E3"):
                        st = r["s2"] if b == "E2" else r["s2h"]
                        why = (f"gate {'PASS' if st['pass'] else 'fail'} iou {st['fit']['iou_open']} "
                               f"off {st['fit']['offset_open_sp']}; ")
                    print(f"{d[:6]} {s:18} {o['pos']!s:>4} {o['v']:7} -> {n['pos']!s:>4} {n['v']:7} "
                          f"ref={r['truth']} kind={r['kind']} {why}{n['reason'][:120]}")
        print("right heads broken:", [s for d in ts.DOCS for s, r in res[d].items()
                                      if r["reads"][a]["v"] == "right" and r["reads"][b]["v"] != "right"])
        print()
    print("--- right heads broken E3 vs M0:", [s for d in ts.DOCS for s, r in res[d].items()
          if r["reads"]["M0"]["v"] == "right" and r["reads"]["E3"]["v"] != "right"])
    print("\n== remaining wrong/undecided after E3 (reference shown; Sean's -6 for 3/0/0/6/2)")
    for d in ts.DOCS:
        for s, r in res[d].items():
            e = r["reads"]["E3"]
            tr = SEAN.get(s, r["truth"]) if d == LIT else r["truth"]
            if ec.verdict(e["pos"], tr) != "right":
                print(f"{d[:6]} {s:18} we={e['pos']!s:>4} ref={tr} ({ec.verdict(e['pos'], tr)})"
                      f" kind={r['kind']} cls={r['cls'][-16:]} std_box={e['std_used']} | {e['reason']}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(sb._clean(res), indent=1, default=str))
    return Ds, res


if __name__ == "__main__":
    main()
