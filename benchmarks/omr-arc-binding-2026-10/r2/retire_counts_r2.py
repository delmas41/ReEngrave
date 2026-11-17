"""arcs-r2 retire counts: with both flags ON, how many exported arcs does ONLY the old (detector-box) path still write? ON-file arcs (`arcs.arcs_of_xml`) whose (start, stop) glyph keys are not
a written page run's. Split by whether a witnessed-but-ABSTAINED run stands over it (rule 8 keeps the old arc) or no run witnesses it.   python3 retire_counts_r2.py LABEL"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

R = pathlib.Path("/private/tmp/claude-501/scr-arcs-r2")
label = sys.argv[1]
tot = collections.Counter()
for st, plates in (("hold", ("litolff", "brahms")), ("dev", ("litolff", "brahms"))):
    for plate in plates:
        d = R / ("pick-%s-%s-%s" % (label, st, plate))
        on = A.arcs_of_xml((d / ("%s.on.musicxml" % plate)).read_text())
        runs = [r for v in json.load(open(d / ("%s.on.extra.json" % plate))) for r in v["detail"]["runs"]]
        written = {(r["start"], r["stop"]) for r in runs if r["status"] == "written"}
        absx = [r for r in runs if r["status"] == "abstained"]
        tot["written page runs"] += sum(1 for r in runs if r["status"] == "written")
        tot["ON file arcs"] += len(on)
        for a in on:
            if (a["start"], a["stop"]) in written:
                tot["arc = a written page run"] += 1
            else:
                tot["arc only the old path writes"] += 1
        tot["abstained runs (old arc kept by rule 8)"] += len(absx)
        tot["abstained: " + plate] += len(absx)
print(dict(tot))
