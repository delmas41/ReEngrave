"""ROADMAP 2.296: the ONE shared lane report (`lane_report.run_report`, docs/measuring.md section 0) over page gathers already made.

    python3 benchmarks/dynamics-not-words-2026-11/report_driver.py --out DIR --off OFFDIR --on ONDIR --pages litolff=2,8 brahms=0,14 [--plates litolff,brahms]

`OFFDIR` / `ONDIR` hold `PLATE.<arm>.gathered.record.json` (`python3 -m tools.omr.staged PDF --pages ... --out`, the same flags and tree but the one flag). The
report's own machinery runs unchanged -- file change by kind (+ gained - lost ~ changed), the OFF==record control, Sean's judged answers right->wrong,
changed places nobody judged, the tiles it cuts -- only `gather_one` is replaced by "use the record already gathered" and the sample's page list by
the pages named (all of them inside the frozen sample, `benchmarks/lane-report/sample.json`). Both arms were gathered the same way: cell map master,
detector cache, same OCR. Reads records; writes only under DIR.
"""
import argparse
import copy
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--pages", nargs="+", required=True, help="plate=p,p ...")
    ap.add_argument("--plates", default=None)
    ap.add_argument("--flag", default="OMR_DYNAMIC_OWN_CLAIM")
    ap.add_argument("--seed", type=int, default=2188)
    a = ap.parse_args()
    from tools.omr.staged import lane_report as LR
    pages = {kv.split("=")[0]: [int(x) for x in kv.split("=")[1].split(",")] for kv in a.pages}
    plates = a.plates.split(",") if a.plates else list(pages)
    sample = copy.deepcopy(LR.load_sample())
    for p in plates:
        assert set(pages[p]) <= set(sample["plates"][p]["pages"]), "%s pages %s are not all inside the frozen sample" % (p, pages[p])
        sample["plates"][p]["pages"] = pages[p]
    recs = {"off": pathlib.Path(a.off), "on": pathlib.Path(a.on)}
    LR.gather_one = lambda plate, arm, flag_env, pgs, work, env0: recs[arm] / ("%s.%s.gathered.record.json" % (plate, arm))
    LR.load_sample = lambda *x, **k: sample
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    flags = LR.parse_flags([a.flag])
    notes = ["2.296 report over page gathers made by hand: %s; both arms gathered the same way (cell map master, detector cache); pages %s inside the frozen sample"
             % (", ".join("%s %s" % (p, pages[p]) for p in plates), "named above")]
    rep = LR.run_report(flags, plates, "gather", out, LR.DEFAULT_TAG, a.seed, 2, sample, notes)
    print(LR.render_text(rep))


main()
