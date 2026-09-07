"""The work's catalog roster read as a constraint on margin labels.

The measured claims are in
`benchmarks/omr-roster-constrained-labels-2026-09/FINDINGS.md`. What is pinned
here is everything a score cannot see: the tier discipline, the abstentions, the
ORDER of the three actions, and the flag being genuinely inert when off.

⚠️ Several of these are written against the COMMITTED catalog
(`data/score-library/catalog.json`) rather than a fixture, deliberately: the
faults they guard are properties of that file's parse — Tchaikovsky 6's dropped
`strings` segment above all — and a hand-built roster would test the test.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from tools.omr import contextual, work_roster as W
from tools.omr.instruments import lookup
from tools.omr.staff_labels import StaffLabel


@pytest.fixture(scope="module")
def tch6():
    r = W.work_roster("tchaikovsky--symphony-6")
    assert r is not None, "the committed catalog must hold this work"
    return r


@pytest.fixture(scope="module")
def beet5():
    r = W.work_roster("beethoven--symphony-5")
    assert r is not None
    return r


@pytest.fixture(scope="module")
def brahms1():
    r = W.work_roster("brahms--symphony-1")
    assert r is not None
    return r


@pytest.fixture(scope="module")
def keyboard_only():
    """A work whose roster admits the KEYBOARD family and nothing else.

    The false-positive stress scored every string against every roster, and
    this is the shape that produced the worst claim it found.
    """
    for wid in ("chopin--nocturnes", "beethoven--piano-sonata-14"):
        r = W.work_roster(wid)
        if r is not None and r.families == frozenset({"keyboard"}):
            return r
    return W.WorkRoster(work_id="synthetic--keyboard",
                        instruments=frozenset({"Piano"}),
                        families=frozenset({"keyboard"}), complete=True)


# ── the tier discipline ──────────────────────────────────────────────────────

def test_only_the_catalog_tier_is_read(tmp_path):
    """A `page`-sourced roster is an OMR OUTPUT and may not be evidence here."""
    import json
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"works": {"x--y": {"instrumentation": {
        "source_kind": "page", "parse_rate": 1.0,
        "roster": [{"kind": "instrument", "instrument": "Horn",
                    "family": "brass"}]}}}}))
    W._catalog.cache_clear()
    try:
        assert W.work_roster("x--y", catalog_path=str(cat)) is None
    finally:
        W._catalog.cache_clear()


def test_the_roster_declares_its_own_provenance(tch6):
    assert tch6.source_kind == "catalog"


# ── what the roster ADMITS ───────────────────────────────────────────────────

def test_a_section_word_the_parser_dropped_still_admits_its_family(tch6):
    """⚠️ The live case this whole design turns on.

    Tchaikovsky 6's InstrDetail ends `..., tam-tam ''(ad lib.)'', strings` and
    the parser filed `strings` under `segments_ignored`, so the parsed roster
    names NO string instrument at `parse_rate 1.0`. Reading absence as denial
    would veto every violin on the page.
    """
    assert not any(n in tch6.instruments
                   for n in ("Violin", "Viola", "Cello", "Contrabass"))
    assert tch6.admits_family("string")


def test_a_work_with_no_singers_does_not_admit_the_voice_family(tch6):
    assert not tch6.admits_family("voice")


@pytest.mark.parametrize("work_id", [
    "beethoven--egmont",            # `narrator (optional), soprano, orchestra`
    "mahler--symphony-4",           # `soprano, orchestra ...`
    "faure--pelleas-et-melisande",  # `voice, orchestra (incidental music)`
    "mahler--lieder-eines-fahrenden-gesellen-gmw-10",   # `low voice, orchestra`
])
def test_a_work_whose_SINGERS_only_the_other_field_names_still_admits_them(work_id):
    """⚠️ The parse reads ONE field, and a detail line lists the ORCHESTRA.

    These four works have real singers and their parsed rosters name none:
    `roster_field` is `InstrDetail` and the voices are in `Instrumentation`.
    A family veto reading the parse alone would strip the name off every vocal
    staff in them, which is the worst thing this layer could do.
    """
    r = W.work_roster(work_id)
    assert r is not None and r.admits_family("voice"), work_id


def test_an_instrument_named_for_a_register_is_not_a_singer():
    """`bass clarinet` must not admit voices — the lexicon settles it.

    The families are read off the raw fields through `instruments.lookup`
    rather than by word search precisely for this: longest-alias-first already
    knows `bass clarinet` is a woodwind.
    """
    r = W.work_roster("brahms--symphony-1")
    assert r is not None and not r.admits_family("voice")


# ── recovery ─────────────────────────────────────────────────────────────────

def test_a_truncated_name_recovers_against_the_roster(tch6):
    assert lookup("orni in F I II") is None            # the lexicon abstains
    d = W.decide("orni in F I II", tch6)
    assert (d.kind, d.match.instrument.name) == ("recovered", "Horn")
    assert d.names_a_staff


def test_recovery_reads_the_printed_key(tch6):
    """`in F` is read exactly as `instruments.lookup` reads it."""
    d = W.decide("orni in F I II", tch6)
    assert d.match.fifths_offset == 1


def test_without_a_roster_a_truncated_name_stays_dropped(tch6):
    assert W.decide("orni in F I II", None).kind == "unchanged"
    assert W.decide("orni in F I II", None).match is None


def test_ambiguity_within_the_roster_abstains(brahms1):
    """A truncated `Fagotti` is a bassoon OR a contrabassoon, and Brahms 1 has
    both. Naming one would be a coin flip dressed as evidence.

    ⚠️ This test used to be written on `ni in F III IV`, which abstains for a
    DIFFERENT reason — `ni` is two letters and never reaches the ambiguity rule
    at all — so breaking the ambiguity rule left it green. Ambiguity is not
    rare: 91 distinct tails are owned by more than one instrument of the
    Brahms 1 roster alone.
    """
    assert lookup("agotti") is None
    d = W.decide("agotti", brahms1)
    assert (d.kind, d.match) == ("unchanged", None)


def test_a_token_under_the_letter_floor_abstains_before_that(tch6):
    """`ni in F III IV` — the real Tchaikovsky label — abstains on LENGTH."""
    d = W.decide("ni in F III IV", tch6)
    assert (d.kind, d.match) == ("unchanged", None)


def test_a_tail_too_short_a_share_of_its_alias_abstains(tch6):
    """`ani` keeps 0.43 of `timpani`, under `MIN_KEPT_FRACTION`."""
    d = W.decide("ani in A.D.E.", tch6)
    assert (d.kind, d.match) == ("unchanged", None)


def test_a_two_letter_tail_never_fires(tch6):
    assert W.decide("ni", tch6).kind == "unchanged"


def test_an_intact_name_is_never_touched(tch6):
    for text in ("Violini I", "Fagotti", "Corni in F"):
        assert W.decide(text, tch6).kind == "unchanged"


def test_words_that_are_not_names_are_left_alone(tch6):
    for text in ("Allegro con brio", "Andante", "sempre dolce", "= 60"):
        d = W.decide(text, tch6)
        assert (d.kind, d.match) == ("unchanged", None), text


def test_a_multi_word_alias_is_not_a_truncation_target(tch6):
    """`tenore` is the tail of the Trombone alias `tr tenore` — and refused.

    A truncation is the tail of a WORD. Matching across a space reaches
    cross-family (`alt` is the tail of `tr alt`, so a truncated ALTO FLUTE
    would read as a trombone), and the one real recovery it would buy here is
    luck rather than mechanism.
    """
    assert ("tr tenore", ) not in [(a, ) for a, _ in W._roster_aliases(tch6)]
    assert W.decide("Alto e Tenore", tch6).match is None


def test_a_spelled_out_count_is_not_a_name(keyboard_only):
    """⚠️ `Vier Flöten` came back as a PIANO — `vier` is a tail of `klavier`.

    Found by the cross-product stress
    (`benchmarks/omr-roster-constrained-labels-2026-09/probe_false_positives.py`),
    not by reasoning: a margin prints `Vier Hörner` and `Drei Klarinetten`
    constantly and those words are COUNTS. Under a keyboard-only roster the
    flute is (correctly) not admitted, and before this the recovery then named
    the wrong instrument instead of leaving the staff unnamed.
    """
    assert lookup("Vier Flöten").instrument.name == "Flute"
    d = W.decide("Vier Flöten", keyboard_only)
    assert (d.kind, d.match) == ("vetoed", None)


# ── veto ─────────────────────────────────────────────────────────────────────

def test_a_singer_in_a_work_with_no_singers_is_vetoed(tch6):
    """`Tromboni Alto e Tenore` cut to `Alto e Tenore` reads as a TENOR."""
    assert lookup("Alto e Tenore").instrument.name == "Tenor"
    d = W.decide("Alto e Tenore", tch6)
    assert (d.kind, d.match, d.before) == ("vetoed", None, "Tenor")
    assert not d.names_a_staff


def test_a_veto_never_installs_a_name(tch6):
    assert W.decide("Alto e Tenore", tch6).match is None


# ── disambiguation ───────────────────────────────────────────────────────────

def test_an_ambiguous_alias_resolves_to_the_reading_the_roster_has(beet5):
    """`Basso.` is the lexicon's Bass VOICE and Beethoven 5 has no singers."""
    assert lookup("Basso.").instrument.name == "Bass voice"
    d = W.decide("Basso.", beet5)
    assert (d.kind, d.match.instrument.name) == ("disambiguated", "Contrabass")


def test_disambiguation_only_uses_the_lexicons_own_candidates(beet5):
    """Not this module's guess — `instruments.AMBIGUOUS_ALIASES` says so."""
    hit = lookup("Basso.")
    assert {i.name for i in hit.alternatives} == {"Bass voice", "Contrabass"}


# ── the ORDER of the three, which was measured ───────────────────────────────

def test_recovery_outranks_disambiguation(tch6):
    """⚠️ `mbone Basso` is `Trombone Basso`, and BOTH actions can fire on it.

    `basso` is an ambiguous alias whose Contrabass reading the roster admits, so
    disambiguation-first answers Contrabass — confidently and wrongly — on a
    label whose surviving letters spell the tail of `trombone`. Run this test
    against a `decide` that tries disambiguation first and it fails.
    """
    assert lookup("mbone Basso").instrument.name == "Bass voice"
    d = W.decide("mbone Basso", tch6)
    assert (d.kind, d.match.instrument.name) == ("recovered", "Trombone")


# ── an incomplete parse acts on nothing ──────────────────────────────────────

def test_an_incomplete_roster_neither_vetoes_nor_recovers(tch6):
    partial = replace(tch6, complete=False)
    assert W.decide("Alto e Tenore", partial).kind == "unchanged"
    assert W.decide("orni in F I II", partial).kind == "unchanged"


# ── the reader boundary ──────────────────────────────────────────────────────

def _label(text: str) -> StaffLabel:
    hit = lookup(text)
    return StaffLabel(staff_index=0, text=text,
                      instrument=hit.instrument if hit else None,
                      fifths_offset=hit.fifths_offset if hit else 0,
                      y_center_px=0.0,
                      confidence=hit.confidence if hit else "none",
                      alias=hit.alias if hit else "")


def test_match_of_reproduces_the_readers_own_confidence():
    """The reconstruction exists to avoid a second 0.6 s `lookup`."""
    for text in ("Violini I", "Basso.", "Fagotti"):
        lab = _label(text)
        assert W.match_of(lab).confidence == lookup(text).confidence, text
    assert W.match_of(_label("Allegro")) is None


def test_the_wrapper_is_inert_when_the_flag_is_off(monkeypatch, tch6):
    """⚠️ The roster is FORCED PRESENT here on purpose.

    An earlier cut passed `"x.pdf"`, which is outside the store and has no
    roster — so the flag could have been defaulted ON and the test would still
    have passed. It guarded nothing. With the roster supplied, the flag is the
    only thing standing between these labels and being repaired.
    """
    given = [_label("Alto e Tenore"), _label("orni in F I II")]
    monkeypatch.setattr(contextual, "_read_labels_for_page",
                        lambda *a, **k: given)
    monkeypatch.setattr(W, "roster_for_pdf", lambda p: tch6)
    monkeypatch.delenv("OMR_ROSTER_LABELS", raising=False)
    out = contextual._labels_for_page(None, "x.pdf", 0, assist=None, budget=[0])
    assert out is given


def test_the_wrapper_repairs_labels_when_the_flag_is_on(monkeypatch, tch6):
    given = [_label("Alto e Tenore"), _label("orni in F I II")]
    monkeypatch.setattr(contextual, "_read_labels_for_page",
                        lambda *a, **k: given)
    monkeypatch.setattr(W, "roster_for_pdf", lambda p: tch6)
    monkeypatch.setenv("OMR_ROSTER_LABELS", "1")
    out = contextual._labels_for_page(None, "x.pdf", 0, assist=None, budget=[0])
    assert [lab.instrument.name if lab.instrument else None for lab in out] \
        == [None, "Horn"]
    # ⚠️ The reader's own string is never rewritten — only what it resolves to.
    assert [lab.text for lab in out] == [lab.text for lab in given]


def test_a_pdf_outside_the_store_has_no_roster():
    assert W.roster_for_pdf("/tmp/some-upload.pdf") is None


def test_a_harness_may_name_the_work_for_a_pdf_the_store_lacks(monkeypatch):
    """`OMR_WORK_ID` — without it the engraved benchmark is a no-op.

    `orchestral_eval` renders its fixtures into a gitignored build directory, so
    no catalogued edition matches them and the layer never fires there.
    """
    monkeypatch.setenv("OMR_WORK_ID", "tchaikovsky--symphony-6")
    r = W.roster_for_pdf("/tmp/fixtures/tchaikovsky-sym6-mvt2.pdf")
    assert r is not None and r.work_id == "tchaikovsky--symphony-6"


def test_an_unknown_work_id_abstains_rather_than_matching_something_near(monkeypatch):
    """The DOSSIER id is a different key space from the library's."""
    monkeypatch.setenv("OMR_WORK_ID", "tchaikovsky-sym6-mvt2")
    assert W.roster_for_pdf("/tmp/anything.pdf") is None


def test_a_token_the_lexicon_already_knows_is_not_a_fragment(tch6):
    """`soprano` is a tail of `mezzosoprano`, and `Soprano Saxophone` came back
    as an ALTO before this. A word the lexicon holds is a name, not a stump."""
    assert "soprano" in W._known_aliases()
    r = W.WorkRoster(work_id="synthetic--voices",
                     instruments=frozenset({"Alto"}),
                     families=frozenset({"voice"}), complete=True)
    assert W.decide("Soprano Saxophone", r).match is None
