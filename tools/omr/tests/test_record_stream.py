"""ROADMAP 2.249: the streamed record file is BYTE-IDENTICAL to the one-string file, and pages are prepared one at a time."""
import json
import math
from pathlib import Path

import pytest

from tools.omr.staged import pipeline, record_io, run_meter
from tools.omr.staged.record_io import dump_to_file, dumps_for_file, load_record


class _Odd:
    def __str__(self):
        return "odd-object"


def _result():
    ids = [f"obs:{i:06d}" for i in range(200)]
    verdicts = []
    for n in range(4):   # a pooled group: one quantity, one decider, one system, >= MIN_POOL_IDS shared ids
        verdicts.append({"id": f"vrd:{n:06d}", "subject": "glyph/0/1/0/2/%d" % n,
                         "quantity": "arc_owner", "decider": "d", "considered": ids + [f"obs:9{n:05d}"],
                         "basis": sorted(ids), "correlated": [ids, ["obs:1"]], "detail": {"x": 1.5, 3: "int key"}})
    return {"record": {"observations": [{"id": "obs:000001", "value": float("nan"), "t": (1, 2), "u": "é ☃",
                                         "o": _Odd(), "big": 1e300, "neg": -0.0}],
                       "abstentions": [], "verdicts": verdicts, "counts": {"observations": 1}},
            "summary": {"a": {"read": 1}}, "provenance": {"code": {"commit": None}, 7: "seven"},
            "weight_routing": None, "stubs": {"decisions": [], "consequences": []}}


def test_stream_is_byte_identical(tmp_path: Path):
    res = _result()
    want = dumps_for_file(res, separators=(",", ":"), default=str)
    assert "pools" in want            # the fixture really is pooled
    p = tmp_path / "r.json"
    n = dump_to_file(res, p)
    got = p.read_text(encoding="utf-8")
    assert got == want
    assert n == len(want)


def test_stream_reads_back(tmp_path: Path):
    res = _result()
    p = tmp_path / "r.json"
    dump_to_file(res, p)
    back = load_record(p)
    assert back["record"]["verdicts"][2]["considered"] == res["record"]["verdicts"][2]["considered"]
    assert math.isnan(back["record"]["observations"][0]["value"])


def test_unpooled_small_record_identical(tmp_path: Path):
    res = {"record": {"observations": [], "abstentions": [], "verdicts": []}, "summary": {}}
    p = tmp_path / "r.json"
    dump_to_file(res, p)
    assert p.read_text() == json.dumps(res, separators=(",", ":"), default=str)


def test_prepared_pages_one_at_a_time():
    made = []

    def make(p):
        made.append(p)
        return [(f"pws{p}", [f"cell{p}"])]
    pp = pipeline.PreparedPages([3, 1, 2], make)
    assert pp.page_indices() == [1, 2, 3] and made == []      # naming the pages prepares nothing
    run_meter.start()
    seen = []
    for pws, cells in pp:
        seen.append(pws)
        assert made == [int(pws[3:]) for pws in seen]          # the next page is not prepared before this one is gathered
    m = run_meter.finish()
    assert seen == ["pws3", "pws1", "pws2"]
    assert [p["page"] for p in m["pages"]] == [3, 1, 2]


def test_gather_page_indices_uses_prepared_pages():
    from tools.omr.staged import gather as G
    pp = pipeline.PreparedPages([5, 4], lambda p: pytest.fail("prepared a page to name it"))
    assert G._run_page_indices(pp) == [4, 5]


def test_stage_without_a_run_is_a_no_op():
    assert run_meter.current() is None
    with run_meter.stage("x"):
        pass


def test_closed_basis_closure_and_memo_release():
    """ROADMAP 2.249: a harness verdict's closure is `{id} | basis` without a walk, and dropping the memo changes no answer."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Log, Outcome, Q, Verdict

    log = Log()
    s = R.page(0)
    o1 = log.observe(s, Q.GLYPH_BOX, 1, reader=R.READERS.GEOMETRY, frame="page")
    o2 = log.observe(s, Q.GLYPH_CONF, 2, reader=R.READERS.GEOMETRY, frame="page", derived_from=[o1.id])
    log.freeze()

    def verdict(q, considered, closed):
        basis = set(considered)
        for rid in considered:
            basis |= log.closure(rid)
        v = log.record(Verdict(id=log._next_id("vrd"), subject=s, quantity=q, outcome=Outcome.DECIDED, value=1,
                               decider="d", reason="r", considered=tuple(considered), basis=tuple(sorted(basis))))
        if closed:
            log.note_closed_basis(v.id)
        return v

    v1 = verdict(Q.DURATION, [o2.id], True)
    v2 = verdict(Q.VOICES, [v1.id], True)
    v3 = verdict(Q.METER, [v2.id, o1.id], False)
    want = {v1.id: {v1.id, o2.id, o1.id}, v2.id: {v2.id, v1.id, o2.id, o1.id},
            v3.id: {v3.id, v2.id, v1.id, o2.id, o1.id}}
    for vid, ids in want.items():
        assert log.closure(vid) == frozenset(ids)
    qic = log.quantities_in_closure(v3.id)
    assert log.release_closure_memo() >= 3
    for vid, ids in want.items():
        assert log.closure(vid) == frozenset(ids)
    log.release_closure_memo(quantities=True)
    assert log.quantities_in_closure(v3.id) == qic == frozenset({Q.GLYPH_BOX, Q.GLYPH_CONF, Q.DURATION, Q.VOICES, Q.METER})
