#!/usr/bin/env python3
"""Fast targeted re-check: re-run ONLY the 43 pages cue A changed, now with the
size-1 guard live (OMR_LEFT_EDGE_SPLIT=1), and classify each vs baseline.
Goal: the 16 regression-suspects revert to baseline; the ~27 fixes stay."""
import json, os, re, sys
from pathlib import Path

os.environ["OMR_LEFT_EDGE_SPLIT"] = "1"  # guarded cue A
ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/system-break-rule-publishers-62ead4")
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

HERE = ROOT / "benchmarks/omr-system-grouping-2026-09"
EDITIONS = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")

def load(path):
    d = {}
    for line in open(path):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        if r.get("error") or not r.get("staves_per_system"): continue
        d[(r["pdf_rel"], r["page"])] = r
    return d

base = load(HERE / "sweep.jsonl")
oldflag = load(HERE / "sweep_leftedge.jsonl")
changed = [k for k in sorted(set(base) & set(oldflag))
           if base[k]["staves_per_system"] != oldflag[k]["staves_per_system"]]
print(f"re-checking {len(changed)} changed pages with the size-1 guard\n")

def sizes_now(row):
    pdf_rel = row["pdf_rel"]
    p = Path(pdf_rel) if os.path.isabs(pdf_rel) else EDITIONS / pdf_rel
    if not p.exists():
        return None
    pi = render_page(str(p), row["page"], dpi=row["dpi"])
    pws = detect_staves(pi)
    from collections import Counter
    c = Counter(s.system_index for s in pws.staves)
    return [c[k] for k in sorted(c)]

reverted = kept_fix = still_diff = err = 0
for k in changed:
    b = base[k]["staves_per_system"]
    old = oldflag[k]["staves_per_system"]
    now = sizes_now(base[k])
    if now is None:
        print(f"  MISSING {k[0][:44]} p{k[1]}"); err += 1; continue
    name = k[0].split("/")[-1][:42]
    if now == b:
        reverted += 1
        tag = "reverted-to-baseline"
    elif len(now) > len(b) and 1 not in now:
        kept_fix += 1
        tag = "FIX kept"
    else:
        still_diff += 1
        tag = "still-differs"
    print(f"  [{tag:20}] {name:44} p{k[1]:<4} base {b}  oldflag {old}  now {now}")

print(f"\n=== summary (guard live) ===")
print(f"reverted to baseline (regressions removed): {reverted}")
print(f"FIX kept (over-merge still split, no size-1): {kept_fix}")
print(f"still differs (inspect): {still_diff}   missing: {err}")
