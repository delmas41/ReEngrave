"""ROADMAP 2.175 -- LilyPond for a whole night record with the flag ON: replay ADJUDICATE..INFER (as replay_2_175.py), write the
.ly with `staged.lilypond.to_lilypond`, compile it with the `lilypond` binary, report warnings/errors and the page count.
usage: lily_2_175.py DOC SLICEDIR OUTDIR"""
import glob
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, ".")
os.environ["OMR_UNISON_TWO_NOTES"] = "1"
from tools.omr.staged import lilypond as L  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
D = os.path.join(SD, DOC)
rows = {k: [] for k in ("observations", "abstentions")}
for k in rows:
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % k))):
        rows[k] += [json.loads(l) for l in open(p)]
rec = {"observations": rows["observations"], "abstentions": rows["abstentions"], "verdicts": []}
t0 = time.time()
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
text, report = L.to_lilypond(result)
ly = os.path.join(OUT, "%s.on.ly" % DOC)
open(ly, "w").write(text)
print("ly written", len(text), "bytes", "%.0fs" % (time.time() - t0), flush=True)
p = subprocess.run(["lilypond", "-o", os.path.join(OUT, DOC + ".on"), ly], capture_output=True, text=True, timeout=3000)
err = p.stderr
print("lilypond exit", p.returncode)
print("warnings", len(re.findall(r"warning", err)), "errors", len(re.findall(r"error", err)))
pdf = os.path.join(OUT, DOC + ".on.pdf")
if os.path.exists(pdf):
    import fitz
    print("pdf pages", len(fitz.open(pdf)))
open(os.path.join(OUT, "lilypond.log"), "w").write(err[-20000:])
print("\n".join(err.splitlines()[-8:]))
