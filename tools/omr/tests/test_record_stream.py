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


def test_lazy_basis_is_the_spelled_out_basis():
    """ROADMAP 2.249: an ADJUDICATE verdict's `LazyBasis` reads exactly as the sorted tuple it replaced, `closure` walks
    the `considered` graph to the same set, and dropping the memo changes no answer."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import LazyBasis, Log, Outcome, Q, Verdict

    log = Log()
    s = R.page(0)
    o1 = log.observe(s, Q.GLYPH_BOX, 1, reader=R.READERS.GEOMETRY, frame="page")
    o2 = log.observe(s, Q.GLYPH_CONF, 2, reader=R.READERS.GEOMETRY, frame="page", derived_from=[o1.id])
    log.freeze()

    def verdict(q, considered, lazy):
        spelled = set(considered)
        for rid in considered:
            spelled |= log.closure(rid)
        basis = LazyBasis(log, considered) if lazy else tuple(sorted(spelled))
        v = log.record(Verdict(id=log._next_id("vrd"), subject=s, quantity=q, outcome=Outcome.DECIDED, value=1,
                               decider="d", reason="r", considered=tuple(considered), basis=basis))
        assert tuple(v.basis) == tuple(sorted(spelled)) and v.basis == tuple(sorted(spelled))
        assert len(v.basis) == len(spelled) and list(v.basis) == v.to_json()["basis"]
        return v

    v1 = verdict(Q.DURATION, [o2.id], True)
    v2 = verdict(Q.VOICES, [v1.id], True)
    v3 = verdict(Q.METER, [v2.id, o1.id], False)
    v4 = verdict(Q.CLEF, [v3.id, v1.id], True)
    want = {v1.id: {v1.id, o2.id, o1.id}, v2.id: {v2.id, v1.id, o2.id, o1.id},
            v3.id: {v3.id, v2.id, v1.id, o2.id, o1.id}, v4.id: {v4.id, v3.id, v2.id, v1.id, o2.id, o1.id}}
    for vid, ids in want.items():
        assert log.closure(vid) == frozenset(ids)
    assert o1.id in v4.basis and v4.basis[0] == sorted(want[v4.id] - {v4.id})[0]
    qic = log.quantities_in_closure(v4.id)
    assert log.release_closure_memo() >= 4
    for vid, ids in want.items():
        assert log.closure(vid) == frozenset(ids)
    log.release_closure_memo(quantities=True)
    assert log.quantities_in_closure(v4.id) == qic == frozenset(
        {Q.GLYPH_BOX, Q.GLYPH_CONF, Q.DURATION, Q.VOICES, Q.METER, Q.CLEF})


def test_lazy_record_writes_the_same_file(tmp_path: Path):
    """ROADMAP 2.249 m5: the CLI's record (ADJUDICATE bases as `LazyBasis`, pooled while written) is byte-identical
    to the spelled-out record pooled whole -- pooled and inline bases, both."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import LazyBasis, Log, Outcome, Q, Verdict

    log = Log()
    obs = [log.observe(R.glyph(0, 0, 0, 0, i), Q.GLYPH_BOX, i, reader=R.READERS.GEOMETRY, frame="page")
           for i in range(90)]
    log.freeze()
    for n in range(6):   # one group (quantity, decider, system): a shared core of 80 ids, one private each
        considered = [o.id for o in obs[:80]] + [obs[80 + n].id]
        log.record(Verdict(id=log._next_id("vrd"), subject=R.glyph(0, 0, 0, 1, n), quantity=Q.DURATION,
                           outcome=Outcome.DECIDED, value=n, decider="d", reason="r",
                           considered=tuple(considered), basis=LazyBasis(log, considered)))
    log.record(Verdict(id=log._next_id("vrd"), subject=R.glyph(0, 1, 0, 1, 0), quantity=Q.VOICES,
                       outcome=Outcome.DECIDED, value=1, decider="e", reason="r", considered=(obs[0].id,),
                       basis=LazyBasis(log, (obs[0].id,))))
    eager = {"record": log.to_json(), "summary": {}}
    lazy = {"record": log.to_json(lazy_basis=True), "summary": {}}
    assert isinstance(lazy["record"]["verdicts"][0]["basis"], LazyBasis)
    want = dumps_for_file(eager, separators=(",", ":"), default=str)
    assert '"$pool"' in want                      # the fixture really pools (`considered`)
    p = tmp_path / "lazy.json"
    n = dump_to_file(lazy, p)
    assert p.read_text(encoding="utf-8") == want and n == len(want)
    assert load_record(p)["record"]["verdicts"][0]["basis"] == eager["record"]["verdicts"][0]["basis"]


def _format2_log():
    """Readings, a derived verdict on a derived verdict, and a verdict with a STORED basis (INFER's kind) between."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import LazyBasis, Log, Outcome, Q, Verdict

    log = Log()
    o = [log.observe(R.glyph(0, 0, 0, 0, i), Q.GLYPH_BOX, i, reader=R.READERS.GEOMETRY, frame="page")
         for i in range(5)]
    o5 = log.observe(R.glyph(0, 0, 0, 0, 5), Q.GLYPH_CONF, 5, reader=R.READERS.GEOMETRY, frame="page",
                     derived_from=[o[0].id, o[1].id])
    log.freeze()

    def derived(q, considered, n):
        return log.record(Verdict(id=log._next_id("vrd"), subject=R.glyph(0, 0, 0, 1, n), quantity=q,
                                  outcome=Outcome.DECIDED, value=n, decider="d", reason="r",
                                  considered=tuple(considered), basis=LazyBasis(log, considered)))

    v1 = derived(Q.DURATION, [o5.id, o[2].id], 1)
    stored = log.record(Verdict(id=log._next_id("vrd"), subject=R.glyph(0, 0, 0, 1, 2), quantity=Q.VOICES,
                                outcome=Outcome.DECIDED, value=2, decider="infer:x", reason="r",
                                considered=(v1.id,), basis=tuple(sorted(log.closure(v1.id)))))
    v3 = derived(Q.METER, [stored.id, o[3].id], 3)
    return log, (v1, stored, v3)


def test_format2_file_stores_considered_not_basis(tmp_path: Path):
    """ROADMAP 2.249 m8 (Sean 2026-11-02): an ADJUDICATE verdict's basis is not in the file -- `basis_from` says it
    is derived from `considered`; a stored basis (any other verdict) and the readings' `basis` are kept."""
    log, (v1, stored, v3) = _format2_log()
    p = tmp_path / "r.json"
    dump_to_file({"record": log.to_json(lazy_basis=True), "summary": {}}, p)
    raw = json.loads(p.read_text())["record"]
    assert raw["format"] == 2
    by_id = {v["id"]: v for v in raw["verdicts"]}
    for v in (v1, v3):
        assert "basis" not in by_id[v.id] and by_id[v.id]["basis_from"] == "considered"
        assert by_id[v.id]["considered"] == list(v.considered)
    assert by_id[stored.id]["basis"] == list(stored.basis) and "basis_from" not in by_id[stored.id]
    obs5 = [o for o in raw["observations"] if o["basis"]]
    assert len(obs5) == 1 and len(obs5[0]["basis"]) == 2


def test_format2_loads_the_same_basis_and_writes_the_same_file(tmp_path: Path):
    """Loading gives every derived verdict the basis the log spells (`RecordBasis`); a loaded record written again is
    the same file."""
    log, rows = _format2_log()
    p = tmp_path / "r.json"
    dump_to_file({"record": log.to_json(lazy_basis=True), "summary": {}}, p)
    rec = load_record(p)["record"]
    by_id = {v["id"]: v for v in rec["verdicts"]}
    for v in rows:
        got = by_id[v.id]["basis"]
        assert list(got) == list(v.basis) and got == list(v.basis) and len(got) == len(v.basis)
        assert all(x in got for x in v.basis)
    q = tmp_path / "again.json"
    dump_to_file(load_record(p), q)
    assert q.read_text() == p.read_text()


def test_format1_record_loads_as_stored(tmp_path: Path):
    """An old record (no `format`, every basis spelled) is read exactly as stored."""
    old = {"record": {"observations": [{"id": "obs:000001", "basis": []}],
                      "abstentions": [],
                      "verdicts": [{"id": "vrd:000002", "subject": "glyph/0/0/0/1/0", "quantity": "duration",
                                    "decider": "d", "considered": ["obs:000001"], "basis": ["obs:000001", "obs:zz"]}],
                      "counts": {}}}
    p = tmp_path / "old.json"
    p.write_text(json.dumps(old))
    v = load_record(p)["record"]["verdicts"][0]
    assert v["basis"] == ["obs:000001", "obs:zz"] and isinstance(v["basis"], list)
