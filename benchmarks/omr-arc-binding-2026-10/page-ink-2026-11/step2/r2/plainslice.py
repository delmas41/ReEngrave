"""2.274 step 2 r2: the PLAIN twin of an injected slice directory (every `page_arc` row removed): what origin/main's tree, which has no step-1 rows, re-adjudicates for the gate.

    python3 plainslice.py SRC DST PLATE
"""
import pathlib
import shutil
import sys

src, dst, plate = sys.argv[1:4]
s, d = pathlib.Path(src) / plate, pathlib.Path(dst) / plate
d.mkdir(parents=True, exist_ok=True)
for kind in ("observations", "abstentions", "verdicts"):
    n = k = 0
    with open(s / (kind + ".jsonl")) as fi, open(d / (kind + ".jsonl"), "w") as fo:
        for line in fi:
            n += 1
            if '"quantity": "page_arc"' in line or '"quantity":"page_arc"' in line:
                continue
            k += 1
            fo.write(line)
    print(plate, kind, n, "->", k)
st = (s / "stamp.json").read_text()
(d / "stamp.json").write_text(st)
