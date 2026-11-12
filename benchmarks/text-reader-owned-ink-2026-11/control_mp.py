"""ROADMAP 2.304 control from the REAL judged case (Sean 2026-11-11, 2.301 r1 tile 4, Litolff p8: "it boxes MP, but it's actually a part of the word sempre"): in the file the
OFF arm writes a false `mp` dynamic at Litolff p8 P2/P3 m12 (the m+p of the unread `sempre`); the control is ON when that `mp` is gone and the word `sempre ... ` is READ there.

    python3 benchmarks/text-reader-owned-ink-2026-11/control_mp.py WORK/litolff.off.symbols.json WORK/litolff.on.symbols.json   (the files `lane_report` writes beside its report)
"""
import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path))
    print(path.split("/")[-1], "arm", d.get("arm"))
    for it in d["loose"]:
        if it.get("part") in ("P1", "P2", "P3", "P4") and str(it.get("measure")) in ("11", "12") and it.get("kind") in ("dynamic", "words"):
            print("   ", it["part"], "m" + str(it["measure"]), it["kind"], it.get("value"))
