"""Unit tests for tools/omr/key_signature_corroboration.py.

Two halves, and both were run RED before they were run green (the mutations
are named on each class).

  * BEHAVIOUR — that an uncorroborated mid-staff key change is reverted, that a
    corroborated one is not, and that only the notes which actually fell
    through to the key are re-spelled.
  * WIRING — that `transcribe` calls the pass, and calls it behind the env
    flag. ⚠️ A test asserting the guard EXISTS is worthless; the caller is
    what a future edit deletes, so deleting the call site has to redden more
    than one test here.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from tools.omr.key_signature_corroboration import (
    ENV_FLAG,
    _split_pitch,
    drop_uncorroborated_key_changes,
    enabled,
)


def key(sharps: int = 0, flats: int = 0) -> dict:
    """A measure key-signature summary, the shape `_key_sig_summary` writes."""
    letters = "FCGDAEB" if sharps else "BEADGCF"
    alterations = {letters[i]: ("#" if sharps else "b")
                   for i in range(sharps or flats)}
    return {"sharps": sharps, "flats": flats, "alterations": alterations}


def notehead(pitch: str, x: int = 0, **extra) -> dict:
    d = {"class": "noteheadBlackInSpace", "category": "notehead",
         "bbox": [x, 0, 10, 10], "pitch": pitch}
    d.update(extra)
    return d


def staff(index: int, keys, *, detections=None, **extra) -> dict:
    """A staff whose measure i carries `keys[i]` (None ⇒ no key on that bar)."""
    measures = []
    for i, k in enumerate(keys):
        measures.append({
            "measure_index": i,
            "key_signature": dict(k) if k else None,
            "detections": list((detections or {}).get(i, [])),
        })
    out = {"staff_index": index, "measures": measures}
    out.update(extra)
    return out


def page(*staves) -> dict:
    return {"systems": [{"staves": list(staves)}]}


# ─────────────────────────── behaviour ───────────────────────────


class TestUncorroboratedChangeReverts:
    """RED-first mutation: `witnesses[...] >= min_witnesses` → `>= 1`, which
    corroborates every change and reverts nothing. Every test in this class
    fails under it."""

    def test_reverts_a_change_the_cross_page_vote_had_confirmed(self):
        # The sharpest real case, from mahler-sym5-mvt1-local-p2 staff 15: the
        # vote said "kept: agrees with the system's 4 sharps" and a single
        # keySharp at confidence 0.33 rewrote the rest of the staff to 1 sharp.
        victim = staff(
            15, [key(sharps=4), key(sharps=4), key(sharps=1), key(sharps=1)],
            key_signature_source="header_vote",
            key_signature_reason="kept: agrees with the system's 4 sharps",
        )
        others = [staff(i, [key(sharps=4)] * 4) for i in range(3)]
        p = page(victim, *others)

        got = drop_uncorroborated_key_changes(p)

        assert got["reverted"] == 1
        assert got["kept"] == 0
        # THE POINT: the staff is back in the key the vote confirmed, on every
        # measure the flip had taken, not merely flagged.
        assert [m["key_signature"]["sharps"] for m in victim["measures"]] == [4, 4, 4, 4]
        record = victim["key_signature_corroboration"][0]
        assert record["measure_index"] == 2
        assert record["from"] == (4, 0) and record["to"] == (1, 0)
        assert record["measures_reverted"] == 2
        assert record["witnesses"] == 1 and record["staves_in_system"] == 4
        assert record["contradicted_vote"] is True
        assert record["vote_reason"] == "kept: agrees with the system's 4 sharps"
        assert p["uncorroborated_key_changes_reverted"] == 1

    def test_a_staff_the_vote_never_spoke_for_is_still_reverted(self):
        # 2 of the 7 real flips are on staves with no `key_signature_source`,
        # which is why the vote is REPORTED and the system is what DECIDES.
        victim = staff(4, [key(), key(), key(), key(flats=1), key(flats=1)])
        p = page(victim, staff(0, [key()] * 5), staff(1, [key()] * 5))

        got = drop_uncorroborated_key_changes(p)

        assert got["reverted"] == 1
        assert [m["key_signature"]["flats"] for m in victim["measures"]] == [0] * 5
        assert victim["key_signature_corroboration"][0]["contradicted_vote"] is False
        assert victim["key_signature_corroboration"][0]["vote_reason"] is None

    def test_the_staffs_opening_key_is_never_touched(self):
        # The opening signature is PRINTED and the vote already ruled on it.
        # Only a later one — ink that resembled a signature — is in scope.
        lone = staff(0, [key(flats=3), key(flats=3)])
        p = page(lone, staff(1, [key()] * 2))

        got = drop_uncorroborated_key_changes(p)

        assert got == {"reverted": 0, "respelled": 0, "kept": 0, "changes": []}
        assert lone["measures"][0]["key_signature"]["flats"] == 3
        assert "uncorroborated_key_changes_reverted" not in p

    def test_a_later_change_gets_its_own_test_rather_than_being_swallowed(self):
        victim = staff(0, [key(flats=2), key(flats=1), key(flats=1), key(flats=3)])
        p = page(victim, staff(1, [key(flats=2)] * 4))

        drop_uncorroborated_key_changes(p)

        # The m1 revert stops at m3, where a different change takes over — and
        # that one is reverted by its own pass over the same list.
        assert [m["key_signature"]["flats"] for m in victim["measures"]] == [2, 2, 2, 2]
        assert len(victim["key_signature_corroboration"]) == 2

    def test_key_signature_final_goes_when_no_change_survives(self):
        victim = staff(0, [key(flats=2), key(flats=1)],
                       key_signature_final=key(flats=1))
        p = page(victim, staff(1, [key(flats=2)] * 2))

        drop_uncorroborated_key_changes(p)

        assert "key_signature_final" not in victim


class TestCorroboratedChangeSurvives:
    """⚠️ A PROXY, NOT A MEASUREMENT. The real corpus holds ZERO mid-staff key
    changes that any staff corroborates — 0 across 417 staves of both families
    — so the guard's COST cannot be measured on it, only on a page built to
    carry the thing the corpus lacks. That is why the flag ships OFF.

    RED-first mutation: drop the `>= min_witnesses` early-`continue`, i.e.
    revert unconditionally. Both tests here fail under it.
    """

    def test_a_system_wide_change_at_one_bar_survives(self):
        # A real key change is printed at ONE BAR of the system, behind a
        # double barline — on every staff, at DIFFERENT fifths, because the
        # clarinets and horns transpose. Value corroboration (the meter guard's
        # witness) would revert all three; position corroboration keeps them.
        concert = staff(0, [key(flats=3), key(flats=3), key(), key()])
        clarinet = staff(1, [key(flats=1), key(flats=1), key(sharps=2), key(sharps=2)])
        horn = staff(2, [key(), key(), key(sharps=3), key(sharps=3)])
        p = page(concert, clarinet, horn)

        got = drop_uncorroborated_key_changes(p)

        assert got["reverted"] == 0
        assert got["kept"] == 3
        assert concert["measures"][3]["key_signature"]["flats"] == 0
        assert clarinet["measures"][3]["key_signature"]["sharps"] == 2
        assert horn["measures"][3]["key_signature"]["sharps"] == 3
        assert "uncorroborated_key_changes" not in p

    def test_one_witness_is_enough_and_none_is_not(self):
        # The constant sits between "no other staff saw it" and "one did".
        two = page(staff(0, [key(flats=2), key(flats=1)]),
                   staff(1, [key(flats=2), key(flats=3)]),
                   staff(2, [key(flats=2), key(flats=2)]))
        assert drop_uncorroborated_key_changes(two)["reverted"] == 0

        one = page(staff(0, [key(flats=2), key(flats=1)]),
                   staff(1, [key(flats=2), key(flats=2)]))
        assert drop_uncorroborated_key_changes(one)["reverted"] == 1


class TestWitnessesAreCountedByMeasureIndex:
    """RED-first mutation: count witnesses by the loop ORDINAL instead of
    `measure_index`."""

    def test_staves_whose_cells_do_not_line_up_still_witness_each_other(self):
        # A staff that lost a barline has fewer cells than its neighbour, so
        # the same printed bar sits at a different position in each list.
        a = staff(0, [key(flats=2), key(flats=2), key(flats=1)])
        a["measures"][2]["measure_index"] = 7
        b = staff(1, [key(flats=2), key(flats=1)])
        b["measures"][1]["measure_index"] = 7
        p = page(a, b)

        got = drop_uncorroborated_key_changes(p)

        assert got["reverted"] == 0 and got["kept"] == 2


class TestRespelling:
    """⚠️ Reverting `measure["key_signature"]` alone is a HALF fix: the key is
    consumed inline while the cell is read, so the notes stay spelled against
    the key that was removed and the file contradicts itself.

    RED-first mutation: make `_respell_measure` return 0 without touching
    anything. Every test in this class fails under it except the two that
    assert a note is LEFT ALONE, which is the point of having both.
    """

    def _flip_page(self, dets):
        victim = staff(0, [key(flats=2), key(flats=1)], detections={1: dets})
        return victim, page(victim, staff(1, [key(flats=2)] * 2))

    def test_a_note_spelled_by_the_key_is_respelled(self):
        victim, p = self._flip_page([notehead("Bb3"), notehead("E4", x=20)])

        got = drop_uncorroborated_key_changes(p)

        # The bar was read in 1 flat, so E4 was spelled plain; restoring the
        # staff's 2 flats has to put the E flat back or `<key>` and `<alter>`
        # disagree in the exported file.
        assert got["respelled"] == 1
        assert [d["pitch"] for d in victim["measures"][1]["detections"]] == ["Bb3", "Eb4"]

    def test_a_note_carrying_its_own_accidental_is_left_alone(self):
        victim, p = self._flip_page([notehead("E4", accidental="natural")])

        got = drop_uncorroborated_key_changes(p)

        assert got["respelled"] == 0
        assert victim["measures"][1]["detections"][0]["pitch"] == "E4"

    def test_a_note_inheriting_an_accidental_from_earlier_in_its_bar_is_left_alone(self):
        victim, p = self._flip_page([
            notehead("E4", x=0, accidental="natural"),
            notehead("E4", x=50),          # carried natural, not the key's doing
            notehead("E5", x=90),          # different octave — the key reaches it
        ])

        got = drop_uncorroborated_key_changes(p)

        assert got["respelled"] == 1
        assert [d["pitch"] for d in victim["measures"][1]["detections"]] == [
            "E4", "E4", "Eb5"]

    def test_the_carry_is_read_in_x_order_not_detection_order(self):
        # The detection list is emitted in detector order. If the walk followed
        # it, the note printed SECOND would set the carry for the note printed
        # first, and the first would wrongly escape the key.
        victim, p = self._flip_page([
            notehead("E4", x=90, accidental="natural"),   # printed second
            notehead("E4", x=10),                         # printed FIRST
        ])

        drop_uncorroborated_key_changes(p)

        pitches = {d["bbox"][0]: d["pitch"]
                   for d in victim["measures"][1]["detections"]}
        assert pitches[10] == "Eb4"   # the key reaches it
        assert pitches[90] == "E4"    # its own natural stands

    def test_pitch_candidates_are_respelled_with_the_note(self):
        victim, p = self._flip_page([
            notehead("Bb3", pitch_candidates=[{"pitch": "Bb3", "weight": 0.9},
                                             {"pitch": "E4", "weight": 0.4}]),
        ])

        drop_uncorroborated_key_changes(p)

        cands = victim["measures"][1]["detections"][0]["pitch_candidates"]
        assert [c["pitch"] for c in cands] == ["Bb3", "Eb4"]


class TestSplitPitch:
    """⚠️ NOT `transcribe._parse_diatonic_pitch`, which returns None for a
    spelled pitch. RED-first mutation: delegate to that function."""

    @pytest.mark.parametrize("spelled,expected", [
        ("C4", ("C", None, 4)),
        ("Bb3", ("B", "b", 3)),
        ("F#5", ("F", "#", 5)),
        ("Gbb2", ("G", "bb", 2)),
        ("C##6", ("C", "##", 6)),
    ])
    def test_an_alteration_comes_off_before_a_new_one_goes_on(self, spelled, expected):
        assert _split_pitch(spelled) == expected

    @pytest.mark.parametrize("bad", ["", "H4", "4", "Cx", None])
    def test_nonsense_abstains(self, bad):
        assert _split_pitch(bad) is None


class TestTheFlag:
    """RED-first mutation: make `enabled()` return False unconditionally, or
    revert the default back to off without updating these two tests.

    ⚠️ The default flipped 2026-09-07 (Sean's call); the measurement gap in
    the module docstring ("WHAT THIS CANNOT MEASURE") did NOT — these tests
    pin the flag's behaviour only, not a claim that the cost is now known.
    """

    def test_on_by_default(self, monkeypatch):
        # This is the test that must fail if a future edit flips the default
        # back to off without updating it here and in the docstrings.
        monkeypatch.delenv(ENV_FLAG, raising=False)
        assert enabled() is True

    @pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "off", " off "])
    def test_off_values_still_disable_it(self, raw, monkeypatch):
        # The flag itself must still work even though its default changed —
        # this is what makes flag-off byte-identity a live, checkable claim
        # rather than a fact about a default nobody can turn off.
        monkeypatch.setenv(ENV_FLAG, raw)
        assert enabled() is False

    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on", " on ", "maybe"])
    def test_everything_else_leaves_it_on(self, raw, monkeypatch):
        # "maybe" belongs here now: with the flag default-ON, an unrecognised
        # value should not silently disable the guard — only a recognised
        # off-spelling may. That is a real behaviour change from when this
        # flag defaulted off (an unrecognised value used to mean off); it is
        # the same shape `system_grouping._choir_grouping_enabled` already
        # uses for its own default-ON flag.
        monkeypatch.setenv(ENV_FLAG, raw)
        assert enabled() is True


# ─────────────────────────── wiring ───────────────────────────


_TRANSCRIBE = pathlib.Path(__file__).resolve().parents[1] / "transcribe.py"
_TREE = ast.parse(_TRANSCRIBE.read_text())

_GUARD = "drop_uncorroborated_key_changes"
_FLAG_FN = "keysig_corroboration_enabled"


def _called_names(node) -> set[str]:
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn = sub.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


class TestTranscribeWiring:
    """⚠️ THE MUTATION THAT MUST REDDEN THESE: delete the

        if keysig_corroboration_enabled():
            keysig_guard = drop_uncorroborated_key_changes(page_dict)
            ...

    block from `transcribe`. Verified to fail ALL THREE of these — a guard
    nothing calls is a guard that does nothing, and a single wiring assertion
    is how a previous sweep's whole record was deleted with every test still
    green.
    """

    def test_transcribe_calls_the_guard(self):
        assert _GUARD in _called_names(_TREE), (
            f"{_GUARD} is imported by transcribe.py but never called — the "
            "pass is dead code")

    def test_the_call_is_gated_on_the_env_flag(self):
        # Not "an `if` exists somewhere near it": the call must be inside a
        # branch whose CONDITION asks the flag. Replacing that condition with
        # `True` would break flag-off byte-identity, which is the property the
        # whole change rests on.
        gated = [
            node for node in ast.walk(_TREE)
            if isinstance(node, ast.If)
            and _FLAG_FN in _called_names(node.test)
            and any(_GUARD in _called_names(stmt) for stmt in node.body)
        ]
        assert gated, (
            f"no `if {_FLAG_FN}(): ... {_GUARD}(...)` branch in transcribe.py")

    def test_both_imported_names_are_used(self):
        # Deleting the call site alone leaves the import behind; this makes
        # that state fail too, so the wiring cannot rot down to an unused
        # import that looks like it is still connected.
        imported = {
            alias.asname or alias.name
            for node in ast.walk(_TREE)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").endswith("key_signature_corroboration")
            for alias in node.names
        }
        assert imported == {_GUARD, _FLAG_FN}, imported
        assert imported <= _called_names(_TREE), (
            f"imported but never called: {imported - _called_names(_TREE)}")
