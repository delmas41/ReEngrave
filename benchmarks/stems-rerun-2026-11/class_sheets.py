"""2.280 r3: my-look contact sheets, 10 seeded (Random(2803)) heads per chain class (i)(ii)(iii). usage: class_sheets.py HEADS.jsonl PLATE OUTPREFIX"""
import json
import random
import subprocess
import sys

heads, plate, pref = sys.argv[1:4]
tmp = "/private/tmp/claude-501/cs.%s.json" % plate
subprocess.run([sys.executable, "benchmarks/stems-rerun-2026-11/chain.py", heads, "--list", tmp], stdout=subprocess.DEVNULL, check=True)
d = json.load(open(tmp))
for k, name in (("(i) n", "i"), ("(ii) ", "ii"), ("(iii)", "iii")):
    v = sorted(d.get(k, []))
    random.Random(2803).shuffle(v)
    subprocess.run([sys.executable, "benchmarks/stems-rerun-2026-11/crops.py", "sheet", heads, plate, "%s.%s.png" % (pref, name)] + v[:10])
