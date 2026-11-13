"""ROADMAP 2.307 T1d -- of the duration/rest verdicts that differ OFF vs ON, how many are copies that simply get none ON, and how many are
a staff's OWN marks whose verdict moved (measure only).

    python3 benchmarks/page-and-zoom-2026-11/t1d_verdict_diff.py WORK_DIR PLATE
"""
import collections
import json
import sys


def live(vs, qs=("duration", "rest_is_not_a_rest")):
    sup = {v.get("supersedes") for v in vs if v.get("supersedes")}
    out = {}
    for v in vs:
        if v["quantity"] in qs and v["id"] not in sup:
            out[(v["subject"], v["quantity"])] = v
    return out


def brief(v):
    return (v["outcome"], json.dumps(v.get("value"), sort_keys=True), v.get("reason"))


def main():
    work, plate = sys.argv[1], sys.argv[2]
    off = json.load(open("%s/%s.off.mini-record.json" % (work, plate)))["verdicts"]
    on = json.load(open("%s/%s.on.mini-record.json" % (work, plate)))["verdicts"]
    a, b = live(off), live(on)
    gone = [k for k in a if k not in b]
    new = [k for k in b if k not in a]
    moved = [k for k in a if k in b and brief(a[k]) != brief(b[k])]
    print(plate, "OFF verdicts", len(a), "ON", len(b), "| absent ON (copies, no longer adjudicated):", len(gone),
          "| new ON:", len(new), "| own marks whose verdict moved:", len(moved))
    c = collections.Counter((a[k]["outcome"], a[k].get("reason")) for k in gone)
    print("  absent ON were OFF:", c.most_common(6))
    for k in moved[:15]:
        print("  moved", k[0], k[1], brief(a[k])[:2], "->", brief(b[k])[:2], b[k].get("reason"))


if __name__ == "__main__":
    main()
