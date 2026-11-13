"""ROADMAP 2.307 T1d: `OMR_PAGE_OWNED_VIEW` hides copies of another staff's mark from LISTING readers; asked by name they still answer."""
from tools.omr.staged import owned_view as OV
from tools.omr.staged.record import Kind, Log, Outcome, Q, Scope, Subject, Verdict


def _log():
    log = Log()
    own = Subject(Kind.GLYPH, 0, 0, 1, 3, 0)       # staff 1's own head
    copy = Subject(Kind.GLYPH, 0, 0, 0, 3, 7)      # the same ink seen in staff 0's padded cell
    for g in (own, copy):
        log.observe(g, Q.GLYPH_BOX, ["noteheadBlack", 0, 0, 10, 10], reader="detector", frame="cell:3")
    log.freeze()
    log.record(Verdict(id="vrd:900001", subject=copy, quantity=Q.GLYPH_OWNER, outcome=Outcome.DECIDED,
                       value="staff/0/0/1", decider="t", reason="t"))
    return log, own, copy


def test_off_is_a_noop(monkeypatch):
    monkeypatch.delenv(OV.ENV, raising=False)
    log, own, copy = _log()
    assert OV.apply_to_log(log) == 0
    assert len(log.rows(Q.GLYPH_BOX, Subject(Kind.PAGE, 0), scope=Scope.SELF_AND_DESCENDANTS)) == 2


def test_on_hides_the_copy_from_listings_only(monkeypatch):
    monkeypatch.setenv(OV.ENV, "1")
    log, own, copy = _log()
    page = Subject(Kind.PAGE, 0)
    assert len(log.rows(Q.GLYPH_BOX, page, scope=Scope.SELF_AND_DESCENDANTS)) == 2   # before ownership: both
    assert OV.apply_to_log(log) == 1
    listed = log.rows(Q.GLYPH_BOX, page, scope=Scope.SELF_AND_DESCENDANTS)
    assert [r.subject for r in listed] == [own]
    assert copy not in log.subjects(Kind.GLYPH)
    assert all(r.subject != copy for r in log.all_rows())
    assert log.rows(Q.GLYPH_BOX, copy)                          # by name it still answers
    assert log.verdict(Q.GLYPH_OWNER, copy) is not None


def test_export_record_uses_the_same_rule(monkeypatch):
    from tools.omr.staged import export as E
    monkeypatch.setenv(OV.ENV, "1")
    rec = {"observations": [{"id": "obs:1", "subject": "glyph/0/0/0/3/7", "quantity": Q.GLYPH_BOX, "value": ["noteheadBlack"]},
                            {"id": "obs:2", "subject": "glyph/0/0/1/3/0", "quantity": Q.GLYPH_BOX, "value": ["noteheadBlack"]}],
           "verdicts": [{"id": "vrd:1", "subject": "glyph/0/0/0/3/7", "quantity": Q.GLYPH_OWNER, "outcome": "decided",
                         "value": "staff/0/0/1"}],
           "abstentions": []}
    r = E.Record({"record": rec})
    assert [o["subject"] for o in r.obs_of(Q.GLYPH_BOX)] == ["glyph/0/0/1/3/0"]
    assert r.verdicts_of(Q.GLYPH_OWNER) == []
    assert r.value(Q.GLYPH_OWNER, "glyph/0/0/0/3/7") == "staff/0/0/1"
    monkeypatch.delenv(OV.ENV)
    assert len(E.Record({"record": rec}).obs_of(Q.GLYPH_BOX)) == 2
