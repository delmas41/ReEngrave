"""The positional prior may not move a staff onto an instrument another label
on the same system already names.

⚠️ THE THIRD INSTANCE OF THE AMBIGUOUS-ALIAS FAMILY (after `c0a80ae7` and
`fa8258c1`), and the first whose fault is in the PRIOR rather than in a consumer
of it. Beethoven 5 / Litolff (imslp984073) prints `Tr.` over the trumpets and
`Tp.` over the timpani on one system. `lookup('Tp.')` returns Timpani at `high`
— the lexicon is right — but `Tp.` is ambiguous, so the slot goes to
`score_layouts.resolve_ambiguous_label`, the canonical layout has the timpani
AFTER the trombones (this edition puts it between the trumpets and the
trombones, the same deviation `score_layouts` documents where it explains
pinning), the monotone aligner hands staff 8 the second trumpet slot, and the
timpani exported as a SECOND TRUMPET — 2 of that page set's 5 wrong names.

The evidence was already on the page and needed no lexicon change: an engraver
does not name one section with two different abbreviations on one system, so
`Tr.` standing four staves up says `Tp.` is not the trumpets.

⚠️ THE CONSTRAINT IS ASYMMETRIC AND THE TESTS BELOW PIN BOTH HALVES. It refuses
only an OVERTURN and never removes the lexicon's own answer, because on
Beethoven 5 p.48 `Tr. Bas.` has BOTH its candidates separately named on the
system (`Tr. Alt.`/`Tr. Ten.` for Trombone, `Tr.` for Trumpet) — a rule that
excluded every clashing candidate would leave nothing and would break a reading
that is already right.

Measured over the 1422-label margin corpus
(`benchmarks/omr-absent-instrument-veto-2026-09/probe/probe_ambiguous_cooccurrence.py`):
86 of 158 ambiguous-alias occurrences share a page with a different alias naming
one of their candidates, and the rule keeps or restores the right answer in 86
of 86 while blocking a correct overturn in 0.

`test_an_overturn_the_system_does_not_contradict_still_happens` is the control
that matters — it is `c0a80ae7`'s measured win (`Basso.` at the foot of an
orchestral score overturned from a singer to the contrabasses) and it must
survive. Every test here has been run RED with the guard removed.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.omr import contextual
from tools.omr.instruments import lookup
from tools.omr.staff_labels import StaffLabel


def _label(staff_index: int, text: str) -> StaffLabel:
    """A label as the readers deliver one: resolved through the real lexicon."""
    match = lookup(text)
    assert match is not None, f"the lexicon no longer reads {text!r}"
    return StaffLabel(
        staff_index=staff_index,
        text=text,
        instrument=match.instrument,
        fifths_offset=0,
        y_center_px=100.0 * staff_index,
        confidence=match.confidence,
        alias=match.alias,
    )


class _Fit:
    """A layout fit that proposes one instrument per ordinal, unconditionally."""

    def __init__(self, proposals: dict[int, str]):
        self._proposals = proposals

    def instrument_for(self, ordinal: int):
        return self._proposals.get(ordinal)

    def support_for(self, ordinal: int):
        name = self._proposals.get(ordinal)
        return {name: 1.0} if name else {}


def _resolve(labels, fit_proposals):
    """Run the resolver over ONE system and report the slot -> name it left."""
    staves = [SimpleNamespace(staff_index=lab.staff_index, system_index=0)
              for lab in labels]
    pws = SimpleNamespace(staves=staves)
    slot_by_staff = {(0, 0, lab.staff_index): lab.staff_index for lab in labels}
    reference = [SimpleNamespace(index=lab.staff_index, instrument=None)
                 for lab in labels]
    instrument_by_slot = {lab.staff_index: lab.instrument for lab in labels}
    instrument_source = {lab.staff_index: "label" for lab in labels}

    contextual._resolve_ambiguous_labels(
        reference, [labels], slot_by_staff, [0], [pws],
        _Fit(fit_proposals), instrument_by_slot, instrument_source)

    return ({slot: inst.name for slot, inst in instrument_by_slot.items()},
            instrument_source)


def test_the_timpani_is_not_renamed_a_second_trumpet():
    """The reported bug, in its own geometry.

    `Tr.` on staff 4 and `Tp.` on staff 5, and a fit that wants a trumpet at
    both. The prior must keep its hands off staff 5.
    """
    labels = [_label(4, "Tr."), _label(5, "Tp.")]
    names, source = _resolve(labels, {4: "Trumpet", 5: "Trumpet"})

    assert names[5] == "Timpani", (
        "the timpani was renamed a second trumpet. The positional prior "
        "overturned a `high`-confidence lexicon answer onto an instrument the "
        "SAME SYSTEM already names separately (`Tr.` on staff 4) — which is "
        "exactly the evidence that says it is wrong.")
    assert names[4] == "Trumpet"
    assert source[5] == "label", (
        "the slot kept the right name but was re-stamped as deduced from "
        "position; it was read off the page and should still say so")


def test_an_overturn_the_system_does_not_contradict_still_happens():
    """⚠️ THE CONTROL. This is `c0a80ae7`'s measured win and it must survive.

    `Basso.` at the foot of an orchestral score resolves to `Bass voice` in the
    lexicon and is overturned to the contrabasses BY POSITION. Nothing on the
    system names Contrabass separately, so the new constraint has nothing to say
    and must stay silent. Measured over the whole 1422-label corpus: no
    orchestral page names Contrabass twice — every such clash is Handel's.
    """
    labels = [_label(0, "Violoncello"), _label(1, "Basso.")]
    assert labels[1].instrument.name == "Bass voice", (
        "the premise moved: `Basso.` no longer reads as a singer in the "
        "lexicon, so this test is no longer exercising the overturn")

    names, source = _resolve(labels, {0: "Cello", 1: "Contrabass"})

    assert names[1] == "Contrabass", (
        "the constraint blocked an overturn nothing on the system contradicts. "
        "It must refuse ONLY where a different alias already names the "
        "instrument the prior wants to move to.")
    assert source[1] == "score_order_ambiguity"


def test_both_candidates_named_keeps_the_lexicon_answer():
    """⚠️ Why the constraint is asymmetric, on the page that forces it.

    Beethoven 5 p.48: `Tr.` (Trumpet), `Tr. Alt.` and `Tr. Ten.` (Trombone),
    and `Tr. Bas.` — whose candidates are Trombone and Trumpet, BOTH of them
    separately named. Excluding every clashing candidate would leave nothing;
    refusing only the overturn leaves the lexicon's Trombone, which is right.
    """
    labels = [_label(7, "Tr."), _label(9, "Tr. Alt."),
              _label(10, "Tr. Ten."), _label(11, "Tr. Bas.")]
    assert labels[3].instrument.name == "Trombone"

    names, _ = _resolve(labels, {7: "Trumpet", 9: "Trombone",
                                 10: "Trombone", 11: "Trumpet"})

    assert names[11] == "Trombone", (
        "the bass trombone was renamed a trumpet. Both of its candidates are "
        "named on this system, so a rule that excluded clashing candidates "
        "would have had nothing left to choose — the constraint must refuse "
        "the overturn and fall back on the lexicon.")


def test_the_same_alias_twice_does_not_block_itself():
    """Two staves of one section carry the SAME alias, and must not veto it.

    `Tr. I` and `Tr. II` both normalize to `tr`. The constraint keys on the
    alias, so a section printed across two staves has to be invisible to it —
    otherwise every divided section would block its own reading.
    """
    labels = [_label(4, "Tp."), _label(5, "Tp.")]
    names, _ = _resolve(labels, {4: "Trumpet", 5: "Trumpet"})
    assert names[4] == "Trumpet" and names[5] == "Trumpet", (
        "a label blocked an overturn that only IT supported — the constraint "
        "must ignore other staves carrying the same alias")


@pytest.mark.parametrize("text", ["Tp.", "Basso.", "Tr. Bas.", "Cor."])
def test_the_aliases_this_guards_are_still_ambiguous(text):
    """The premise, stated rather than assumed.

    If one of these became unambiguous the resolver would stop seeing it, and
    this file would pass while guarding nothing.
    """
    from tools.omr.instruments import candidates_for_alias
    match = lookup(text)
    assert match is not None and len(candidates_for_alias(match.alias)) >= 2, (
        f"{text!r} is no longer an ambiguous alias. That may be an improvement, "
        f"but re-point these tests rather than deleting them.")
