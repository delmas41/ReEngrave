"""ROADMAP 2.97 control -- every notehead duration verdict on Sean's hand-truth
page (Brahms 317803, pdf index 0) against HIS boxes, base vs arm.

   python3 truth_2_97.py BASE.pkl ARM.pkl OUT.json

For each standing (non-rest) duration verdict whose head matches a truth head
(`hand_truth.score.match_boxes`, by overlap) in a fully labelled cell and whose
truth stem is boxed (`status == ok`): judged against `derive()["written"]`
(beats) -- decided RIGHT / WRONG; narrowed WITH truth among its candidates /
WITHOUT. The headline for 2.97 is WRONG not rising; the changed heads are
listed so each can be cropped.  Sean's boxes are the evidence (rule 7); the
record's side is never used to derive the truth.
"""
import collections
import json
import pickle
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-missing-notes-2026-09" / "probe"))

from l281_truth import Truth  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged.record import Kind, Outcome, Q  # noqa: E402

PAGE = 0
T = Truth()
by_idx = {h.idx: h for h in T.heads}


def heads_of(log):
    out = {}
    for v in list(log._vrd.values()):
        if v.quantity != Q.DURATION or v.subject.page != PAGE:
            continue
        cur = log.verdict(Q.DURATION, v.subject)
        if cur is None or cur.id != v.id or C._is_rest(cur):
            continue
        if cur.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        rows = log.rows(Q.GLYPH_BOX, v.subject)
        box = ((rows[-1].detail or {}).get("bbox_page_px")) if rows else None
        if not box:
            continue
        out[v.subject.to_key()] = (cur, [float(x) for x in box])
    return out


def judge(log):
    hs = heads_of(log)
    keys = list(hs)
    read = [(i, tuple(hs[k][1]), "head") for i, k in enumerate(keys)]
    truth = [(h.idx, h.rect, h.cls) for h in T.heads]
    pairs, _a, _b = S.match_boxes(truth, read)
    res = {}
    for t_idx, (r_i, iou) in pairs.items():
        k = keys[r_i]
        dv = T.derive(by_idx[t_idx])
        if dv["status"] != "ok" or not dv.get("full_cell") \
                or dv.get("written") is None:
            continue
        v = hs[k][0]
        tw = float(dv["written"])
        if v.outcome is Outcome.DECIDED:
            b = float((v.value or {}).get("beats") or 0.0)
            j = "decided_right" if abs(b - tw) < 1e-6 else "decided_WRONG"
            val = b
        else:
            cands = [float(c.value.get("beats")) for c in v.candidates
                     if isinstance(c.value, dict)]
            j = ("narrowed_with_truth" if any(abs(c - tw) < 1e-6 for c in cands)
                 else "narrowed_without_truth")
            val = cands
        res[k] = {"judge": j, "truth": tw, "ours": val,
                  "decider": v.decider, "cell": "/".join(map(str, [
                      v.subject.page, v.subject.system, v.subject.staff,
                      v.subject.cell]))}
    return res


b = judge(pickle.load(open(sys.argv[1], "rb")))
a = judge(pickle.load(open(sys.argv[2], "rb")))
cb = collections.Counter(r["judge"] for r in b.values())
ca = collections.Counter(r["judge"] for r in a.values())
print("judged heads: base", len(b), " arm", len(a))
print("base", dict(cb))
print("arm ", dict(ca))
moved = {k: (b.get(k), a.get(k)) for k in set(b) | set(a)
         if (b.get(k) or {}).get("judge") != (a.get(k) or {}).get("judge")}
print("heads whose judgement changed:", len(moved))
trans = collections.Counter((x[0] or {}).get("judge", "-") + " -> " + (x[1] or {}).get("judge", "-")
                            for x in moved.values())
for k, v in trans.most_common():
    print("  ", v, k)
json.dump({"base": b, "arm": a, "moved": moved}, open(sys.argv[3], "w"), indent=1)
