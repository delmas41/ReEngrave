"""One record, exported TWICE — by the base tree and by this one.

⚠️ WHY A RE-EXPORT IS THE RIGHT INSTRUMENT HERE, and it needed an argument
rather than a shortcut. A plain re-export is normally BLIND to an ADJUDICATE
or GATHER change; this change is neither. `git diff` touches exactly one file,
`tools/omr/staged/export.py`, and the quantities it newly reads
(`Q.ACCIDENTAL`) were already on the record and already read at EXPORT time by
the very line being repaired. So the record is a fixed input and the only
variable is the exporter — which is what an A/B needs.

⚠️⚠️ THE TWO ARMS SHARE ONE PROCESS INVOCATION EACH, DELIBERATELY. Python
caches a module after the first import, so running both arms in one process
would export twice with whichever `export.py` was imported first — the
mid-run-edit hazard CLAUDE.md records costing a session two gathers. Each arm
is a SUBPROCESS.

⚠️⚠️ IT SWAPS A TRACKED FILE AND MUST LEAVE THE TREE AS IT FOUND IT — which
is not the same as leaving it as GIT has it. A BYTE snapshot is taken before
the first swap, the restore is VERIFIED by hash, and an in-flight sentinel is
written that a later run refuses to start over. This is the rule the mutation
batteries in this repo paid for twice, applied to an A/B arm.

    python3 benchmarks/omr-sounding-pitch-2026-09/export_arm.py \\
        library/_shared-records/beethoven5-p1-p4.record.json --tag beet5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tools" / "omr" / "staged" / "export.py"
HERE = Path(__file__).resolve().parent
SENTINEL = HERE / ".arm-in-flight"

# The tree this lane branched from. The BEFORE arm is this file's export.py.
BASE = "28749347"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def run_export(record: str, out: Path) -> dict:
    """Export in a FRESH process, so the module cache cannot leak an arm."""
    code = (
        "import json,sys;"
        f"sys.path.insert(0,{str(ROOT)!r});"
        "from tools.omr.staged import export as E;"
        f"d=json.load(open({record!r}));"
        "d = d if 'record' in d else {'record': d};"
        "x,r=E.to_musicxml(d);"
        f"open({str(out)!r},'w').write(x);"
        f"open({str(out) + '.coverage.json'!r},'w')"
        ".write(json.dumps(r,indent=2,default=str))"
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"export failed:\n{p.stdout}\n{p.stderr}")
    return json.loads(Path(str(out) + ".coverage.json").read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--outdir", default=str(HERE / "out"))
    a = ap.parse_args()

    if SENTINEL.exists():
        raise SystemExit(
            f"REFUSING TO START: {SENTINEL} exists, so an earlier run was "
            f"interrupted mid-swap and {TARGET} may still hold the BASE "
            f"version. It should hash {SENTINEL.read_text().strip()}; check "
            f"`git diff` before deleting the sentinel.")

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    mine = TARGET.read_bytes()
    mine_md5 = md5(mine)
    base = subprocess.check_output(
        ["git", "show", f"{BASE}:tools/omr/staged/export.py"], cwd=str(ROOT))
    if md5(base) == mine_md5:
        raise SystemExit("DEAD ARM: this tree's export.py is byte-identical "
                         "to the base. There is nothing to measure.")

    print(f"  AFTER  export.py md5 {mine_md5}")
    print(f"  BEFORE export.py md5 {md5(base)}  (from {BASE})")

    after_x = out / f"{a.tag}-after.musicxml"
    before_x = out / f"{a.tag}-before.musicxml"

    print("\n  exporting AFTER (this tree) ...")
    after_r = run_export(a.record, after_x)

    SENTINEL.write_text(mine_md5 + "\n")
    try:
        TARGET.write_bytes(base)
        print("  exporting BEFORE (base tree) ...")
        before_r = run_export(a.record, before_x)
    finally:
        TARGET.write_bytes(mine)
        got = md5(TARGET.read_bytes())
        if got != mine_md5:
            raise SystemExit(f"RESTORE FAILED: {TARGET} is {got}, want "
                             f"{mine_md5}. The sentinel is left in place.")
        SENTINEL.unlink()
        print(f"  restored, verified {got}")

    summary = {
        "record": a.record,
        "base": BASE,
        "export_md5": {"before": md5(base), "after": mine_md5},
        "before": {"coverage": str(before_x) + ".coverage.json",
                   "xml": str(before_x)},
        "after": {"coverage": str(after_x) + ".coverage.json",
                  "xml": str(after_x)},
        "written_before": before_r.get("written"),
        "written_after": after_r.get("written"),
        "accidental_reading_after": after_r.get("accidental_reading"),
    }
    (out / f"{a.tag}-arm.json").write_text(json.dumps(summary, indent=2,
                                                      default=str))
    print(f"\n  wrote {out}/{a.tag}-{{before,after}}.musicxml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
