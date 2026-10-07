"""lane-brahms-1007-worse-and-slow, PART 2: why is ADJUDICATE slower on the 10-07 tree?  (STAGED, GATHER rows saved, no gather.)

  python3 brahms_1007_profile.py cache <NEW record.json> <pages csv> <cache.json>     # stream those pages' GATHER rows once
  python3 brahms_1007_profile.py run   <cache.json> <arm> [--prof N] [--verdicts out.json]

Arms toggle the three features whose cost is in ADJUDICATE:
  all        every 10-07 feature on (the NEW record's own defaults)
  nofromstaves  OMR_OWNER_FROM_STAVES=0
  nomarks    the Q.MARK_GROUP rows removed from the log (what `OMR_MARK_GROUPS` off gathers)
  noownerled the Q.FAR_HEAD_OWNER_LEDGER rows removed (what `OMR_FARHEAD_OWNER_LEDGERS` off gathers)
  none       all three off (the 10-06 configuration)
`--prof N` prints the top N functions by cumulative and by own time (cProfile).  `--verdicts` writes every standing verdict
(quantity, subject, outcome, value, reason, basis count) for the bit-identity check.
"""
from __future__ import annotations
import cProfile, io, json, os, pstats, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import mark_identity_rebuild as MR
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged.record import Q


def cache(src, pages, dst):
    t = time.time()
    res = MR.load_pages_streaming(src, set(int(p) for p in pages.split(",")))
    Path(dst).write_text(json.dumps(res))
    print("cached", len(res["record"]["observations"]), "obs", len(res["record"]["abstentions"]), "abs", f"{time.time() - t:.0f}s")


def run(cache_path, arm, prof=0, verdicts=None, pages=None):
    res = json.loads(Path(cache_path).read_text())
    rec = res["record"]
    drop = set()
    if arm in ("nomarks", "none"):
        drop.add(Q.MARK_GROUP)
    if arm in ("noownerled", "none"):
        drop.add(Q.FAR_HEAD_OWNER_LEDGER)
    if drop:
        rec = dict(rec, observations=[o for o in rec["observations"] if o["quantity"] not in drop],
                   abstentions=[a for a in rec["abstentions"] if a["quantity"] not in drop])
    if arm in ("nofromstaves", "none"):
        os.environ["OMR_OWNER_FROM_STAVES"] = "0"
    else:
        os.environ.pop("OMR_OWNER_FROM_STAVES", None)
    pg = set(int(p) for p in pages.split(",")) if pages else None
    log = MR.rebuild(rec, pg)
    pr = cProfile.Profile() if prof else None
    t0 = time.time()
    if pr:
        pr.enable()
    adjudicate.run(log)
    if pr:
        pr.disable()
    dt = time.time() - t0
    print(f"ARM {arm}: adjudicate {dt:.1f} s ({'under cProfile' if pr else 'plain'})", flush=True)
    if pr:
        for key in ("cumulative", "tottime"):
            s = io.StringIO()
            pstats.Stats(pr, stream=s).sort_stats(key).print_stats(prof)
            print(f"--- top {prof} by {key} ---")
            print("\n".join(l for l in s.getvalue().splitlines() if l.strip())[:9000])
    if verdicts:
        out = log.to_json()
        sup = {v["supersedes"] for v in out["verdicts"] if v.get("supersedes")}
        rows = [[v["quantity"], v["subject"], v["outcome"], json.dumps(v.get("value"), default=str, sort_keys=True),
                 v.get("reason"), len(v.get("basis") or [])] for v in out["verdicts"] if v["id"] not in sup]
        rows.sort(key=lambda r: (r[0], r[1]))
        Path(verdicts).write_text(json.dumps(rows))
        print("verdicts", len(rows))
    return dt


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "cache":
        cache(a[1], a[2], a[3])
    else:
        run(a[1], a[2], int(a[a.index("--prof") + 1]) if "--prof" in a else 0,
            a[a.index("--verdicts") + 1] if "--verdicts" in a else None,
            a[a.index("--pages") + 1] if "--pages" in a else None)
