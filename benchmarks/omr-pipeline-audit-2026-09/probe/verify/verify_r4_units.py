"""VERIFIER round 2 — recompute the meter/clef guard asymmetry, and check UNITS.

`drop_uncorroborated_meter_changes` increments `reverted` inside the per-MEASURE
loop (rhythm.py:666), and its docstring says "how many measures were reverted".
The clef figure (11) counts CHANGES. This checks both and reports them apart.
"""
import json, glob, os
from pathlib import Path
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _os.pardir))
from fixture_root import fixture_glob, repo_glob, repo_root, add_repo_to_syspath  # noqa: E402
# ⚠️ THE VERIFIER HIT THIS BUG ITSELF (VERIFICATION.md §D16): the first cut of
# this file resolved ROOT to the worktree and printed a clean all-zeros table
# before anyone noticed `fixtures/` does not exist here. `fixture_glob` exits 2.

def survey(pat, label):
    rev_measures = 0; meter_changes = 0; clef_changes = 0
    staves = 0; pages = 0; per_page = {}
    for f in fixture_glob(pat, "transcriptions"):
        d = json.load(open(f)); nm = os.path.basename(f).split('.')[0]
        r = 0
        for pg in d.get("pages", []):
            pages += 1
            r += pg.get('uncorroborated_meter_changes_reverted', 0)
            for sy in pg.get("systems", []):
                for st in sy.get("staves", []):
                    staves += 1
                    prev_m = prev_c = None
                    for m in st.get("measures", []):
                        ts = m.get("time_signature")
                        cur_m = (ts.get("numerator"), ts.get("denominator")) if ts else None
                        if cur_m is not None and prev_m is not None and cur_m != prev_m:
                            meter_changes += 1
                        if cur_m is not None: prev_m = cur_m
                        cur_c = m.get("clef")
                        if cur_c is not None and prev_c is not None and cur_c != prev_c:
                            clef_changes += 1
                        if cur_c is not None: prev_c = cur_c
        rev_measures += r
        if r: per_page[nm] = r
    print(f"=== {label}: {pages} pages, {staves} staves")
    print(f"   meter MEASURES reverted (the field the guard writes) : {rev_measures}")
    print(f"   meter CHANGES surviving in the artefact              : {meter_changes}")
    print(f"   clef  CHANGES surviving in the artefact              : {clef_changes}")
    print(f"   per-page reverted-measure counts: {per_page}")

survey('benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json', 'scan')
survey('benchmarks/omr-orchestral-e2e/fixtures/*.omr.json', 'engraved')
