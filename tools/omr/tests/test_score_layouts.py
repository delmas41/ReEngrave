"""The score-order prior (`tools/omr/score_layouts.py`).

Score order is monotone — instruments never appear out of family order — so
"which instrumentation is this?" is an alignment against a library of standard
layouts rather than a classification. These tests pin the three things that
makes it useful: it reads an unlabelled system by position, it refuses to name
a staff the plausible layouts disagree about, and it settles the labels a
lexicon cannot.

Synthetic — no PDF, no weights — so it runs in the default suite. The measured
results on real pages live in `benchmarks/omr-score-order/RESULTS.md`.
"""

from __future__ import annotations

from tools.omr.instruments import candidates_for_alias, lookup
from tools.omr.score_layouts import (
    LAYOUTS,
    align_to_layout,
    fit_layouts,
    resolve_ambiguous_label,
)


def _layout(name: str):
    return next(layout for layout in LAYOUTS if layout.name == name)


CLASSICAL = ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet", "Timpani",
             "Violin", "Violin", "Viola", "Cello", "Contrabass"]


def _true_clefs(parts):
    out = {}
    for i, name in enumerate(parts):
        match = lookup(name)
        if match:
            out[i] = match.instrument.default_clef
    return out


class TestAlignment:

    def test_a_layout_aligns_to_itself(self):
        layout = _layout("classical-condensed")
        score, assignment = align_to_layout(layout, layout.size)
        assert list(assignment) == list(layout.parts)
        assert score > 0

    def test_a_missing_part_is_a_gap_not_a_shift(self):
        """A system without trombones is the same orchestra with a part tacet.
        Everything below the gap must keep its own name."""
        layout = _layout("romantic")
        parts = [p for p in layout.parts if p != "Trombone"]
        labels = {i: p for i, p in enumerate(parts)}
        _score, assignment = align_to_layout(layout, len(parts), labels)
        assert list(assignment) == parts

    def test_a_part_may_take_more_than_one_staff(self):
        """Two horns on two staves, a harp on two, violins divided: the extra
        staves belong to the part above them, not to the next instrument."""
        layout = _layout("french-large")
        # 17 parts printed on 19 staves: the horns take two, the harp takes two.
        n = layout.size + 2
        _score, assignment = align_to_layout(layout, n, clefs=None)
        # However it distributes them, order is preserved and nothing is
        # invented: every assigned part appears in the layout, in order.
        assigned = [a for a in assignment if a is not None]
        positions = [layout.parts.index(a) for a in assigned]
        assert positions == sorted(positions)


class TestFit:

    def test_an_unlabelled_classical_system_is_read_by_position(self):
        """The case this exists for: no text, no labels, twelve staves."""
        fit = fit_layouts(12, clefs=_true_clefs(CLASSICAL))
        assert fit is not None
        assert fit.layout.name.startswith("classical")
        named = [(i, a) for i, a in enumerate(fit.assignment) if a is not None]
        assert len(named) >= 10
        assert all(a == CLASSICAL[i] for i, a in named)

    def test_it_abstains_on_a_system_too_small_to_have_an_order(self):
        assert fit_layouts(2) is None

    def test_a_staff_the_layouts_disagree_about_is_not_named(self):
        """Confidence is agreement among the plausible layouts, not the score
        margin between the best two — so where traditions differ, it says
        nothing rather than picking one."""
        fit = fit_layouts(20)
        assert fit is not None
        assert any(a is None for a in fit.assignment), (
            "a 20-staff system with no other evidence cannot be certain of "
            "every part"
        )
        # ...and where it does speak, it is because the voters agreed.
        for name, share in zip(fit.assignment, fit.agreement):
            if name is not None:
                assert share >= 0.75

    def test_the_string_section_is_the_confident_end(self):
        """Violins, viola and cello are the same in every tradition, so that is
        where a position-only reading is on firmest ground.

        The LAST staff is not, and the fit says so: `classical-condensed` gives
        the basses their own staff and `classical-shared-bass` has them share
        the cellos', which is a real disagreement between two real conventions.
        It comes out unnamed at 0.64 agreement rather than guessed."""
        fit = fit_layouts(len(CLASSICAL), clefs=_true_clefs(CLASSICAL))
        assert fit is not None
        assert list(fit.assignment[7:11]) == ["Violin", "Violin", "Viola", "Cello"]
        assert fit.assignment[11] is None
        assert 0.5 <= fit.agreement[11] < 0.75


class TestAmbiguousLabels:
    """`Tp.` is Timpani in the German and Italian tradition and Trumpet in the
    English one. The lexicon has to pick one; position can actually know."""

    def test_the_alias_is_declared_ambiguous(self):
        candidates = candidates_for_alias("tp")
        assert [c.name for c in candidates] == ["Timpani", "Trumpet"]

    def test_position_picks_timpani_below_the_trumpets(self):
        fit = fit_layouts(len(CLASSICAL), clefs=_true_clefs(CLASSICAL))
        assert fit is not None
        # slot 6 sits below Horn and Trumpet — the timpani's place.
        chosen = resolve_ambiguous_label(6, candidates_for_alias("tp"), fit)
        assert chosen is not None and chosen.name == "Timpani"

    def test_position_picks_trumpet_where_the_trumpets_are(self):
        """The same alias, five staves higher, is the other instrument. This is
        the half a lexicon cannot do."""
        fit = fit_layouts(len(CLASSICAL), clefs=_true_clefs(CLASSICAL))
        assert fit is not None
        chosen = resolve_ambiguous_label(5, candidates_for_alias("tp"), fit)
        assert chosen is not None and chosen.name == "Trumpet"

    def test_no_fit_means_no_opinion(self):
        """With nothing to go on it must not choose — the caller keeps whatever
        reading it already had."""
        assert resolve_ambiguous_label(6, candidates_for_alias("tp"), None) is None

    def test_it_only_chooses_among_the_candidates(self):
        """The prior may not overrule the label with something the alias cannot
        mean: at slot 0 the layout says Flute, which is not on the ballot."""
        fit = fit_layouts(len(CLASSICAL), clefs=_true_clefs(CLASSICAL))
        assert fit is not None
        assert resolve_ambiguous_label(0, candidates_for_alias("tp"), fit) is None


# ─── Violins are not a condensable pair ─────────────────────────────────────


class TestViolinsDoNotCondense:
    """`MERGE_SAME_PENALTY` is cheap because numbered parts of one instrument
    share a staff — Flauti 1 and 2. Canonicalisation collapses "Violin 1" and
    "Violin 2" to one name, so without `NEVER_CONDENSED` the aligner sees a
    cheap same-name pair where every orchestral tradition prints two staves.

    Measured on Beethoven 5 p.2 (18 parts, 11 staves, 7 merges required): the
    work offers exactly 7 same-name merges only if the violins count, so the
    aligner condensed the two violin sections and every string slot below
    shifted by one. 8 of 11 slots correct before, 10 after.
    """

    def _align(self, parts, n_slots, labels=None):
        from tools.omr.score_layouts import ScoreLayout, align_to_layout
        layout = ScoreLayout(name="work", parts=tuple(parts))
        _score, assignment = align_to_layout(
            layout, n_slots, labels=labels or {}, allow_merge=True,
            return_indices=True,
        )
        return assignment

    def test_two_violins_take_two_staves_when_the_count_allows(self):
        # Four parts, four staves: nothing forces a merge, so nothing merges.
        parts = ["Violin", "Violin", "Viola", "Cello"]
        assert self._align(parts, 4) == [0, 1, 2, 3]

    def test_a_forced_merge_does_not_fall_on_the_violins(self):
        # Five parts, four staves: exactly one merge is required. The flutes are
        # a genuine condensable pair; the violins are not, so the merge must
        # land on the flutes and every string keeps its own slot.
        parts = ["Flute", "Flute", "Violin", "Violin", "Viola"]
        assignment = self._align(parts, 4)
        assert assignment[0] == 0, "the flute pair should share the first staff"
        # Violin 1 (index 2), Violin 2 (index 3) and Viola (4) each keep a slot.
        assert assignment[1:] == [2, 3, 4]

    def test_violin_is_the_only_name_excluded(self):
        from tools.omr.score_layouts import NEVER_CONDENSED
        assert NEVER_CONDENSED == frozenset({"Violin"})


class TestLabelPins:
    """A labelled staff pins its part, so the print's order can beat the list's.

    `benchmarks/omr-part-staff-join-2026-08/` — Beethoven 5 p.48 prints `Timp.`
    above the three trombones and the work's part list has the trombones first.
    """

    # The p.48 shape, reduced to what matters: the timpani part comes AFTER the
    # trombones in the list and BEFORE them on the page.
    PARTS = ("Trumpet", "Trombone", "Trombone", "Trombone", "Timpani", "Violin")
    #          0           1           2           3           4         5

    def test_runs_are_maximal_and_consecutive(self):
        from tools.omr.score_layouts import unique_part_runs
        runs = unique_part_runs(self.PARTS)
        assert runs["Trombone"] == (1, 3)
        assert runs["Timpani"] == (4, 4)

    def test_a_name_printed_twice_has_no_run_to_pin_to(self):
        from tools.omr.score_layouts import unique_part_runs
        runs = unique_part_runs(("Flute", "Oboe", "Flute"))
        assert "Flute" not in runs, "two separated runs cannot resolve a label"
        assert runs["Oboe"] == (1, 1)

    def test_only_the_first_staff_of_a_block_pins(self):
        # Three staves all naming the trombones say where the trombones BEGIN.
        # How many staves they take is the alignment's job, not the label's.
        from tools.omr.score_layouts import label_pins
        labels = {0: "Trombone", 1: "Trombone", 2: "Trombone"}
        assert label_pins(3, labels, self.PARTS) == [(0, 1)]

    def test_an_ambiguous_label_never_pins(self):
        # `Tp.` is Timpani or Trumpet and only POSITION settles it — which is
        # the one thing a pin takes off the table.
        from tools.omr.score_layouts import label_pins
        labels = {0: "Trumpet", 2: "Timpani"}
        assert label_pins(3, labels, self.PARTS) == [(0, 0), (2, 4)]
        assert label_pins(3, labels, self.PARTS, pinnable={0}) == [(0, 0)]

    def test_one_name_claimed_by_two_separated_blocks_pins_neither(self):
        # What a misread looks like: p.48 prints `Tr.` for the trumpets and
        # `Tr. Bas.` for the bass trombone, and a lexicon that reads both as
        # Trumpet has produced a contradiction, not evidence.
        from tools.omr.score_layouts import label_pins
        labels = {0: "Trumpet", 3: "Trumpet"}
        assert label_pins(4, labels, self.PARTS) == []

    def test_no_pins_leaves_the_alignment_exactly_as_it_was(self):
        from tools.omr.score_layouts import (ScoreLayout, align_to_layout,
                                             align_to_layout_pinned)
        layout = ScoreLayout(name="work", parts=self.PARTS)
        _score, plain = align_to_layout(layout, 4, allow_merge=True,
                                        return_indices=True)
        pinned, pins = align_to_layout_pinned(layout, 4, allow_merge=True)
        assert pins == []
        assert pinned == list(plain)

    def test_the_transposition_the_monotone_path_cannot_express(self):
        from tools.omr.score_layouts import (ScoreLayout, align_to_layout,
                                             align_to_layout_pinned)
        layout = ScoreLayout(name="work", parts=self.PARTS)
        # As PRINTED: trumpet, timpani, then the three trombones, then violins.
        labels = {0: "Trumpet", 1: "Timpani",
                  2: "Trombone", 3: "Trombone", 4: "Trombone"}

        # Monotone: having consumed the timpani at part 4 it cannot go back to
        # the trombones at 1-3, so the staves that carry them come back empty.
        _score, plain = align_to_layout(layout, 6, labels=labels,
                                        allow_merge=True, return_indices=True)
        assert plain[1] != 4 or None in plain[2:5]

        pinned, pins = align_to_layout_pinned(layout, 6, labels=labels,
                                              allow_merge=True)
        assert (1, 4) in pins and (2, 1) in pins
        # Every staff reads its own part, in the order the page prints them.
        assert pinned == [0, 4, 1, 2, 3, 5]

    def test_a_span_needing_no_condensation_does_not_condense(self):
        # Between two pins both counts are known, which is where the global
        # merge budget becomes local. Three staves and three trombone parts
        # need no merge — and a merge is rewarded with another full pair score,
        # so leaving it available reads all three staves as the alto trombone.
        from tools.omr.score_layouts import ScoreLayout, align_to_layout_pinned
        # No timpani here: an unpinned part between two pins genuinely has to go
        # somewhere, and that is the merge budget rather than this.
        layout = ScoreLayout(name="work", parts=("Trumpet", "Trombone",
                                                 "Trombone", "Trombone", "Violin"))
        labels = {0: "Trumpet", 1: "Trombone", 4: "Violin"}
        pinned, _pins = align_to_layout_pinned(layout, 5, labels=labels,
                                               allow_merge=True)
        assert pinned == [0, 1, 2, 3, 4]
