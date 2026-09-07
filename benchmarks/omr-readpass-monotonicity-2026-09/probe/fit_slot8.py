#!/usr/bin/env python3
"""The mechanism, isolated to one call: what does the layout fit put at slot 8?

`_resolve_ambiguous_labels` asks `resolve_ambiguous_label(slot, candidates,
fit)`, which returns whichever CANDIDATE the fit proposes at that ordinal.  For
`Tp.` the candidates are Timpani and Trumpet.  So the whole disagreement between
a transcription and an identity-only replay reduces to one question: what does
`fit_layouts` propose at ordinal 8 with, and without, the clefs?

The labels handed in are the reference lineup's own resolved names MINUS the
ambiguous slots (8 and 16), which is exactly what `contextual` builds as
`fit_labels`.  The clefs are the per-slot majority of a real run's readings.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.score_layouts import fit_layouts, resolve_ambiguous_label  # noqa
from tools.omr.instruments import candidates_for_alias                    # noqa

LABELS = {0: "Piccolo", 1: "Flute", 2: "Oboe", 3: "Clarinet", 4: "Bassoon",
          5: "Contrabassoon", 6: "Horn", 7: "Trumpet",
          9: "Trombone", 10: "Trombone", 11: "Trombone",
          12: "Violin", 13: "Violin", 14: "Viola", 15: "Cello"}
# per-slot majority read clef, from probe/slot_clefs.py on the real run
CLEFS = {0: "treble", 1: "treble", 2: "treble", 3: "treble", 4: "bass",
         5: "bass", 6: "treble", 7: "treble", 8: "bass", 9: "alto",
         10: "tenor", 11: "bass", 12: "treble", 13: "treble", 14: "treble",
         15: "bass", 16: "bass"}

cands = candidates_for_alias("tp")
print("candidates for the alias `tp`:", [c.name for c in cands])
for tag, clefs in (("clef-blind (an identity-only replay)", {}),
                   ("with the real run's clefs", CLEFS)):
    fit = fit_layouts(17, labels=LABELS, clefs=clefs)
    proposed = fit.instrument_for(8) if fit else None
    chosen = resolve_ambiguous_label(8, cands, fit)
    print(f"  {tag:38s} fit proposes {proposed!r:12s} "
          f"-> ambiguous alias resolves to {chosen.name if chosen else None!r}")
