"""ROADMAP 2.61b -- each flag has ONE reader; the second module calls it.

`OMR_OWNER_FROM_STAVES` was read in `gather.py` and again in
`adjudicators/ownership.py`; `OMR_DIRECTION_TEXT` in `gather.py` and again in
`pipeline.py`. Two readers of one flag drift: a change to one default or one
off-word list silently leaves the other behind. Both are now ONE predicate in
`gather.py` that the other module imports or calls. These tests are
behavioural (CLAUDE.md section 6c: no source-text assertions): flipping the
environment moves BOTH consumers together, and a typo leaves both on.
"""

from __future__ import annotations

from tools.omr.staged import gather as G
from tools.omr.staged import pipeline as P
from tools.omr.staged.adjudicators import ownership as O

OFF_WORDS = ("0", "", "false", "no", "off", "OFF", " 0 ")


def test_owner_from_staves_has_one_predicate(monkeypatch):
    assert O.owner_from_staves_enabled is G.owner_from_staves_enabled
    monkeypatch.delenv("OMR_OWNER_FROM_STAVES", raising=False)
    assert G.owner_from_staves_enabled() and O.owner_from_staves_enabled()
    for word in OFF_WORDS:
        monkeypatch.setenv("OMR_OWNER_FROM_STAVES", word)
        assert not G.owner_from_staves_enabled(), word
        assert not O.owner_from_staves_enabled(), word
    # a typo leaves the default (ON) in force
    monkeypatch.setenv("OMR_OWNER_FROM_STAVES", "flase")
    assert G.owner_from_staves_enabled() and O.owner_from_staves_enabled()


def test_direction_text_one_predicate_drives_pipeline_header(monkeypatch):
    monkeypatch.delenv("OMR_DIRECTION_TEXT", raising=False)
    assert G.direction_text_enabled()
    assert "OMR_DIRECTION_TEXT=1" in P._rung_header(False, False)
    for word in OFF_WORDS:
        monkeypatch.setenv("OMR_DIRECTION_TEXT", word)
        assert not G.direction_text_enabled(), word
        assert "OMR_DIRECTION_TEXT=0" in P._rung_header(False, False), word
    # a typo leaves the default (ON) in force, for both
    monkeypatch.setenv("OMR_DIRECTION_TEXT", "flase")
    assert G.direction_text_enabled()
    assert "OMR_DIRECTION_TEXT=1" in P._rung_header(False, False)
