"""Which committed artefact is which arm, and — critically — which REGIME.

⚠️ **PAGE-SET SIZE CHANGES IDENTITY RESULTS.**  This bit three sessions on
2026-09-06.  `--pages 0-4` (what the web app does via `OMR_MAX_PAGES=5`), a
window CROSSING a movement boundary, and a whole work are three different
regimes, and a real fix measured exactly ZERO in two of them.  A harness that
reports one number for a work is misleading; every row here carries its regime
and the runner never pools across regimes.

⚠️⚠️ **AND SO DOES THE CLEF REGIME — measured 2026-09-07.**  Every arm below
except `beet5/shipped` is a `compose.py` REPLAY, which passes
`apply_contextual_analysis` page dicts with no staves; `_read_clefs_by_slot`
then returns `{}` and the score-order layout fit runs blind.  On Beethoven 5
that is worth **51 of 807 judgeable records** (0.9368 clef-blind vs 1.0000 with
a real run's clefs) — 8.5x the largest flag graded here — and it is what made
one transcription arm and one replay arm look like "more evidence, worse
answer".  A flag A/B *within* a block is unaffected (both arms are the same
kind of replay); comparing a replay row with the one transcription row is not.
`benchmarks/omr-readpass-monotonicity-2026-09/FINDINGS.md`.

Everything below is a COMMITTED artefact of an earlier session.  Nothing here
re-transcribes: an arm loads in well under a second where a whole-work read
pass is ~26 minutes.  The arms of a given (work, regime) block all came off ONE
shared read pass, so a difference between them is the flag and nothing else —
`selftest.py` asserts that on the staff-record KEY SET, not on its size.
"""
from __future__ import annotations

B = "benchmarks/"

#: name -> (work, path, regime, note)
ARMS: dict[str, tuple[str, str, str, str]] = {}


def _add(name, work, path, regime, note):
    ARMS[name] = (work, path, regime, note)


# ── Beethoven 5 / Litolff, whole work (88 pages) ─────────────────────────────
_add("beet5/shipped", "beet5",
     B + "omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json",
     "whole work 0-87",
     "the veto session's own whole-work run; the ONLY artefact in the 'staff' "
     "shape, which is what licenses the shape-agreement assertion")

for _flag in ("ordinal", "map"):
    for _sp in ("off", "on"):
        _add(f"beet5/groupmap={_flag},spans={_sp}", "beet5",
             f"{B}omr-slot-alignment-2026-09/out/-{_flag}-spans-{_sp}.json",
             "whole work 0-87",
             "OMR_SLOT_GROUP_MAP A/B off one shared read pass")

for _fit in ("off", "refuse", "search"):
    for _sp in ("off", "on"):
        _add(f"beet5/fit={_fit},spans={_sp}", "beet5",
             f"{B}omr-span-composition-2026-09/out/beet5/-fit{_fit}-spans-{_sp}.json",
             "whole work 0-87",
             "OMR_SPAN_REFERENCE_FIT A/B off one shared read pass")

# ── Brahms 1 / Breitkopf, whole work (86 pages) ──────────────────────────────
for _fit in ("off", "refuse", "search"):
    for _sp in ("off", "on"):
        _add(f"brahms1/fit={_fit},spans={_sp}", "brahms1",
             f"{B}omr-span-composition-2026-09/out/brahms1/-fit{_fit}-spans-{_sp}.json",
             "whole work 0-85",
             "OMR_SPAN_REFERENCE_FIT A/B off one shared read pass")

for _flag in ("ordinal", "map"):
    for _sp in ("off", "on"):
        _add(f"brahms1/groupmap={_flag},spans={_sp}", "brahms1",
             f"{B}omr-slot-alignment-2026-09/out/brahms1/-{_flag}-spans-{_sp}.json",
             "whole work 0-85",
             "OMR_SLOT_GROUP_MAP A/B off one shared read pass")

_add("brahms1/noshape,spans=on", "brahms1",
     B + "omr-span-composition-2026-09/out/brahms1/-noshape-spans-on.json",
     "whole work 0-85",
     "the shape-recurrence tie-break dropped from the candidate tail")
_add("brahms1/noshape,spans=off", "brahms1",
     B + "omr-span-composition-2026-09/out/brahms1/-noshape-spans-off.json",
     "whole work 0-85", "as above, spans off")

# ── The three NARROW regimes (the ones the web app actually runs) ────────────
_REGIME_PAGES = {
    "front": ("narrow at the front (pages 0-4)", "0-4"),
    "cross": ("narrow, crossing a movement boundary", "brahms 40-49 / beet5 39-48"),
    "adhoc": ("two ad-hoc pages", "brahms 30,45 / beet5 23,44"),
}
for _w, _tag in (("brahms1", "brahms"), ("beet5", "beet5")):
    for _reg, (_desc, _pages) in _REGIME_PAGES.items():
        for _fit in ("off", "refuse", "search"):
            for _sp in ("off", "on"):
                _add(f"{_w}/{_reg}:fit={_fit},spans={_sp}", _w,
                     f"{B}omr-span-composition-2026-09/out/regimes/"
                     f"-{_tag}-{_reg}-{_fit}-spans-{_sp}.json",
                     f"{_desc} [{_pages}]",
                     "regime arm — the flag may not even REACH this page set")


def by_regime() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name, (_w, _p, regime, _n) in ARMS.items():
        out.setdefault(regime, []).append(name)
    return out
