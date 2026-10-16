"""ROADMAP 2.153 -- run tag_notes_2_153.py over the three document slices ONE AT A TIME (one box, memory), with the arms named on
the command line. usage: run_tags_2_153.py SUFFIX ARM [ARM ...]  -> out/2.153/tags_<doc>_<SUFFIX>.json / .log"""
import subprocess
import sys

suffix, arms = sys.argv[1], sys.argv[2:]
for doc, sl in (("brahms_p0p3", "slice_p0p3_all"), ("litolff", "slice_litolff_all"), ("brahms", "slice_brahms_all")):
    out = "out/2.153/tags_%s_%s.json" % (doc, suffix)
    with open("out/2.153/tags_%s_%s.log" % (doc, suffix), "w") as lg:
        subprocess.run([sys.executable, "benchmarks/omr-bar-sum-holdout-2026-09/probe/tag_notes_2_153.py",
                        "out/2.153/%s.json" % sl, doc, out] + arms, stdout=lg, stderr=subprocess.STDOUT)
    print(doc, "done", flush=True)
