"""ROADMAP 2.39 -- per-consumer changed-row diff between a base and a new
GATHER-through-ADJUDICATE record on the SAME page, SAME weights, SAME
settings.

Compares VERDICTS (by (subject, quantity)) for the quantities each of the
five 2.39 connections can move, plus OBSERVATIONS for Q.LEDGER_RUNG_INK /
Q.NOTEHEAD_INK (GATHER rows, not verdicts) since those are the direct
witnesses two of the five connections write.

Usage: python3 diff_2.39_ab.py base.json new.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

VERDICT_QUANTITIES = [
    "notehead_is_not_a_notehead", "glyph_owner", "duration",
    "notehead_is_a_whole_rest",
]
OBSERVATION_QUANTITIES = ["ledger_rung_ink", "notehead_ink", "stem", "beam_stroke"]


def _load(path):
    with open(path) as f:
        return json.load(f)["record"]


def _verdict_index(record, quantity):
    out = {}
    for v in record["verdicts"]:
        if v["quantity"] == quantity:
            out[v["subject"]] = v
    return out


def _obs_index(record, quantity):
    out = defaultdict(list)
    for o in record["observations"]:
        if o["quantity"] == quantity:
            out[o["subject"]].append(o)
    return out


def diff_verdicts(base, new, quantity):
    b = _verdict_index(base, quantity)
    n = _verdict_index(new, quantity)
    subjects = sorted(set(b) | set(n))
    changed = []
    for s in subjects:
        bv, nv = b.get(s), n.get(s)
        b_key = None if bv is None else (bv["outcome"], bv["value"], bv["reason"])
        n_key = None if nv is None else (nv["outcome"], nv["value"], nv["reason"])
        if b_key != n_key:
            changed.append((s, b_key, n_key))
    return changed


def diff_observation_counts(base, new, quantity):
    b = _obs_index(base, quantity)
    n = _obs_index(new, quantity)
    subjects = sorted(set(b) | set(n))
    changed = []
    for s in subjects:
        bl, nl = len(b.get(s, [])), len(n.get(s, []))
        bv = [round(o["value"], 4) if isinstance(o["value"], float) else o["value"]
              for o in b.get(s, [])]
        nv = [round(o["value"], 4) if isinstance(o["value"], float) else o["value"]
              for o in n.get(s, [])]
        if bl != nl or sorted(map(str, bv)) != sorted(map(str, nv)):
            changed.append((s, bv, nv))
    return changed


def main():
    base_path, new_path = sys.argv[1], sys.argv[2]
    base, new = _load(base_path), _load(new_path)
    print(f"base={base_path} new={new_path}")
    for q in VERDICT_QUANTITIES:
        changed = diff_verdicts(base, new, q)
        print(f"  verdict {q}: {len(changed)} changed rows")
        for s, bk, nk in changed[:20]:
            print(f"    {s}: base={bk} new={nk}")
    for q in OBSERVATION_QUANTITIES:
        changed = diff_observation_counts(base, new, q)
        print(f"  observation {q}: {len(changed)} changed subjects")
        for s, bv, nv in changed[:10]:
            print(f"    {s}: base={bv} new={nv}")


if __name__ == "__main__":
    main()
