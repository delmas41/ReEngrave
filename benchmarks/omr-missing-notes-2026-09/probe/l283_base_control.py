#!/usr/bin/env python3
"""l283_base_control: is the OVERNIGHT record a valid BASE for pages this lane did not re-gather on the base tree? The control:
on pages this lane DID re-gather on `faf913f4` (clean), every head's standing ADJUDICATE duration verdict (outcome, reason, the
levels it allows) must equal the overnight record's. A control that can fail: `--break` perturbs one overnight verdict and the
count of differing heads must move. ROADMAP 2.83 probe.

    python3 l283_base_control.py --fresh fresh.record.json --overnight overnight.json --pages 1,10 [--break]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_compare import head_rows  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", required=True)
    ap.add_argument("--overnight", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--break", dest="brk", action="store_true")
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")}
    fresh = head_rows(RD.load_run(a.fresh), pages)
    on = json.loads(Path(a.overnight).read_text())
    if a.brk:
        k = sorted(k for k in on if k in fresh)[0]
        on[k]["levels"] = on[k]["levels"] + [9]
    both = [k for k in fresh if k in on]
    diff = [k for k in both if (fresh[k]["outcome"], fresh[k]["reason"], fresh[k]["levels"])
            != (on[k]["outcome"], on[k]["reason"], on[k]["levels"])]
    only_f = [k for k in fresh if k not in on]
    only_o = [k for k in on if k not in fresh]
    print(f"pages {sorted(pages)}: fresh heads {len(fresh)}, overnight verdicts {len(on)} (these pages), in both {len(both)}, "
          f"only fresh {len(only_f)}, only overnight {len(only_o)}; DIFFERENT {len(diff)}")
    for k in diff[:10]:
        print("  ", k, (fresh[k]["outcome"], fresh[k]["reason"], fresh[k]["levels"]), "vs", (on[k]["outcome"], on[k]["reason"], on[k]["levels"]))


if __name__ == "__main__":
    main()
