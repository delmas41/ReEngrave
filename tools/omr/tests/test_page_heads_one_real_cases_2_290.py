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
CROPS = sorted((HERE / "crops").glob("*.npz")) if (HERE / "crops").exists() else []


#: real cases this build does NOT pass, each with its cause and the plan step that owns it (never silently skipped)
KNOWN = {
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
    meta, items, foreign, lab, props, binary = _load(path)
    e = meta["case"]["expect"]
    oh, B, sb, mine = _read(meta, items, foreign, lab, props, binary)
    cut = 0.5 if e == "not_head" else 0.3
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
    elif e == "tall_box":
        big = [it for it in oh.items if _share(B, it["box"]) >= 0.8]
        assert all(oh.how[oh.items.index(it)] == "tall_read" or not it["ink_px"] or len(oh.groups[oh.group_of_key[it["key"]]]) == 1 for it in big), said
        assert not any(h["rep"] in {it["key"] for it in big} and len(h["strokes"]) > 0 and h["members"] != [h["rep"]] for h in oh.heads)
    del groups


def test_the_cases_list_is_current():
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    assert len(cases) >= 80 and {c["expect"] for c in cases} >= {"head", "not_head", "part_of_head", "chord"}
