"""ROADMAP 2.290 build -- REAL-PAGE controls (CLAUDE rule 7; DECISIONS 2026-11-10 CONTROLS FROM REAL JUDGED CASES): the head reader (`page_heads.core`,
the same function the gather runs) replayed on the page pixels of marks Sean has named, cut from a 2.290 ON gather into
`benchmarks/page-heads-ledger-2026-11/real_cases/crops/` (`OMR_PAGE_HEAD_CASES_DUMP`; cases.json says what Sean said and what is expected).

  head          a real notehead: exactly ONE page head stands on the tile's box, and it claims ink there
  part_of_head  part of a real note: at most one head claims ink on the box
  not_head      not a head (barline, beam, tremolo slash, ledger line, stem, flag, an accidental, a rest): no head claims a stroke mostly inside the box
  tall_box      a box around several heads: it is no head of its own
The chord cases (2.291 tiles 7, 10, 11) are bar-level and checked on the gather's own rows (`real_cases/check_real_cases.py`)."""
import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import page_heads as PH

HERE = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "page-heads-ledger-2026-11" / "real_cases"
# the crops are TRACKED (benchmarks/**/crops/ is gitignored, so they live in npz/): a clean checkout runs the controls, it does not skip them
CROPS = sorted((HERE / "npz").glob("*.npz")) if (HERE / "npz").exists() else []


#: real cases this build does NOT pass, each with its cause and the plan step that owns it (never silently skipped)
KNOWN = {
    "2.289_r1__9": "Sean's unison half note (Litolff p2) shows on the page as two thin horizontal rims only (1.27 x 0.19 and 1.27 x 0.25 sp): by 2.290 build r2's "
                   "rule a claim is a whole head's ink, so each rim is a sliver and stays with the cell boxes (the same shape as r1 tile 8, which Sean called "
                   "a sliver); reading a hollow head from its rims is plan step 5",
    "2.290_build_r1__3": "Sean's eighth (Litolff p2, 2.290 build r1 tile 3) is a head fused with its stem stub into ONE page stroke 0.9 x 2.5 sp: a stroke bigger "
                         "than a head is not claimed (left to the cell boxes, never mis-claimed: Sean judged r1's empty claim right); plan step 5",
    "2.289_r1__10": "Sean's eighth (Litolff p2) is fused with its chord neighbour into ONE page stroke 1.26 x 3.15 sp: a stroke bigger than a head is not "
                    "claimed (it stays with the cell boxes, as today); splitting merged ink is plan step 5",
}


def _load(p):
    z = np.load(p, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    items = []
    for it in meta["items"]:
        d = dict(it)
        d["box"] = tuple(float(v) for v in it["box"])
        d["scope"] = tuple(it["scope"])
        d["cell"] = tuple(it["cell"])
        items.append(d)
    return meta, items, [tuple(f) for f in meta["foreign"]], z["lab"], [tuple(x) for x in meta["props"]], z["binary"]


def _share(inner, outer):
    ix = min(inner[2], outer[2]) - max(inner[0], outer[0])
    iy = min(inner[3], outer[3]) - max(inner[1], outer[1])
    a = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return 0.0 if (ix <= 0 or iy <= 0 or a <= 0) else ix * iy / a


def _stroke_boxes(lab, s):
    out = {}
    for v in np.unique(lab):
        if v <= 0:
            continue
        ys, xs = np.nonzero(lab == v)
        out[int(v) - 1] = (xs.min() / s, ys.min() / s, (xs.max() + 1) / s, (ys.max() + 1) / s)
    return out


def _read(meta, items, foreign, lab, props, binary):
    oh = PH.core([dict(i) for i in items], foreign, lab, props, binary, float(meta["scale"]), float(meta["sp"]))
    ox, oy = meta["origin"]
    b = meta["case"]["box"]
    B = (b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy)
    sb = _stroke_boxes(lab, float(meta["scale"]))
    mine = [it["key"] for it in oh.items if _share(it["box"], B) >= 0.5 or _share(B, it["box"]) >= 0.5]
    return oh, B, sb, mine


@pytest.mark.skipif(not CROPS, reason="no real-case crops cut yet (run a 2.290 ON gather with OMR_PAGE_HEAD_CASES_DUMP)")
@pytest.mark.parametrize("path", CROPS, ids=[p.stem for p in CROPS])
def test_real_case(path):
    if path.stem in KNOWN:
        pytest.xfail(KNOWN[path.stem])
    _check_case(path)


def _check_case(path):
    meta, items, foreign, lab, props, binary = _load(path)
    e = meta["case"]["expect"]
    oh, B, sb, mine = _read(meta, items, foreign, lab, props, binary)
    cut = 0.5 if e in ("not_head", "between_heads") else 0.3
    # a stroke an earlier page-wide claim holds is marked, never claimed (`page_heads.file_one_claims`; the crop carries which, `held`)
    held = {n for n, pid in enumerate(meta["stroke_ids"]) if str(pid) in (meta.get("held") or {})}
    claims = [h for h in oh.heads if any(i in sb and i not in held and _share(sb[i], B) >= cut for i in h["strokes"])]
    groups = {oh.group_of_key[k] for k in mine if oh.items[[x["key"] for x in oh.items].index(k)]["ink_px"]}
    said = "Sean: %s" % meta["case"]["sean"]
    if e == "head":
        assert len(claims) == 1, "%s -- %d head claims on the box" % (said, len(claims))
    elif e == "part_of_head":
        assert len(claims) <= 1, "%s -- %d head claims on the box" % (said, len(claims))
    elif e == "not_head":
        assert not claims, "%s -- a head claims its ink (%s)" % (said, [h["rep"] for h in claims])
    elif e == "between_heads":
        # Sean, 2.290 build r1 tile 12: the box lands BETWEEN two half notes a third apart and takes a little ink of each: the two heads are TWO page heads
        # (never one, however the ink the boxes clip lies) and the ink between them is claimed by neither
        near = [it for it in oh.items if it["ink_px"] and _share(B, it["box"]) >= 0.25]
        assert len({oh.group_of_key[it["key"]] for it in near}) >= 2, "%s -- the heads a third apart were joined into one" % said
        assert not claims, "%s -- a head claims the ink between the two heads (%s)" % (said, [h["rep"] for h in claims])
    elif e == "tall_box":
        big = [it for it in oh.items if _share(B, it["box"]) >= 0.8]
        assert all(oh.how[oh.items.index(it)] == "tall_read" or not it["ink_px"] or len(oh.groups[oh.group_of_key[it["key"]]]) == 1 for it in big), said
        assert not any(h["rep"] in {it["key"] for it in big} and len(h["strokes"]) > 0 and h["members"] != [h["rep"]] for h in oh.heads)
    del groups


@pytest.mark.skipif(not CROPS, reason="no real-case crops cut yet")
def test_the_control_can_fail(monkeypatch):
    """CLAUDE rule 7: with the head-ink shape test broken (every stroke is head ink, any size is claimable) some of Sean's not-a-head marks DO get a head
    claim -- the fixture is able to fail. (Broken: any stroke touching a head's oval is claimed, whatever its shape or size.)"""
    monkeypatch.setattr(PH, "is_head_ink", lambda *a: True)
    monkeypatch.setattr(PH, "CLAIM_MAX_W_SP", 99.0)
    monkeypatch.setattr(PH, "CLAIM_MAX_H_SP", 99.0)
    monkeypatch.setattr(PH, "CLAIM_SHARE_MIN", 0.0)
    monkeypatch.setattr(PH, "OTHER_HEAD_MAX", 99.0)
    monkeypatch.setattr(PH, "CLAIM_UNION_MIN_SP", 0.0)           # (round 2's size rule is another control, below)
    monkeypatch.setattr(PH, "CLAIM_UNION_MAX_H_SP", 99.0)
    broke = 0
    for path in CROPS:
        meta, items, foreign, lab, props, binary = _load(path)
        if meta["case"]["expect"] != "not_head":
            continue
        oh, B, sb, _mine = _read(meta, items, foreign, lab, props, binary)
        held = {n for n, pid in enumerate(meta["stroke_ids"]) if str(pid) in (meta.get("held") or {})}
        if any(i in sb and i not in held and _share(sb[i], B) >= 0.5 for h in oh.heads for i in h["strokes"]):
            broke += 1
    assert broke >= 1


#: Sean's four WRONG answers on 2.290 build r1 (answers-2.290-build-r1.json): the claim was a sliver (8, 10), half of a rest (9), a box between two heads a third apart (12)
R1_WRONG = ["2.290_build_r1__8", "2.290_build_r1__9", "2.290_build_r1__10", "2.290_build_r1__12"]


@pytest.mark.skipif(not CROPS, reason="no real-case crops")
def test_round_2_controls_fail_on_the_round_1_rules(monkeypatch):
    """CLAUDE rule 7: each of Sean's four wrong r1 claims, on its own pixels, PASSES with the round-2 rules and FAILS with them switched off (the r1 reader)."""
    paths = {p.stem: p for p in CROPS}
    for name in R1_WRONG:
        _check_case(paths[name])
    monkeypatch.setattr(PH, "BOX_CENTRES_A_THIRD_SP", 99.0)
    monkeypatch.setattr(PH, "CLAIM_UNION_MIN_SP", 0.0)
    monkeypatch.setattr(PH, "CLAIM_UNION_MAX_H_SP", 99.0)
    for name in R1_WRONG:
        with pytest.raises(AssertionError):
            _check_case(paths[name])


def test_claim_size_reason():
    assert PH.claim_size_reason(0.89, 1.33) is None          # r1 tile 1, right
    assert PH.claim_size_reason(1.59, 0.19) == "too_small"   # r1 tile 8
    assert PH.claim_size_reason(0.38, 1.52) == "too_small"   # r1 tile 10
    assert PH.claim_size_reason(1.02, 1.59) == "too_tall"    # r1 tile 9
    assert PH.claim_size_reason(2.78, 1.45) is None          # a head fused to its ledger line is still one head (Brahms 2.282 tile 1)


def test_the_cases_list_is_current():
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    assert len(cases) >= 80 and {c["expect"] for c in cases} >= {"head", "not_head", "part_of_head", "chord"}
