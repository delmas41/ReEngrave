"""ROADMAP 2.153 -- tag_notes_2_153.py over the interior_white-INJECTED slices (probe; see inject_iw_2_153.py), one at a time.
usage: run_tags_iw_2_153.py SUFFIX ARM [ARM ...]  -> out/2.153/tags_<doc>_<SUFFIX>.json / .log"""
import subprocess
import sys

suffix, arms = sys.argv[1], sys.argv[2:]
for doc, sl in (("litolff", "slice_litolff_iw"), ("brahms", "slice_brahms_iw")):
    out = "out/2.153/tags_%s_%s.json" % (doc, suffix)
    with open("out/2.153/tags_%s_%s.log" % (doc, suffix), "w") as lg:
        subprocess.run([sys.executable, "benchmarks/omr-bar-sum-holdout-2026-09/probe/tag_notes_2_153.py",
                        "out/2.153/%s.json" % sl, doc, out] + arms, stdout=lg, stderr=subprocess.STDOUT)
    print(doc, "done", flush=True)
