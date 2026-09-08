"""Runs INSIDE .venv-omrned. Standalone by design: `_omrned_worker` must not be
imported by anything in the repo, so this is a sibling, not a caller.

Scores the same 20 scan-gate pairs at several musicdiff DetailLevels. The one
that matters is AllObjects|NoteStaffPosition: musicdiff's own comment says it
compares STAFF POSITION instead of PITCH precisely "so that an erroneous clef
or ottava should not propagate errors into every affected note".
"""
import json, shutil, sys, tempfile
from pathlib import Path
from musicdiff import DetailLevel, diff_ml_training

pairs = json.load(open(sys.argv[1]))
ARMS = json.loads(sys.argv[2])

def safe(n): return "".join(c if (c.isalnum() or c in "-_") else "-" for c in n).strip("-")

out_all = {}
for arm_name, detail in ARMS.items():
    tmp = Path(tempfile.mkdtemp(prefix=f"md-{safe(arm_name)}-"))
    pd, td, od = tmp/"pred", tmp/"truth", tmp/"out"
    for d in (pd, td, od): d.mkdir(parents=True)
    for p in pairs:
        stem = safe(p["name"])
        shutil.copy(p["pred"], pd/f"{stem}.musicxml")
        shutil.copy(p["truth"], td/f"{stem}.musicxml")
    diff_ml_training(str(pd), str(td), str(od), detail=detail)
    csv = next(od.glob("*.csv"), None)
    rows = [l.rstrip("\n") for l in open(csv)] if csv else []
    out_all[arm_name] = {"detail": detail, "csv": rows}
    print(f"{arm_name}: detail={detail}  rows={len(rows)}", file=sys.stderr, flush=True)
json.dump(out_all, open(sys.argv[3], "w"), indent=1)
