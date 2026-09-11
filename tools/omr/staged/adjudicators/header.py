"""The key signature — positions gathered clef-free, named with the clef."""

from __future__ import annotations

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.KEY_SIGNATURE,
    checkable=Checkable.MIXED,
    checked_by=(
        '"the accidental ORDER is fixed (F#-C#-G#... / Bb-Eb-Ab...): a run that SKIPS a slot is impossible"',
        '"across the staves of a system the DELTA is shared, never the value -- transposing parts print different signatures for one key"',
        '"a key CHANGE is printed on every staff at the same bar (key_signature_corroboration -- CONSUMED, default-ON)"',
    ),
    implicates=(Q.KEY_SIGNATURE, Q.CLEF, Q.KEYSIG_RUN_POSITION),
    composed_from=(Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.CLEF),
    scope=Kind.STAFF,
    wants=(Q.KEYSIG_RUN_POSITION, Q.KEYSIG_MARKER, Q.KEYSIG_CLEF_FIT,
           Q.KEYSIG_TEMPLATE_FIT, Q.CLEF, Q.DOSSIER_FACT),
    reasons=("fitted", "fitted_by_template", "needs_clef",
             "run_fits_no_slot_table", "no_run", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_key_signature(ev: Evidence) -> Ruling:
    """The key signature, fitted to the clef that was SETTLED, not guessed.

    ⚠️ THE GUARD MOVED; IT WAS NOT REMOVED. `key_signature_locator.py:310`
    refuses to run without a clef, and it is right to: fitting three flats
    against a guessed clef once returned TWO SHARPS -- a different accidental
    type fitting a different prefix well inside tolerance. GATHER asks the
    reader once per CANDIDATE clef, which is the honest form of the question;
    this decision then reads the answer for the clef that actually won.

    ⚠️ IF THE CLEF ABSTAINED, SO DOES THIS. That is the guard, expressed as a
    dependency rather than as a boolean inside a reader: no clef, no name.

    ⚠️ TWO READERS, AND THE PRECEDENCE IS INHERITED RATHER THAN CHOSEN.
    `key_signature_template` answers GAPS ONLY -- where the locator produced
    no fit for this staff's settled clef. That is the legacy path's own rule
    (`transcribe.py`: *"the reader speaks only into GAPS"*) and the
    alternative is already priced and already REFUSED there: letting the
    fuller reading win *"is worth +1 on beet5-p2 and +2 on the Pastoral and
    costs a WRONG reading on the cleanest page in the corpus"*. The two
    readers fail in opposite directions -- the locator loses accidentals to
    broken ink, the template can match spurious ink and over-count -- so the
    one that cannot invent a glyph goes first.
    """
    clef = ev.verdict(Q.CLEF)
    if clef is None or clef.value is None:
        return Ruling.abstain("needs_clef")

    fits = ev.rows(Q.KEYSIG_CLEF_FIT)
    for row in fits:
        if str(row.value) != str(clef.value):
            continue
        fifths = row.detail.get("fifths")
        if fifths is None:
            continue
        return Ruling(value=int(fifths), reason="fitted",
                      used=(row.id, clef.id),
                      detail={"n_accidentals": row.detail.get("n_accidentals"),
                              "accidental": row.detail.get("accidental"),
                              "decided_by": row.detail.get("decided_by")})

    for row in ev.rows(Q.KEYSIG_TEMPLATE_FIT):
        if str(row.value) != str(clef.value):
            continue
        fifths = row.detail.get("fifths")
        if fifths is None:
            continue
        return Ruling(value=int(fifths), reason="fitted_by_template",
                      used=(row.id, clef.id),
                      detail={"n_accidentals": row.detail.get("n_accidentals"),
                              "accidental": row.detail.get("accidental"),
                              "decided_by": "template"})

    if not fits:
        state = ev.state(Q.KEYSIG_RUN_POSITION)
        return Ruling.abstain("no_run" if state is State.READ
                              else "no_evidence")

    # ⚠️ The run was read and fits SOME slot table, but not the one this
    # staff's settled clef chooses, and the template could not answer for that
    # clef either. That is a CONTRADICTION worth recording rather than a gap --
    # it says the clef and the key disagree, and `implicates` names both.
    return Ruling.abstain("run_fits_no_slot_table",
                          clef=str(clef.value),
                          fits=[str(r.value) for r in fits])
