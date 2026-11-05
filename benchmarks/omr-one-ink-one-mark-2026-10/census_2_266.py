"""2.266 census: per plate, for every DECIDED accidental_owner verdict (one per detector glyph; twins collapse by HEAD below), the family reading
(type from strokes) against the one-ink merge's detector winner. Input: census_2_266_extract.py output.
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/census_2_266.py SCRATCH_DIR [OUT.json]"""
import json, sys
from collections import Counter, defaultdict

S = sys.argv[1].rstrip("/") + "/"
T = {"accidentalflat": "flat", "accidentaldoubleflat": "flat", "accidentalnatural": "natural", "accidentalsharp": "sharp",
     "accidentaldoublesharp": "sharp", "keyflat": "flat", "keynatural": "natural", "keysharp": "sharp"}
ALT = {"#": "sharp", "b": "flat", "n": "natural", "natural": "natural", "sharp": "sharp", "flat": "flat", "##": "sharp", "bb": "flat"}


def ty(c):
    return T.get(str(c or "").lower())


def rows(plate):
    for l in open(S + plate + ".c266.jsonl"):
        r = json.loads(l)
        f, oi = r["family"], r["one_ink"]
        r["ftype"] = f.get("type") if f and f.get("type") in ("flat", "natural", "sharp") else None
        r["fmargin"] = f.get("margin") if f else None
        r["oiwin"] = ty((oi.get("winner") or {}).get("class")) if oi else None
        r["oirivals"] = sorted({ty(x.get("class")) for x in (oi.get("rivals") or ())} - {None}) if oi else []
        r["oimargin"] = oi.get("margin") if oi else None
        r["det"] = ty(r["detector_class"])
        yield r


def q(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return "n=0"
    return "n=%d p10 %.2f p25 %.2f med %.2f p75 %.2f p90 %.2f" % (len(v), v[len(v) // 10], v[len(v) // 4], v[len(v) // 2], v[3 * len(v) // 4], v[9 * len(v) // 10])


def main():
    out = {}
    for plate in ("litolff", "brahms"):
        rs = list(rows(plate))
        print("==", plate, "decided owner verdicts:", len(rs), " with a written accidental on the head:", sum(1 for r in rs if r["written"] is not None))
        c = Counter()
        pair = Counter()
        for r in rs:
            fam, oi = r["ftype"], r["oiwin"]
            c[("family_clear" if fam else "family_none", "oneink" if r["one_ink"] else "no_oneink")] += 1
            if fam and oi:
                pair[(fam, oi, "agree" if fam == oi else "DISAGREE")] += 1
        for k, v in sorted(c.items()):
            print("   ", k, v)
        print("   both speak (family type clear AND one-ink winner):", sum(pair.values()), " agree", sum(v for k, v in pair.items() if k[2] == "agree"),
              " disagree", sum(v for k, v in pair.items() if k[2] != "agree"))
        for k, v in sorted(pair.items(), key=lambda kv: -kv[1]):
            print("      family %-7s one-ink winner %-7s %-8s %d" % (k[0], k[1], k[2], v))
        dis = [r for r in rs if r["ftype"] and r["oiwin"] and r["ftype"] != r["oiwin"]]
        inr = sum(1 for r in dis if r["ftype"] in r["oirivals"])
        print("   disagree rows where family's type IS among one-ink's rivals:", inr, "of", len(dis))
        w = Counter()
        for r in dis:
            a = ALT.get(str(r["alteration"]).lower(), str(r["alteration"]))
            w["written=family" if a == r["ftype"] else "written=oneink" if a == r["oiwin"] else "written=other:%s" % a] += 1
        print("   disagree rows: the owner verdict's alteration (what the file writes) equals:", dict(w))
        print("   one-ink margin  agree   :", q([r["oimargin"] for r in rs if r["ftype"] and r["oiwin"] == r["ftype"]]))
        print("   one-ink margin  disagree:", q([r["oimargin"] for r in dis]))
        print("   family margin   agree   :", q([r["fmargin"] for r in rs if r["ftype"] and r["oiwin"] == r["ftype"]]))
        print("   family margin   disagree:", q([r["fmargin"] for r in dis]))
        byh = defaultdict(list)
        for r in rs:
            if r["head"]:
                byh[r["head"]].append(r)
        hd = Counter()
        for h, g in byh.items():
            if any(x["ftype"] and x["oiwin"] and x["ftype"] != x["oiwin"] for x in g):
                hd["head with a disagree"] += 1
            elif any(x["ftype"] and x["oiwin"] for x in g):
                hd["head both speak, agree"] += 1
            elif any(x["ftype"] for x in g) and not any(x["oiwin"] for x in g):
                hd["head family only"] += 1
            elif any(x["oiwin"] for x in g) and not any(x["ftype"] for x in g):
                hd["head one-ink only"] += 1
            else:
                hd["head neither (family unclear, no merge)"] += 1
        print("   by HEAD (twins collapsed):", len(byh), dict(hd))
        nat = [r for r in rs if r["ftype"] == "natural" and r["fmargin"] is not None and r["fmargin"] >= 0.25 and r["written"] is not None]
        print("   family natural >= 0.25 with a written accidental:", len(nat), " one-ink present (so still blue):", sum(1 for r in nat if r["one_ink"]),
              " winner natural:", sum(1 for r in nat if r["oiwin"] == "natural"), " flat:", sum(1 for r in nat if r["oiwin"] == "flat"),
              " sharp:", sum(1 for r in nat if r["oiwin"] == "sharp"))
        for t in ("flat", "sharp", None):
            sel = [r for r in rs if r["ftype"] == t and r["written"] is not None]
            print("   family %-6s written %d; one-ink present %d; winner agrees %d" % (t, len(sel), sum(1 for r in sel if r["one_ink"]),
                                                                                    sum(1 for r in sel if r["one_ink"] and r["oiwin"] == t)))
        out[plate] = {"pairs": {"|".join(k): v for k, v in pair.items()}}
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], "w"), indent=1)


main()
