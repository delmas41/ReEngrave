"""Dossier loading, the checks, and the meter → rhythm correction."""
from __future__ import annotations

import json

import pytest

from tools.omr import dossier as dz
from tools.omr.transcribe import _reconcile_measure_to_meter


# ── fixtures ────────────────────────────────────────────────────────────────

def make_dossier(**over):
    d = {
        "schema_version": 3,
        "work_id": "test-work",
        "total_measures": 100,
        "starting_meter": {"beats": 2, "beat_type": 4},
        "meter_changes": [{"measure": 1, "beats": 2, "beat_type": 4}],
        "constant_meter": True,
        "n_parts": 4,
        "parts": [
            {"slot": 0, "name": "Flute", "written_clef": "treble",
             "written_fifths": -3, "transposition_semitones": 0,
             "clef_changes": [], "key_changes": [], "measures": 100},
            {"slot": 1, "name": "Clarinet in Bb", "written_clef": "treble",
             "written_fifths": -1, "transposition_semitones": -2,
             "clef_changes": [], "key_changes": [], "measures": 100},
            {"slot": 2, "name": "Viola", "written_clef": "alto",
             "written_fifths": -3, "transposition_semitones": 0,
             "clef_changes": [], "key_changes": [], "measures": 100},
            {"slot": 3, "name": "Cello", "written_clef": "bass",
             "written_fifths": -3, "transposition_semitones": 0,
             "clef_changes": [], "key_changes": [], "measures": 100},
        ],
        "clefs_used": ["alto", "bass", "treble"],
        "written_fifths_used": [-3, -1],
    }
    d.update(over)
    return d


def staff(idx, clef=None, source=None, fifths=None, measures=None):
    st = {"staff_index": idx, "measures": measures if measures is not None else []}
    if clef:
        st["clef"] = clef
    if source:
        st["clef_source"] = source
    if fifths is not None:
        st["key_signature"] = {"fifths": fifths}
    return st


def page(*staves, system_index=0):
    return {"page_index": 0,
            "systems": [{"system_index": system_index, "staves": list(staves)}]}


# ── loading ─────────────────────────────────────────────────────────────────

def test_load_rejects_wrong_schema_version(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"schema_version": 2, "work_id": "x"}))
    with pytest.raises(ValueError, match="schema_version"):
        dz.load_dossier(p)


def test_find_dossier_missing_returns_none(tmp_path):
    assert dz.find_dossier("nope", dossier_dir=tmp_path) is None


# ── the meter ───────────────────────────────────────────────────────────────

def test_expected_meter_matches_pipeline_shape():
    m = dz.expected_meter(make_dossier())
    assert m == {"numerator": 2, "denominator": 4, "source": "dossier"}
    assert dz.meter_beats(m) == 2.0


def test_expected_meter_abstains_when_the_meter_changes():
    """A page cannot be located in the piece, so the opening meter cannot be
    asserted over it. See the note in dossier.expected_meter."""
    d = make_dossier(constant_meter=False)
    assert dz.expected_meter(d) is None


def test_apply_meter_fills_and_overrides():
    d = make_dossier()
    pg = page(staff(0, measures=[
        {"measure_index": 0},                                     # nothing read
        {"measure_index": 1,
         "time_signature": {"numerator": 7, "denominator": 24}},  # a misread
        {"measure_index": 2,
         "time_signature": {"numerator": 2, "denominator": 4}},   # agrees
    ]))
    warnings = dz.apply_meter(pg, d)
    measures = pg["systems"][0]["staves"][0]["measures"]
    assert all(m["time_signature"]["numerator"] == 2 for m in measures)
    # Only the genuine disagreement is reported.
    assert [w["read"] for w in warnings] == ["7/24"]


def test_apply_meter_keeps_the_glyph_the_page_printed():
    """The numbers come from the work, the GLYPH comes from the page.

    A dossier is built from one MusicXML file and cannot say whether the print
    in hand set its 2/4 as digits or its 2/2 as a stroked C. Dropping the
    detected `symbol` on override was worth 270 edits over 5 works of the
    widened corpus — 3 per staff, every staff — and nothing on the three works
    the benchmark used to be, all of which print digit meters.
    """
    d = make_dossier(starting_meter={"beats": 2, "beat_type": 2})
    pg = page(staff(0, measures=[
        {"measure_index": 0,
         "time_signature": {"numerator": 2, "denominator": 2,
                            "raw": "C|", "symbol": "cut"}},
    ]))
    dz.apply_meter(pg, d)
    ts = pg["systems"][0]["staves"][0]["measures"][0]["time_signature"]
    assert ts["numerator"] == 2 and ts["denominator"] == 2
    assert ts["symbol"] == "cut"
    assert ts["source"] == "dossier"


def test_apply_meter_drops_a_glyph_read_off_a_different_meter():
    """A `timeSigCommon` read on a 2/4 movement is a misread, and its glyph is
    as wrong as its numbers. The symbol may only ride on agreement."""
    d = make_dossier()  # 2/4
    pg = page(staff(0, measures=[
        {"measure_index": 0,
         "time_signature": {"numerator": 4, "denominator": 4,
                            "raw": "C", "symbol": "common"}},
    ]))
    dz.apply_meter(pg, d)
    ts = pg["systems"][0]["staves"][0]["measures"][0]["time_signature"]
    assert ts["numerator"] == 2 and ts["denominator"] == 4
    assert "symbol" not in ts


def test_apply_meter_invents_no_glyph_where_nothing_was_read():
    """A staff that read no meter exports digits, exactly as before."""
    d = make_dossier(starting_meter={"beats": 4, "beat_type": 4})
    pg = page(staff(0, measures=[{"measure_index": 0}]))
    dz.apply_meter(pg, d)
    assert "symbol" not in (
        pg["systems"][0]["staves"][0]["measures"][0]["time_signature"])


def test_apply_meter_does_not_flag_equal_bar_lengths():
    """6/8 and 3/4 are the same bar length; the beat-sum path cannot separate
    them and must not be called wrong for it."""
    d = make_dossier(starting_meter={"beats": 6, "beat_type": 8})
    pg = page(staff(0, measures=[
        {"measure_index": 0,
         "time_signature": {"numerator": 3, "denominator": 4}},
    ]))
    assert dz.apply_meter(pg, d) == []


# ── alignment-free checks ───────────────────────────────────────────────────

def test_clef_vocabulary_flags_a_clef_the_work_never_prints():
    pg = page(staff(0, clef="soprano", source="cv_locator"))
    out = dz.check_clef_vocabulary(pg, make_dossier())
    assert len(out) == 1 and out[0]["read"] == "soprano"


def test_clef_vocabulary_ignores_a_defaulted_clef():
    """A clef with no `clef_source` was never read — it is the positional
    default. Flagging it would flag the pipeline's own fallback."""
    pg = page(staff(0, clef="soprano"))
    assert dz.check_clef_vocabulary(pg, make_dossier()) == []


def test_key_vocabulary_flags_an_impossible_signature():
    pg = page(staff(0, fifths=2))
    out = dz.check_key_vocabulary(pg, make_dossier())
    assert len(out) == 1 and out[0]["read_fifths"] == 2


def test_key_vocabulary_never_flags_zero():
    """0 is also what a staff reports when nothing was read, so a genuine C
    major cannot be told from silence."""
    pg = page(staff(0, fifths=0))
    assert dz.check_key_vocabulary(pg, make_dossier()) == []


def test_clef_distribution_catches_an_all_treble_page():
    """The failure the self-consistency layer structurally cannot see: a page
    where every staff reads treble is entirely self-consistent."""
    pg = page(*[staff(i, clef="treble", source="detector") for i in range(8)])
    out = dz.check_clef_distribution(pg, make_dossier())
    missing = {w["clef"] for w in out}
    assert "bass" in missing  # 1 of 4 parts is bass → expect ~2 of 8 staves


def test_clef_distribution_quiet_on_a_realistic_mix():
    pg = page(staff(0, clef="treble", source="detector"),
              staff(1, clef="treble", source="detector"),
              staff(2, clef="alto", source="detector"),
              staff(3, clef="bass", source="detector"),
              staff(4, clef="bass", source="detector"),
              staff(5, clef="treble", source="detector"))
    assert dz.check_clef_distribution(pg, make_dossier()) == []


# ── slot-level ──────────────────────────────────────────────────────────────

def test_slot_checks_abstain_when_counts_disagree():
    """Condensation and divisi mean part index != staff index; forcing that
    join measured F1 0.064."""
    pg = page(*[staff(i, clef="treble", source="detector") for i in range(6)])
    assert dz.check_slot_alignment(pg, make_dossier()) == []


def test_slot_checks_fire_when_counts_match():
    pg = page(staff(0, clef="treble", source="detector"),
              staff(1, clef="treble", source="detector"),
              staff(2, clef="treble", source="detector"),   # should be alto
              staff(3, clef="bass", source="detector"))
    out = dz.check_slot_alignment(pg, make_dossier())
    assert len(out) == 1
    assert out[0]["part"] == "Viola" and out[0]["expected"] == "alto"


# ── whole-run ───────────────────────────────────────────────────────────────

def test_measure_overcount_only_fires_above_the_work_total():
    d = make_dossier(total_measures=10)
    result = {"pages": [page(staff(0, measures=[{"measure_index": i}
                                                for i in range(20)]))]}
    out = dz.check_total_measures(result, d)
    assert len(out) == 1 and out[0]["read_measures"] == 20
    # A partial run reads fewer and is silent.
    result2 = {"pages": [page(staff(0, measures=[{"measure_index": 0}]))]}
    assert dz.check_total_measures(result2, d) == []


# ── the meter → rhythm correction ───────────────────────────────────────────

# Notehead geometry at roughly the scale the pipeline actually works in.
# `group_chords_in_measure` decides a chord by x-proximity relative to notehead
# width, so toy coordinates a few pixels apart collapse into one chord and the
# fixture stops resembling the thing under test.
_NH_W = 30


def nh(x, beats, levels, dur_type="sixteenth"):
    # bbox is [x, y, w, h] in cell-local coords — the frame `voicing` groups in.
    return {"category": "notehead", "bbox": [x, 0, _NH_W, _NH_W],
            "bbox_page": [x, 0, _NH_W, _NH_W],
            "duration_beats": beats, "duration_type": dur_type,
            "beam_levels": levels, "dots": 0, "pitch": f"C{4 + (x // 150) % 3}",
            "stem_direction": "up"}


def measure_of(dets, num=2, den=4):
    return {"measure_index": 0,
            "time_signature": {"numerator": num, "denominator": den,
                               "source": "dossier"},
            "detections": dets}


def test_reconcile_reads_beethoven_fifth_correctly():
    """Three notes read as 16ths in a 2/4 bar that must hold 2.0 beats. Read
    as eighths the bar is right — which is what the page says."""
    m = measure_of([nh(150, 0.25, 2), nh(300, 0.25, 2), nh(450, 0.25, 2),
                    {"category": "rest", "bbox": [0, 0, 30, 30],
                     "bbox_page": [0, 0, 30, 30],
                     "duration_beats": 0.5, "duration_type": "eighth",
                     "dots": 0}])
    record = _reconcile_measure_to_meter(m)
    assert record is not None
    assert record["from_level"] == 2 and record["to_level"] == 1
    assert all(d["duration_beats"] == 0.5
               for d in m["detections"] if d["category"] == "notehead")


def test_reconcile_leaves_a_correct_bar_alone():
    m = measure_of([nh(0, 0.5, 1, "eighth"), nh(150, 0.5, 1, "eighth"),
                    nh(300, 0.5, 1, "eighth"), nh(450, 0.5, 1, "eighth")])
    before = [d["duration_beats"] for d in m["detections"]]
    assert _reconcile_measure_to_meter(m) is None
    assert [d["duration_beats"] for d in m["detections"]] == before


def test_reconcile_abstains_without_a_meter():
    m = measure_of([nh(0, 0.25, 2)])
    m["time_signature"] = None
    assert _reconcile_measure_to_meter(m) is None


def test_reconcile_abstains_when_the_answer_is_not_unique():
    """Two groups at the same level could each be adjusted to make the sum
    work. We do not know which, so nothing is changed."""
    # 4 sixteenths (1.0) + 4 sixteenths (1.0) = 2.0 already correct, so build a
    # bar where either group moving to eighths would land on the target.
    dets = [nh(0, 0.25, 2), nh(150, 0.25, 2),
            nh(600, 0.25, 3, "thirty_second"), nh(750, 0.25, 3, "thirty_second")]
    m = measure_of(dets, num=3, den=4)
    m["detections"][2]["duration_beats"] = 0.25
    m["detections"][3]["duration_beats"] = 0.25
    # sum = 1.0; either group doubling to 0.5 each gives 1.5, not 3.0 — so
    # neither is a candidate and the bar is left alone.
    assert _reconcile_measure_to_meter(m) is None


def test_reconcile_never_changes_the_number_of_notes():
    m = measure_of([nh(0, 0.25, 2), nh(150, 0.25, 2), nh(300, 0.25, 2)])
    n_before = len(m["detections"])
    _reconcile_measure_to_meter(m)
    assert len(m["detections"]) == n_before


# ── the meter plausibility guard ────────────────────────────────────────────
# Digits are concatenated positionally, so spurious digit detections used to
# produce arbitrarily large "meters" that the exporter wrote straight into
# MusicXML. Measured on an engraved Brahms 1 excerpt: 686/868, 786/86, 68/862.

class FakeDigit:
    def __init__(self, x, y, value, w=20):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical = w
        self.category = "time_sig_digit"
        self.smufl_name = f"timeSig{value}"


def test_parse_time_signature_reads_a_real_meter():
    from tools.omr.rhythm import parse_time_signature
    dets = [FakeDigit(40, 10, 6), FakeDigit(40, 40, 8)]
    assert parse_time_signature(dets) == {
        "numerator": 6, "denominator": 8, "raw": "6/8"}


def test_parse_time_signature_rejects_an_impossible_denominator():
    from tools.omr.rhythm import parse_time_signature
    # 686/868 — the exact shape that broke the Brahms export.
    dets = [FakeDigit(40, 10, 6), FakeDigit(60, 10, 8), FakeDigit(80, 10, 6),
            FakeDigit(40, 40, 8), FakeDigit(60, 40, 6), FakeDigit(80, 40, 8)]
    assert parse_time_signature(dets) is None


def test_parse_time_signature_rejects_an_absurd_numerator():
    from tools.omr.rhythm import parse_time_signature
    dets = [FakeDigit(40, 10, 6), FakeDigit(60, 10, 8),  # 68
            FakeDigit(40, 40, 4)]
    assert parse_time_signature(dets) is None


# ── seeding: the dossier as an input ────────────────────────────────────────

def test_slot_facts_join_only_when_counts_match():
    d = make_dossier()
    assert dz.slot_facts_for_system(4, d) is not None
    assert dz.slot_facts_for_system(6, d) is None
    assert dz.slot_facts_for_system(0, d) is None


def test_slot_facts_carry_written_clef_and_key():
    facts = dz.slot_facts_for_system(4, make_dossier())
    assert [f["clef"] for f in facts] == ["treble", "treble", "alto", "bass"]
    assert [f["fifths"] for f in facts] == [-3, -1, -3, -3]


def test_page_level_join_survives_broken_system_grouping():
    """One musical system of 21 staves was reported as TWELVE systems of 1-5,
    so a per-system join can never match. The page total still can."""
    d = make_dossier()
    assert dz.slot_facts_for_page(4, d) is not None
    # Two real systems on one page count 2x parts and must NOT join.
    assert dz.slot_facts_for_page(8, d) is None


# ── one glyph, one staff ────────────────────────────────────────────────────
# Cells are padded 4 staff-spaces each way, so on a conductor's score adjacent
# cells overlap and the detector finds the same ink twice.

from tools.omr.transcribe import _dedupe_cross_staff_detections  # noqa: E402


def _staff_with(idx, dets):
    return {"staff_index": idx,
            "measures": [{"measure_index": 0, "detections": list(dets)}]}


def _det(x, y, w=30, h=30, cat="notehead"):
    return {"category": cat, "bbox": [x, y, w, h], "bbox_page": [x, y, w, h],
            "duration_beats": 1.0, "pitch": "C4"}


def test_duplicate_is_kept_on_the_nearer_staff():
    # staff 0 band 0..100, staff 1 band 300..400. The glyph sits at y=110,
    # inside both padded cells but far nearer staff 0.
    a, b = _det(50, 110), _det(50, 110)
    pg = page(_staff_with(0, [a]), _staff_with(1, [b]))
    removed = _dedupe_cross_staff_detections(pg, {0: (0, 100), 1: (300, 400)})
    assert removed == 1
    kept = [s["measures"][0]["detections"] for s in pg["systems"][0]["staves"]]
    assert len(kept[0]) == 1 and kept[1] == []


def test_distinct_glyphs_are_untouched():
    pg = page(_staff_with(0, [_det(50, 10)]), _staff_with(1, [_det(400, 350)]))
    assert _dedupe_cross_staff_detections(pg, {0: (0, 100), 1: (300, 400)}) == 0


def test_different_categories_never_merge():
    """A rest and a notehead at the same place are two readings of one glyph,
    but resolving that is the detector's job, not this pass's."""
    pg = page(_staff_with(0, [_det(50, 110)]),
              _staff_with(1, [_det(50, 110, cat="rest")]))
    assert _dedupe_cross_staff_detections(pg, {0: (0, 100), 1: (300, 400)}) == 0


def test_a_page_whose_bands_never_overlap_is_unchanged():
    """The keyboard case: nothing to arbitrate, so nothing changes."""
    pg = page(_staff_with(0, [_det(50, 10), _det(90, 20)]),
              _staff_with(1, [_det(50, 320), _det(90, 330)]))
    before = [list(s["measures"][0]["detections"])
              for s in pg["systems"][0]["staves"]]
    assert _dedupe_cross_staff_detections(pg, {0: (0, 100), 1: (300, 400)}) == 0
    after = [s["measures"][0]["detections"] for s in pg["systems"][0]["staves"]]
    assert before == after
# ── joining a work's parts to a condensed page ──────────────────────────────


class TestJoinPartsToSlots:
    """A work lists parts; a page prints staves, and condenses.

    `slot_facts_for_system` needs the two counts to agree, which they rarely do
    — Beethoven 5 is written for 18 parts and printed 11 staves to a system, so
    the dossier stays silent on every page of it. `join_parts_to_slots` aligns
    them instead, on the margin labels and never on the clefs, since clefs are
    what the join exists to supply.
    """

    @staticmethod
    def _work(names, clefs=None):
        clefs = clefs or ["treble"] * len(names)
        return {
            "work_id": "test-work",
            "parts": [{"name": n, "written_clef": c, "written_fifths": 0}
                      for n, c in zip(names, clefs)],
        }

    def test_a_condensed_pair_is_one_staff(self):
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(["Flute 1", "Flute 2", "Oboe 1", "Oboe 2"])
        facts = join_parts_to_slots(2, work, {0: "Flute", 1: "Oboe"})
        assert [f["part"] for f in facts] == ["Flute 1", "Oboe 1"]

    def test_an_unlabelled_staff_between_anchors_is_still_placed(self):
        """The case this earns its keep on: Beethoven 5's bassoon staff carries
        no label, and is pinned by the clarinets above and the horns below."""
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(
            ["Clarinet 1", "Clarinet 2", "Bassoon 1", "Bassoon 2", "Horn 1", "Horn 2"],
            ["treble", "treble", "bass", "bass", "treble", "treble"])
        facts = join_parts_to_slots(3, work, {0: "Clarinet", 2: "Horn"})
        assert facts[1]["part"] == "Bassoon 1"
        assert facts[1]["clef"] == "bass"
        assert facts[1]["anchored"] is True

    def test_it_condenses_rather_than_dropping_a_part(self):
        """Five string parts on four staves: the cellos and basses share the
        bottom one. Pricing a same-instrument merge cheaply and a
        different-instrument merge dearer is what settles this — with one price
        for both, the aligner drops the second violin instead."""
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(
            ["Violin 1", "Violin 2", "Viola", "Violoncello", "Contrabass"],
            ["treble", "treble", "alto", "bass", "bass"])
        facts = join_parts_to_slots(4, work, {0: "Violin", 2: "Viola"})
        assert [f["part"] for f in facts][:3] == ["Violin 1", "Violin 2", "Viola"]
        assert facts[3]["clef"] == "bass"

    def test_a_tail_with_slack_is_not_anchored(self):
        """Between labels the alignment cannot slip; past them it is guessing,
        and on the ground-truth pages that is exactly where it goes wrong — the
        string section, which carries no labels at all.

        Two staves below the last label and THREE parts left for them: one part
        has to be dropped or condensed, and nothing says which. That is a real
        guess and stays gated.
        """
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(["Flute 1", "Oboe 1", "Violin 1", "Viola", "Cello"])
        facts = join_parts_to_slots(4, work, {0: "Flute", 1: "Oboe"})
        assert [f["anchored"] for f in facts] == [True, True, False, False]

    def test_a_tail_whose_count_closes_exactly_IS_anchored(self):
        """...but "past the last label" is not one thing.

        Two staves below the last label and exactly TWO parts left for them. A
        monotone alignment has one option: it cannot merge, extend or skip
        without leaving a staff empty. There is nothing left to get wrong, so
        the tail is trusted — which is what takes Beethoven 5 p.48 from 14 of 17
        clefs to 17 of 17. Trusting the tail UNCONDITIONALLY is the different,
        rejected rule (50/52 -> 44/52); see `dossier._determined_tail`.
        """
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(["Flute 1", "Oboe 1", "Violin 1", "Viola"],
                          ["treble", "treble", "treble", "alto"])
        facts = join_parts_to_slots(4, work, {0: "Flute", 1: "Oboe"})
        assert [f["anchored"] for f in facts] == [True, True, True, True]
        assert facts[3]["part"] == "Viola" and facts[3]["clef"] == "alto"

    def test_no_labels_anchors_nothing(self):
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(["Flute 1", "Oboe 1"])
        facts = join_parts_to_slots(2, work, {})
        assert all(not f["anchored"] for f in facts if f)


class TestJoinPinsOnUnambiguousLabelsOnly:
    """A pin is a hard constraint, so an ambiguous label must not make one.

    `benchmarks/omr-part-staff-join-2026-08/RESULTS.md`.
    """

    WORK = {"work_id": "toy", "parts": [
        {"name": "Trumpet 1", "written_clef": "treble"},
        {"name": "Trombone 1", "written_clef": "alto"},
        {"name": "Trombone 2", "written_clef": "tenor"},
        {"name": "Timpani", "written_clef": "bass"},
    ]}

    def _join(self, labels):
        from tools.omr.dossier import join_parts_to_slots
        return [f["part"] if f else None
                for f in join_parts_to_slots(4, self.WORK, labels)]

    def test_the_printed_order_beats_the_part_list(self):
        # Timpani printed ABOVE the trombones, as Beethoven 5 p.48 prints them.
        # A monotone alignment cannot go back for the trombones once it has
        # taken the timpani; pinning reaches all four.
        assert self._join({0: "Tr.", 1: "Timp.", 2: "Tromboni", 3: "Tromboni"}) == [
            "Trumpet 1", "Timpani", "Trombone 1", "Trombone 2"]

    def test_an_ambiguous_alias_is_tested_after_the_part_numbers(self):
        # "Cor." is Horn or Trumpet and must not pin. A margin prints the
        # numbered form as often as the bare one, and testing the whole label
        # rather than the alias that matched lets "Cor. 1. 2." through.
        from tools.omr.instruments import AMBIGUOUS_ALIASES, lookup, normalize_label
        for label in ("Cor.", "Cor. 1. 2."):
            assert lookup(label).alias in AMBIGUOUS_ALIASES, label
        assert normalize_label("Cor. 1. 2.") not in AMBIGUOUS_ALIASES, (
            "the whole label is NOT the thing to test — this is the gap")
        # And a full name that happens to carry numbers stays pinnable.
        assert lookup("Corni 1. 2.").alias not in AMBIGUOUS_ALIASES


class TestTailCountingSeesCondensedStaves:
    """The exact-tail rule is a COUNT, so it has to count condensed parts.

    `benchmarks/omr-part-staff-join-2026-08/RESULTS.md` — the Pastoral is the
    case: five labelled wind staves carry ten parts, two to a staff, leaving
    exactly five parts for the five string staves. Counting from the assignment
    alone misses the second of every pair, so the tail reads as five staves
    chasing six parts and stays gated with the viola unread.
    """

    def _work(self, names, clefs):
        return {"work_id": "toy", "parts": [
            {"name": n, "written_clef": c, "written_fifths": 0}
            for n, c in zip(names, clefs)]}

    def test_a_condensed_staff_reports_every_part_it_took(self):
        from tools.omr.score_layouts import ScoreLayout, align_to_layout
        layout = ScoreLayout("w", ("Flute", "Flute", "Viola"))
        absorbed: dict[int, list[int]] = {}
        _score, out = align_to_layout(layout, 2, {0: "Flute", 1: "Viola"},
                                      allow_merge=True, return_indices=True,
                                      absorbed=absorbed)
        # The assignment can only name one part for the condensed staff...
        assert out == [0, 2]
        # ...while `absorbed` names both, which is what the count needs.
        assert sorted(absorbed[0]) == [0, 1]
        assert absorbed[1] == [2]

    def test_the_tail_below_a_condensation_still_closes(self):
        """The Pastoral, reduced: two wind pairs on two labelled staves, then
        three unlabelled string staves for exactly three remaining parts."""
        from tools.omr.dossier import join_parts_to_slots

        work = self._work(
            ["Flute 1", "Flute 2", "F Horn 1", "F Horn 2",
             "Violin 1", "Viola", "Violoncello"],
            ["treble", "treble", "treble", "treble", "treble", "alto", "bass"])
        facts = join_parts_to_slots(5, work, {0: "Flute", 1: "Horn"})
        assert [f["part"] for f in facts] == [
            "Flute 1", "F Horn 1", "Violin 1", "Viola", "Violoncello"]
        assert all(f["anchored"] for f in facts), \
            "the three staves below the last label have exactly three parts left"
        assert facts[3]["clef"] == "alto", "and that is what supplies the viola"
