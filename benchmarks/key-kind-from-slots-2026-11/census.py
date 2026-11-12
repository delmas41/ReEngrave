"""2.299 -- what the key object's measured slots say, staff-system by staff-system, against what ADJUDICATE did.  MEASURE ONLY.

    PYTHONPATH=. python3 benchmarks/key-kind-from-slots-2026-11/census.py OUT.json X.json [X.json ...]     (X = analyze.py output, flag OFF)

For every staff-system that has a `system_key_object` row: the slot read (`key_kind_slots.read`) against the clef the staff READ, the standing
KEY_SIGNATURE verdict (read / abstained + why / filled by INFER) and the 2.292 cause bucket (`classify.key_cause`) for the filled ones.
Prints: per bucket, how many staff-systems / blue notes the slots reach (READ), abstain (with the refusal named), and where a READ slot
reading disagrees with the INFER fill (these are the cases a pitch can change).
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import key_cause  # noqa: E402
from tally import staff_of, reasons_for  # noqa: E402
from tools.omr.staged import key_kind_slots as KKS  # noqa: E402


def ko_row(v):
    for r in v["evidence"].get("claimed_area", []):
        dt = r.get("detail")
        if isinstance(dt, dict) and dt.get("source") == "system_key_object" and dt.get("key_object"):
            return {"ko": dt["key_object"], "space": dt.get("space_page_px")}
    return None


def clef_read(v):
    c = v["clef"][0] if v["clef"] else None
    if not c or c["outcome"] != "decided" or str(c.get("decider", "")).startswith("infer"):
        return None
    return c["value"]


def run(paths):
    out = []
    for path in paths:
        d = json.load(open(path))
        sym = collections.defaultdict(list)
        for s in d["symbols"]:
            if not s["is_rest"]:
                sym[staff_of(s["sub"])].append(s)
        for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
            if not v["key"]:
                continue
            notes = sym.get(k, [])
            top = v["key"][0]
            filled = top["decider"].startswith("infer")
            blue = sum(1 for s in notes if s["blue"] and "key_fill" in reasons_for(s))
            row = ko_row(v)
            clef = clef_read(v)
            res = KKS.read(row, clef)
            if filled:
                cause, info = key_cause(v)
                bucket = cause.split()[0]
            else:
                bucket, info = "READ", {}
            standing = "filled" if filled else ("decided" if top["outcome"] == "decided" else "abstained:%s" % top.get("reason"))
            out.append(dict(plate=d["plate"], staff=k, bucket=bucket, standing=standing, fill=(top["value"] if filled else None),
                            read_value=(top["value"] if not filled and top["outcome"] == "decided" else None),
                            notes=len(notes), blue_key=blue, clef=clef, slots=res, fifths=KKS.fifths_of(res),
                            own_slots=(row["ko"].get("own_slots") if row else None), system_count=(row["ko"].get("system_count") if row else None),
                            has_ko=row is not None, markers=info.get("markers"), prior=info.get("prior")))
    return out


if __name__ == "__main__":
    res = run(sys.argv[2:])
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=str)
    by = collections.defaultdict(lambda: collections.Counter())
    for r in res:
        if r["standing"] != "filled":
            continue
        key = (r["plate"], r["bucket"])
        c = by[key]
        c["staff_systems"] += 1
        c["blue_notes"] += r["blue_key"]
        if not r["has_ko"]:
            c["no_key_object"] += 1
        elif r["fifths"] is not None:
            c["READ"] += 1
            c["READ_blue"] += r["blue_key"]
            c["READ_equals_fill" if r["fifths"] == r["fill"] else "READ_differs_from_fill"] += 1
        else:
            c["abstain:" + r["slots"]["why"]] += 1
    for (plate, b), c in sorted(by.items()):
        print(plate, b, dict(c))
    print("== staves with a READ (decided) key whose slots read something different (control)")
    for r in res:
        if r["standing"] == "decided" and r["fifths"] is not None and r["fifths"] != r["read_value"]:
            print("  ", r["plate"], r["staff"], "read", r["read_value"], "slots", r["fifths"], r["slots"].get("flat_devs"), r["slots"].get("sharp_devs"))
