"""Part 2 helper: time `Evidence.correlated_groups` per DECISION (adjudicator) and report the size of its all-pairs set
(`others` = verdict/abstention rows the decision consulted) -- the all-pairs loop that dominates ADJUDICATE on the 10-07 tree.

  python3 brahms_1007_corr_by_decision.py <cache.json> <arm>        (arms as in brahms_1007_profile.py)
"""
from __future__ import annotations
import collections, json, os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import mark_identity_rebuild as MR
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged.record import Q


def main(cache, arm):
    res = json.loads(Path(cache).read_text())
    rec = res["record"]
    if arm == "nofromstaves":
        os.environ["OMR_OWNER_FROM_STAVES"] = "0"
    log = MR.rebuild(rec)
    T = collections.defaultdict(lambda: [0, 0.0, 0, 0, 0])   # calls, seconds, sum rows, sum others, max others
    orig = adjudicate.Evidence.correlated_groups

    def wrapped(self):
        rows = {i for i in self._seen if self.log.row(i) is not None}
        others = sum(1 for i in rows if not isinstance(self.log.row(i), adjudicate.Observation))
        t = time.perf_counter()
        out = orig(self)
        d = T[self._spec.name]
        d[0] += 1; d[1] += time.perf_counter() - t; d[2] += len(rows); d[3] += others; d[4] = max(d[4], others)
        return out
    adjudicate.Evidence.correlated_groups = wrapped
    t0 = time.time()
    adjudicate.run(log)
    print(f"ARM {arm}: adjudicate {time.time() - t0:.1f} s; correlated_groups total {sum(v[1] for v in T.values()):.1f} s")
    print(f"{'decision':32s} {'calls':>7s} {'seconds':>8s} {'avg rows':>9s} {'avg others':>10s} {'max others':>10s}")
    for n, v in sorted(T.items(), key=lambda t: -t[1][1])[:12]:
        print(f"{n:32s} {v[0]:7d} {v[1]:8.1f} {v[2] / v[0]:9.1f} {v[3] / v[0]:10.1f} {v[4]:10d}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
