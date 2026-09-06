"""The absent-instrument veto: what it refuses, and what it must not touch."""

from __future__ import annotations

import pytest

from tools.omr.absent_instrument import (DEFAULT_RULE, DEFAULT_WINDOW,
                                         attested_pages, find_vetoes,
                                         veto_config)


class TestVetoConfig:
    @pytest.mark.parametrize("raw", ["", "0", "off", "no", "false", "nonsense"])
    def test_off_is_the_default_and_the_fallback(self, raw):
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": raw})[0] == "off"

    def test_unset_is_on_and_zero_turns_it_off(self):
        """Default flipped ON 2026-09-06: 91 impossible instruments to 0, and
        on the 807 adjudicable staves 7 vetoes of which all 7 removed a WRONG
        name. It refuses rather than renames, so its failure is an unnamed
        staff. See `DEFAULT_MODE` for the cost and the pairing.
        """
        assert veto_config({})[0] == "apply"
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "0"})[0] == "off"
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "off"})[0] == "off"

    def test_report_changes_nothing_but_records(self):
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "report"})[0] == "report"

    def test_on_takes_the_default_window_and_rule(self):
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "on"}) == (
            "apply", DEFAULT_WINDOW, DEFAULT_RULE)

    def test_a_bare_integer_is_a_window(self):
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "5"}) == (
            "apply", 5, DEFAULT_RULE)

    def test_rule_prefix(self):
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "window:3"}) == (
            "apply", 3, "window")
        assert veto_config({"OMR_ABSENT_INSTRUMENT_VETO": "span:0"}) == (
            "apply", 0, "span")


# A three-part document. Slots: 0 Flute, 1 Violin, 2 Trombone.
#   Flute     labelled on every page
#   Violin    labelled on pages 0 and 9 only — the "read here, missed there"
#             case Litolff's strings actually produce
#   Trombone  labelled from page 8 on — it enters in the finale
EVIDENCE = {
    0: {0: "Flute", 1: "Violin"},
    1: {0: "Flute"},
    4: {0: "Flute"},
    8: {0: "Flute", 2: "Trombone"},
    9: {0: "Flute", 1: "Violin", 2: "Trombone"},
}
NAMES = {0: "Flute", 1: "Violin", 2: "Trombone"}
SOURCE = {0: "label", 1: "label", 2: "label"}


def _keys_and_slots(page, staff_slots):
    keys = [(page, 0, s) for s in staff_slots]
    return keys, {(page, 0, s): s for s in staff_slots}


def _run(page, staff_slots, *, window, rule):
    keys, sbs = _keys_and_slots(page, staff_slots)
    return {v["instrument"] for v in find_vetoes(
        staff_keys=keys, slot_by_staff=sbs, instrument_name_by_slot=NAMES,
        instrument_source=SOURCE, evidence=EVIDENCE, window=window, rule=rule)}


class TestTheVeto:
    def test_attested_pages_is_the_inverted_evidence(self):
        att = attested_pages(EVIDENCE)
        assert att["Trombone"] == {8, 9}
        assert att["Violin"] == {0, 9}

    def test_an_instrument_that_enters_later_is_vetoed_early(self):
        # page 4: the trombones do not exist yet under either reading.
        assert _run(4, [2], window=0, rule="span") == {"Trombone"}
        assert _run(4, [2], window=0, rule="window") == {"Trombone"}

    def test_a_staff_that_carries_its_own_label_is_never_vetoed(self):
        # Page 8 labels staff 2 as Trombone, so it speaks for itself even at
        # window 0 — the veto only ever removes a name carried from elsewhere.
        assert _run(8, [2], window=0, rule="span") == set()

    @pytest.mark.parametrize("rule", ["span", "window"])
    def test_a_name_the_score_order_prior_deduced_is_out_of_scope(self, rule):
        keys, sbs = _keys_and_slots(4, [2])
        assert find_vetoes(staff_keys=keys, slot_by_staff=sbs,
                           instrument_name_by_slot=NAMES,
                           instrument_source={2: "score_order"},
                           evidence=EVIDENCE, window=0, rule=rule) == []

    def test_THE_UNLABELLED_INSTRUMENT_SEPARATES_THE_TWO_RULES(self):
        """Page 4's violin is unlabelled *there* and labelled either side.

        This is the case the whole veto lives or dies on: `absent because
        unlabelled` must not be read as `absent because tacet`. The window rule
        cannot tell them apart at any window narrower than the gap; the span
        rule does, because page 4 lies inside Violin's [0, 9] attestation.
        """
        assert _run(4, [1], window=0, rule="span") == set()
        assert _run(4, [1], window=3, rule="window") == {"Violin"}

    def test_the_span_rule_still_refuses_a_page_past_the_last_attestation(self):
        assert _run(20, [1], window=2, rule="span") == {"Violin"}

    def test_the_window_widens_the_span_symmetrically(self):
        assert _run(6, [2], window=0, rule="span") == {"Trombone"}
        assert _run(6, [2], window=2, rule="span") == set()

    def test_an_instrument_attested_nowhere_is_left_alone(self):
        keys, sbs = _keys_and_slots(4, [0])
        assert find_vetoes(staff_keys=keys, slot_by_staff=sbs,
                           instrument_name_by_slot={0: "Ophicleide"},
                           instrument_source={0: "label"}, evidence=EVIDENCE,
                           window=0, rule="span") == []

    def test_the_record_says_why(self):
        keys, sbs = _keys_and_slots(4, [2])
        (rec,) = find_vetoes(staff_keys=keys, slot_by_staff=sbs,
                             instrument_name_by_slot=NAMES,
                             instrument_source=SOURCE, evidence=EVIDENCE,
                             window=0, rule="span")
        assert rec["instrument"] == "Trombone"
        assert rec["attested_first"] == 8 and rec["attested_last"] == 9
        assert rec["nearest_attested_page"] == 8
        assert rec["distance_pages"] == 4
        assert rec["pages_outside"] == 4


class TestAnchoring:
    """A staff its own system's labels already force is not a guess.

    Both sides, reproduced from the Beethoven 5 measurements: page 1 loses only
    `Oboi.` to the margin reader and the oboe staff sits between a labelled
    Flute and a labelled Clarinet — one staff, one slot, no freedom. Page 23's
    string staves take the trombone slots with a labelled Timpani above and
    nothing labelled below them at all.
    """

    # Reference: 0 Fl, 1 Ob, 2 Cl, 3 Timp, 4 Tbn, 5 Tbn, 6 Vln
    NAMES = {0: "Flute", 1: "Oboe", 2: "Clarinet", 3: "Timpani",
             4: "Trombone", 5: "Trombone", 6: "Violin"}
    SOURCE = {k: "label" for k in NAMES}
    # Trombone attested only on the late page; everything else on both.
    EV = {0: {0: "Flute", 20: "Clarinet", 30: "Timpani", 60: "Violin"},
          9: {0: "Flute", 1: "Oboe", 2: "Clarinet", 3: "Timpani",
              4: "Trombone", 5: "Trombone", 6: "Violin"}}

    def _vetoes(self, page, pairs, **kw):
        sbs = {(page, 0, si): slot for si, slot in pairs}
        sbs.update({(9, 0, i): i for i in range(7)})
        return {(v["staff_index"], v["instrument"]) for v in find_vetoes(
            staff_keys=list(sbs), slot_by_staff=sbs,
            instrument_name_by_slot=self.NAMES, instrument_source=self.SOURCE,
            evidence=self.EV, window=0, rule="span", **kw)}

    def test_a_staff_bracketed_by_consecutive_labelled_slots_is_exempt(self):
        # staff 10 (slot 1, Oboe) between staff 0 (slot 0) and staff 20 (slot 2)
        assert self._vetoes(0, [(0, 0), (10, 1), (20, 2)]) == set()

    def test_and_is_vetoed_once_the_exemption_is_turned_off(self):
        assert self._vetoes(0, [(0, 0), (10, 1), (20, 2)],
                            anchored_exempt=False) == {(10, "Oboe")}

    def test_a_staff_with_nothing_labelled_below_is_not_anchored(self):
        # Timpani labelled above (slot 3); the two trombone staves below carry
        # no label and there is nothing labelled under them.
        assert self._vetoes(0, [(0, 0), (30, 3), (40, 4), (50, 5)]) == {
            (40, "Trombone"), (50, "Trombone")}

    def test_anchoring_needs_the_arithmetic_to_CLOSE_not_merely_two_labels(self):
        # Labelled above at slot 0 and below at slot 6, with two staves between:
        # slots are skipped somewhere in that stretch, so the trombone staves
        # are not forced and stay vetoable.
        assert self._vetoes(0, [(0, 0), (40, 4), (50, 5), (60, 6)]) == {
            (40, "Trombone"), (50, "Trombone")}


class TestTheSystemsOwnEndsAreAnchorsToo:
    """A run of unlabelled staves at the top or bottom of a system.

    Before the first staff lies slot -1 and after the last lies slot `n`, both
    known exactly, so the same monotone-DP arithmetic that anchors a staff
    between two labels anchors a run against a boundary. Passing no
    `reference_size` withholds the boundaries, which is what every test above
    relies on.

    This is what keeps Beethoven 5's finale strings. They are attested on four
    pages of eighty-eight — Litolff labels strings at movement starts only — so
    on every finale page after 44 they sit outside their own span, and every one
    of those pages prints the full lineup with the string block running to the
    foot of the system. Worth 174 wrongly-vetoed staves over the whole work.
    """

    NAMES = {0: "Flute", 1: "Oboe", 2: "Clarinet", 3: "Trombone", 4: "Violin"}
    SOURCE = {k: "label" for k in NAMES}
    EV = {0: {10: "Oboe"},                       # only the oboe read here
          9: {i * 10: n for i, n in NAMES.items()}}
    FULL = [(0, 0), (10, 1), (20, 2), (30, 3), (40, 4)]

    def _vetoes(self, pairs, **kw):
        sbs = {(0, 0, si): slot for si, slot in pairs}
        sbs.update({(9, 0, i * 10): i for i in range(5)})
        return {(v["staff_index"], v["instrument"]) for v in find_vetoes(
            staff_keys=list(sbs), slot_by_staff=sbs,
            instrument_name_by_slot=self.NAMES, instrument_source=self.SOURCE,
            evidence=self.EV, window=0, rule="span", **kw)}

    def test_a_full_system_is_entirely_forced(self):
        # 5 staves, 5 slots: no gap is reachable, so every staff is forced even
        # though only the oboe carries a label — including the trombone, which
        # this page has no business naming but did not GUESS.
        assert self._vetoes(self.FULL, reference_size=5) == set()

    def test_and_without_the_boundary_the_same_system_is_stripped(self):
        assert self._vetoes(self.FULL) == {(0, "Flute"), (20, "Clarinet"),
                                           (30, "Trombone"), (40, "Violin")}

    def test_a_tail_that_does_not_close_is_still_vetoable(self):
        # 4 staves against 5 slots. Below the oboe (pos 1, slot 1) the boundary
        # is (pos 4, slot 5): 5 - 1 = 4 but 4 - 1 = 3, so a slot is skipped
        # somewhere below and NOTHING down there is forced — both staves of the
        # tail stay vetoable, not just the one whose name looks wrong.
        assert self._vetoes([(0, 0), (10, 1), (30, 3), (40, 4)],
                            reference_size=5) == {(30, "Trombone"),
                                                  (40, "Violin")}

    def test_the_head_anchors_against_slot_minus_one(self):
        # Staff 0 sits above the labelled oboe at slot 1: one staff, one slot.
        assert (0, "Flute") not in self._vetoes(
            [(0, 0), (10, 1), (30, 3), (40, 4)], reference_size=5)
