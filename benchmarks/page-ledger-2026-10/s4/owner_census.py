"""2.240 step 3: glyph_owner / arc_owner verdicts OFF vs ON (lane_report arms' mini-records), by subject.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/owner_census.py OFF.mini-record.json ON.mini-record.json
"""
import collections
import json
import pathlib
import sys

from tools.omr.staged.judged import iter_array


def verdicts(path, qs=("glyph_owner", "arc_owner")):
    out = {}
    for v in iter_array(pathlib.Path(path), "verdicts"):
        if v.get("quantity") in qs:
            out[(v["quantity"], v["subject"])] = (v.get("outcome"), v.get("value"), v.get("reason"), (v.get("detail") or {}).get("page_owner"))
    return out


def main():
    off, on = verdicts(sys.argv[1]), verdicts(sys.argv[2])
    for q in ("glyph_owner", "arc_owner"):
        o = {k: v for k, v in off.items() if k[0] == q}
        n = {k: v for k, v in on.items() if k[0] == q}
        print("%s: OFF %d verdicts %s" % (q, len(o), dict(collections.Counter(v[2] for v in o.values()).most_common())))
        print("%s: ON  %d verdicts %s" % (q, len(n), dict(collections.Counter(v[2] for v in n.values()).most_common())))
        moved = [(k, o[k], n[k]) for k in o if k in n and (o[k][0], o[k][1]) != (n[k][0], n[k][1])]
        print("  owner changed %d: by OFF reason -> ON reason %s" % (len(moved), dict(collections.Counter("%s -> %s" % (a[2], b[2]) for _k, a, b in moved).most_common())))
        same = collections.Counter("%s=%s" % (o[k][2], n[k][2]) for k in o if k in n and (o[k][0], o[k][1]) == (n[k][0], n[k][1]) and o[k][2] != n[k][2])
        print("  same owner, new reason: %s" % dict(same.most_common(12)))
        if q == "glyph_owner":
            silent = collections.Counter(o[k][2] for k in o if k in n and n[k][2] not in ("page_owner", "page_owner_guessed"))
            print("  OFF reasons where the page owner did not decide (old rule stays, counted): %s" % dict(silent.most_common()))


if __name__ == "__main__":
    main()
