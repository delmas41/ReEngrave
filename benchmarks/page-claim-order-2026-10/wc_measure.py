"""ROADMAP 2.221 word coverage: what the extra word / bracket claims CAPTURE on Brahms p0's hand truth, BEFORE vs AFTER.

    python3 benchmarks/page-claim-order-2026-10/wc_measure.py BEFORE_WORK AFTER_WORK     # -> wc-measure.json

BEFORE_WORK / AFTER_WORK = lane_report `work/` dirs (`--from gather`); claims are read from each dir's `brahms.on.gathered.record.json`.
STAGED, read-only. Truth classes (data/hand-truth/pages/imslp317803/0.json, 600 dpi page px): `text` split into INSTRUMENT (right edge left of
x 1200: the margin names), TITLE (bottom edge above y 1320: title block, composer, opus) and WORD (the rest), `dynamic*`, `brace`.
A truth mark is CLAIMED when some claim covers at least half of the truth box (or the truth box covers half the claim, m1_pagewide._cover).
A claim matching no truth mark of those classes is FALSE (listed with the truth boxes it overlaps).

Also: the LONE dynamic letters, the detector's `Q.DYNAMIC_LETTER` rows of the page that no claim holds, against the truth class
under each, by letter and detector score band.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import m1_pagewide as M                                      # noqa: E402
from tools.omr.staged import lane_report as LR               # noqa: E402
from tools.omr.staged.judged import iter_array               # noqa: E402

TRUTH = ROOT / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"
LETTER_CLASS = {"f": "dynamicF", "p": "dynamicP", "m": "dynamicM", "s": "dynamicS", "z": "dynamicZ", "r": "dynamicR"}


def kind_of(b):
    c = str(b["cls"])
    if c != "text":
        return "dynamic" if c.startswith("dynamic") else c
    x0, y0, x1, y1 = b["rect"]
    if x1 < 1200:
        return "instrument_name"
    if y1 < 1320:
        return "title"
    return "word"


def score(work):
    claims, census = M._claims(pathlib.Path(work), "brahms")
    mine = [c for c in claims if c["page"] == 0]
    boxes = json.loads(TRUTH.read_text())["boxes"]
    marks = [b for b in boxes if str(b["cls"]).startswith(M.TRUTH_CLASSES)]
    got, un = collections.Counter(), collections.Counter()
    unclaimed = []
    matched = set()
    for m in marks:
        k = kind_of(m)
        hit = [c for c in mine if M._cover(m["rect"], c["box"]) >= 0.5]
        if hit:
            got[k] += 1
            matched.update(c["id"] for c in hit)
        else:
            un[k] += 1
            unclaimed.append(dict(kind=k, rect=[round(v) for v in m["rect"]], text=m.get("text"), cls=m["cls"]))
    false = [dict(source=c["source"], owner=c["owner"], kind=c["kind"], text=c["text"], box=[round(v) for v in c["box"]],
                  overlaps=[(b["cls"], round(M._cover(b["rect"], c["box"]), 2)) for b in boxes if M._cover(b["rect"], c["box"]) >= 0.3][:4])
             for c in mine if c["id"] not in matched]
    by_source = collections.Counter("%s:%s" % (c["owner"], c["source"]) for c in mine)
    return dict(truth_marks=len(marks), claimed=sum(got.values()), unclaimed=sum(un.values()), claimed_by_kind=dict(got),
                unclaimed_by_kind=dict(un), n_claims=len(mine), claims_by_source=dict(by_source), false_claims=len(false),
                false_list=false, unclaimed_list=unclaimed, census=census.get(0)), mine


def lone_letters(work, claims):
    rec = pathlib.Path(work) / "brahms.on.gathered.record.json"
    boxes = json.loads(TRUTH.read_text())["boxes"]
    tb = [(b["cls"], b["rect"]) for b in boxes if str(b["cls"]).startswith(("dynamic", "text"))]
    c = collections.Counter()
    c_score = collections.defaultdict(collections.Counter)            # detector confidence band -> outcome
    for o in iter_array(rec, "observations"):
        if o.get("quantity") != "dynamic_letter" or LR.page_of(o.get("subject")) != 0:
            continue
        d = o.get("detail") or {}
        bb, letter = d.get("bbox_page_px"), d.get("letter")
        if not (bb and letter):
            continue
        if any(M._cover(bb, cl["box"]) >= 0.5 for cl in claims):
            c["inside_a_claim"] += 1
            continue
        best = max(((M._cover(bb, r), cls) for cls, r in tb), default=(0.0, None))
        want = LETTER_CLASS.get(str(letter))
        sc = o.get("score")
        band = "score>=0.8" if (sc or 0) >= 0.8 else ("score 0.5-0.8" if (sc or 0) >= 0.5 else "score<0.5")
        if best[0] < 0.5:
            k = "lone:matches_no_truth_mark"
        elif best[1] == want:
            k = "lone:is_that_letter_(truth_dynamic_same_class)"
        elif str(best[1]).startswith("dynamic"):
            k = "lone:truth_dynamic_other_class"
        else:
            k = "lone:inside_a_truth_word"
        c[k] += 1
        c_score[band][k] += 1
    return dict(c, by_score={b: dict(v) for b, v in sorted(c_score.items())})


if __name__ == "__main__":
    before, after = sys.argv[1], sys.argv[2]
    out = {}
    for name, w in (("before", before), ("after", after)):
        s, mine = score(w)
        out[name] = s
        out[name]["lone_letters"] = lone_letters(w, mine)
    (HERE / "wc-measure.json").write_text(json.dumps(out, indent=1, default=str))
    for name in ("before", "after"):
        s = out[name]
        print(name, {k: s[k] for k in ("truth_marks", "claimed", "unclaimed", "claimed_by_kind", "unclaimed_by_kind", "n_claims",
                                       "claims_by_source", "false_claims")})
        print("   lone letters", s["lone_letters"])
