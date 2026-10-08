"""ROADMAP 2.58d -- count what the stem witness changed, by rule, from a `stem_owner_replay.py` output.

  python3 benchmarks/omr-local-staff-2026-09/stem_owner_report.py <extract.pkl> <replay.json>
"""
import collections
import json
import pickle
import sys


def main(pkl, rep):
    data = pickle.load(open(pkl, "rb"))
    H = json.load(open(rep))["heads"]
    lines = {o["subject"]: o["value"] for o in data["obs"] if o["quantity"] == "staff_lines"}
    box = {o["subject"]: o["detail"]["bbox_page_px"] for o in data["obs"]
           if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}

    def inband(h):
        ys = lines["staff/" + "/".join(h.split("/")[1:4])]
        b = box[h]
        cy = (b[1] + b[3]) / 2
        return min(ys) <= cy <= max(ys)

    fc, inb = collections.Counter(), 0
    for h, r in H.items():
        a, b = r["off_final"], r["on_final"]
        if (a and a[1]) != (b and b[1]):
            fc[(a[2] if a else None, b[2] if b else None, b[0] if b else None)] += 1
            inb += inband(h)
    print("final owner changes", sum(fc.values()), "| head centre inside its FILING staff's band:", inb)
    for k, n in fc.most_common():
        print(f"  {n:5d} {k}")
    dc = collections.Counter()
    for h, r in H.items():
        if r["off"][:2] != r["on"][:2]:
            dc[(r["off"][2], r["on"][2], "in-band" if inband(h) else "out-of-band")] += 1
    print("decision changes (off reason, on reason):")
    for k, n in dc.most_common():
        print(f"  {n:5d} {k}")
    # the two copies of ONE mark: how many marks end with two different owners now vs before
    print("stem direction of all contested heads:", collections.Counter(r["stem"] for r in H.values()))


if __name__ == "__main__":
    main(*sys.argv[1:3])
