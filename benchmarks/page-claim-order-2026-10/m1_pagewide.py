"""ROADMAP 2.221 m1/m1b page-wide: what the word / dynamic / bracket claims CAPTURE (Sean 2026-10-29: prove a GATHER claim by what it
captures -- tiles and hand-labelled pages -- not a full re-gather).

    python3 benchmarks/page-claim-order-2026-10/m1_pagewide.py count WORK   # claims per page, Brahms p0 vs hand truth -> m1-pagewide.json
    python3 benchmarks/page-claim-order-2026-10/m1_pagewide.py tiles WORK   # 12 blind tiles -> out/print/2.221-m1-pagewide/

WORK = a lane_report `work/` dir whose ON arm ran with OMR_CLAIM_WORDS_FIRST=1 OMR_CLAIM_BRACKETS_FIRST=1 (`--from gather`).
STAGED, read-only: reads the ON arm's gathered record and the PDF page; changes nothing.

Truth match (Brahms p0, data/hand-truth/pages/imslp317803/0.json; 600 dpi page px like the record): a truth mark of class `text`,
`dynamic*`, `brace` or `bracket*` is CLAIMED when some claim box covers at least half of the truth box's area (or the truth box covers
half of the claim's); a claim matching no truth mark of those classes is listed with what truth boxes it does overlap.
"""
from __future__ import annotations

import collections
import json
import pathlib
import random
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR            # noqa: E402
from tools.omr.staged.judged import iter_array            # noqa: E402

SAMPLE = json.loads((HERE / "m1-pagewide-sample.json").read_text())
TRUTH = {("brahms", 0): ROOT / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"}
OUT_JSON = HERE / "m1-pagewide.json"
PRINT = ROOT / "out" / "print" / "2.221-m1-pagewide"
TRUTH_CLASSES = ("text", "dynamic", "brace", "bracket")


def _claims(work, plate):
    pages = set(SAMPLE["plates"][plate]["pages"])
    claims, census = [], {}
    rec = work / ("%s.on.gathered.record.json" % plate)
    for o in iter_array(rec, "observations"):
        if o.get("quantity") != "claimed_area":
            continue
        d = o.get("detail") or {}
        if d.get("owner") not in ("word", "bracket") or d.get("scope") != "system":
            continue
        pg = LR.page_of(o.get("subject"))
        if pg in pages:
            claims.append(dict(id=o["id"], page=pg, subject=o["subject"], box=[float(v) for v in o["value"]], owner=d["owner"],
                               source=d.get("source"), text=d.get("text"), kind=d.get("kind"), category=d.get("category"),
                               inside=sorted(k for k, e in (d.get("boxes_inside") or {}).items()
                                             if float(e.get("ink_share_inside", 0)) >= 0.5)))
    for a in iter_array(rec, "abstentions"):
        d = a.get("detail") or {}
        if a.get("quantity") == "claimed_area" and d.get("why") == "page_claim_census":
            census[LR.page_of(a.get("subject"))] = d.get("census")
    return claims, census


def _cover(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    sa, sb = max(1.0, (a[2] - a[0]) * (a[3] - a[1])), max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
    return max(ix * iy / sa, ix * iy / sb)


def count(work):
    out = {"plates": {}, "truth": {}}
    for plate in ("litolff", "brahms"):
        claims, census = _claims(work, plate)
        per = collections.defaultdict(collections.Counter)
        for c in claims:
            per[c["page"]]["%s:%s%s" % (c["owner"], c["source"], ":" + c["kind"] if c["kind"] else "")] += 1
        out["plates"][plate] = {"claims_per_page": {str(k): dict(v) for k, v in sorted(per.items())},
                                "census": {str(k): v for k, v in sorted(census.items())},
                                "head_boxes_held_ink_ge_half": sum(len(c["inside"]) for c in claims),
                                "claims": claims}
        for (tp, tpg), path in TRUTH.items():
            if tp != plate:
                continue
            boxes = json.loads(path.read_text())["boxes"]
            marks = [b for b in boxes if str(b["cls"]).startswith(TRUTH_CLASSES)]
            mine = [c for c in claims if c["page"] == tpg]
            got, unclaimed = [], []
            for m in marks:
                hit = [c["id"] for c in mine if _cover(m["rect"], c["box"]) >= 0.5]
                (got if hit else unclaimed).append(dict(id=m["id"], cls=m["cls"], rect=m["rect"], text=m.get("text"), claims=hit))
            matched = {i for g in got for i in g["claims"]}
            stray = []
            for c in mine:
                if c["id"] in matched:
                    continue
                over = [(b["cls"], round(_cover(b["rect"], c["box"]), 2)) for b in boxes if _cover(b["rect"], c["box"]) >= 0.3]
                stray.append(dict(c, truth_overlaps=over))
            out["truth"]["%s p%d" % (plate, tpg)] = {
                "truth_marks": dict(collections.Counter(str(m["cls"]) for m in marks)), "claimed": len(got),
                "unclaimed": len(unclaimed), "claims_matching_no_truth_mark": len(stray),
                "claimed_by_class": dict(collections.Counter(g["cls"] for g in got)),
                "unclaimed_by_class": dict(collections.Counter(u["cls"] for u in unclaimed)),
                "unclaimed_marks": unclaimed, "stray_claims": stray}
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str))
    for plate, v in out["plates"].items():
        print(plate, "claims per page", v["claims_per_page"], "| head boxes held", v["head_boxes_held_ink_ge_half"])
        print("  census", v["census"])
    for k, v in out["truth"].items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("unclaimed_marks", "stray_claims")})


def _page(plate, pg):
    from tools.omr.preprocessing import render_page
    pi = render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600)
    g = np.asarray(pi.rgb if getattr(pi, "rgb", None) is not None else pi.binary)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR) if g.ndim == 2 else cv2.cvtColor(g, cv2.COLOR_RGB2BGR)


def tiles(work):
    data = json.loads(OUT_JSON.read_text())
    rng = random.Random(2221)
    pool = [dict(c, plate=p) for p, v in data["plates"].items() for c in v["claims"]]
    t = data["truth"].get("brahms p0", {})
    stray = [dict(c, plate="brahms") for c in t.get("stray_claims", [])]
    stray_ids = {c["id"] for c in stray}
    picks = [("random_claim", c) for c in rng.sample([c for c in pool if c["id"] not in stray_ids], min(8, len(pool)))]
    picks += [("claim_matching_no_truth_mark", c) for c in rng.sample(stray, min(2, len(stray)))]
    un = t.get("unclaimed_marks", [])
    picks += [("unclaimed_truth_mark", dict(plate="brahms", page=0, box=u["rect"], cls=u["cls"], id=u["id"]))
              for u in rng.sample(un, min(2, len(un)))]
    rng.shuffle(picks)
    (PRINT / "tiles").mkdir(parents=True, exist_ok=True)
    key, pages = [], {}
    for i, (what, c) in enumerate(picks, 1):
        pk = (c["plate"], c["page"])
        if pk not in pages:
            pages[pk] = _page(*pk)
        img = pages[pk]
        x0, y0, x1, y1 = (int(round(v)) for v in c["box"])
        m = 140
        crop = img[max(0, y0 - m):y1 + m, max(0, x0 - m):x1 + m].copy()
        ox, oy = max(0, x0 - m), max(0, y0 - m)
        cv2.rectangle(crop, (x0 - ox - 4, y0 - oy - 4), (x1 - ox + 4, y1 - oy + 4), (0, 140, 255), 3)   # neutral orange box
        cv2.imwrite(str(PRINT / "tiles" / ("tile_%02d.png" % i)), crop)
        key.append(dict(tile=i, what=what, plate=c["plate"], page=c["page"], box=c["box"], claim=c.get("id"), owner=c.get("owner"),
                        source=c.get("source"), text=c.get("text"), kind=c.get("kind"), truth_cls=c.get("cls"),
                        truth_overlaps=c.get("truth_overlaps")))
    (PRINT / "key.json").write_text(json.dumps(key, indent=1))
    (PRINT / "tiles" / "README.md").write_text(
        "# 2.221 m1/m1b page-wide claims: 12 blind tiles\n\nEach tile is a piece of the printed page. The ORANGE box marks one "
        "mark.\n\nQuestion: **Is the ink in the orange box a word, a dynamic, a bracket or a brace -- or something else (say what)?**\n")
    print("wrote", len(key), "tiles to", PRINT)


if __name__ == "__main__":
    cmd, work = sys.argv[1], pathlib.Path(sys.argv[2])
    {"count": count, "tiles": tiles}[cmd](work)
