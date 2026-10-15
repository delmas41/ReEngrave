"""ROADMAP 2.141h -- read the arms' durations.json (written by arm_2_141h.py) and report, per movement and per flag:
the transitions of every standing duration against the W2-only base arm, the key cells (Sean's judged tiles), and a JSON
of the changed bars for the blind tiles.

    python3 summarise_2_141h.py ARMS_DIR lit|brah OUT.json
ARMS_DIR/<mov>-<arm>/durations.json, arm in base f1 f2 f3 all  (base = OMR_INFER_CARRIED_METER_FIX only: W2 ON).
{subject: [outcome, beats, beam_levels, reason, decider, n_cand, detail]}
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTD = HERE.parent / "out"
ARMS = ("f1", "f2", "f3", "all")


def load(d, mov, arm):
    p = Path(d) / f"{mov}-{arm}" / "durations.json"
    return json.load(open(p)) if p.exists() else None


def cell_of(subj):
    p = subj.split("/")
    return tuple(int(x) for x in p[1:5])


def state(v):
    if v is None:
        return ("absent", None)
    return (v[0], v[1] if v[0] == "decided" else None)


def key_cells():
    """Sean-judged cells: {(mov, cell): (label, sean_beats or None)}."""
    out = {}
    k = json.load(open(OUTD / "2.136-step2" / "tiles-key.json"))
    ans = json.load(open("/private/tmp/claude-501/answers/a2136.json"))["tiles"]
    for t, a in zip(k["tiles"], ans):
        out[(t["movement"], tuple(t["cell"]))] = (f"2.136 tile {t['n']}", a["sean"], a["agrees"])
    k = json.load(open(OUTD / "2.141" / "tiles-key.json"))
    for t in k["tiles"]:
        out[("lit", tuple(t["cell"]))] = (f"2.141 tile {t['n']}", "all right under W2 (Sean)", True)
    return out


def main():
    d, mov, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    base = load(d, mov, "base")
    res = {"mov": mov, "arms": {}, "key": {}}
    by_cell = collections.defaultdict(dict)
    for subj in base:
        by_cell[cell_of(subj)][subj] = base[subj]
    for arm in ARMS:
        a = load(d, mov, arm)
        if a is None:
            continue
        trans = collections.Counter()
        dec_changed = []
        changed_cells = collections.defaultdict(list)
        for subj in set(base) | set(a):
            b, n = base.get(subj), a.get(subj)
            sb, sn = state(b), state(n)
            if sb == sn and (b or [None] * 4)[3] == (n or [None] * 4)[3]:
                continue
            trans[f"{sb[0]}->{sn[0]}" + ("" if sb[0] != "decided" or sn[0] != "decided" else f" ({sb[1]}->{sn[1]})")] += 1
            if sb != sn:
                changed_cells[cell_of(subj)].append([subj, list(sb), list(sn), (n or [None] * 5)[4], (n or [None] * 6)[5:]])
            if sb[0] == "decided" and sn[0] == "decided" and sb[1] != sn[1]:
                dec_changed.append(subj)
        res["arms"][arm] = {
            "n_standing": len(a), "n_changed_state": sum(len(v) for v in changed_cells.values()),
            "n_decided_value_changed": len(dec_changed), "transitions": dict(trans),
            "changed_cells": {",".join(map(str, c)): v for c, v in changed_cells.items()},
        }
    for (m, cell), (label, sean, agrees) in key_cells().items():
        if m != mov:
            continue
        row = {"label": label, "sean": sean, "agrees_under_W2": agrees}
        subs = sorted(s for s in base if cell_of(s) == cell)
        row["base"] = {s.split("/")[-1]: state(base[s]) for s in subs}
        for arm in ARMS:
            a = load(d, mov, arm)
            if a is not None:
                row[arm] = {s.split("/")[-1]: state(a.get(s)) for s in subs}
        res["key"][",".join(map(str, cell))] = row
    Path(outp).write_text(json.dumps(res, indent=1, default=str))
    for arm, r in res["arms"].items():
        print(f"{mov} {arm}: standing {r['n_standing']}, changed state {r['n_changed_state']}, "
              f"DECIDED value changed {r['n_decided_value_changed']}")
        for k, v in sorted(r["transitions"].items(), key=lambda t: -t[1])[:12]:
            print(f"    {v:6d}  {k}")
    for c, row in res["key"].items():
        print(c, row["label"], "Sean:", row["sean"])
        for k in ("base",) + ARMS:
            if k in row:
                print("    ", k, {g: v for g, v in row[k].items() if v[0] != "absent"})


if __name__ == "__main__":
    main()
