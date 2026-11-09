"""2.274 step 2 r2 measure-first (c)/(d): per written end, `out_by_spaces` (how far past the ink's own end the bound head stands), and for a chord end whether the bound member is the
outer one on the arc's side.

    python3 endfields.py WORKDIR plate:p,p [plate:p ...] [--list OUTMIN]
"""
import collections
import json
import pathlib
import sys

BINS = [-99, -0.5, 0.5, 1.5, 2.5, 3.5, 5, 99]


def main():
    argv = sys.argv[1:]
    lst = None
    if "--list" in argv:
        i = argv.index("--list")
        lst = float(argv[i + 1])
        del argv[i:i + 2]
    work = pathlib.Path(argv[0])
    tab = collections.Counter()
    chord = collections.Counter()
    rows = []
    for spec in argv[1:]:
        plate, pg = spec.split(":")
        pages = set(int(x) for x in pg.split(","))
        extra = json.loads((work / ("%s.on.extra.json" % plate)).read_text())
        for v in extra:
            p = int(v["subject"].split("/")[1])
            if p not in pages:
                continue
            for r in (v.get("detail") or {}).get("runs") or ():
                if r.get("status") != "written":
                    continue
                for side in ("left", "right"):
                    e = r.get(side) or {}
                    ob = e.get("out_by_spaces")
                    if ob is not None:
                        for lo, hi in zip(BINS, BINS[1:]):
                            if lo <= ob < hi:
                                tab["%g..%g" % (lo, hi)] += 1
                        if lst is not None and ob >= lst:
                            rows.append((plate, p, r["ordinal"], r.get("piece"), side, ob))
                    if e.get("chord"):
                        chord[(e["chord"] >= 2, e.get("outer_on_side"), bool(e.get("via_closest")))] += 1
    print("out_by_spaces:", dict(tab))
    print("chord ends (chord, outer_on_side, via_closest):", dict(chord))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
