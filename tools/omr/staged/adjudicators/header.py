"""The key signature — positions gathered clef-free, named with the clef."""

from __future__ import annotations

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.KEY_SIGNATURE,
    checkable=Checkable.MIXED,
    checked_by=(
        "the accidental ORDER is fixed (F#-C#-G#... / Bb-Eb-Ab...): a run that SKIPS a slot is impossible",
        "across the staves of a system the DELTA is shared, never the value -- transposing parts print different signatures for one key",
        "a key CHANGE is printed on every staff at the same bar (key_signature_corroboration -- CONSUMED, default-ON)",
    ),
    implicates=(Q.KEY_SIGNATURE, Q.CLEF, Q.KEYSIG_RUN_POSITION),
    composed_from=(Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.CLEF),
    scope=Kind.STAFF,
    wants=(Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.CLEF, Q.DOSSIER_FACT),
    reasons=("fitted", "needs_clef", "no_run", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_key_signature(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB, and the shape of the fix is the interesting part.

    The accidental run's POSITIONS are pure geometry and are gathered without
    a clef. Choosing the SLOT TABLE needs the clef -- and that is the whole
    of the dependency. So this decision:

      * reads `Q.CLEF` as a VERDICT (not as a reading), so if the clef
        abstained, this abstains too with `needs_clef` -- rather than fitting
        against a guess. ⚠️ That guard is paid for: fitting three flats
        against a guessed clef once returned TWO SHARPS, a different
        accidental type fitting a different prefix well inside tolerance.
        `transcribe.py:4670-4679` says so in the code's own comment --
        "reading a key signature against a guessed clef is guessing twice".
      * may only SEED where nothing was read. The reader speaks into GAPS.
        Letting a fuller reading win instead was measured: +1 on beet5-p2,
        +2 on the Pastoral, and a WRONG reading on the cleanest page in the
        corpus. Priced and refused.
      * ⚠️ MUST NOT INFER. `fit_key_signature` recovers slots nothing was
        detected at, which is right for a reader that only ever LOSES
        accidentals; a template reader can GAIN a spurious match, and
        inference once compounded five matches into SEVEN SHARPS on a
        four-sharp page.
      * ⚠️ MUST NOT CARRY ACROSS SYSTEMS. One staff's spurious fifth sharp
        was carried onto every treble staff of all five systems, taking a
        page from 10 correct to 5 correct and 5 wrong.

    ⚠️ AND THE CORROBORATION IT REPLACES ALREADY WORKS.
    `key_signature_corroboration` is the ONE existing decision in the tree
    shaped like this design -- it consumes the vote evidence, returns a value
    AND a record, and went default-ON on 2026-09-07. Port it; do not rewrite
    it.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
