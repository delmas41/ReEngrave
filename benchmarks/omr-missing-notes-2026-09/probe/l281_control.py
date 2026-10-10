#!/usr/bin/env python3
"""l281_control: the streamed extract against the sanctioned reader (rule 7: a control must
be able to fail).

`l281_extract.py` reads a record with `ijson` (the sanctioned `record_io.load_record` /
`readout.load_run` needs ~6.6x the file resident). This loads the SMALL quick record BOTH ways
and compares, head by head, the ADJUDICATE standing readout reports against the one the
extract-side `adj_status` computes, and the stem/tip rows readout holds against the extract's.
It also runs the comparison on a PERTURBED extract (one head's status flipped) and requires
that to be reported different.

    python3 l281_control.py --record RECORD.json --ext DIR --tag bquick
"""
import argparse
import collections
import copy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_population import adj_status, load  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def compare(run, ext):
    bad = collections.Counter()
    n = 0
    for key, g in run.glyphs.items():
        if key not in ext["obs"]["heads"]:
            if (g.cls or "").startswith("notehead"):
                bad["head missing from extract"] += 1
            continue
        n += 1
        st, why = RO.adjudicate_status(run, g)
        rows = ext["ver"]["verdicts"].get(key, [])
        est, ewhy = adj_status(rows, key)
        if st == "narrowed":
            dur = [v for v in run.verdicts_at(key, "ADJUDICATE") if v["quantity"] == Q.DURATION][-1]
            if (est, ewhy) != ("narrowed", dur["reason"]):
                bad["narrowed reason differs"] += 1
        elif st in ("kept", "refused", "given_away", "abstained"):
            if (st == "kept" and est != "decided") or (st != "kept" and est != st):
                bad[f"status differs ({st} vs {est})"] += 1
    # tip rows: count per cell
    n_tip = sum(1 for o in run.observations if o["quantity"] == Q.STEM_TIP_INK)
    e_tip = sum(len(v) for v in ext["obs"]["tips"].values())
    n_abs = sum(1 for a in run.abstentions if a["quantity"] == Q.STEM_TIP_INK)
    e_abs = sum(len(v) for v in ext["abs"]["tips_abs"].values())
    if n_tip != e_tip:
        bad[f"tip rows {n_tip} vs {e_tip}"] += 1
    if n_abs != e_abs:
        bad[f"tip abstentions {n_abs} vs {e_abs}"] += 1
    return n, dict(bad), (n_tip, n_abs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    run = RO.load_run(a.record)
    ext = load(a.ext, a.tag)
    n, bad, tips = compare(run, ext)
    print(f"compared {n} heads, tip rows/abstentions {tips}; differences: {bad or 'NONE'}")
    # the control that must fail: flip one narrowed head's reason in a copy
    pert = copy.deepcopy(ext)
    flipped = None
    for key, rows in pert["ver"]["verdicts"].items():
        for r in rows:
            if r["q"] == Q.DURATION and r["stage"] == "ADJUDICATE" and r["outcome"] == "narrowed":
                r["reason"] = "PERTURBED"
                flipped = key
                break
        if flipped:
            break
    n2, bad2, _ = compare(run, pert)
    print(f"perturbed copy (head {flipped}): differences {bad2 or 'NONE'}")
    if bad or not bad2:
        print("CONTROL FAILED" if bad else "CONTROL CANNOT FAIL")
        sys.exit(1)
    print("CONTROL OK: identical on every head; a perturbed copy is reported different")


if __name__ == "__main__":
    main()
