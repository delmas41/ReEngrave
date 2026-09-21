"""The key signature — positions gathered clef-free, named with the clef."""

from __future__ import annotations

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State



def _marker_ink(ev: Evidence) -> dict:
    """What the DETECTOR saw of this staff's key accidentals — RECORDED ONLY.

    ⚠️⚠️ THE COUNT IS NOT THE ANSWER, AND SAYING SO IS THE WHOLE POINT OF
    THIS FUNCTION EXISTING RATHER THAN A `len()` AT THE CALL SITE. Counting
    key markers is a rule this project has already built, measured and
    condemned: on the LEGACY path `transcribe._detect_key_sig_from_cell`
    falls back to counting them where the slot fit abstains, and
    `key_signature_corroboration.py` records what that cost — **seven
    spurious key flips over eleven scanned pages, every one of them landing
    on exactly one accidental** from one stray marker.

    ⚠️ AND THE STAGED RECORD AGREES, FROM ITS OWN SIDE. Over the staves this
    decision DECIDES, the marker count equals `|fifths|` on only **19 of 49**
    (Litolff) and **39 of 76** (Breitkopf) — 39% and 51%. A reading that
    disagrees with the settled answer half the time is not a value; it is
    evidence that ink was there.

    So this returns DETAIL and never a candidate, and the caller may use it
    to say WHICH KIND of silence it is falling into. `markers_without_a_run`
    is an abstention like `no_evidence` — it writes no `<key>` and changes no
    note — and the only thing it changes is what the record says happened.
    """
    marks = ev.rows(Q.KEYSIG_MARKER)
    if not marks:
        # ⚠️ ABSENT AND DECLINED ARE DIFFERENT HERE TOO. `ev.state` separates
        # "the detector produced no row" from "it produced a row saying it saw
        # nothing", and collapsing them would reintroduce, one level down,
        # exactly the fault this detail exists to repair.
        return {"keysig_marker_ink": 0,
                "keysig_marker_state": str(ev.state(Q.KEYSIG_MARKER))}
    return {"keysig_marker_ink": len(marks),
            "keysig_marker_state": str(ev.state(Q.KEYSIG_MARKER)),
            "keysig_marker_classes": sorted({str(m.value) for m in marks}),
            # ⚠️ NOT a proposed value. See this function's docstring: the
            # count agrees with the settled answer on about half the staves.
            "keysig_marker_count_is_not_a_reading": True}


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
             "run_fits_no_slot_table", "no_run", "markers_without_a_run",
             "no_evidence"),
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

    ⚠️⚠️ THE THIRD `checked_by` STATEMENT CANNOT BE PERFORMED HERE, AND IT IS
    NOT AN OVERSIGHT — IT IS STRUCTURALLY ABSENT. *"a key CHANGE is printed on
    every staff at the same bar (key_signature_corroboration -- CONSUMED,
    default-ON)"* describes a LEGACY-path mechanism, and on this path there is
    no mid-staff key change for it to corroborate: this decision is
    `Kind.STAFF` and reads the header, `_gather_keysig_markers` reads
    `R.cell(p, s, i, 0)` — CELL 0 AND NOTHING ELSE — and
    `staged/export.py` carries ONE `fifths` per staff-run. Measured on the two
    shared records: **75 and 97 key verdicts, every one staff-scoped; 105 and
    146 marker rows, every one filed at `cell:0`.** Nothing can express a
    change, so nothing can contradict one.

    ⚠️ `key_signature_corroboration` is ALSO simply not imported here — its
    only non-test import in the tree is `transcribe.py`. But *"wire the
    import"* is the wrong repair and would produce a pass with an empty
    domain: the missing piece is upstream, a key reader that looks past cell
    0, and that is a GATHER change.

    ⚠️ ITS REACH IS MEASURED AND SMALL, WHICH IS WHY THIS IS RECORDED RATHER
    THAN BUILT. Key-accidental classes detected in cells OTHER than cell 0,
    gathered by nothing today: **21 (Litolff, 4 pages) and 2 (Breitkopf, 4
    pages)**. ⚠️⚠️ And the legacy path is the warning about what reading them
    naively would cost: of the 15 later-cell markers it does read across 11
    scanned pages, **7 CHANGED THE KEY AND ALL SEVEN WERE WRONG**. So a
    mid-staff key reader must arrive WITH its corroboration, not before it —
    which is the one thing the staged path can say that the legacy path
    could not, because here the guard would be designed in rather than bolted
    on. Full measurement:
    `benchmarks/omr-keysig-staged-reach-2026-09/FINDINGS.md`.

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
        if state is State.READ:
            return Ruling.abstain("no_run", **_marker_ink(ev))
        # ⚠️⚠️ `no_evidence` WAS WRONG ON ROUGHLY HALF THE STAVES IT WAS
        # REPORTED ON, and `Q.KEYSIG_MARKER` — declared in `wants` AND in
        # `composed_from` since this decision was written, and read by NOTHING
        # until 2026-09-21 — is what says so. Measured on the two shared
        # records: of the staves abstaining `no_evidence`, **7 of 17**
        # (Litolff) and **9 of 20** (Breitkopf) carry detected key
        # accidentals. The CV header reader could not speak; the DETECTOR saw
        # ink. Reporting that as "no evidence" is the ABSENT/DECLINED collapse
        # this record exists to prevent, and it sends the next person to the
        # wrong module: *nothing was printed here* wants a reader, *we could
        # not fit what was printed* wants a fitter.
        #
        # ⚠️ THE STATED REASON FOR LEAVING IT UNREAD WAS FALSE. The gap lists
        # excused it as *"the decision reads `keysig_clef_fit`, which the
        # markers already feed in GATHER"*. They do not: `Q.KEYSIG_CLEF_FIT`
        # comes from `locate_key_signature` on the header CROP, and the one
        # place detections enter that call is `_occupied_boxes`, which filters
        # to NOTEHEADS. The markers feed nothing at all.
        marks = ev.rows(Q.KEYSIG_MARKER)
        if marks:
            return Ruling.abstain("markers_without_a_run", **_marker_ink(ev))
        return Ruling.abstain("no_evidence", **_marker_ink(ev))

    # ⚠️ The run was read and fits SOME slot table, but not the one this
    # staff's settled clef chooses, and the template could not answer for that
    # clef either. That is a CONTRADICTION worth recording rather than a gap --
    # it says the clef and the key disagree, and `implicates` names both.
    return Ruling.abstain("run_fits_no_slot_table",
                          clef=str(clef.value),
                          fits=[str(r.value) for r in fits],
                          **_marker_ink(ev))
