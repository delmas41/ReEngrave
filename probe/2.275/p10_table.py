"""2.167b probe 10: side-by-side first-cause table (distinct ink NOT in the file) from the p3b outputs of two nights.
usage: python3 probe/2.167/p10_table.py RDIR OUTDIR     (RDIR holds {litolff,brahms}-{20261016,20261018}-night.{ink,part,summary}.json)
Copies slim outputs (ink.json without `members`) to OUTDIR and prints the markdown table. The real / non-note class per cause is the
agent's look carried over from 2.167 (ours, not Sean's)."""
import json
import sys
from pathlib import Path

R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
N = ("20261016", "20261018")
CLASS = {
    "held_bar_sum": "real (held by design)",
    "refused:duration_narrowed": "mostly real",
    "refused:chord_value_undecided": "real",
    "refused:no_pitch": "real",
    "refused:owned_by_another_staff": "copy whose owner lost it",
    "refused:owner_not_read": "real",
    "refused:not_a_notehead:too_narrow": "non-note",
    "refused:not_a_notehead:clipped_fragment": "mostly cut copies / letters",
    "refused:ink_is_a_whole_rest": "rest",
}
data = {}
for plate in ("litolff", "brahms"):
    for n in N:
        ink = json.load(open(R / f"{plate}-{n}-night.ink.json"))
        summ = json.load(open(R / f"{plate}-{n}-night.summary.json"))
        slim = {k: v for k, v in ink.items() if k != "members"}
        slim["notes_not_written_total"] = sum(summ["notes_not_written"].values())
        slim["notes_written_report"] = summ["notes_written_report"]
        json.dump(slim, open(OUT / f"{plate}-{n}-night.ink.slim.json", "w"), indent=1)
        data[(plate, n)] = slim
causes = set()
for d in data.values():
    causes |= set(d["ink_not_in_file"])
tot = lambda p, n: data[(p, n)]["ink_not_in_file"]
order = sorted(causes, key=lambda c: -(tot("litolff", N[1]).get(c, 0) + tot("brahms", N[1]).get(c, 0)))
print("| first cause (distinct ink NOT in file) | Lit 1016 | Lit 1018 | d | Brah 1016 | Brah 1018 | d | class (agent look) |")
print("|---|--:|--:|--:|--:|--:|--:|---|")
for c in order:
    v = [tot(p, n).get(c, 0) for p in ("litolff", "brahms") for n in N]
    cls = CLASS.get(c, "non-note" if "not_a_notehead" in c else "?")
    print("| %s | %d | %d | %+d | %d | %d | %+d | %s |" % (c, v[0], v[1], v[1] - v[0], v[2], v[3], v[3] - v[2], cls))
for p in ("litolff", "brahms"):
    for n in N:
        d = data[(p, n)]
        print("%s %s: boxes %d ink %d in-file %d not-in-file %d (+gap %d) bucket sum %d notes_not_written %d notes_written %s" % (
            p, n, d["boxes"], d["clusters"], d["ink_in_file"], sum(d["ink_not_in_file"].values()), d["gap_rows_unlocatable"],
            d["ink_in_file"] + sum(d["ink_not_in_file"].values()), d["notes_not_written_total"], d["notes_written_report"]))
