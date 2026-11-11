"""ROADMAP 2.290 round 4 (CLAUDE rule 7, a control from REAL rows): a page head the one identity folds from boxes that write DIFFERENT pitches is ONE head with ONE
position, measured from its own ink -- never the more confident box's (Litolff p2 m7: G3 written, the page and the tie F3). The rows are those of every such fold on
the five sample pages (`benchmarks/page-heads-ledger-2026-11/real_cases/fold_rows.json`, built by `build_fold_rows.py`)."""
import json
import pathlib
from types import SimpleNamespace

import pytest

from tools.omr.staged import export as E

HERE = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "page-heads-ledger-2026-11" / "real_cases"
FOLDS = json.loads((HERE / "fold_rows.json").read_text())
SPACING = {"litolff": 16.0, "brahms": 26.4}      # the staff space of the plates' sample pages in page px (export `run.spacing`)


class _Rec:
    def __init__(self, members):
        self.rows = {m["sub"]: m["rows"] for m in members}

    def obs(self, quantity, sub):
        key = {E.Q.GLYPH_BOX: "glyph_box", E.Q.NOTEHEAD_STAFF_POSITION: "notehead_staff_position", E.Q.MARK_GROUP: "mark_group", E.Q.GLYPH_CONF: "glyph_conf"}[quantity]
        r = self.rows.get(sub, {}).get(key)
        return [r] if r else []


def _run(fold_id, tall_ok=True):
    fold = FOLDS[fold_id]
    run = SimpleNamespace(spacing=SPACING[fold["plate"]])
    members = fold["members"]
    queued = []
    for m in members:
        conf = float(m["rows"]["glyph_conf"]["value"])
        queued.append((fold_id, conf, m["sub"], run, 0, {"category": "notehead", "pitch": m["pitch"]}, {}))
    best = {}
    for gid, conf, sub, *_r in queued:
        cur = best.get(gid)
        if cur is None or (-conf, sub) < (-cur[0], cur[1]):
            best[gid] = (conf, sub)
    before = dict(best)
    E._settle_folded_pitches(_Rec(members), queued, best)
    return queued, before, best


@pytest.mark.parametrize("fold_id", sorted(FOLDS))
def test_the_one_position_of_a_folded_head(fold_id):
    expect = FOLDS[fold_id]["expect"]
    queued, before, best = _run(fold_id)
    guessed = [q for q in queued if (q[5].get("guess") or {}).get("rule") == E.FOLD_PITCH_RULE]
    if expect == "settle":
        # Litolff p2 m7: the hole puts the head at step 8 = the F3 box; the G3 box (the more confident) loses; nothing is guessed (the ink decides)
        assert before[fold_id][1] == "glyph/2/0/9/6/1" and best[fold_id][1] == "glyph/2/0/9/6/2"
        assert not guessed
    elif expect == "guess":
        assert best[fold_id] == before[fold_id], "the most confident member stands where no ink witness settles it"
        assert len(guessed) == 1 and guessed[0][2] == best[fold_id][1], FOLDS[fold_id]["what"]
        cands = {c["value"] for c in guessed[0][5]["guess"]["candidates"]}
        assert len(cands) >= 2 and guessed[0][5]["guess"]["chosen"]["value"] in cands
    else:
        assert best[fold_id] == before[fold_id] and not guessed, FOLDS[fold_id]["what"]


def test_the_control_can_fail(monkeypatch):
    """With the settle switched off (the round-3 export) p2 m7 keeps the G3 box: the control fails where it should."""
    monkeypatch.setattr(E, "_settle_folded_pitches", lambda rec, queued, best: None)
    queued, before, best = _run("mg/2/0/245")
    assert best["mg/2/0/245"][1] == "glyph/2/0/9/6/1"          # G3, the wrong note
    with pytest.raises(AssertionError):
        test_the_one_position_of_a_folded_head("mg/2/0/245")


def test_flag_off_groups_are_untouched():
    """A group the old identity filed (no `identity: page_head`) is never touched."""
    queued, before, best = _run("mg/2/0/245")
    members = [dict(m, rows={k: v for k, v in m["rows"].items() if k != "mark_group"}) for m in FOLDS["mg/2/0/245"]["members"]]
    run = SimpleNamespace(spacing=16.0)
    q2 = [("mg/2/0/245", float(m["rows"]["glyph_conf"]["value"]), m["sub"], run, 0, {"category": "notehead", "pitch": m["pitch"]}, {}) for m in members]
    best2 = {"mg/2/0/245": (0.4016, "glyph/2/0/9/6/1")}
    E._settle_folded_pitches(_Rec(members), q2, best2)
    assert best2["mg/2/0/245"][1] == "glyph/2/0/9/6/1" and not any(q[5].get("guess") for q in q2)
