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
