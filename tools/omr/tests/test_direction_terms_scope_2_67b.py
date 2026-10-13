"""ROADMAP 2.67b: the terms library wired into the direction lexicon, with
Sean's limits (2026-10-12): the work's languages, no short forms alone, no
instrument or theory words, and -- in ADJUDICATE -- technique words only on
their own family's staff and heading words only where headings are printed.
"""
from types import SimpleNamespace

from tools.omr import musical_terms as MT
from tools.omr.direction_lexicon import lookup, scope_for
from tools.omr.staged.adjudicators import text as T
from tools.omr.staged.record import Kind, Q, Subject

MAHLER = scope_for("mahler--symphony-5")
TCHAIK = scope_for("tchaikovsky--symphony-6")
UNKNOWN = scope_for(None)


def _accepts(text, scope):
    return lookup(text, scope=scope) is not None


# ── the reader: what the library adds, and under which scope ───────────────

def test_unscoped_lookup_is_the_curated_lexicon_unchanged():
    # LEGACY never passes a scope: a library-only word stays refused there.
    assert lookup("Sehr langsam") is None
    assert lookup("legato") is not None


def test_the_composers_language_is_read():
    for text in ("Sehr langsam", "Etwas bewegter", "Mit Dämpfer",
                 "nicht eilen", "Tempo I"):
        hit = lookup(text, scope=MAHLER)
        assert hit is not None and not hit.other_language, text


def test_another_language_only_as_a_whole_word_of_five_letters():
    hit = lookup("Sehr langsam", scope=TCHAIK)
    assert hit is not None and hit.other_language
    # ... and never inside a phrase: `langsamer` is German, `poco` Italian
    assert _accepts("poco langsamer", MAHLER)
    assert not _accepts("poco langsamer", TCHAIK)


def test_the_editions_labels_widen_the_languages():
    edition = scope_for("tchaikovsky--symphony-6",
                        ["Flöte", "Hoboe", "Fagott", "Violine"])
    assert "German" in edition.languages
    assert _accepts("poco langsamer", edition)
    # one German label is a stray, not an edition
    assert "German" not in scope_for("tchaikovsky--symphony-6",
                                     ["Flöte", "Oboe"]).languages


def test_an_unknown_work_admits_every_language_and_says_so():
    assert UNKNOWN.languages is None and UNKNOWN.to_json()["unknown_work"]
    assert _accepts("poco langsamer", UNKNOWN)


def test_noise_short_forms_instruments_and_theory_are_never_directions():
    # the control: each of these is IN the library and must still be refused
    for text in ("et", "en", "e", "Fl.", "Vl.", "Ob.", "Flöte", "Horn",
                 "Sonata form", "Cadence", "und mit sehr", "IIII", "e e e"):
        for scope in (MAHLER, TCHAIK, UNKNOWN):
            assert not _accepts(text, scope), (text, scope.work_id)


def test_the_hand_marks_and_GP_stand_alone():
    assert _accepts("l.H.", MAHLER)
    assert _accepts("G.P.", TCHAIK)          # German, printed everywhere
    assert not _accepts("m.g.", MAHLER)      # French, two letters, not Mahler's


def test_every_listed_id_is_in_the_library():
    assert all(MT.by_id(i) for i in MT.FAMILY_OF)
    assert all(MT.by_id(i) for i in MT.NAVIGATION)


# ── ADJUDICATE: where a word is printed ──────────────────────────────────────

class _Ev:
    """The two questions `_held_back` asks: a staff's instrument, a
    system's staff count."""

    def __init__(self, families, n_staves, staff=0):
        self.subject = Subject(Kind.CELL, page=0, system=0, staff=staff, cell=0)
        self._fam = families
        self._n = n_staves

    def verdict(self, quantity, subject=None):
        if quantity == Q.SYSTEM_STAFF_COUNT:
            return SimpleNamespace(value=self._n)
        fam = self._fam.get(subject.staff)
        return None if fam is None else SimpleNamespace(
            value={"name": fam, "family": fam})


# staves: 0 oboe, 1 horn, 2 violin I, 3 violin II
ORCH = {0: "woodwind", 1: "brass", 2: "string", 3: "string"}


def _why(text, staff, placement="below", families=ORCH, n=4):
    out = T._held_back(_Ev(families, n, staff),
                       {"text": text, "placement": placement})
    return out and out["held_reason"]


def test_a_technique_word_on_another_family_is_held_back():
    assert _why("pizz.", 1) == "wrong_family"            # pizz. under a horn
    assert _why("pizz.", 3) is None                      # under violin II
    assert _why("gestopft", 2) == "wrong_family"
    assert _why("gestopft", 1) is None
    assert _why("a 2", 0) is None and _why("a 2", 3) == "wrong_family"
    assert _why("con sord.", 1) is None and _why("con sord.", 0) == "wrong_family"
    assert _why("dolce", 1) is None                      # any family


def test_an_undecided_staff_holds_nothing_back():
    assert _why("pizz.", 1, families={}) is None
    assert _why("Allegro", 0, families={}) is None


def test_a_heading_is_kept_above_the_system_the_first_strings_and_the_bottom():
    assert _why("Allegro con brio", 0, placement="above") is None
    assert _why("Allegro con brio", 1) is None           # horn band, violins below
    assert _why("Allegro con brio", 0) == "heading_out_of_place"
    assert _why("Allegro con brio", 2) == "heading_out_of_place"   # between violins
    # under the last staff: Breitkopf prints it there (Brahms 1 p3, bar 38)
    assert _why("Allegro", 3) is None
    assert _why("Trio", 0) == "heading_out_of_place"


def test_tempo_changes_and_navigation_go_under_any_staff():
    for text in ("rit.", "a tempo", "accel.", "D.C.", "Fine"):
        assert _why(text, 0) is None, text
