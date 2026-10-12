#!/usr/bin/env python3
"""l283_flag_tally: heads that LOSE or GAIN flag evidence between two records of the same pages. A head's FLAG STATE is read off its standing ADJUDICATE
duration verdict: `eighth+` (decided, `hooks_counted`, level >= 1), `flag?` (narrowed `flag_ink_unread`: a hook seen, the count not), `disputed`
(narrowed `tip_readers_disagree`), `attached` (decided with a detector flag box attached, `flag_levels` >= 1), else `none`. LOST = base in
{eighth+, flag?, attached} and arm `none`; GAINED = the reverse; the lists name the heads. ROADMAP 2.83 fix round: how many of the Litolff flags the v5 arm lost
come back. Heads are matched by key (same pages, same detector).

    python3 l283_flag_tally.py --base A.record.json --arm B.record.json [--list]
"""
import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def states(path):
    run = RD.load_run(path)
    out = {}
    for key, g in run.glyphs.items():
        if not (g.cls or "").startswith("notehead"):
            continue
        du = run.standing(key, Q.DURATION, "ADJUDICATE")
        if du is None:
            continue
        reason = du.get("reason")
        det = du.get("detail") or {}
        if reason == "hooks_counted":
            st = "eighth+"
        elif reason == "flag_ink_unread":
            st = "flag?"
        elif reason == "tip_readers_disagree":
            st = "disputed"
        elif (det.get("flag_levels") or 0) >= 1 or (det.get("flags_attached") or 0) >= 1:
            st = "attached"
        else:
            st = "none"
        out[key] = (st, du.get("outcome"), reason)
    del run
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    B, A = states(a.base), states(a.arm)
    both = set(B) & set(A)
    flagged = {"eighth+", "flag?", "attached"}
    lost, gained, other = [], [], collections.Counter()
    for k in sorted(both):
        b, r = B[k][0], A[k][0]
        if b in flagged and r == "none":
            lost.append(k)
        elif b == "none" and r in flagged:
            gained.append(k)
        elif b != r:
            other[(b, r)] += 1
    print(f"heads in both {len(both)} (only base {len(set(B) - set(A))}, only arm {len(set(A) - set(B))})")
    print(f"LOST   flag evidence: {len(lost)}   by base state: {dict(collections.Counter(B[k][0] for k in lost))}")
    print(f"GAINED flag evidence: {len(gained)}   by arm state: {dict(collections.Counter(A[k][0] for k in gained))}")
    print("other changes of state:", {f"{b}->{r}": n for (b, r), n in other.items()})
    if a.list:
        for k in lost:
            print("  LOST  ", k, B[k], "->", A[k])
        for k in gained:
            print("  GAINED", k, B[k], "->", A[k])


if __name__ == "__main__":
    main()
