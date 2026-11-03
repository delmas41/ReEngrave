"""ROADMAP 2.256: OMR_KEY_HEADER_INK raises an under-counted marker run from the key object's own slots; nothing else."""
from types import SimpleNamespace

from tools.omr.staged import key_header_ink as K


def _row(own, system=3, more=False, pieces=None, reader="cv_key_object", source="system_key_object"):
    ko = {"own_slots": own, "system_count": system, "more_than_system": more,
          "read_pieces": pieces if pieces is not None else [{"cx": 10.0 + 18 * i} for i in range(own)]}
    return SimpleNamespace(reader=reader, detail={"source": source, "key_object": ko})


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(K.ENV, raising=False)
    assert not K.enabled()
    for v in ("1", "true", "YES", "on"):
        monkeypatch.setenv(K.ENV, v)
        assert K.enabled()
    for v in ("", "0", "off", "no"):
        monkeypatch.setenv(K.ENV, v)
        assert not K.enabled()


def test_raises_when_key_object_reads_more_slots():
    ko = K.key_object_of([_row(3)])
    assert K.raise_count(ko, 2)["slots"] == 3
    assert K.raise_count(ko, 1)["slots"] == 3


def test_never_lowers_or_equal():
    ko = K.key_object_of([_row(2)])
    assert K.raise_count(ko, 2)["slots"] is None
    assert K.raise_count(ko, 3)["slots"] is None


def test_refuses_past_the_system_count_or_missing_pieces():
    assert K.raise_count(K.key_object_of([_row(4, system=3)]), 2)["why"] == "more_than_system"
    assert K.raise_count(K.key_object_of([_row(3, more=True)]), 2)["why"] == "more_than_system"
    assert K.raise_count(K.key_object_of([_row(3, pieces=[])]), 2)["why"] == "no_key_object"
    assert K.raise_count(None, 2)["why"] == "no_key_object"
    assert K.raise_count(K.key_object_of([_row(3)]), 0)["slots"] is None     # no marker run = no kind to raise


def test_only_the_key_object_reader_counts():
    assert K.key_object_of([_row(3, reader="cv_key_signature_claim")]) is None
    assert K.key_object_of([_row(3, source="detector_key_run")]) is None
