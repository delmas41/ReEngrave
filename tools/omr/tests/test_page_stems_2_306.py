"""ROADMAP 2.306 -- stems read once on the page (`page_stems`, flag `OMR_PAGE_STEMS`, default OFF).

Controls are REAL judged cases (CLAUDE rule 7): Brahms 317803 p0, the page heads and the page map's vertical strokes of eight bars, cut from a gather
(`fixtures/page_stems_2_306_brahms_p0.json`), against Sean's own stem labels in those bars (data/hand-truth/pages/imslp317803/0.json) and 2.300 tile 2
(staff 6 bar 1: Sean "dotted quarter chord (a second)" -- one stem). Each control is shown failing first: the same page MIRRORED left-right (an up stem
then stands at its head's LEFT) must lose Sean's stems, so a rule that ignored the engraving side would pass where it should fail.
"""
import json
import os

from tools.omr.staged import page_stems as PS

FX = os.path.join(os.path.dirname(__file__), "fixtures", "page_stems_2_306_brahms_p0.json")


def _load():
    with open(FX) as f:
        fx = json.load(f)
    heads = [dict(h, box=tuple(h["box"])) for h in fx["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in fx["verticals"]]
    return fx, heads, verts, {int(k): v for k, v in fx["held"].items()}


def _hit(t, b):
    tx, bx = (t[0] + t[2]) / 2.0, (b[0] + b[2]) / 2.0
    ov = min(t[3], b[3]) - max(t[1], b[1])
    return abs(tx - bx) <= 8 and ov >= 0.5 * min(t[3] - t[1], b[3] - b[1])


def _found(fx, res, verts):
    vby = {v["ord"]: v["box"] for v in verts}
    mine = [vby[o] for o in res["stems"]]
    return sum(1 for t in fx["sean_stems"] if any(_hit(t, b) for b in mine)), mine


def _mirror(fx, heads, verts):
    W = 6000.0
    m = lambda b: (W - b[2], b[1], W - b[0], b[3])
    return (dict(fx, sean_stems=[list(m(t)) for t in fx["sean_stems"]]), [dict(h, box=m(h["box"])) for h in heads], [dict(v, box=m(v["box"])) for v in verts])


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(PS.ENV, raising=False)
    assert PS.enabled() is False
    monkeypatch.setenv(PS.ENV, "1")
    assert PS.enabled() is True


def test_seans_p0_stems_found_and_the_mirror_fails():
    fx, heads, verts, held = _load()
    res = PS.read(heads, verts, held)
    found, mine = _found(fx, res, verts)
    n = len(fx["sean_stems"])
    assert n >= 15
    # measured 14 of 17 (main 718c83964): the three misses abstain -- two strokes read as an up stem at one end and a down stem at the other with
    # head ink at both (`stroke_read_both_ways`), one head whose two candidate strokes both end at a neighbour (`two_voices`, gaps 0.70 / 0.74 sp)
    assert found >= 14, (found, n)
    # (precision is not asserted here: Sean's labels in these bars are not every stem -- 2.300 tile 2's three stems carry none)
    # control: mirrored, the engraving side is wrong everywhere -- the up / down rule must lose (nearly) all of them
    fxm, hm, vm = _mirror(fx, heads, verts)
    found_m, _ = _found(fxm, PS.read(hm, vm, held), vm)
    assert found_m <= n // 4, found_m


def _tile2(heads, verts, held):
    res = PS.read(heads, verts, held)
    return {o: sorted(s["heads"]) for o, s in res["stems"].items() if any(k.startswith("glyph/0/0/6/1/") for k in s["heads"])}, res


def test_2300_tile_2_three_chords_three_stems(monkeypatch):
    """Sean (2.300 tile 2): "dotted quarter chord (a second); quarter chord; eighth chord" -- three stems, two heads each; the dot boxed as a head reads
    no stroke. The second's displaced head (`/11`) stands on its partner's stem."""
    fx, heads, verts, held = _load()
    stems, res = _tile2(heads, verts, held)
    assert sorted(stems.values()) == [["glyph/0/0/6/1/11", "glyph/0/0/6/1/2"], ["glyph/0/0/6/1/17", "glyph/0/0/6/1/7"],
                                      ["glyph/0/0/6/1/4", "glyph/0/0/6/1/5"]], stems
    assert res["heads"]["glyph/0/0/6/1/18"]["state"] == "none"
    # control: without the second's rule the displaced head reads no stroke and the chord falls apart
    monkeypatch.setattr(PS, "SECOND_DY_SP", 0.0)
    stems0, res0 = _tile2(heads, verts, held)
    assert res0["heads"]["glyph/0/0/6/1/11"]["state"] == "none"
    assert ["glyph/0/0/6/1/11", "glyph/0/0/6/1/2"] not in sorted(stems0.values())


def test_held_stroke_is_never_a_stem():
    fx, heads, verts, held = _load()
    res = PS.read(heads, verts, held)
    o = next(iter(res["stems"]))
    h2 = dict(held)
    h2[o] = "accidental"
    res2 = PS.read(heads, verts, h2)
    assert o not in res2["stems"]
    marked = [r for r in res2["heads"].values() if any(c["stroke"] == o for c in r["held"])]
    assert marked and all(c["owner"] == "accidental" for r in marked for c in r["held"] if c["stroke"] == o)


def test_abstain_with_candidates_and_margin():
    # a head with an up stem at its right AND a down stem at its left, both ending at it: two voices on one head (page-facts), never a pick
    h = dict(id="h", members=["glyph/0/0/0/0/0"], box=(100.0, 100.0, 130.0, 120.0), sp=20.0, ink=True)
    up = dict(ord=1, box=(129.0, 30.0, 132.0, 110.0), sp=20.0)
    dn = dict(ord=2, box=(99.0, 110.0, 102.0, 190.0), sp=20.0)
    r = PS.read([h], [up, dn])["heads"]["h"]
    assert r["state"] == "two_voices" and r["stroke"] is None and len(r["candidates"]) == 2 and r["margin"] is not None
    r0 = PS.read([h], [])["heads"]["h"]
    assert r0["state"] == "none" and r0["how"] == "no_stroke"


class _OwnerEv:
    def __init__(self, v):
        self.v = v

    def verdict(self, q, subject=None):
        return self.v


def test_r3_a_copy_owned_by_another_staff_takes_no_part_in_this_staffs_split(monkeypatch):
    """ROADMAP 2.306 r3 (the cause of r1's new red bars: 533 Brahms / 454 Litolff padded-cell copies gained a stem direction and split this staff's chords).
    The owner test is EXPORT's own (`is_relocated_copy` on the decided `Q.GLYPH_OWNER`); with the flag off nothing changes."""
    from types import SimpleNamespace as NS
    from tools.omr.staged.adjudicators import rhythm as R
    from tools.omr.staged.record import Subject
    sub = Subject.from_key("glyph/4/0/11/1/4")                     # Brahms p4 staff 11 bar 1: a staff-12 head's copy (r2's first new red bar)
    elsewhere = NS(outcome="decided", value="staff/4/0/12")
    home = NS(outcome="decided", value="staff/4/0/11")
    monkeypatch.setenv(PS.ENV, "1")
    assert R.owned_by_another_staff(_OwnerEv(elsewhere), sub) is True
    assert R.owned_by_another_staff(_OwnerEv(home), sub) is False
    assert R.owned_by_another_staff(_OwnerEv(None), sub) is False
    assert R.owned_by_another_staff(_OwnerEv(NS(outcome="abstained", value=None)), sub) is False
    monkeypatch.setenv(PS.ENV, "0")
    assert R.owned_by_another_staff(_OwnerEv(elsewhere), sub) is False


class _Ev:
    """The two calls `page_own_stems` makes, on a hand-built reading (no record)."""

    def __init__(self, rows=(), refusals=()):
        self._rows, self._ref = tuple(rows), tuple(refusals)

    def rows(self, q, **kw):
        return self._rows

    def refusals(self, q, **kw):
        return self._ref


def test_retire_page_abstention_is_no_stem_and_flag_off_keeps_the_cell_join(monkeypatch):
    from types import SimpleNamespace as NS
    from tools.omr.staged.adjudicators import rhythm as R
    a = NS(id="obs:1", value=[10.0, 0.0, 3.0, 80.0])
    b = NS(id="obs:2", value=[40.0, 0.0, 3.0, 80.0])
    monkeypatch.setenv(PS.ENV, "1")
    assert R.page_own_stems(_Ev(rows=[NS(value="obs:2", detail={})]), [a, b]) == [b]
    assert R.page_own_stems(_Ev(refusals=[NS(detail={"how": "no_stroke"})]), [a, b]) == []          # retired: the cell join no longer answers
    assert R.page_own_stems(_Ev(refusals=[NS(detail={"how": "two_voices"})]), [a, b]) is None      # the unison rule keeps the cell join
    assert R.page_own_stems(_Ev(), [a, b]) is None                                                  # no page reading: the cell join stands
    monkeypatch.setenv(PS.ENV, "0")
    assert R.page_own_stems(_Ev(rows=[NS(value="obs:2", detail={})]), [a, b]) is None


# ───────────── ROADMAP 2.306 r4: a stem is the whole collinear run (Sean's r1 tiles 6 and 7 "stop a bit short") ─────────────

FX4 = os.path.join(os.path.dirname(__file__), "fixtures", "page_stems_2_306_r4_extent.json")


def _case(name):
    with open(FX4) as f:
        c = json.load(f)[name]
    t = lambda xs: [dict(x, box=tuple(x["box"])) for x in xs]
    return c, t(c["heads"]), t(c["verticals"]), t(c["crossers"]), {int(k): v for k, v in c["held"].items()}


def _stem_of(res, heads, glyph):
    hid = next(h["id"] for h in heads if glyph in h["members"])
    r = res["heads"][hid]
    return r, (res["stems"].get(r["stroke"]) if r["stroke"] is not None else None)


def test_r4_tile7_chord_stem_is_one_stroke_through_its_heads():
    """Sean (r1 tile 7): "a long stem on a chord, the box only gets part of it". The page map cuts the stem at the chord's inner head."""
    c, heads, verts, cross, held = _case("tile7")
    r1 = PS.read(heads, verts, held)                                   # r1: no join -- the control fails here
    _r, st1 = _stem_of(r1, heads, c["glyph"])
    assert st1 is not None and len(st1["heads"]) == 1                 # the chord's heads stand on two different pieces
    r4 = PS.read(heads, verts, held, crossers=cross)
    _r, st = _stem_of(r4, heads, c["glyph"])
    assert st is not None and len(st["members"]) == 2 and len(st["heads"]) == 2, st
    assert st["box"][3] - st["box"][1] > (st1["box"][3] - st1["box"][1]) * 2


def test_r4_tile6_stem_runs_through_the_tremolo_slash():
    """Sean (r1 tile 6): "interrupted by a trem slash". r1 read only the piece above the junction; the whole run reaches the half note's head.
    (The slash itself is boxed and claimed as a head there -- a head on the other side of the run -- so the head's reading abstains rather than pick.)"""
    c, heads, verts, cross, held = _case("tile6")
    r1 = PS.read(heads, verts, held)
    _r, st1 = _stem_of(r1, heads, c["glyph"])
    runs, cen = PS.join_runs(verts, heads, cross, held)
    whole = max(runs, key=lambda r: len(r["members"]))
    assert len(whole["members"]) == 2
    assert st1 is not None and whole["box"][3] > st1["box"][3] + 20      # r1's stem stopped short of the head; the run reaches it


def test_r4_two_voices_end_to_end_are_not_joined():
    """A real Brahms pair: two collinear stems whose gap holds heads on both sides of the column -- two voices end to end, never one stem."""
    c, heads, verts, cross, held = _case("divisi")
    a, b = c["pair"]
    pairs = []
    runs, cen = PS.join_runs(verts, heads, cross, held, pairs)
    assert (a, b, "!heads_both_sides") in pairs
    run_of = {m: r["ord"] for r in runs for m in r["members"]}
    assert run_of[a] != run_of[b]


def test_r4_empty_paper_is_never_bridged():
    v1 = dict(ord=1, box=(100.0, 0.0, 103.0, 60.0), sp=20.0)
    v2 = dict(ord=2, box=(100.0, 75.0, 103.0, 140.0), sp=20.0)       # 15 px = 0.75 sp of empty paper
    runs, cen = PS.join_runs([v1, v2], [], [])
    assert len(runs) == 2 and cen.get("refused:empty_paper") == 1
    runs, cen = PS.join_runs([v1, v2], [], [dict(ord=3, box=(90.0, 58.0, 120.0, 78.0), kind="slash")])
    assert len(runs) == 1 and cen.get("joined:slash") == 1
