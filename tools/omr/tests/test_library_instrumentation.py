"""Work-level instrumentation capture: parsing, abstention, and provenance.

Lives beside the OMR tests because that is the suite that actually runs; the
module under test is ``tools/library/instrumentation.py``.  No network: every
input here is a string taken verbatim from a real IMSLP page.
"""

from __future__ import annotations

import json

import pytest

from tools.library import instrumentation as instr
from tools.library import score_library as lib

BEETHOVEN_5 = ("{{More}} piccolo, 2 flutes, 2 oboes, 2 clarinets, 2 bassoons, "
               "contrabassoon<br>2 horns, 2 trumpets, 3 trombones, timpani, "
               "strings {{MoreEnd}}")
BRAHMS_1 = "2, 2, 2, 2+1 - 4, 2, 3, 0, timp, strs {{More}}"
MAHLER_5 = "4d4, 3d1, 3d1, 3d1 - 6, 4, 3, 1, tmp, 4prc, hp, strs {{More}}"
BACH_B_MINOR = ("SSATB soli, SSATB chorus<br>2, 3 (1-2d obda), 0, 2 - 1, 3, timp, "
                "strs, bc {{More}}\n:2 flutes, 3 oboes (1st and 2nd also oboe "
                "d’amore), 2 bassoons<br>horn, 3 trumpets, timpani, strings, "
                "continuo (harpsichord and organ) {{MoreEnd}}")


def _named(parsed):
    return [i.get("instrument") or i.get("section") for i in parsed["roster"]]


class TestProseDialect:
    def test_beethoven_5_reads_the_printed_roster(self):
        parsed = instr.parse_roster(BEETHOVEN_5)
        assert parsed["dialect"] == "prose"
        assert parsed["unparsed"] == []
        assert _named(parsed) == [
            "Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
            "Horn", "Trumpet", "Trombone", "Timpani", "Strings",
        ]
        counts = {i.get("instrument"): i.get("count") for i in parsed["roster"]}
        assert counts["Trombone"] == 3 and counts["Piccolo"] == 1

    def test_an_english_plural_now_resolves_without_normalising(self):
        # This asserted the opposite until the lexicon learned English plurals
        # (2026-09-05): it knew "oboi" and "Ob." — printed margin labels — but
        # not the plural an encyclopaedia writes, so this parser de-pluralised
        # and flagged it.  The flag existed because normalising is fine and
        # doing it silently is not; the lexicon fix removed the need, taking
        # this workaround from 195 firings across the IMSLP corpus to 0.
        # `lexicon_depluralized` is kept for any plural the lexicon still
        # lacks — its ABSENCE here is the point.
        oboe = next(i for i in instr.parse_roster(BEETHOVEN_5)["roster"]
                    if i.get("instrument") == "Oboe")
        assert "lexicon_depluralized" not in oboe

    def test_a_section_is_not_an_instrument_and_carries_no_count(self):
        strings = next(i for i in instr.parse_roster(BEETHOVEN_5)["roster"]
                       if i.get("section") == "Strings")
        assert strings["kind"] == "section"
        assert "count" not in strings      # a count here would read as one player
        assert "instrument" not in strings


class TestCompactDialect:
    def test_slots_are_positional(self):
        parsed = instr.parse_roster(BRAHMS_1)
        assert parsed["dialect"] == "compact"
        assert parsed["unparsed"] == []
        by_name = {i.get("instrument") or i.get("section"): i for i in parsed["roster"]}
        assert by_name["Flute"]["count"] == 2
        assert by_name["Horn"]["count"] == 4
        assert by_name["Trombone"]["count"] == 3
        assert by_name["Bassoon"]["modifier"] == "+1"   # "2+1", kept verbatim
        assert "Tuba" not in by_name                    # the "0" slot is empty

    def test_doubling_and_extras(self):
        by_name = {i.get("instrument") or i.get("section"): i
                   for i in instr.parse_roster(MAHLER_5)["roster"]}
        assert by_name["Flute"]["count"] == 4 and by_name["Flute"]["modifier"] == "d4"
        assert by_name["Tuba"]["count"] == 1
        assert by_name["Percussion"]["count"] == 4
        assert by_name["Harp"]["count"] == 1
        assert "Strings" in by_name

    def test_a_group_that_is_not_four_slots_abstains_whole(self):
        # Three wind tokens is a convention this does not know.  Mapping them
        # onto the first three slot names would be an off-by-one instrument list
        # that looks completely plausible.
        parsed = instr.parse_roster("2, 2, 2 - 4, 2, 3, 0")
        assert not any(i.get("instrument") in {"Flute", "Oboe", "Clarinet"}
                       for i in parsed["roster"])
        assert parsed["unparsed"][:3] == ["2", "2", "2"]


class TestBothDialectsInOneField:
    def test_the_segment_that_parses_best_wins_and_the_other_is_kept(self):
        parsed = instr.parse_roster(BACH_B_MINOR)
        # Read as one string this scored 0 of 18 — neither dialect.
        assert parsed["parse_rate"] > 0.8
        assert "Trumpet" in _named(parsed)
        assert parsed["segments_ignored"]          # nothing silently discarded


TANNHAUSER = (
    "{{More}} ''Cast''\n:''Minnesingers''\n::Tannhäuser (tenor)<br>Wolfram von "
    "Eschenbach (baritone)<br>Biterolf (bass)\n''Mixed Chorus'' (SATB)\n"
    ":Nobles, knights, ladies, pilgrims\n''Orchestra''\n"
    ":3 flutes (3rd also piccolo), 2 oboes, 2 clarinets, bass clarinet, 2 "
    "bassoons<br>4 horns, 3 trumpets, 3 trombones, tuba<br>timpani, bass drum, "
    "cymbals, triangle, tambourine, harp, strings (16, 16, 12, 12, 8) {{MoreEnd}}"
)


class TestOperaFields:
    def test_the_cast_list_is_not_read_as_a_roster(self):
        # Read whole, Tannhäuser scored 0 of 54: the knights and the ladies
        # charged as abstentions while the orchestra sat in the same string.
        parsed = instr.parse_roster(TANNHAUSER)
        assert parsed["roster_heading"] == "Orchestra"
        names = _named(parsed)
        assert "Trombone" in names and "Tuba" in names and "Bass clarinet" in names
        assert not any("Tannh" in str(u) for u in parsed["unparsed"])
        assert parsed["segments_ignored"]

    def test_desk_counts_do_not_make_a_prose_roster_look_compact(self):
        # "strings (16, 16, 12, 12, 8)" is five bare numbers at the end of plain
        # prose; a numeric-token COUNT sent all 21 fragments to the positional
        # parser, which then correctly abstained on every one of them.
        assert instr.parse_roster(TANNHAUSER)["dialect"] == "prose"
        assert instr._is_compact(BRAHMS_1.replace(" {{More}}", "")) is True
        assert instr._is_compact(
            "3 flutes, 2 oboes, 2 clarinets, bass clarinet, 2 bassoons, 4 horns, "
            "3 trumpets, 3 trombones, tuba, timpani, bass drum, cymbals, "
            "triangle, tambourine, harp, strings (16, 16, 12, 12, 8)") is False


class TestDoubling:
    """⚠️ The head is the CHAIR; a parenthetical is not a chair.

    The fourth confident-wrong-answer shape this field has produced, and the
    only one that reported ``parse_rate 1.0`` while doing it.  A flautist
    switches to piccolo and an oboist to English horn, and IMSLP says so in
    parentheses — ``2 flutes (2nd also piccolo)``.  Resolved whole, the lexicon
    matched ``piccolo`` INSIDE the fragment and returned Piccolo with the
    flutes' own count, deleting the flutes.  58 of 223 held works write "also".
    """

    def test_the_chair_survives_and_the_double_is_recorded_on_it(self):
        parsed = instr.parse_roster("2 flutes (2nd also piccolo), 2 clarinets")
        flute = parsed["roster"][0]
        assert flute["instrument"] == "Flute" and flute["count"] == 2
        assert flute["doubles"] == ["Piccolo"]
        assert _named(parsed) == ["Flute", "Clarinet"]

    def test_a_double_is_never_a_roster_entry_of_its_own(self):
        # A doubling player is ONE chair holding two instruments.  Emitting the
        # auxiliary as a chair would also make the edition tier report it
        # missing from every page the player has not picked it up on.
        parsed = instr.parse_roster("2 oboes (2nd also English horn)")
        assert _named(parsed) == ["Oboe"]

    def test_a_comma_inside_a_parenthetical_is_not_a_separator(self):
        # "4 oboes (3rd, 4th also English horn)" was cut in half; the head
        # `4 oboes (3rd` resolved to nothing, so Mahler lost its oboes entirely.
        parsed = instr.parse_roster("4 oboes (3rd, 4th also English horn), 2 clarinets")
        assert _named(parsed) == ["Oboe", "Clarinet"]
        assert parsed["unparsed"] == []
        assert parsed["roster"][0]["doubles"] == ["English horn"]

    def test_a_parenthetical_with_no_doubling_marker_is_a_qualifier(self):
        # "4 horns (2 natural, 2 chromatic)" is four horns, not more instruments.
        parsed = instr.parse_roster("4 horns (2 natural, 2 chromatic)")
        assert _named(parsed) == ["Horn"]
        horn = parsed["roster"][0]
        assert horn["count"] == 4 and horn["qualifier"] == "2 natural, 2 chromatic"
        assert "doubles" not in horn

    def test_an_alternative_is_not_a_doubling(self):
        # "harp (or piano)" is a substitution the conductor chooses between, not
        # an instrument the player also holds.
        parsed = instr.parse_roster("harp (or piano)")
        assert _named(parsed) == ["Harp"]
        assert "doubles" not in parsed["roster"][0]

    def test_a_head_the_lexicon_cannot_name_still_falls_back_to_the_whole(self):
        # "percussion (3 players: cymbals, triangle)" parsed before this change
        # and must keep parsing.
        parsed = instr.parse_roster("percussion (3 players: cymbals, triangle)")
        assert _named(parsed) == ["Percussion"]

    def test_continuo_with_its_realisation_stays_a_section(self):
        # "continuo (harpsichord)" used to resolve to Piano, on six works —
        # a keyboard chair invented out of a figured-bass line.
        parsed = instr.parse_roster("strings, continuo (harpsichord and organ)")
        assert _named(parsed) == ["Strings", "Continuo"]


class TestAbstention:
    def test_an_unknown_fragment_is_recorded_not_guessed(self):
        parsed = instr.parse_roster("2 flutes, hurdy-gurdy, 3 sackbuts")
        assert _named(parsed) == ["Flute"]
        assert "hurdy-gurdy" in parsed["unparsed"]
        assert parsed["parse_rate"] == pytest.approx(1 / 3, abs=1e-4)

    def test_an_empty_field_has_no_parse_rate(self):
        parsed = instr.parse_roster("")
        assert parsed["dialect"] == "empty" and parsed["parse_rate"] is None


class TestProvenance:
    def _fetched(self, detail=BEETHOVEN_5, generic="orchestra"):
        return {
            "imslp_page": "Symphony No.5, Op.67 (Beethoven, Ludwig van)",
            "imslp_url": "https://imslp.org/wiki/x",
            "imslp_revid": 1234,
            "raw": {"Instrumentation": generic, "InstrDetail": detail},
        }

    def test_a_fact_names_its_source_and_its_kind(self):
        fact = instr.build_fact(self._fetched())
        assert fact["source"] == "imslp"
        assert fact["source_kind"] == "catalog"
        assert fact["imslp_revid"] == 1234
        assert fact["raw"]["InstrDetail"] == BEETHOVEN_5   # verbatim

    def test_an_encoding_derived_fact_is_a_different_kind(self):
        # The distinction is the point: a roster read out of a MusicXML file is
        # the same substrate the benchmarks score against.
        assert instr.SOURCE_KINDS["musicxml"] == "encoding"
        assert instr.SOURCE_KINDS["imslp"] == "catalog"

    def test_a_fact_with_no_provenance_is_refused(self):
        with pytest.raises(ValueError):
            instr.validate_fact({"source": "guess", "raw": {}})
        with pytest.raises(ValueError):
            instr.validate_fact({"source": "imslp", "source_kind": "catalog"})
        with pytest.raises(ValueError):
            # a catalog fact that claims to be encoding-derived, or vice versa
            instr.validate_fact({"source": "imslp", "source_kind": "encoding",
                                 "raw": {}})

    def test_the_roster_field_actually_used_is_recorded(self):
        # Brandenburg 2 has no InstrDetail; its roster is in Instrumentation.
        fact = instr.build_fact(self._fetched(
            detail="", generic="recorder, oboe, trumpet, violin, strings"))
        assert fact["roster_field"] == "Instrumentation"
        assert "Trumpet" in _named(fact)
        assert instr.build_fact(self._fetched())["roster_field"] == "InstrDetail"

    def test_a_fact_says_it_describes_a_work_not_a_page_layout(self):
        fact = instr.build_fact(self._fetched())
        assert fact["describes"] == "work"
        assert "not N staves" in fact["note"]


class TestCatalogRecording:
    def _fact(self, page):
        return instr.build_fact({
            "imslp_page": page, "imslp_url": "", "imslp_revid": 1,
            "raw": {"Instrumentation": "orchestra", "InstrDetail": BRAHMS_1},
        })

    def test_recording_is_idempotent(self):
        catalog = {"entries": []}
        assert instr.record(catalog, "brahms--symphony-1", self._fact("A")) == "added"
        assert instr.record(catalog, "brahms--symphony-1", self._fact("A")) == "updated"
        assert len(catalog["works"]) == 1

    def test_two_pages_on_one_work_id_conflict_rather_than_overwrite(self):
        # Clara Schumann's Op.7 and Robert's Op.54 are both
        # "schumann--piano-concerto" under the catalog's own key.
        catalog = {"entries": []}
        instr.record(catalog, "schumann--piano-concerto",
                     self._fact("Piano Concerto, Op.7 (Schumann, Clara)"))
        assert instr.record(catalog, "schumann--piano-concerto",
                            self._fact("Piano Concerto, Op.54 (Schumann, Robert)")) \
            == "conflict"
        entry = catalog["works"]["schumann--piano-concerto"]
        assert entry["instrumentation_conflict"]
        assert len(entry["instrumentation_conflicts"]) == 1

    def test_a_rebuild_does_not_destroy_work_level_facts(self, tmp_path):
        # Work facts are network-fetched and have no sidecar to be rebuilt from.
        path = tmp_path / "catalog.json"
        catalog = {"entries": []}
        instr.record(catalog, "brahms--symphony-1", self._fact("A"))
        lib.save_catalog(catalog, path)
        lib.rebuild_catalog(path)
        assert json.loads(path.read_text())["works"]["brahms--symphony-1"][
            "instrumentation"]["source"] == "imslp"


class TestBackfillTargets:
    def test_targets_are_deduplicated_on_the_page_and_skip_recorded_works(self):
        catalog = {"entries": [
            {"source": "imslp", "work_id": "w1", "raw": {"imslp_page": "P1"}},
            {"source": "imslp", "work_id": "w1", "raw": {"imslp_page": "P1"}},
            {"source": "imslp", "work_id": "w2", "raw": {"imslp_page": "P2"}},
            {"source": "gradus", "work_id": "w3", "raw": {"imslp_page": "P3"}},
        ]}
        assert instr.pages_to_fetch(catalog) == [("w1", "P1"), ("w2", "P2")]
        instr.record(catalog, "w1", instr.build_fact(
            {"imslp_page": "P1", "imslp_url": "", "imslp_revid": 1,
             "raw": {"Instrumentation": "orchestra", "InstrDetail": BRAHMS_1}}))
        assert instr.pages_to_fetch(catalog) == [("w2", "P2")]
        assert len(instr.pages_to_fetch(catalog, refetch=True)) == 2
