"""ROADMAP 2.67: the copy of the Gradus terms library and its exact lookup."""
from tools.omr import musical_terms as mt


def _ids(text):
    return {m.term.id for m in mt.lookup(text)}


def test_copy_is_a_clean_export_and_its_counts_hold():
    lib = mt.library()
    assert len(lib["generated_from"]) == 40          # a Gradus commit sha
    assert lib["data_dirty"] is False                # a dirty export is not a copy to keep
    assert lib["counts"]["terms"] == len(mt.terms())
    assert len({t.id for t in mt.terms()}) == len(mt.terms())


def test_term_abbreviation_and_variant_each_match():
    assert _ids("legato") == {"legato"}
    assert [m.via for m in mt.lookup("G.P.")] == ["abbreviation"]
    assert "erstes-tempo" in _ids("Tempo I")         # a variant


def test_folding_is_the_documented_one():
    assert _ids("piu mosso") == _ids("PIÙ MOSSO") == _ids("più  mosso.")
    assert _ids("m. g.") == _ids("m.g.") != set()
    assert _ids("Ritard.") == _ids("ritard")


def test_ambiguous_strings_keep_every_candidate():
    assert {"ritardando", "ritenuto"} <= _ids("rit.")
    assert {"trill", "trumpet"} <= _ids("tr")


def test_noise_and_unknowns_are_not_terms():
    # the control: OCR noise the direction reader sees must find nothing
    for noise in ("", "~", "IIII", "#", "e e e", "legatto", "Cor. II"):
        assert mt.lookup(noise) == (), noise
