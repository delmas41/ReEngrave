"""A generative decoder that stops transcribing and starts WRITING.

`staff_labels_surya.read_crops_text` is the direction reader's rung into a 650M
GGUF driven by llama.cpp, and it degenerates: asked what a crop a few staff
spaces tall says, it has answered with an English essay and with a run of
measure numbers that are not in the crop. Decode is not under this repo's
control — `temperature`, `top_p`, `seed`, `n_predict` and `repeat_penalty`
appear nowhere in `tools/omr` — so a guard is the available defence, not a fix
for the cause.

The margin-label path already has one: `_surya_worker._assign` drops a block
taller than half the system's tick span. `direction_text` bypasses `_assign`
entirely by calling `read_crops_text`, so the single runaway defence this rung
has was not on this path. These tests pin its sibling.

⚠️ The guard is a READER-side sanity check, not a semantic one. What is musical
is the lexicon's question and stays the lexicon's question — including decoder
repetition (`'Cresc. Cresc. Cresc. …'`), which `direction_lexicon` already
refuses by name. This only asks whether a string is a plausible OCR answer at
all.

## What each mutation catches, and why there are two

The constant and the guard are tested SEPARATELY, and each mutation bites on
its own test — which is the property to preserve if these are ever edited:

    mutation                             fails    caught ONLY by that mutation
    guard block removed, constant left   7 / 29   the_boundary_is_where_
                                                  it_says_it_is
    cap raised to 100000, guard left    10 / 29   the_cap_is_inside_the_empty_
                                                  interval, and the three
                                                  predicate tests that name a
                                                  length outright

`test_the_cap_is_inside_the_empty_interval` drives no reader at all — it is
about where 120 sits in the measured distribution — so it survives losing the
guard entirely. `test_the_boundary_is_where_it_says_it_is` drives the reader
against whatever cap is declared, so it survives the cap moving. Neither
mutation is caught by both, which is the point: a correct constant nothing
calls, and a correct guard on a wrong constant, are different bugs.

⚠️ These counts were restated once already, after the predicate tests were
added — re-measure them rather than editing the prose if tests are added again.
A third mutation, the shape this repo has been bitten by (log the refusal, then
return the string anyway), fails 5.

The two long strings below are VERBATIM from committed transcriptions:
`benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-indent35/beethoven-sym3-mvt1.omr.json`
(854 chars, a page read by Surya alone) and
`benchmarks/omr-scan-e2e-2026-09/fixtures/beethoven-sym5-mvt1-984073-p2.restamp-composed.omr.json`
(144 chars).
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys

import numpy as np
import pytest

from tools.omr import staff_labels_surya as S


# ── the two measured runaways ───────────────────────────────────────────────

#: The essay. Note it OPENS with a real reading — `cresc.` was on that page and
#: the generated text buried it, so a runaway is not merely noise: it costs a
#: direction. Refusing it does not recover the prefix, and it must not — that
#: would be repairing a reading, which `strip_line_fragments` documents as the
#: line this rung does not cross.
RUNAWAY_ESSAY = (
    "cresc. The crescence of the core of the system is suggested by the "
    "following facts: 1. A statistical analysis of the data is conducted. "
) + " ".join(f"{n}. The" for n in range(2, 65))

#: The measure-number run, from a real scan of Beethoven 5 / Litolff p.2.
RUNAWAY_NUMBERS = " ".join(f"- {n} -" for n in range(8, 33))

#: Real readings, longest first, from the same corpus: the longest string the
#: lexicon ever ACCEPTED (17), the CC0 footer a LilyPond fixture really prints
#: (47), and a decoder repetition (55) that is real ink read many times and is
#: the LEXICON's to refuse, not this guard's.
REAL_LONGEST_ACCEPTED = "Un poco sostenuto"
REAL_PAGE_FOOTER = "Score: CC0 1.0 Universal: Annotations: CC-By-SA"
REAL_REPEATED = "Cresc. " * 7 + "Cresc."


def _crop():
    return np.zeros((40, 200, 3), dtype=np.uint8)


@pytest.fixture()
def stub_worker(monkeypatch):
    """Drive `read_crops_text` without a venv, a GGUF, or a shared server.

    Points `interpreter()` at this Python and replaces the subprocess with one
    that returns whatever payload the test asks for — so the code under test is
    the real function, and only the model is faked.
    """
    monkeypatch.setenv("OMR_SURYA_PYTHON", sys.executable)

    def _install(texts):
        payload = {"crops": [{"text": t} for t in texts]}

        def _fake_run(*_args, **_kwargs):
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload), stderr="")

        monkeypatch.setattr(S.subprocess, "run", _fake_run)

    return _install


class TestARunawayIsRefused:
    def test_the_essay_comes_back_empty(self, stub_worker):
        stub_worker([RUNAWAY_ESSAY])
        assert S.read_crops_text([_crop()]) == [""]

    def test_the_measure_number_run_comes_back_empty(self, stub_worker):
        stub_worker([RUNAWAY_NUMBERS])
        assert S.read_crops_text([_crop()]) == [""]

    def test_one_runaway_does_not_take_the_batch_with_it(self, stub_worker):
        """Per crop, not per call — a page is one call and holds many crops."""
        stub_worker([REAL_LONGEST_ACCEPTED, RUNAWAY_ESSAY, "dolce"])
        assert S.read_crops_text([_crop()] * 3) == [
            REAL_LONGEST_ACCEPTED, "", "dolce"]


class TestRealReadingsAreUntouched:
    """The guard may not encroach on the lexicon. Every one of these is a
    string the corpus really produced; two of the three the lexicon refuses,
    and it must go on being the thing that refuses them."""

    @pytest.mark.parametrize("text", [
        REAL_LONGEST_ACCEPTED, REAL_PAGE_FOOTER, REAL_REPEATED,
        "", "f", "cresc.", "Allegro con brio", "rCTesEC.",
    ])
    def test_it_comes_back_unchanged(self, stub_worker, text):
        stub_worker([text])
        assert S.read_crops_text([_crop()]) == [text]


class TestTheRefusalIsRecorded:
    """The whole audit this came out of exists because the pipeline drops
    things quietly. A refusal that says nothing would be the same defect in a
    new place."""

    def test_a_refusal_warns_with_its_length(self, stub_worker, caplog):
        stub_worker([RUNAWAY_ESSAY])
        with caplog.at_level(logging.WARNING, logger=S.logger.name):
            S.read_crops_text([_crop()])
        blob = "\n".join(r.getMessage() for r in caplog.records)
        assert str(len(RUNAWAY_ESSAY)) in blob, "the length is not recorded"
        assert "runaway" in blob.lower()

    def test_a_clean_batch_warns_about_nothing(self, stub_worker, caplog):
        stub_worker([REAL_LONGEST_ACCEPTED, "dolce"])
        with caplog.at_level(logging.WARNING, logger=S.logger.name):
            S.read_crops_text([_crop()] * 2)
        assert not [r for r in caplog.records
                    if "runaway" in r.getMessage().lower()]

    def test_the_batch_is_counted(self, stub_worker, caplog):
        stub_worker([RUNAWAY_ESSAY, "dolce", RUNAWAY_NUMBERS])
        with caplog.at_level(logging.WARNING, logger=S.logger.name):
            S.read_crops_text([_crop()] * 3)
        blob = "\n".join(r.getMessage() for r in caplog.records)
        assert "2 of 3" in blob, f"no batch count in: {blob}"


class TestThePredicateItself:
    """`is_runaway_read` is public so its boundary can be tested WITHOUT the
    reader around it, the way `strip_line_fragments` is — its docstring
    promises this, and until 2026-09-07 no test made good on the promise.

    These are deliberately not a substitute for the `read_crops_text` tests
    above: a correct predicate that nothing calls is the exact shape of bug
    this repo keeps finding, so the wiring is tested separately and neither
    set covers for the other.
    """

    @pytest.mark.parametrize("text", [
        "", "f", "cresc.", REAL_LONGEST_ACCEPTED, REAL_PAGE_FOOTER,
        REAL_REPEATED, "x" * S.RUNAWAY_TEXT_MAX_CHARS,
    ])
    def test_a_plausible_reading_is_not_a_runaway(self, text):
        assert S.is_runaway_read(text) is False

    @pytest.mark.parametrize("text", [
        RUNAWAY_ESSAY, RUNAWAY_NUMBERS,
        "x" * (S.RUNAWAY_TEXT_MAX_CHARS + 1),
    ])
    def test_a_runaway_is_one(self, text):
        assert S.is_runaway_read(text) is True

    def test_it_measures_characters_and_not_words(self):
        """One 200-character 'word' is as impossible as forty short ones —
        the guard is about how much text a crop can hold, not about spaces."""
        assert S.is_runaway_read("x" * 200) is True
        assert S.is_runaway_read("x " * 100) is True


class TestTheCapSitsOnTheMeasuredGap:
    """Measured over all 113 committed transcriptions carrying a
    `direction_text` block (45 have one): 438 strings reached the lexicon, and
    the distinct lengths at 30 and above are

        34, 41, 47, 48, 55, 144, 854

    — everything at or below 55 is a plausible reading of ink really on the
    page (the 47/48s are a LilyPond fixture's CC0 footer), and 144 and 854 are
    the two runaways. The widest empty interval is (55, 144), 89 wide, and the
    cap has to sit inside it. On the Surya-ONLY pages, where attribution is
    unambiguous, the interval is wider still: 47 then 854.

    A character count needs no scale term, unlike `_assign`'s pixel height: a
    printed direction is a short phrase whatever the DPI or the staff space.
    """

    def test_the_cap_is_inside_the_empty_interval(self):
        assert 55 < S.RUNAWAY_TEXT_MAX_CHARS < 144

    def test_the_longest_real_reading_is_kept(self, stub_worker):
        text = "x" * 55
        stub_worker([text])
        assert S.read_crops_text([_crop()]) == [text]

    def test_the_shortest_measured_runaway_is_refused(self, stub_worker):
        stub_worker(["x" * 144])
        assert S.read_crops_text([_crop()]) == [""]

    def test_the_boundary_is_where_it_says_it_is(self, stub_worker):
        cap = S.RUNAWAY_TEXT_MAX_CHARS
        stub_worker(["x" * cap, "x" * (cap + 1)])
        assert S.read_crops_text([_crop()] * 2) == ["x" * cap, ""]
