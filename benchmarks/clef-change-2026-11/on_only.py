"""2.251 carry: an ON-arm-only lane report. The OFF arm's GATHERED record is reused from an earlier run of the same tree (its OFF
export was byte-identical to round 2's); only the ON arm is re-gathered. Both arms are then exported and compared by lane_report's
own code (`run_report`), so the file line, judged moves and tiles are the one shared command's.

python3 work-2.251/on_only.py OLD_WORK_DIR OUT_DIR
"""
import os, pathlib, shutil, sys
sys.path.insert(0, os.getcwd())
from tools.omr.staged import lane_report as LR  # noqa: E402

old, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
work = out / "work"
work.mkdir(parents=True, exist_ok=True)
for name in ("litolff.off.gathered.record.json", "litolff.off.gather.log"):
    shutil.copy2(old / name, work / name)
_orig = LR.gather_one


def gather_one(plate, arm, flag_env, pages, w, env0):
    if arm == "off":
        print("  gather %s off: REUSED %s" % (plate, old / "litolff.off.gathered.record.json"), flush=True)
        return w / ("%s.off.gathered.record.json" % plate)
    return _orig(plate, arm, flag_env, pages, w, env0)


LR.gather_one = gather_one
sys.exit(LR.main(["--plates", "litolff", "--flag", "OMR_CLEF_CARRY", "--from", "gather", "--cell-map", "master", "--workers", "2",
                  "--out", str(out)]))
