"""`OMR_SLOT_STITCH` — joining by contextual slot where the ordinal join refuses.

MEASURED AND DELIBERATELY DEFAULT-OFF. See
`benchmarks/omr-staff-structure-2026-09/FINDINGS.md`: on the one scan-benchmark
page whose systems disagree about staff count (Brahms 1 p.2, hand-verified as
14 staves then 13, the second Trompeten staff suppressed) the flag recovers 14
continuous parts from the 27 per-system fragments the refusal falls back to,
and is worth 216 edits — while more than DOUBLING the `entire staff` bucket the
work was scoped to reduce (715 -> 1,632). It is off because that trade has been
priced on exactly one page.

The shape these tests pin is what makes the flag safe to carry:

  * flag OFF is byte-identical to a tree without the feature;
  * flag ON changes NOTHING on a page whose systems agree on staff count — the
    ordinal join is reached first and is untouched;
  * flag ON never grafts by position: it abstains whole unless every staff of
    every system carries a slot and no system repeats one;
  * a slot missing from a system keeps ITS OWN system's measure numbering,
    which is the bug a naive `zip(slot, starts)` would introduce.
"""
from __future__ import annotations

import os

import pytest

from tools.omr.export import _stitch_slots, _stitch_slots_by_slot, to_musicxml

from .test_export_part_stitching import _parts, _result, _root, _staff


def _slotted(staves, slots):
    for staff, slot in zip(staves, slots):
        staff["slot_index"] = slot
    return staves


@pytest.fixture
def flag_on():
    old = os.environ.get("OMR_SLOT_STITCH")
    os.environ["OMR_SLOT_STITCH"] = "1"
    yield
    if old is None:
        os.environ.pop("OMR_SLOT_STITCH", None)
    else:
        os.environ["OMR_SLOT_STITCH"] = old


def _tacet_page():
    """Two systems, the second suppressing the staff at slot 1.

    This is the Brahms 1 p.2 shape in miniature: the full lineup, then the same
    lineup with one tacet part's staff not printed. The ordinal join must
    refuse it — joining by position would put slot 2's music onto slot 1.
    """
    first = _slotted([_staff(i, 2) for i in range(4)], [0, 1, 2, 3])
    second = _slotted([_staff(i, 3) for i in range(3)], [0, 2, 3])
    return _result([first, second])


def _agreeing_page():
    first = _slotted([_staff(i, 2) for i in range(3)], [0, 1, 2])
    second = _slotted([_staff(i, 3) for i in range(3)], [0, 1, 2])
    return _result([first, second])


class TestTheOrdinalJoinIsUntouched:
    def test_it_still_refuses_a_staff_count_mismatch(self):
        # The refusal is the correct behaviour and the flag does not relax it —
        # the slot join is a different fallback, not a loosened ordinal join.
        assert _stitch_slots(_tacet_page()) is None

    def test_an_agreeing_page_is_identical_with_the_flag_on(self, flag_on):
        result = _agreeing_page()
        with_flag = to_musicxml(result)
        os.environ["OMR_SLOT_STITCH"] = "0"
        without = to_musicxml(_agreeing_page())
        assert with_flag == without


class TestFlagOffChangesNothing:
    def test_the_tacet_page_still_fragments(self):
        os.environ["OMR_SLOT_STITCH"] = "0"
        xml = to_musicxml(_tacet_page())
        # 4 staves + 3 staves, each its own part: the documented fallback.
        assert len(_parts(xml)) == 7

    def test_slots_on_the_staves_do_not_by_themselves_engage_it(self):
        os.environ["OMR_SLOT_STITCH"] = "0"
        assert len(_parts(to_musicxml(_tacet_page()))) == 7


class TestTheSlotJoin:
    def test_it_recovers_continuous_parts(self, flag_on):
        xml = to_musicxml(_tacet_page())
        parts = _parts(xml)
        # Four slots, not seven fragments.
        assert len(parts) == 4

    def test_the_suppressed_slot_is_short_and_the_others_are_whole(self, flag_on):
        xml = to_musicxml(_tacet_page())
        counts = [len(p.findall("measure")) for p in _parts(xml)]
        # slot 0, 2, 3 appear in both systems (2 + 3); slot 1 only in the first.
        assert counts == [5, 2, 5, 5]

    def test_a_slot_missing_a_system_keeps_that_systems_numbering(self, flag_on):
        """The bug a naive `zip(slot, starts)` introduces.

        System 2's measures begin at 3. A slot present in both systems must
        number its second run from 3; the SHORT slot must not silently borrow
        system 2's start for its system-1 measures.
        """
        xml = to_musicxml(_tacet_page())
        parts = _parts(xml)
        nums = [[m.get("number") for m in p.findall("measure")] for p in parts]
        assert nums[0] == ["1", "2", "3", "4", "5"]
        assert nums[1] == ["1", "2"]          # the tacet slot, system 1 only
        assert nums[2] == ["1", "2", "3", "4", "5"]

    def test_a_slot_that_ENTERS_on_the_second_system_starts_there(self, flag_on):
        """The case a naive `zip(slot, starts)` gets wrong, and the reason the
        system index is carried rather than inferred from position.

        Where a slot is missing from an EARLY system, its one staff is the
        FIRST element of its list, so zipping against `starts` hands it
        `starts[0]` — numbering a system-2 staff from measure 1 and stacking it
        on top of everyone else's opening bars. Every slot in `_tacet_page` is
        present in system 1, so that fixture cannot tell the two apart; this
        one can.
        """
        first = _slotted([_staff(i, 2) for i in range(3)], [0, 1, 2])
        second = _slotted([_staff(i, 3) for i in range(4)], [0, 1, 2, 3])
        xml = to_musicxml(_result([first, second]))
        parts = _parts(xml)
        assert len(parts) == 4
        nums = [[m.get("number") for m in p.findall("measure")] for p in parts]
        # Slot 3 exists only in system 2, whose measures begin at 3.
        assert nums[3] == ["3", "4", "5"]

    def test_music_is_never_lost(self, flag_on):
        """Every staff of every system reaches exactly one part."""
        off_notes = None
        for flag in ("0", "1"):
            os.environ["OMR_SLOT_STITCH"] = flag
            root = _root(to_musicxml(_tacet_page()))
            notes = len(root.findall(".//note"))
            if off_notes is None:
                off_notes = notes
            else:
                assert notes == off_notes


class TestItAbstainsRatherThanGuesses:
    def test_an_unassigned_staff_abstains_whole(self, flag_on):
        result = _tacet_page()
        result["pages"][0]["systems"][1]["staves"][0]["slot_index"] = -1
        assert _stitch_slots_by_slot(result) is None
        # ... and the export is the fragmenting fallback, unchanged.
        assert len(_parts(to_musicxml(result))) == 7

    def test_a_staff_with_no_slot_key_at_all_abstains(self, flag_on):
        result = _tacet_page()
        result["pages"][0]["systems"][1]["staves"][1].pop("slot_index")
        assert _stitch_slots_by_slot(result) is None

    def test_a_repeated_slot_within_one_system_abstains(self, flag_on):
        result = _tacet_page()
        result["pages"][0]["systems"][1]["staves"][1]["slot_index"] = 0
        assert _stitch_slots_by_slot(result) is None

    def test_a_single_system_page_abstains(self, flag_on):
        result = _result([_slotted([_staff(i, 2) for i in range(3)], [0, 1, 2])])
        assert _stitch_slots_by_slot(result) is None
