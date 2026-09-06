"""`clef_register_warning` — REACH, then precision. Nobody had measured either.

`docs/scope-identity-upstream-2026-09-06.md` §9 nominates this check as the
best available lever on the clef ceiling, on two structural grounds (it names no
instrument, so it survives where labels do not; it compares two staves, so it
cannot confirm itself) and explicitly records that its REACH is unmeasured.

This dumps every firing over both benchmark families with enough context to
adjudicate it by hand: the two staves, their clefs, their instruments, their
provenance, and their median registers.

    OMR_FIXTURE_ROOT=/path/to/main python3 <this>
"""
from __future__ import annotations

import glob
import json
import os

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def main():
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or "graft09" not in p
                       and "restamp" not in p)
        print(f"\n{'='*76}\n{fam.upper()}\n{'='*76}")
        n_fire = n_staves = 0
        for path in paths:
            doc = json.load(open(path))
            for page in doc.get("pages", []):
                for sysm in page.get("systems", []):
                    sts = sysm.get("staves", [])
                    n_staves += len(sts)
                    by_idx = {s.get("staff_index"): s for s in sts}
                    for st in sts:
                        w = st.get("clef_register_warning")
                        if not w:
                            continue
                        n_fire += 1
                        up = by_idx.get(w.get("upper_staff_index"), {})
                        lo = by_idx.get(w.get("lower_staff_index"), {})
                        print(f"\n{os.path.basename(path)[:46]} "
                              f"p{page.get('page_index')} sys"
                              f"{sysm.get('system_index')}  gap="
                              f"{w.get('register_gap_semitones')}st  "
                              f"{w.get('confidence_label')}")
                        for tag, s, midi in (
                                ("upper", up, w.get("upper_staff_median_midi")),
                                ("lower", lo, w.get("lower_staff_median_midi"))):
                            print(f"   {tag} idx={s.get('staff_index')} "
                                  f"clef={s.get('clef')}"
                                  f"({s.get('clef_source')}) "
                                  f"median_midi={midi} "
                                  f"instrument={s.get('instrument')!r}"
                                  f"({s.get('instrument_source')})")
        print(f"\nREACH: {n_fire} firings over {n_staves} staves "
              f"({n_fire/max(1,n_staves):.1%})")


if __name__ == "__main__":
    main()
