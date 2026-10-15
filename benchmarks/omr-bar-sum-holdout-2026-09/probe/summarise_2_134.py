"""ROADMAP 2.134: summarise_2_96 with the 2.134 file names (<lab>-<kind>-part.json).

    python3 .../summarise_2_134.py <dump-dir> <held|partial>   (reads {lit,brah}-<kind>-part.json)
"""
import collections
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
KIND = sys.argv[2]
FAMILY = {
    "N": "narrowed head(s), candidates land the bar",
    "Y": "chord value undecided, candidates land the bar",
    "W": "lone whole rest left at 4 beats",
    "I:eighth": "unboxed eighth-rest-shaped ink",
    "I:quarter": "unboxed quarter-rest-shaped ink",
    "I:half_whole": "unboxed half/whole-rest-shaped ink",
    "D": "a dot the record saw and did not settle",
    "B": "a beam level at a doubted note", "G": "a beam GROUP level at a doubted note",
    "S": "one rest/head boxed twice", "E": "a barline read as a quarter rest",
    "V": "two voices written as two streams", "K": "a missed barline (cell ~k bars wide)",
    "O": "owner_not_read head", "P": "no_pitch head", "Q": "owned_by_another_staff head",
    "A": "abstained rest", "F": "mixed head fill in a chord", "X": "owner-doubtful extra note",
    "F~": "ARITH: one head fill/stem misread", "X~": "ARITH: drop one event",
    "B~": "ARITH: one beam level", "G~": "ARITH: one beam group", "K~": "ARITH: k bars",
    "I:any": "ARITH: ink of no rest shape",
}


def fam(tok):
    if tok.startswith("R:"):
        return "refused-as-not-a-note/rest (" + tok[2:] + "), value fills"
    if tok.startswith("U:"):
        return "refused (" + tok[2:] + "), no value, position only"
    return FAMILY.get(tok, tok)


data = {k: json.load(open(D / f"{k}-{KIND}-part.json")) for k in ("lit", "brah")}
for k, p in data.items():
    tot = p["total"]
    prim = collections.Counter()
    for key, v in p["primary"].items():
        tier, cause = key.split("|", 1)
        if tier == "evidenced":
            prim["evidenced, ONE cause" if "+" not in cause else
                 "evidenced, compound (2-3 causes)"] += v
        elif tier == "arith_only":
            prim["arithmetic only (a sum lands, no row points at it)"] += v
        else:
            prim["unexplained"] += v
    prim["on a doubled staff (exporter counts, cannot locate)"] += p["doubled"]
    print(f"\n### {k}: {tot} held bars\n")
    for a, v in prim.most_common():
        print(f"| {a} | {v} | {100*v/tot:.1f}% |")
    assert sum(prim.values()) == tot
print("\n### Ranking: bars released if that ONE cause alone were fixed\n")
fams = collections.defaultdict(lambda: [0, 0, 0, 0])
for i, k in enumerate(("lit", "brah")):
    for t, v in data[k]["single_evidenced"].items():
        fams[("E", fam(t))][i] += v
    for t, v in data[k]["single_arith"].items():
        fams[("A", fam(t if t != "D" else "D"))][i] += v
rows = sorted(fams.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
print("| cause | tier | Litolff | Brahms | total |\n|---|---|--:|--:|--:|")
for (tier, name), (a, b, _c, _d) in rows[:22]:
    print(f"| {name} | {'evidenced' if tier == 'E' else 'ARITHMETIC'} | {a} | {b} | {a+b} |")
print("\n### Primary-cause partition, by leading token\n")
lead = collections.defaultdict(lambda: [0, 0])
for i, k in enumerate(("lit", "brah")):
    for key, v in data[k]["primary"].items():
        tier, cause = key.split("|", 1)
        if tier == "unexplained":
            lead[("unexplained", "")][i] += v
        else:
            lead[(tier, cause)][i] += v
for (tier, cause), (a, b) in sorted(lead.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:30]:
    print(f"| {cause or 'unexplained'} | {tier} | {a} | {b} |")
