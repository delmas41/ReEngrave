"""2.280 r3: the 12 blind tiles. SEEDED RULE (stated, no hand picking): from each plate's fresh-gather rows (heads.PLATE.C*.jsonl), take the VALUE-uncertain READ heads
(chain.py), group by chain class (i) no stem row, (ii) stem row but no beam/flag read, (iii) beam/flag read but not bound; draw 2 per class per plate with
random.Random(2803) over the class list sorted by sub id; if a class has fewer than 2, top up from the same class on the 2.280 11-04 gather re-adjudicated rows
(stems are byte-identical, the print is the same), then shuffle the 12 with the same RNG.
usage: select_tiles.py LIT_HEADS BRAHMS_HEADS OUT.json [LIT_B_HEADS BRAHMS_B_HEADS]"""
import json
import random
import subprocess
import sys

lit, br, out = sys.argv[1:4]
extra = {"litolff": sys.argv[4] if len(sys.argv) > 4 else None, "brahms": sys.argv[5] if len(sys.argv) > 5 else None}
rng = random.Random(2803)
sel = []
for plate, heads in (("litolff", lit), ("brahms", br)):
    for src in (heads, extra[plate]):
        if src is None:
            continue
        tmp = "/private/tmp/claude-501/classes.%s.json" % plate
        subprocess.run([sys.executable, "benchmarks/stems-rerun-2026-11/chain.py", src, "--list", tmp], stdout=subprocess.DEVNULL, check=True)
        cl = json.load(open(tmp))
        for k in ("(i) n", "(ii) ", "(iii)"):
            have = [s for s in sel if s["plate"] == plate and s["bucket"] == k]
            if len(have) >= 2:
                continue
            pool = sorted(set(cl.get(k, [])) - {s["sub"] for s in sel})
            rng.shuffle(pool)
            for sub in pool[:2 - len(have)]:
                sel.append(dict(plate=plate, heads=src, sub=sub, bucket=k, source="fresh" if src == heads else "11-04 gather re-adjudicated"))
rng.shuffle(sel)
json.dump(sel, open(out, "w"), indent=1)
print(len(sel), "selected:", [(s["plate"], s["bucket"], s["source"][:5]) for s in sel])
