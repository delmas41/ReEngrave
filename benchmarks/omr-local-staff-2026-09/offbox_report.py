"""lane-offbox-check: tabulate `offbox_check.py`'s output. Control first (the check must FAIL on a shifted reference
and PASS the references), then the census of every decided far head, reader and geometry.

  python3 offbox_report.py <offbox.json>
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C
import overnight_1004_report as R


def pct(a, b):
    return f"{a}/{b} ({100.0 * a / b:.1f}%)" if b else "0/0"


def matched(truth, heads):
    out, miss = [], 0
    for h in truth:
        best, bi = None, 0.0
        for s, g in heads.items():
            if R.page_of(s) != h["page"]:
                continue
            v = R.iou(h["box"], g["box"])
            if v > bi:
                best, bi = (s, g), v
        if bi >= R.IOU_MIN:
            out.append((h, best[0], best[1]))
        else:
            miss += 1
    return out, miss


def dist(steps):
    c = collections.Counter("none" if s is None else (s if s < 3 else "3+") for s in steps)
    return {str(k): c[k] for k in (1, 2, "3+", "none")}


def main(path):
    res = json.loads(Path(path).read_text())
    print(f"constants (fixed before looking): BAND={C.BAND} (central {int(C.BAND*100)}% of box height), EDGE_TOL={C.EDGE_TOL} sp\n")
    out = {}
    for doc, D in res.items():
        print("=" * 100)
        print(doc, " local staff lines used / global fallback:", D["lines_source"])
        for run in ("RUN1", "RUN2"):
            H = D["heads"][run]
            print(f"\n--- {doc} {run}: far heads {len(H)}")
            # ---------------- CONTROL: references and shifts, on the matched truth-set heads
            M, miss = matched(D["truth"], H)
            ref_ok = shift = 0
            sh_flag = collections.Counter()
            n_sh = collections.Counter()
            for (h, s, g) in M:
                t = h["truth"][0]
                ref_ok += C.passes(t, g["box"], g["lines"])
                for dlt in (-2, -1, 1, 2):
                    n_sh[dlt] += 1
                    sh_flag[dlt] += (not C.passes(t + dlt, g["box"], g["lines"]))
            print(f"  CONTROL truth-set heads matched {len(M)} of {len(D['truth'])} (unmatched {miss}).")
            print(f"    references PASS the check: {pct(ref_ok, len(M))}")
            for dlt in (-1, 1, -2, 2):
                print(f"    reference {dlt:+d} step FLAGGED off-box: {pct(sh_flag[dlt], n_sh[dlt])}")
            both = sum(1 for (h, s, g) in M if not C.passes(h["truth"][0] - 1, g["box"], g["lines"])
                       and not C.passes(h["truth"][0] + 1, g["box"], g["lines"]))
            print(f"    both +-1 shifts flagged: {pct(both, len(M))}")
            failing_refs = [(s, h["truth"][0], g["box_source"], C.off_steps(h["truth"][0], g["box"], g["lines"])) for (h, s, g) in M
                            if not C.passes(h["truth"][0], g["box"], g["lines"])]
            print("    references that FAIL:", failing_refs)
            # right/wrong cross-tab on the truth set
            xt = collections.Counter()
            for (h, s, g) in M:
                t = set(h["truth"])
                if g["dec"] is None:
                    xt["reader undecided"] += 1
                else:
                    ok = C.passes(g["dec"], g["box"], g["lines"])
                    xt[("reader right" if g["dec"] in t else "reader wrong", "ON" if ok else "OFF")] += 1
                ok = C.passes(g["geo"], g["box"], g["lines"])
                xt[("geo right" if g["geo"] in t else "geo wrong", "ON" if ok else "OFF")] += 1
            print("    truth-set cross-tab (answer right/wrong x check ON/OFF):", dict(xt))
            # ---------------- census of decided far heads
            dec = {s: g for s, g in H.items() if g["dec"] is not None}
            print(f"  decided far heads: {len(dec)}   reasons {dict(collections.Counter(g['reason'] for g in dec.values()))}")
            rd_off, ge_off = [], []
            rd_on = ge_on = 0
            for s, g in dec.items():
                a = C.off_steps(g["dec"], g["box"], g["lines"])
                b = C.off_steps(g["geo"], g["box"], g["lines"])
                if a == 0:
                    rd_on += 1
                else:
                    rd_off.append(a)
                if b == 0:
                    ge_on += 1
                else:
                    ge_off.append(b)
            n = len(dec)
            print(f"  READER   ON the box {pct(rd_on, n)}   OFF {pct(len(rd_off), n)}   steps off {dist(rd_off)}")
            print(f"  GEOMETRY ON the box {pct(ge_on, n)}   OFF {pct(len(ge_off), n)}   steps off {dist(ge_off)}")
            both_on = sum(1 for g in dec.values() if C.passes(g["dec"], g["box"], g["lines"]) and C.passes(g["geo"], g["box"], g["lines"]))
            only_r = sum(1 for g in dec.values() if C.passes(g["dec"], g["box"], g["lines"]) and not C.passes(g["geo"], g["box"], g["lines"]))
            only_g = sum(1 for g in dec.values() if not C.passes(g["dec"], g["box"], g["lines"]) and C.passes(g["geo"], g["box"], g["lines"]))
            neither = n - both_on - only_r - only_g
            print(f"  both ON {both_on}  only reader ON {only_r}  only geometry ON {only_g}  neither {neither}")
            agree = [g for g in dec.values() if g["dec"] == g["geo"]]
            dis = [g for g in dec.values() if g["dec"] != g["geo"]]
            for nm, grp in (("reader==geometry", agree), ("reader!=geometry", dis)):
                k = sum(1 for g in grp if C.passes(g["dec"], g["box"], g["lines"]))
                print(f"    {nm}: {len(grp)} heads, reader answer ON {pct(k, len(grp))}")
            for src in sorted({str(g["box_source"]) for g in dec.values()}):
                grp = [g for g in dec.values() if str(g["box_source"]) == src]
                k = sum(1 for g in grp if C.passes(g["dec"], g["box"], g["lines"]))
                kg = sum(1 for g in grp if C.passes(g["geo"], g["box"], g["lines"]))
                print(f"    box_source {src}: {len(grp)} heads, reader ON {pct(k, len(grp))}, geometry ON {pct(kg, len(grp))}")
            side = collections.Counter()
            for g in dec.values():
                if not C.passes(g["dec"], g["box"], g["lines"]):
                    side[("above" if g["dec"] < 4 else "below") + ("/even" if g["dec"] % 2 == 0 else "/odd")] += 1
            print("    reader OFF by side/kind of answer:", dict(side))
            out[f"{doc}|{run}"] = dict(decided=n, reader_on=rd_on, reader_off=len(rd_off), reader_steps=dist(rd_off),
                                       geo_on=ge_on, geo_off=len(ge_off), geo_steps=dist(ge_off),
                                       ref_pass=ref_ok, ref_n=len(M), both_on=both_on, only_reader_on=only_r,
                                       only_geo_on=only_g, neither=neither)
    Path(path).with_suffix(".summary.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
