"""2.266: Sean's answered accidental tiles joined BY PLACE (page + overlapping box; margin_judged.match, never an id alone) to the 20261103-night record's
DECIDED accidental_owner verdicts, then scored three readings against Sean: the family type (strokes), the one-ink detector winner, and what the
owner verdict writes. Reuses 2.263's tile loader and matcher.
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/judged_2_266.py SCRATCH_DIR OUT.json"""
import json, sys
from collections import Counter

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-accidental-family-2026-10")
import margin_judged as MJ

R = "/Users/seanjohnson/Desktop/ReEngrave/"
W = R + ".claude/worktrees/"
MJ.BOX_ON_ACCIDENTAL += [("2.263", "out/print/2.263-accidental-margin/"),
                         ("2.263b", W + "agent-a13774aa2e4b69a91/out/print/2.263b-natural-read/")]
S = sys.argv[1].rstrip("/") + "/"
T = {"accidentalflat": "flat", "accidentaldoubleflat": "flat", "accidentalnatural": "natural", "accidentalsharp": "sharp",
     "accidentaldoublesharp": "sharp", "keyflat": "flat", "keynatural": "natural", "keysharp": "sharp"}
ALT = {"#": "sharp", "b": "flat", "n": "natural", "natural": "natural", "sharp": "sharp", "flat": "flat"}


def c266(plate):
    d = {}
    for l in open(S + plate + ".c266.jsonl"):
        r = json.loads(l)
        f, oi = r["family"], r["one_ink"]
        d[r["subject"]] = dict(ftype=(f or {}).get("type") if (f or {}).get("type") in ("flat", "natural", "sharp") else None,
                               fmargin=(f or {}).get("margin"),
                               oiwin=T.get(str(((oi or {}).get("winner") or {}).get("class") or "").lower()) if oi else None,
                               oimargin=(oi or {}).get("margin"), alteration=ALT.get(str(r["alteration"]).lower()), head=r["head"])
    return d


def main():
    P = {p: MJ.load_plate(S, p) for p in ("litolff", "brahms")}
    C = {p: c266(p) for p in ("litolff", "brahms")}
    res = []
    for t in MJ.load_tiles():
        if t["sean"] not in ("natural", "flat", "sharp"):
            continue
        boxes, fam, owners = P[t["plate"]]
        hits = MJ.match(t, boxes, fam, owners)
        rows = []
        for sub, (how, r) in hits.items():
            c = C[t["plate"]].get(sub)
            if c is None:
                continue
            if t.get("box_on_accidental") and how[0] == "C":
                continue
            rows.append(dict(sub=sub, how=how, **c))
        if len(rows) != 1:      # twins / no place: not placeable as one reading (kept apart, counted)
            res.append(dict(set=t["set"], tile=t["tile"], plate=t["plate"], page=t["page"], sean=t["sean"], n_matches=len(rows), rows=rows))
            continue
        res.append(dict(set=t["set"], tile=t["tile"], plate=t["plate"], page=t["page"], sean=t["sean"], n_matches=1, **rows[0]))
    json.dump(res, open(sys.argv[2], "w"), indent=1)
    placed = [r for r in res if r["n_matches"] == 1]
    print("tiles with a Sean kind:", len(res), " placed on exactly one decided owner verdict:", len(placed), " unplaced/ambiguous:", len(res) - len(placed))
    print(Counter((r["set"], r["n_matches"]) for r in res))
    # classes of placed tile
    for name, sel in (("BOTH speak and AGREE", lambda r: r["ftype"] and r["oiwin"] and r["ftype"] == r["oiwin"]),
                      ("BOTH speak and DISAGREE", lambda r: r["ftype"] and r["oiwin"] and r["ftype"] != r["oiwin"]),
                      ("family only (no one-ink merge)", lambda r: r["ftype"] and not r["oiwin"]),
                      ("one-ink only (family unclear)", lambda r: r["oiwin"] and not r["ftype"]),
                      ("neither speaks", lambda r: not r["ftype"] and not r["oiwin"])):
        g = [r for r in placed if sel(r)]
        fr = sum(1 for r in g if r["ftype"] == r["sean"])
        orr = sum(1 for r in g if r["oiwin"] == r["sean"])
        wr = sum(1 for r in g if r["alteration"] == r["sean"])
        print("%-34s n=%3d  family right %3d/%d   one-ink winner right %3d/%d   written (owner alteration) right %3d" %
              (name, len(g), fr, sum(1 for r in g if r["ftype"]), orr, sum(1 for r in g if r["oiwin"]), wr))
        if name.startswith("BOTH speak and DISAGREE"):
            for r in g:
                print("      %-7s %-3s p%-3s sean=%-7s family=%-7s (%.2f)  one-ink=%-7s (%s)  written=%s  [%s]" % (
                    r["set"], r["tile"], r["page"], r["sean"], r["ftype"], r["fmargin"] or -1, r["oiwin"], r["oimargin"], r["alteration"], r["plate"]))


main()
