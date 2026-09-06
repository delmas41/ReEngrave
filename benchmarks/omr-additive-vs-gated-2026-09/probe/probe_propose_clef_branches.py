"""WHICH cutoff in `propose_clef` returns None, per staff -- attribution, not a
total.

`clef_correction.propose_clef` has six `return None` exits and the module
records none of them, so "the fill tier reaches 0" is a number with no cause.
This replays the function's own arithmetic (its helpers, its constants) over
every staff in both benchmark families and reports which exit each staff took.
Reads committed transcriptions only; changes nothing.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from tools.omr.clef_correction import (  # noqa: E402
    CANDIDATE_CLEFS, MIN_FIT, MIN_FIT_MARGIN, MIN_NOTEHEADS, _CLEF_ANCHORS,
    _midis_under, range_fit)
from tools.omr.pitch_resolver import clef_diatonic_shift  # noqa: E402
from tools.omr.instruments import lookup  # noqa: E402

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def branch(staff, instrument):
    """The exit `propose_clef` takes, and the fits it computed on the way."""
    current = staff.get("clef")
    if current not in _CLEF_ANCHORS:
        return "no_anchor_clef", None
    lo, hi = instrument.written_range
    fits, n = {}, 0
    for cand in CANDIDATE_CLEFS:
        delta = clef_diatonic_shift(current, cand)
        if delta is None:
            continue
        midis = _midis_under(staff, delta)
        n = max(n, len(midis))
        fits[cand] = range_fit(midis, lo, hi)
    if n < MIN_NOTEHEADS or not fits:
        return "too_few_noteheads", fits
    current_fit = fits.get(current, 0.0)
    ranked = sorted(fits.items(), key=lambda kv: -kv[1])
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    default = instrument.default_clef
    if fits.get(default, 0.0) >= MIN_FIT:
        chosen, chosen_fit = default, fits[default]
    else:
        chosen, chosen_fit = ranked[0]
        if chosen_fit < MIN_FIT or (chosen_fit - runner_up) < MIN_FIT_MARGIN:
            return "range_alone_not_decisive", fits
    if chosen == current:
        return "already_in_effect", fits
    if chosen_fit < current_fit:
        return "would_worsen_register", fits
    return f"PROPOSAL {current}->{chosen}", fits


def main():
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or ("graft09" not in p
                                            and "restamp" not in p))
        tally = {"read": collections.Counter(), "unread": collections.Counter()}
        detail = []
        for path in paths:
            for page in json.load(open(path)).get("pages", []):
                for sysm in page.get("systems", []):
                    for st in sysm.get("staves", []):
                        name = st.get("instrument")
                        key = "read" if st.get("clef_source") else "unread"
                        if not name:
                            tally[key]["no_instrument"] += 1
                            continue
                        match = lookup(name)
                        inst = getattr(match, "instrument", None)
                        if inst is None or getattr(inst, "unpitched", False) \
                                or not getattr(inst, "written_range", None):
                            tally[key]["instrument_unusable"] += 1
                            continue
                        b, fits = branch(st, inst)
                        tally[key][b.split()[0]] += 1
                        if b.startswith("PROPOSAL"):
                            detail.append((os.path.basename(path)[:34], key,
                                           st.get("staff_index"), name, b,
                                           {k: round(v, 2)
                                            for k, v in (fits or {}).items()}))
        print(f"\n{'='*76}\n{fam.upper()}: which exit `propose_clef` takes\n"
              f"{'='*76}")
        for key in ("unread", "read"):
            tot = sum(tally[key].values())
            print(f"\n  clef {key.upper()}  (n={tot})"
                  + ("   <- the FILL tier's population; only this one may APPLY"
                     if key == "unread" else
                     "   <- proposals here are recorded, never applied"))
            for b, c in tally[key].most_common():
                print(f"     {b:28s} {c:5d}  {c/max(1,tot):6.1%}")
        for row in detail:
            print("   *", row)


if __name__ == "__main__":
    main()
