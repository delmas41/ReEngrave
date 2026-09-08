"""Score the 20 scan-gate pairs at ONE musicdiff DetailLevel. Runs inside
.venv-omrned.

⚠️⚠️ ONE DETAIL LEVEL PER PROCESS — THIS IS A CORRECTNESS REQUIREMENT, NOT
TIDINESS. `musicdiff.visualization.Visualization.create_header_names_once()`
returns early when the class-level `_ORDERED_HEADER_NAMES` is already
populated. Score `AllObjects` first and the header is built WITHOUT the
Voicing-only columns (`wrong pitch`, `pitch insert/delete`, `voice
insert/delete`); a later `Voicing` run in the same interpreter then has
nowhere to file those ops and `get_omr_ed_dict` dumps them into `wrong
direction`, while `wrong pitch` silently reads ZERO.

Diagnosed by Agent III on 2026-09-07 after this file's predecessor
(`run_detail_arms.py`) ran three levels in one process and produced a
duration-vs-pitch ratio computed against a pitch mass that was structurally
zero. The pooled figures survived; the ratio did not.

`run_detail_arms.py` is kept for provenance and MUST NOT be used again.

    .venv-omrned/bin/python run_one_arm.py <pairs.json> <DETAIL_INT> <out.csv>
"""
import json, shutil, sys, tempfile
from pathlib import Path
from musicdiff import diff_ml_training
from musicdiff.visualization import Visualization

pairs = json.load(open(sys.argv[1]))
detail = int(sys.argv[2])
dest = Path(sys.argv[3])
if not pairs:
    sys.exit("FATAL: empty pair set")

# Fail loudly if this interpreter has already built a header for another level.
if getattr(Visualization, "_ORDERED_HEADER_NAMES", None):
    sys.exit("FATAL: a header is already cached in this process — one detail "
             "level per process (see the module docstring)")

def safe(n): return "".join(c if (c.isalnum() or c in "-_") else "-" for c in n).strip("-")
tmp = Path(tempfile.mkdtemp(prefix=f"md1-{detail}-"))
pd, td, od = tmp/"pred", tmp/"truth", tmp/"out"
for d in (pd, td, od): d.mkdir(parents=True)
for p in pairs:
    stem = safe(p["name"])
    shutil.copy(p["pred"], pd/f"{stem}.musicxml")
    shutil.copy(p["truth"], td/f"{stem}.musicxml")
diff_ml_training(str(pd), str(td), str(od), detail=detail)
csv = next(od.glob("*.csv"), None)
if csv is None:
    sys.exit("FATAL: musicdiff wrote no csv")
shutil.copy(csv, dest)
hdr = open(dest).readline().count(",") + 1
print(f"detail={detail} -> {dest}  ({hdr} columns)", file=sys.stderr)
