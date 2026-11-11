"""2.299: OFF vs ON of two analyze.py runs (same gathered rows, same tree, same stages): which staves' key standing changed, which notes turned
plain, and every note whose PITCH changed.
    PYTHONPATH=. python3 compare.py OFF.json ON.json
"""
import collections
import json
import sys

from tally import reasons_for, staff_of


def pitch_of(s):
    return s.get("pitch")


def main(off_p, on_p):
    off, on = json.load(open(off_p)), json.load(open(on_p))
    print("plate", off["plate"], "pages", off["pages"])
    # staves
    ch = []
    for k, v in sorted(off["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
        a, b = v["key"][0], on["staffs"][k]["key"][0]
        if (a["decider"], a["outcome"], a["value"]) != (b["decider"], b["outcome"], b["value"]):
            ch.append((k, a, b))
    print("staves whose KEY verdict changed:", len(ch))
    for k, a, b in ch:
        print("  %-14s OFF %-34s %s -> ON %-26s %s (%s)" % (k, a["decider"][:34], a["value"], b["decider"][:26], b["value"], (b.get("reason") or "")))
    # notes
    O = {s["sub"]: s for s in off["symbols"]}
    N = {s["sub"]: s for s in on["symbols"]}
    lost = [k for k in O if k not in N]
    gained = [k for k in N if k not in O]
    print("symbols lost %d gained %d" % (len(lost), len(gained)))
    blue_to_plain = []
    plain_to_blue = []
    pitch_changed = []
    other = collections.Counter()
    for k, a in O.items():
        b = N.get(k)
        if b is None or a["is_rest"]:
            continue
        pa, pb = pitch_of(a), pitch_of(b)
        if pa != pb:
            pitch_changed.append((k, pa, pb, a["blue"], b["blue"]))
        if a["blue"] and not b["blue"]:
            blue_to_plain.append(k)
        elif b["blue"] and not a["blue"]:
            plain_to_blue.append(k)
        if bool(reasons_for(a) & {"key_fill"}) and not (reasons_for(b) & {"key_fill"}):
            other["key_fill_reason_gone"] += 1
    print("blue -> plain %d, plain -> blue %d, key_fill reason gone %d, PITCH changed %d" % (len(blue_to_plain), len(plain_to_blue), other["key_fill_reason_gone"], len(pitch_changed)))
    per_page = collections.Counter(k.split("/")[1] for k in blue_to_plain)
    print("blue -> plain by page:", dict(sorted(per_page.items(), key=lambda kv: int(kv[0]))))
    by_staff = collections.Counter(staff_of(k) for k in blue_to_plain)
    print("blue -> plain by staff:", dict(by_staff))
    for r in pitch_changed:
        print("  PITCH CHANGED", r)
    for k in plain_to_blue:
        print("  PLAIN -> BLUE", k)
    json.dump({"staves_changed": [(k, a, b) for k, a, b in ch], "blue_to_plain": blue_to_plain, "plain_to_blue": plain_to_blue,
               "pitch_changed": pitch_changed}, open(on_p + ".cmp.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
