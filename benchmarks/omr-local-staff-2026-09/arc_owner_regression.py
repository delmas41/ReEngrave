"""lane-arc-owner-regression, STAGED, GATHER+ADJUDICATE only, READ ONLY.  Replays the CURRENT `adjudicate_arc_owner` over every arc of
the NEW (10-07) shared records of Brahms and Litolff from the inputs the records hold (`arc_owner_extract.py` -> pickles), and
compares with the verdict the record itself holds.

  python3 arc_owner_regression.py <brh_new.pkl> <lit_new.pkl> <brh_base.pkl> [--seed 20261007] -> out/arc_owner_regression.json

CONTROL (must be able to fail): with the pre-fix function (`--old`) the replay must reproduce the record's arc_owner verdict on
EVERY arc; any mismatch means the replay inputs are not the live ones and nothing else it prints is evidence.
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import arc_owner_replay as R
from tools.omr.staged.adjudicators import ownership as O

OUT = HERE / "out/arc_owner_regression.json"


def old_fn(ev):
    """The comparative rule alone: the end rule is switched off by making `_arc_end_owner` find nothing."""
    saved = O._arc_end_owner
    O._arc_end_owner = lambda *a, **k: None
    try:
        return O.adjudicate_arc_owner(ev)
    finally:
        O._arc_end_owner = saved


def replay(path, fn=None):
    d = R.load(path)
    log = R.build_log(d)
    arcs = [v["subject"] for v in d["verdicts"] if v["quantity"] == "arc_owner"]
    out = R.run_arcs(log, arcs, fn=fn)
    rec = {v["subject"]: v for v in d["verdicts"] if v["quantity"] == "arc_owner"}
    return d, out, rec


def main(brh, lit, brh_base, seed=20261007):
    res = {}
    for tag, path in (("brahms", brh), ("litolff", lit)):
        d, ctl, rec = replay(path, fn=old_fn)
        mism = [a for a in rec if (ctl[a][1], ctl[a][2]) != (rec[a]["value"], rec[a]["reason"])]
        d, new, rec = replay(path)
        changed = [a for a in rec if new[a][1] != rec[a]["value"]]
        res[tag] = dict(arcs=len(rec), control_mismatch_old_fn_vs_record=len(mism), changed_owner=len(changed),
                        changed=[dict(arc=a, record=(rec[a]["value"], rec[a]["reason"]), now=(new[a][1], new[a][2]),
                                      detail=new[a][3]) for a in changed])
        print(tag, "arcs", len(rec), "CONTROL old-fn mismatches vs record:", len(mism), "| owner changed by the end rule:", len(changed), flush=True)
        if tag == "brahms":
            dB = R.load(brh_base)
            base = {v["subject"]: v for v in dB["verdicts"] if v["quantity"] == "arc_owner"}
            seventeen = [a for a, v in rec.items() if base.get(a) and base[a]["outcome"] == "decided" and v["outcome"] == "decided"
                         and base[a]["value"] != v["value"]]
            res["seventeen"] = [dict(arc=a, base=base[a]["value"], record_new=rec[a]["value"], fixed=new[a][1], reason=new[a][2],
                                     agrees_with="base" if new[a][1] == base[a]["value"] else ("record_new" if new[a][1] == rec[a]["value"] else "neither")) for a in seventeen]
            print("17 changed arcs:", len(seventeen), dict(collections.Counter(r["agrees_with"] for r in res["seventeen"])))
            rnd = random.Random(seed)
            unch = sorted(a for a in rec if a not in seventeen)
            samp = rnd.sample(unch, 30)
            res["brahms_sample30"] = dict(arcs=samp, changed=[a for a in samp if new[a][1] != rec[a]["value"]])
            print("brahms seeded 30 unchanged arcs: changed by the end rule:", len(res["brahms_sample30"]["changed"]))
        else:
            rnd = random.Random(seed)
            samp = rnd.sample(sorted(rec), 30)
            res["litolff_sample30"] = dict(arcs=samp, changed=[a for a in samp if new[a][1] != rec[a]["value"]])
            print("litolff seeded 30 arcs: changed by the end rule:", len(res["litolff_sample30"]["changed"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main(*sys.argv[1:4])
