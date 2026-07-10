"""Tests for score_comparison — multi-part measure extraction and comparison.

Covers the fix for "multi-source comparison reads only parts[0]": these
tests build small two- and three-part MusicXML fixtures where the
interesting disagreement lives in a part *other* than the first, and
assert that extract_measures / compare_two_scores / compare_multiple all
account for it.
"""

import textwrap

import pytest

from modules.score_comparison import (
    _measure_fingerprint,
    compare_multiple,
    compare_two_scores,
    extract_measures,
    parse_musicxml,
)


def _two_part_score(part1_pitch: str, part2_pitch: str) -> str:
    """A minimal 2-part, 1-measure MusicXML score.

    part1_pitch / part2_pitch look like ("C", 4) tuples' XML: e.g. "C4".
    """
    step1, octave1 = part1_pitch[0], part1_pitch[1:]
    step2, octave2 = part2_pitch[0], part2_pitch[1:]
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <score-partwise version="3.1">
          <part-list>
            <score-part id="P1"><part-name>Violin</part-name></score-part>
            <score-part id="P2"><part-name>Cello</part-name></score-part>
          </part-list>
          <part id="P1">
            <measure number="1">
              <attributes>
                <divisions>1</divisions>
                <time><beats>4</beats><beat-type>4</beat-type></time>
                <clef><sign>G</sign><line>2</line></clef>
              </attributes>
              <note>
                <pitch><step>{step1}</step><octave>{octave1}</octave></pitch>
                <duration>4</duration>
                <type>whole</type>
              </note>
            </measure>
          </part>
          <part id="P2">
            <measure number="1">
              <attributes>
                <divisions>1</divisions>
                <time><beats>4</beats><beat-type>4</beat-type></time>
                <clef><sign>F</sign><line>4</line></clef>
              </attributes>
              <note>
                <pitch><step>{step2}</step><octave>{octave2}</octave></pitch>
                <duration>4</duration>
                <type>whole</type>
              </note>
            </measure>
          </part>
        </score-partwise>
    """)


@pytest.fixture
def matching_score_paths(tmp_path):
    """Two files where BOTH parts agree (part 1 = C4, part 2 = C3)."""
    xml = _two_part_score("C4", "C3")
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    a.write_text(xml, encoding="utf-8")
    b.write_text(xml, encoding="utf-8")
    return str(a), str(b)


@pytest.fixture
def second_part_diff_paths(tmp_path):
    """Two files that agree on part 1 (first part) but differ on part 2 —
    the case the parts[0]-only bug would have missed entirely.
    """
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    a.write_text(_two_part_score("C4", "C3"), encoding="utf-8")
    b.write_text(_two_part_score("C4", "D3"), encoding="utf-8")
    return str(a), str(b)


# ---------------------------------------------------------------------------
# _measure_fingerprint (pure function)
# ---------------------------------------------------------------------------


class TestMeasureFingerprint:
    def test_equal_measures_fingerprint_equal(self):
        m1 = {"notes": [{"pitch": 60, "duration": 1.0, "voice": "1"}]}
        m2 = {"notes": [{"pitch": 60, "duration": 1.0, "voice": "1"}]}
        assert _measure_fingerprint(m1) == _measure_fingerprint(m2)

    def test_different_pitch_differs(self):
        m1 = {"notes": [{"pitch": 60, "duration": 1.0, "voice": "1"}]}
        m2 = {"notes": [{"pitch": 62, "duration": 1.0, "voice": "1"}]}
        assert _measure_fingerprint(m1) != _measure_fingerprint(m2)

    def test_chord_pitch_list_is_hashable_tuple(self):
        m = {"notes": [{"pitch": [60, 64, 67], "duration": 1.0, "voice": "1"}]}
        fp = _measure_fingerprint(m)
        assert fp == (((60, 64, 67), 1.0),)

    def test_empty_notes_is_empty_tuple(self):
        assert _measure_fingerprint({"notes": []}) == ()


# ---------------------------------------------------------------------------
# extract_measures — must cover every part, not just parts[0]
# ---------------------------------------------------------------------------


class TestExtractMeasures:
    def test_extracts_all_parts(self, tmp_path):
        p = tmp_path / "score.xml"
        p.write_text(_two_part_score("C4", "E3"), encoding="utf-8")
        score = parse_musicxml(str(p))
        measures = extract_measures(score)

        part_indices = {m["part_index"] for m in measures}
        assert part_indices == {0, 1}, (
            "extract_measures must return measures for every part, "
            "not just the first"
        )

    def test_second_part_notes_are_not_dropped(self, tmp_path):
        p = tmp_path / "score.xml"
        p.write_text(_two_part_score("C4", "E3"), encoding="utf-8")
        score = parse_musicxml(str(p))
        measures = extract_measures(score)

        second_part_measure = next(m for m in measures if m["part_index"] == 1)
        assert second_part_measure["notes"], "second part's notes were dropped"
        assert second_part_measure["notes"][0]["pitch"] == 52  # E3


# ---------------------------------------------------------------------------
# compare_two_scores — a difference confined to part 2 must be detected
# ---------------------------------------------------------------------------


class TestCompareTwoScores:
    def test_identical_multi_part_scores_are_100_pct_similar(self, matching_score_paths):
        path_a, path_b = matching_score_paths
        result = compare_two_scores(path_a, path_b)
        assert result["error"] is None
        assert result["similarity_pct"] == 100.0

    def test_second_part_difference_is_detected(self, second_part_diff_paths):
        path_a, path_b = second_part_diff_paths
        result = compare_two_scores(path_a, path_b)

        assert result["error"] is None
        # Only 1 of the 2 (part, measure) units differs.
        assert result["similarity_pct"] == 50.0

        differing = [d for d in result["measure_diffs"] if d["status"] == "differ"]
        assert len(differing) == 1
        assert differing[0]["part_index"] == 1

        matching = [d for d in result["measure_diffs"] if d["status"] == "match"]
        assert len(matching) == 1
        assert matching[0]["part_index"] == 0


# ---------------------------------------------------------------------------
# compare_multiple — per-measure consensus must aggregate across all parts
# ---------------------------------------------------------------------------


class TestCompareMultiple:
    def test_agreement_when_all_parts_match_across_all_sources(self, tmp_path):
        xml = _two_part_score("C4", "C3")
        paths = []
        for i in range(3):
            p = tmp_path / f"s{i}.xml"
            p.write_text(xml, encoding="utf-8")
            paths.append(str(p))

        result = compare_multiple(paths)
        assert result["error"] is None
        assert len(result["per_measure_agreement"]) == 1
        entry = result["per_measure_agreement"][0]
        assert entry["agreement_pct"] == 100.0
        assert entry["sources_agreeing"] == 3
        assert result["consensus_issues"] == []

    def test_disagreement_confined_to_second_part_lowers_agreement(self, tmp_path):
        # Two sources agree on both parts; one differs only in part 2.
        # A parts[0]-only implementation would report 100% agreement here.
        paths = []
        xmls = [
            _two_part_score("C4", "C3"),
            _two_part_score("C4", "C3"),
            _two_part_score("C4", "D3"),  # part 2 differs
        ]
        for i, xml in enumerate(xmls):
            p = tmp_path / f"s{i}.xml"
            p.write_text(xml, encoding="utf-8")
            paths.append(str(p))

        result = compare_multiple(paths)
        assert result["error"] is None
        assert len(result["per_measure_agreement"]) == 1
        entry = result["per_measure_agreement"][0]
        assert entry["measure_num"] == 1
        assert entry["sources_agreeing"] == 2
        assert entry["agreement_pct"] == pytest.approx(66.67, abs=0.01)
        assert result["consensus_issues"] == [1]

    def test_response_shape_is_backward_compatible(self, matching_score_paths):
        path_a, path_b = matching_score_paths
        result = compare_multiple([path_a, path_b])
        # Same top-level fields the frontend (GradusLibrary.tsx) reads.
        assert set(result.keys()) == {
            "labels", "matrix", "per_measure_agreement", "consensus_issues", "error",
        }
        for entry in result["per_measure_agreement"]:
            assert set(entry.keys()) == {"measure_num", "agreement_pct", "sources_agreeing"}
