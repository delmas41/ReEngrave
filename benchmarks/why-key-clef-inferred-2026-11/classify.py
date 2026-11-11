"""2.292: sort every FILLED key / clef staff-system into a first upstream cause, from the record's own verdict chains and GATHER evidence.
    python3 classify.py OUT.json X.json [X.json ...]        (X = analyze.py output; one per plate/page-set; first line of each = label)
The causes are DEFINED HERE from the data (rule written in `key_cause` / `clef_cause`), not assumed; a staff gets exactly one.
Notes are counted by DISTINCT note (glyph subject).  `blue_*` = notes whose pitch basis cites the filled verdict.
"""
import collections
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from tally import staff_of, reasons_for  # noqa


def ko_of(v):
    for r in v["evidence"].get("claimed_area", []):
        dt = r["detail"]
        if isinstance(dt, dict) and dt.get("key_object"):
            return dt["key_object"]
    return None


def key_cause(v):
    f, p = v["key"][0], v["key"][-1]
    reason = p["reason"]
    pd = p.get("detail") or {}
    fill = f["value"]
    off = (f.get("detail") or {}).get("fifths_offset")
    markers = v["evidence"].get("keysig_marker", [])
    ko = ko_of(v) or {}
    own, sysc = ko.get("own_slots"), ko.get("system_count")
    info = dict(prior=reason, fill=fill, tier=(f.get("detail") or {}).get("tier"), offset=off, markers=len(markers),
                own_slots=own, system_count=sysc, more_than_system=ko.get("more_than_system"),
                clef_measured=ko.get("clef_measured"), staff_read=pd.get("written_fifths"), read_by=pd.get("read_by"),
                slot_from_infer=(f.get("detail") or {}).get("part_from_an_inference"))
    if reason == "needs_clef":
        c = "K6 clef unread, so the key could not be checked"
    elif reason == "natural_markers":
        c = "K3 a flat box read as a natural (marker kind)"
    elif reason == "mixed_marker_kinds":
        c = "K4 mixed marker kinds in the run (a flat/sharp/natural mix)"
    elif reason == "no_evidence":
        c = "K5 no marker evidence (blank signature, or none read)"
    elif reason.startswith("disagrees"):
        wr = pd.get("written_fifths")
        if reason == "disagrees_with_system" and wr is not None and wr == fill:
            c = "K2 staff read the right count; the system check had no peer for it and abstained it"
        elif not markers:
            c = "K7 no marker box at all; a fit (read_by=%s) guessed a different count" % pd.get("read_by")
        else:
            c = "K1 marker run counted fewer flats than printed (crushed flats)"
    else:
        c = "K9 other (%s)" % reason
    return c, info


def clef_cause(v):
    f, p = v["clef"][0], v["clef"][-1]
    det = f.get("detail") or {}
    info = dict(prior="%s:%s" % (p["outcome"], p["reason"]), tier=f["reason"], value=f["value"], instrument=det.get("instrument"),
                slot_from_infer=det.get("part_from_an_inference"), n_systems_read=det.get("n_systems_read"),
                glyph=[x["value"] for x in v["evidence"].get("clef_glyph", [])][:3],
                located=[x["value"] for x in v["evidence"].get("clef_located", [])][:3])
    if p["outcome"] == "abstained":
        c = "C1 clef abstained (%s): no candidate read at the header" % p["reason"]
    else:
        c = "C2 clef narrowed (%s): contest not separated" % p["reason"]
    return c, info


def run(paths):
    out = {"keys": [], "clefs": []}
    for path in paths:
        d = json.load(open(path))
        sym = collections.defaultdict(list)
        for s in d["symbols"]:
            if not s["is_rest"]:
                sym[staff_of(s["sub"])].append(s)
        for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
            notes = sym.get(k, [])
            if v["key"] and v["key"][0]["decider"].startswith("infer"):
                c, info = key_cause(v)
                out["keys"].append(dict(src=path, plate=d["plate"], staff=k, cause=c, notes=len(notes),
                                        blue_key=sum(1 for s in notes if s["blue"] and "key_fill" in reasons_for(s)), **info))
            if v["clef"] and v["clef"][0]["decider"].startswith("infer"):
                c, info = clef_cause(v)
                out["clefs"].append(dict(src=path, plate=d["plate"], staff=k, cause=c, notes=len(notes),
                                         blue_clef=sum(1 for s in notes if s["blue"] and "clef_fill" in reasons_for(s)), **info))
    return out


def summarize(res):
    for kind, nk in (("keys", "blue_key"), ("clefs", "blue_clef")):
        by = collections.defaultdict(lambda: [0, 0, 0])
        for r in res[kind]:
            b = by[(r["plate"], r["cause"])]
            b[0] += 1
            b[1] += r[nk]
            b[2] += r["notes"]
        print("== %s: cause / staff-systems / blue notes / notes on those staves" % kind)
        for (plate, cause), (n, b, notes) in sorted(by.items(), key=lambda kv: (kv[0][0], -kv[1][1])):
            print("  %-8s %-95s %4d %5d %6d" % (plate, cause[:95], n, b, notes))


if __name__ == "__main__":
    res = run(sys.argv[2:])
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=str)
    summarize(res)
