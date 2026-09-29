"""ROADMAP 2.12k — a change holds until a printed change BACK, and the
return is always printed (Sean, 2026-09-28).

Brahms 1 / Breitkopf, whole-movement: `system/1/0`'s opening (m. 8, the
hemiola bar) is corroborated `9/8` by the PRECEDING system's own cautionary
(2.12h). One bar later (m. 9, cell 1) the plate prints a clean `6/8` on
about 13 of 14 staves and the detector boxes none of it (FINDINGS
`benchmarks/omr-shape-role-2026-09/FINDINGS.md` SS2.12h.b / PART 7). Traced
on the saved whole-movement record
(`.claude/worktrees/redecide-f4168dfd/out-redecide/brahms/amended.record.json`,
via `record_io.load_record`): `system/1/0`'s `Q.METER` verdict is
`abstained`, `reason="carry_not_corroborated"`, `detail.carried_via_
cautionary=True` — the carry (via the cautionary) never had enough of this
system's own bars to check itself against, so it never asserts anything, and
the exporter's `in_force` fallback silently continues declaring whatever the
PREVIOUS system last stated. The `6/8` that resumes from m. 9 is therefore
never READ and never LABELLED — it is simply what was already in force
before the confirmed `9/8` change, reappearing because nothing overwrote it.

This file covers two layers, matching the two places the brief asks for a
change: ADJUDICATE (`adjudicators.rhythm._carry_meter`, the LABEL) and
EXPORT (`staged.export`/`staged.lilypond`, the MARK).

⚠️ RED-BEFORE, self-contained (the same technique 2.12h's own RED test
uses, `test_staged_opening_meter.py`): `TestTheLabel`'s two "meter_return_
not_read" tests monkeypatch `rhythm_mod._adjacent_corroborated_cautionary`
to always return `None` — exactly what every call site saw before this
item, and before 2.12h. With it patched, the carry falls back to the
SOURCE's own plain in-force meter (never the cautionary's), so a
destination whose bars genuinely fit that PRIOR meter now DECIDES
`"carried"` at it — the file's silent, unlabelled reversion this item
exists to stop being silent. `TestTheMark`'s tests are RED against the
unrepaired tree a different way: every assertion reads a key
(`report["meter_returns_not_read"]`) or a rendered string (`"meter?"`,
`METER_RETURN_NOT_READ_REASON`) that does not exist before this branch's
`rhythm.py` / `export.py` / `lilypond.py` changes, so they fail on
`AttributeError` / `KeyError` rather than a behavioural difference.

⚠️ No test here reads module source text (CLAUDE.md rule 6c / SS6c) — every
assertion is against a live `Ruling`/`Verdict`, or a rendered MusicXML /
LilyPond string.
"""

from __future__ import annotations

import os
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as staged_lily
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_export import QUARTER, _log_json, _obs, _vrd

# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE — the label
# ─────────────────────────────────────────────────────────────────────────────


def _opening(log, sysj, num, den, raw=None, n_staves=3):
    for st in range(n_staves):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE,
                    (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7,
                    raw=raw or f"{num}/{den}")


def _cautionary_or_change_glyphs(log, sysj, staff_index, cell, num, den):
    """A complete stacked meter on ONE staff at `cell` — a CAUTIONARY if
    `cell` is `sysj`'s own LAST cell, a mid-system CHANGE otherwise (the
    same helper `test_staged_opening_meter.py` uses, under its own name)."""
    for digit, y in ((num, 10.0), (den, 30.0)):
        log.observe(R.staff(sysj.page, sysj.system, staff_index),
                    Q.METER_GLYPH, "timeSig%d" % digit,
                    reader=READERS.DETECTOR, frame="cell:%d" % cell,
                    score=0.9, cell=cell, x=10.0, y_center=y, letter=False)


def _staff_count(log, sysj, n_staves):
    log.record(adjudicate.Verdict(
        id=log._next_id("vrd"), subject=sysj,
        quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
        value=n_staves, decider="t", reason="counted"))


def _measure_partition(log, sysj, n_staves, n_cells):
    for st in range(n_staves):
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(sysj.page, sysj.system, st),
            quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
            value=n_cells, decider="t", reason="barlines"))


def _bars(log, sysj, n_staves, n_bars, beats, *, first_cell=0):
    """`n_bars` bars from `first_cell`, each read by `n_staves` staves at
    `beats` quarters — the shape `_bar_lengths_for`/`_corroborate` read."""
    for st in range(n_staves):
        for c in range(first_cell, first_cell + n_bars):
            cell = R.cell(sysj.page, sysj.system, st, c)
            g = R.glyph(sysj.page, sysj.system, st, c, 0)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 400, 0, 600, 16),
                        reader=READERS.DETECTOR, frame="cell:%d" % c,
                        score=0.9)
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                outcome=Outcome.DECIDED,
                value={"beats": beats, "written": beats,
                       "duration_type": "quarter", "dots": 0},
                decider="t", reason="head_and_marks"))
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                outcome=Outcome.DECIDED,
                value={"events": [{"glyphs": [0], "x": 500.0,
                                   "kind": "chord"}]},
                decider="t", reason="x_clustered"))


def _run(log):
    """Adjudicate METER over every system in document order, carry ON, the
    bars-derive-a-length rung OFF — isolating the carry/cautionary
    mechanism under test, `test_staged_opening_meter.py`'s own discipline."""
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    prev = {k: os.environ.get(k) for k in
            (rhythm_mod.METER_CARRY_ENV, rhythm_mod.METER_FROM_BARS_ENV)}
    os.environ[rhythm_mod.METER_CARRY_ENV] = "1"
    os.environ[rhythm_mod.METER_FROM_BARS_ENV] = "0"
    try:
        for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
            adjudicate.adjudicate_one(log, spec, sysj)
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


N_STAVES = 3


def _source(*, src_n_cells=7, cautionary_staves=None):
    """SOURCE = system(0, 0): opens `6/8` cleanly, and corroborates a `9/8`
    cautionary at its own LAST cell — 2.12h's own shape."""
    log = Log()
    src = R.system(0, 0)
    _staff_count(log, src, N_STAVES)
    _measure_partition(log, src, N_STAVES, src_n_cells)
    _opening(log, src, 6, 8, n_staves=N_STAVES)
    for st in (cautionary_staves if cautionary_staves is not None
              else range(N_STAVES)):
        _cautionary_or_change_glyphs(log, src, st, src_n_cells - 1, 9, 8)
    return log, src


class TestTheLabel(unittest.TestCase):
    """The Brahms shape: a corroborated cautionary confirms a printed `9/8`
    change into the DESTINATION's own opening; the destination's OWN bars
    (from cell 1 onward — the bar the cautionary says nothing about) fit a
    DIFFERENT length, `6/8`. Sean, 2026-09-28: the change holds until a
    printed change back, and the return is always printed — so this is not
    "the meter silently became 6/8", it is "a printed return exists here and
    we never read it"."""

    def _destination(self, log, *, n_cells=3, bar_beats=3.0):
        """DESTINATION = system(1, 0): its own vote disagrees with the
        cautionary (the Brahms case: the header template misreads `9/8` as
        `9/4`), rerouting through the fallback ladder; `n_cells - 1` bars
        from cell 1 read `bar_beats` quarters each."""
        dst = R.system(1, 0)
        _staff_count(log, dst, N_STAVES)
        _measure_partition(log, dst, N_STAVES, n_cells)
        _opening(log, dst, 9, 4, n_staves=N_STAVES)      # the misread digit
        _bars(log, dst, N_STAVES, n_cells - 1, bar_beats, first_cell=1)
        return dst

    # ── RED -> GREEN ─────────────────────────────────────────────────────

    def test_the_fix_is_reachable_RED_without_it(self):
        """⚠️ RED-BEFORE. With the cautionary lookup forced to `None` —
        every call site's answer before 2.12h, and the shape this item's own
        carry-weighing still falls back to when there is nothing to prefer —
        `_carry_meter` carries the SOURCE's plain in-force meter (`6/8`)
        instead of the cautionary's `9/8`. The destination's bars (6/8-worth
        each) then CONFIRM that carry, so it silently DECIDES `"carried"` at
        `6/8` — the exact unlabelled reversion CLAUDE.md SS10 and this
        item's own roadmap row describe, reproduced as a live regression
        guard rather than only asserted in prose.
        """
        log, _src = _source()
        dst = R.system(1, 0)
        _staff_count(log, dst, N_STAVES)
        _measure_partition(log, dst, N_STAVES, 3)
        # ⚠️ NO VOTE AT ALL -- with the cautionary lookup patched off,
        # `adjudicate_meter`'s own disagreement check ALSO sees `None`, so a
        # destination that voted anything would simply be ASSERTED as
        # `"voted"`, never reaching `_carry_meter` -- a different, unrelated
        # green. Empty `Q.METER_TEMPLATE` rows is the shape that reaches the
        # carry regardless (`adjudicate_meter`'s own `"no_evidence"` branch).
        _bars(log, dst, N_STAVES, 2, 3.0, first_cell=1)
        with mock.patch.object(rhythm_mod, "_adjacent_corroborated_cautionary",
                               return_value=None):
            _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (6, 8))

    def test_the_bars_overturning_the_cautionary_are_labelled_not_silent(self):
        """GREEN: the SAME fixture, cautionary lookup live. The carry now
        tries the CONFIRMED `9/8` (from the cautionary) first; the
        destination's own bars (each 3.0 quarters, `6/8`-worth) contradict
        it on every one of them, so the carry is overturned — and because
        the overturned candidate came from a corroborated cautionary
        (`carried_via_cautionary`), the abstention is `meter_return_not_read`
        rather than the bare `carry_outweighed_by_the_bars`, naming the bar
        (cell 1, the very next one) where the print's own return must sit.
        """
        log, _src = _source()
        dst = self._destination(log, bar_beats=3.0)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, rhythm_mod.METER_RETURN_NOT_READ_REASON)
        self.assertTrue(v.detail["carried_via_cautionary"])
        self.assertEqual(v.detail["at_cell"], rhythm_mod.METER_RETURN_MARK_CELL)
        self.assertEqual(v.detail["at_cell"], 1)

    def test_TOO_FEW_bars_to_check_is_the_same_label(self):
        """The OTHER rung `_carry_meter` can abstain from
        (`carry_not_corroborated`, too few assessable bars rather than
        bars that actively disagree) — the Brahms record's OWN shape
        (`bars_assessable: 0`). Still a confirmed change nothing could
        confirm past its own opening, so the SAME label applies."""
        log, _src = _source()
        dst = R.system(1, 0)
        _staff_count(log, dst, N_STAVES)
        _measure_partition(log, dst, N_STAVES, 3)
        _opening(log, dst, 9, 4, n_staves=N_STAVES)
        # no `_bars` at all -- nothing is assessable
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, rhythm_mod.METER_RETURN_NOT_READ_REASON)
        self.assertEqual(v.detail["at_cell"], 1)

    # ── controls: when the label must NOT fire ──────────────────────────

    def test_CONTROL_bars_that_FIT_the_change_carry_it_unlabelled(self):
        """Control: a stated change followed by bars that FIT it -> no
        switch, no label. The same fixture, `bar_beats=4.5` (`9/8`-worth)
        instead of `3.0` -- the cautionary's own candidate is CONFIRMED, so
        it stands as an ordinary `"carried"` decision."""
        log, _src = _source()
        dst = self._destination(log, bar_beats=4.5)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 8))
        self.assertNotEqual(v.reason, rhythm_mod.METER_RETURN_NOT_READ_REASON)

    def test_CONTROL_a_READ_return_is_switched_and_unlabelled(self):
        """Control: the return is genuinely PRINTED and GATHER read it —
        the destination's own opening AGREES with the cautionary (so no
        reroute at all: a plain `"voted"` decision) and a mid-system CHANGE
        back to `6/8`, corroborated on every staff, is read at cell 1 (NOT
        this system's own last cell, so it is a change and not a second
        cautionary). `meter_at` answers `6/8` from cell 1 -- switched -- and
        the reason is the ordinary `"voted"`, carrying no `meter_return_not_
        read` label at all, because there is nothing unread here."""
        log, _src = _source()
        dst = R.system(1, 0)
        _staff_count(log, dst, N_STAVES)
        _measure_partition(log, dst, N_STAVES, 3)
        _opening(log, dst, 9, 8, n_staves=N_STAVES)     # AGREES with the cautionary
        for st in range(N_STAVES):
            _cautionary_or_change_glyphs(log, dst, st, 1, 6, 8)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "voted")
        self.assertEqual(R.meter_at(v.value, 0)["raw"], "9/8")
        self.assertEqual(R.meter_at(v.value, 1)["raw"], "6/8")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT — the mark
# ─────────────────────────────────────────────────────────────────────────────


def _vrd_detail(i, subject, quantity, value, *, outcome="decided",
               reason="x", detail=None):
    v = _vrd(i, subject, quantity, value, outcome=outcome, reason=reason)
    v["detail"] = dict(detail or {})
    return v


def _notes_at_cell(obs, vrd, cell, pitches, *, start_id, dur=QUARTER):
    for k, pitch in enumerate(pitches):
        gi = 100 * cell + k
        sub = f"glyph/0/0/0/{cell}/{gi}"
        obs.append(_obs(start_id + 4 * k, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", 100 * k, 50, 40, 40],
                        category="notehead"))
        obs.append(_obs(start_id + 4 * k + 1, sub, Q.NOTEHEAD_CLASS,
                        "noteheadBlackOnLine"))
        vrd.append(_vrd(start_id + 4 * k + 2, sub, Q.PITCH, pitch))
        vrd.append(_vrd(start_id + 4 * k + 3, sub, Q.DURATION, dur))


def _meter_return_page(*, marked=True, staff=0):
    """One system, one staff, two bars. Cell 0 carries one note (the
    corroborated-but-un-asserted `9/8` change, per the trace); cell 1
    carries three quarter notes (the printed `6/8` return, un-read).

    ⚠️ NO PRECEDING METER IS DECLARED, and that is deliberate isolation, not
    an oversight: with `Q.METER` `abstained` at `system/0/0`, `run.meter` is
    `None` for every one of its own cells and `in_force` never moves off its
    initial `None` either -- so `judged` is `None` throughout and NEITHER
    bar can be held out by ROADMAP 2.8's bar-sum check (`_bar_quarters(None)`
    is `None`). That isolates the MARK from the HOLD-OUT: this test is about
    whether a bar with real notes gets the "meter?" direction, not about
    whether it also happens to add up.
    """
    obs, vrd = [], []
    _notes_at_cell(obs, vrd, 0, ["C4"], start_id=0)
    _notes_at_cell(obs, vrd, 1, ["D4", "E4", "F4"], start_id=100)
    vrd.append(_vrd(900, f"staff/0/0/{staff}", Q.MEASURE_PARTITION, 2))
    vrd.append(_vrd(901, f"staff/0/0/{staff}", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    if marked:
        vrd.append(_vrd_detail(
            904, "system/0/0", Q.METER, None, outcome="abstained",
            reason=SX.METER_RETURN_NOT_READ_REASON,
            detail={"at_cell": 1, "carried_from": "system/-1/0",
                    "carried_via_cautionary": True,
                    "instead_of": "opening_disagrees_with_prior_cautionary"}))
    else:
        vrd.append(_vrd(904, "system/0/0", Q.METER,
                        {"numerator": 9, "denominator": 8, "raw": "9/8"},
                        reason="carried"))
    return _log_json(obs, vrd)


def _directions(xml):
    return ET.fromstring(xml).findall(".//direction")


def _measures(xml):
    return ET.fromstring(xml).findall(".//measure")


class TestTheMark(unittest.TestCase):
    """(the bar gets a marker without being emptied) -- "it is NOT a
    held-out bar, and the accounting equality must still balance" (brief)."""

    def test_the_second_measure_carries_the_red_word_and_keeps_its_notes(self):
        xml, rep = SX.to_musicxml(_meter_return_page())
        measures = _measures(xml)
        self.assertEqual(len(measures), 2)
        # cell 0: untouched, no marker.
        self.assertEqual(measures[0].findall(".//direction"), [])
        # cell 1: the marker, ABOVE the staff, red, and the real notes kept.
        dirs = measures[1].findall(".//direction")
        self.assertEqual(len(dirs), 1)
        self.assertEqual(dirs[0].get("placement"), "above")
        words = dirs[0].find("./direction-type/words")
        self.assertEqual(words.text, "meter?")
        self.assertEqual(words.get("color"), SX.UNREAD_BAR_MARK_COLOR)
        pitches = measures[1].findall(".//note/pitch/step")
        self.assertEqual([p.text for p in pitches], ["D", "E", "F"])

    def test_it_is_counted_and_not_a_held_bar(self):
        _xml, rep = SX.to_musicxml(_meter_return_page())
        self.assertEqual(rep["meter_returns_not_read"], 1)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"].get("notes", 0), 4)   # 1 + 3, ALL written

    def test_lilypond_carries_the_same_mark(self):
        text, rep = staged_lily.to_lilypond(_meter_return_page())
        self.assertIn('\\mark \\markup { \\with-color #red "meter?" }', text)
        self.assertEqual(rep["meter_returns_not_read"], 1)
        # the bar's own notes are still there, not a rest:
        self.assertIn("d'4", text)
        self.assertIn("e'4", text)
        self.assertIn("f'4", text)

    # ── control: no switch, no mark ──────────────────────────────────────

    def test_CONTROL_a_plain_carried_meter_is_not_marked(self):
        """Control: the SAME two bars, but `Q.METER` DECIDED (`"carried"`)
        rather than abstained `meter_return_not_read` -- no marker anywhere,
        in either file."""
        xml, rep = SX.to_musicxml(_meter_return_page(marked=False))
        # ⚠️ NOT "no directions at all" -- a plain DECIDED `9/8` judges BOTH
        # bars (no segment narrows it to cell 0 alone) and cell 1's three
        # quarters do not add up to it, so ROADMAP 2.8's OWN unrelated
        # hold-out mark fires here. This control is about THIS mechanism
        # only: no "meter?" word, anywhere.
        words = [d.find("./direction-type/words").text
                for d in _directions(xml)]
        self.assertNotIn("meter?", words)
        self.assertEqual(rep["meter_returns_not_read"], 0)
        text, ly_rep = staged_lily.to_lilypond(_meter_return_page(marked=False))
        self.assertNotIn("meter?", text)
        self.assertEqual(ly_rep["meter_returns_not_read"], 0)


if __name__ == "__main__":
    unittest.main()
