"""Direction text's share of wall clock, WITH the page-set regime beside it.

The decision map says "~75% of wall clock on a whole-work run" in three places,
unqualified. This measures the committed corpus -- and the point of the probe is
the `n_pages_processed` column, not the percentage: every committed
transcription is a ONE-PAGE run, so this distribution and the 88-page figure
describe different regimes and must not be differenced.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import chdir_root, fixtures  # fail-loud
chdir_root()

import glob, json
from collections import Counter

rows = []
# ⚠️ WAS a raw `glob.glob` while importing `fixtures` purely for `chdir_root`,
# so the lint's token heuristic saw "fixtures(" and passed it. An empty match
# here still printed a table.
for f in fixtures("benchmarks/**/fixtures/*.omr.json", expect_at_least=11):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    rt = d.get("runtime") or {}
    tot, dt = rt.get("total_s"), rt.get("direction_text_s")
    if not tot or dt is None:
        continue
    rows.append((100.0 * dt / tot, d.get("n_pages_processed"), tot, dt,
                 os.path.basename(f)))

if not rows:
    sys.stderr.write("FATAL: no transcription carried both clocks.\n")
    raise SystemExit(2)

rows.sort()
pct = [r[0] for r in rows]
print(f"n = {len(rows)} committed transcriptions carrying both clocks")
print(f"direction_text share of total_s: min={pct[0]:.1f}%  "
      f"median={pct[len(pct)//2]:.1f}%  max={pct[-1]:.1f}%")
regimes = Counter(r[1] for r in rows)
print(f"⚠️ pages per run: {dict(regimes)}  "
      f"-- {'ALL SINGLE-PAGE' if set(regimes) == {1} else 'MIXED REGIMES'}")
print("\ntail (the density effect, at one page):")
for r in rows[-3:]:
    print(f"   {r[0]:5.1f}%  pages={r[1]}  total={r[2]:.1f}s  dir={r[3]:.1f}s  {r[4][:46]}")
print("head:")
for r in rows[:3]:
    print(f"   {r[0]:5.1f}%  pages={r[1]}  total={r[2]:.1f}s  dir={r[3]:.1f}s  {r[4][:46]}")
