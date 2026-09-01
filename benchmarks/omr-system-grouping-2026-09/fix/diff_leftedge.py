#!/usr/bin/env python3
"""Diff the flag-ON sweep against baseline: which pages did cue A change, and is
each change an over-merge FIX or an over-split REGRESSION? Cue A is union-only,
so every change should be old_n_systems < new_n_systems. A regression = a change
that introduces fragmentation (size-1 systems / a balanced split shattered)."""
import json, re, sys
from collections import defaultdict

HERE = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/system-break-rule-publishers-62ead4/benchmarks/omr-system-grouping-2026-09"
BASE = HERE + "/sweep.jsonl"
NEW = HERE + "/sweep_leftedge.jsonl"

VOCAL = re.compile(r"(te-deum|requiem|mass|messiah|passion|oratorio|cantata|magnificat|"
                   r"stabat|zauberflote|giovanni|figaro|nozze|fidelio|opera|lieder|"
                   r"gesange|vocal|choral|choir|elijah|creation|missa|psalm|carmina|"
                   r"symphony-9|resurrection|damnation|faust|matthau|johannes)", re.I)

def load(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("error") or not r.get("staves_per_system"):
                continue
            d[(r["pdf_rel"], r["page"])] = r
    return d

base, new = load(BASE), load(NEW)
keys = sorted(set(base) & set(new))
print(f"baseline rows {len(base)}  flag-on rows {len(new)}  compared {len(keys)}")

changed, gained, lost_or_other = [], 0, 0
for k in keys:
    b, n = base[k]["staves_per_system"], new[k]["staves_per_system"]
    if b == n:
        continue
    changed.append(k)
    if len(n) > len(b):
        gained += 1
    else:
        lost_or_other += 1  # should be 0 for a union-only splitter

print(f"changed pages: {len(changed)}  (gained systems {gained}, other {lost_or_other})")

def is_vocal(pdf): return bool(VOCAL.search(pdf))
def frag_new(sizes):
    n1 = sum(1 for s in sizes if s == 1)
    return n1 >= 1, n1

# Classify each changed page
print("\n=== every changed page (baseline -> flag-on) ===")
reg_suspect = []
for pdf, pg in changed:
    b = base[(pdf, pg)]["staves_per_system"]
    n = new[(pdf, pg)]["staves_per_system"]
    tok = base[(pdf, pg)].get("publisher_token", "?")
    voc = "VOCAL" if is_vocal(pdf) else "instr"
    new_has1, n1 = frag_new(n)
    # Regression suspects: new introduces a size-1 system, OR a previously balanced
    # multi-system got more pieces, OR one system split into >2.
    old_had1 = any(s == 1 for s in b)
    suspect = (new_has1 and not old_had1) or (len(n) - len(b) >= 3) or \
              (len(b) >= 2 and min(n) <= 2 and min(b) >= 4)
    mark = "  <== REGRESSION-SUSPECT" if suspect else ""
    if suspect:
        reg_suspect.append((pdf, pg, b, n, tok, voc))
    name = pdf.split("/")[-1][:46]
    print(f"  [{voc:5}] {tok:24} {name:48} p{pg:<4} {b} -> {n}{mark}")

print(f"\n=== summary ===")
voc_ch = sum(1 for (pdf, pg) in changed if is_vocal(pdf))
print(f"changed: {len(changed)}  vocal {voc_ch}  instrumental {len(changed)-voc_ch}")
print(f"regression-suspects (need eyeball): {len(reg_suspect)}")
for pdf, pg, b, n, tok, voc in reg_suspect:
    print(f"    [{voc}] {tok} p{pg}: {b} -> {n}")
print("\nInstrumental changes are the ones that matter for Sean's corpus.")
print("A FIX looks like [N] -> [a,b] with balanced a,b. A REGRESSION shatters or adds size-1.")
