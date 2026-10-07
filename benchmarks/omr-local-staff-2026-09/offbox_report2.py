"""lane-offbox-check: the check with the reader's MEASURED ledger rows (offbox_measured.py's replay), falling back to the
grid only where no replay exists. Control first, then the census.

  python3 offbox_report2.py <offbox.json (grid pass)> <dir with m_RUN{1,2}_<doc>.json> [--json out]
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C
import offbox_report as O
import overnight_1004_report as R

pct = O.pct


def rows_for(g, m):
    """Rows for one head: measured when the replay reproduced the record, else the grid (flag returned)."""
    if m is not None and m.get("repro"):
        return C.Rows(g["lines"], m["rungs"]), "measured"
    return C.Rows(g["lines"]), "grid"


def stats(items):
    """items: list of (g, rows, ans) -> dict of ON/OFF + off-steps distribution."""
    on = sum(1 for g, r, a in items if C.passes(a, g["box"], r))
    off = [C.off_steps(a, g["box"], r) for g, r, a in items if not C.passes(a, g["box"], r)]
    return on, off


def main(path, mdir, out=None):
    res = json.loads(Path(path).read_text())
    summ = {}
    for doc, D in res.items():
        for run in ("RUN1", "RUN2"):
            M = json.loads((Path(mdir) / f"m_{run}_{doc}.json").read_text())
            H, MH = D["heads"][run], M["heads"]
            print("=" * 100)
            print(f"{doc} {run}: far heads {len(H)}; replay of the reader: {M['stats']}")
            # ---------- CONTROL
            T, miss = O.matched(D["truth"], H)
            n_meas = sum(1 for (h, s, g) in T if MH.get(s, {}).get("repro"))
            print(f"  CONTROL truth heads matched {len(T)}/{len(D['truth'])}; with measured rows (replay reproduced) {n_meas}, "
                  f"on the grid {len(T) - n_meas}")
            for label, only_meas in (("all matched", False), ("measured-rows only", True)):
                sel = [(h, s, g) for (h, s, g) in T if (not only_meas) or MH.get(s, {}).get("repro")]
                okc = 0
                fl = collections.Counter()
                bad = []
                for (h, s, g) in sel:
                    r, how = rows_for(g, MH.get(s))
                    t = h["truth"][0]
                    if C.passes(t, g["box"], r):
                        okc += 1
                    else:
                        bad.append((s, t, how, C.off_steps(t, g["box"], r), C.named_kinds(t, r)))
                    for d_ in (-2, -1, 1, 2):
                        fl[d_] += (not C.passes(t + d_, g["box"], r))
                both = sum(1 for (h, s, g) in sel
                           if not C.passes(h["truth"][0] - 1, g["box"], rows_for(g, MH.get(s))[0])
                           and not C.passes(h["truth"][0] + 1, g["box"], rows_for(g, MH.get(s))[0]))
                print(f"  [{label}] n={len(sel)}: references PASS {pct(okc, len(sel))}; shifted -1 FLAGGED {pct(fl[-1], len(sel))}, "
                      f"+1 FLAGGED {pct(fl[1], len(sel))}, both +-1 flagged {pct(both, len(sel))}, -2 {pct(fl[-2], len(sel))}, +2 {pct(fl[2], len(sel))}")
                print(f"     references that FAIL: {bad}")
                summ[f"{doc}|{run}|control|{label}"] = dict(n=len(sel), ref_pass=okc, m1=fl[-1], p1=fl[1], both=both)
            xt = collections.Counter()
            for (h, s, g) in T:
                r, how = rows_for(g, MH.get(s))
                tt = set(h["truth"])
                if g["dec"] is None:
                    xt["reader undecided"] += 1
                else:
                    xt[("reader right" if g["dec"] in tt else "reader wrong", "ON" if C.passes(g["dec"], g["box"], r) else "OFF")] += 1
                xt[("geo right" if g["geo"] in tt else "geo wrong", "ON" if C.passes(g["geo"], g["box"], r) else "OFF")] += 1
            print("  truth cross-tab (answer right/wrong x ON/OFF):", dict(xt))
            # ---------- CENSUS on decided far heads whose replay reproduced
            dec = {s: g for s, g in H.items() if g["dec"] is not None}
            rep = {s: g for s, g in dec.items() if MH.get(s, {}).get("repro")}
            print(f"  decided far heads {len(dec)}; replay reproduced the record on {len(rep)} ({100.0*len(rep)/max(1,len(dec)):.1f}%); "
                  f"census below is on those {len(rep)}")
            items_r = [(g, C.Rows(g["lines"], MH[s]["rungs"]), g["dec"]) for s, g in rep.items()]
            items_g = [(g, C.Rows(g["lines"], MH[s]["rungs"]), g["geo"]) for s, g in rep.items()]
            n = len(items_r)
            ron, roff = stats(items_r)
            gon, goff = stats(items_g)
            print(f"  READER   ON {pct(ron, n)}   OFF {pct(n - ron, n)}   steps off {O.dist(roff)}")
            print(f"  GEOMETRY ON {pct(gon, n)}   OFF {pct(n - gon, n)}   steps off {O.dist(goff)}")
            both_on = sum(1 for (g, r, a), (_, _, b) in zip(items_r, items_g) if C.passes(a, g["box"], r) and C.passes(b, g["box"], r))
            only_r = sum(1 for (g, r, a), (_, _, b) in zip(items_r, items_g) if C.passes(a, g["box"], r) and not C.passes(b, g["box"], r))
            only_g = sum(1 for (g, r, a), (_, _, b) in zip(items_r, items_g) if not C.passes(a, g["box"], r) and C.passes(b, g["box"], r))
            print(f"  both ON {both_on}  only reader ON {only_r}  only geometry ON {only_g}  neither {n - both_on - only_r - only_g}")
            # kinds of lines named
            for nm, items in (("reader", items_r), ("geometry", items_g)):
                kc = collections.Counter()
                for g, r, a in items:
                    ks = C.named_kinds(a, r)
                    kc["extrapolated" if "extrapolated" in ks else ("interpolated" if "interpolated" in ks else "measured/staff")] += 1
                print(f"  {nm} named line is: {dict(kc)}")
                for grp in ("measured/staff", "interpolated", "extrapolated"):
                    sel = [(g, r, a) for g, r, a in items
                           if ("extrapolated" if "extrapolated" in C.named_kinds(a, r) else ("interpolated" if "interpolated" in C.named_kinds(a, r) else "measured/staff")) == grp]
                    if sel:
                        o_, _ = stats(sel)
                        print(f"     {nm} lines {grp}: {len(sel)} heads, ON {pct(o_, len(sel))}")
            # same-answer split + box source
            for nm, f in (("reader==geometry", lambda g: g["dec"] == g["geo"]), ("reader!=geometry", lambda g: g["dec"] != g["geo"])):
                sel = [(g, r, a) for g, r, a in items_r if f(g)]
                o_, _ = stats(sel)
                print(f"    {nm}: {len(sel)} heads, reader ON {pct(o_, len(sel))}")
            for src in sorted({str(g["box_source"]) for g, r, a in items_r}):
                sel = [(g, r, a) for g, r, a in items_r if str(g["box_source"]) == src]
                o_, _ = stats(sel)
                selg = [(g, r, g["geo"]) for g, r, a in sel]
                og, _ = stats(selg)
                print(f"    box_source {src}: {len(sel)} heads, reader ON {pct(o_, len(sel))}, geometry ON {pct(og, len(sel))}")
            # secondary: the box the reader USED (cap_box) instead of the record's detector box
            sec = [(dict(box=MH[s]["cap_box"]), C.Rows(g["lines"], MH[s]["rungs"]), g["dec"]) for s, g in rep.items() if MH[s].get("cap_box")]
            o2, off2 = stats(sec)
            print(f"  SECONDARY (box = the box the reader's step rule used): reader ON {pct(o2, len(sec))}  steps off {O.dist(off2)}")
            summ[f"{doc}|{run}|census"] = dict(decided=len(dec), replayed=n, reader_on=ron, reader_off=n - ron, reader_steps=O.dist(roff),
                                               geo_on=gon, geo_off=n - gon, geo_steps=O.dist(goff), both_on=both_on,
                                               only_reader_on=only_r, only_geo_on=only_g, neither=n - both_on - only_r - only_g,
                                               secondary_reader_on=o2, secondary_n=len(sec))
    if out:
        Path(out).write_text(json.dumps(summ, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index("--json") + 1] if "--json" in a else None)
