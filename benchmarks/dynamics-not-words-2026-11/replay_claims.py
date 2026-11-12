"""ROADMAP 2.301 measure: replay the PAGE-WIDE CLAIM pass (`gather.gather_page_claims`) of a page on the rows a saved gather already holds -- no OCR, no detector, no re-gather.

    python3 benchmarks/dynamics-not-words-2026-11/replay_claims.py --plate brahms --slice SLICE_DIR --page 0 --out OUT.json [--env NAME=V ...]

The inputs are exactly what the pass reads: the page's `direction_word` / `dynamic_letter` rows (the OCR and detector readings of the saved gather), the detector boxes of
the page (rebuilt from its `glyph_box` rows: cell-canonical value -> page px), and the page RASTER and staves loaded from the master cell map (`cell_map.load_prepared`).
The pass then runs on THIS tree. Because the words are read rows, two arms (before / after a code change) differ only in the code: the OCR cannot starve.
Writes the page's `claimed_area` rows of owner `word` (area rows: value, source, text, owner_row, compound_of, detector_letter) as JSON.
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


class FakeDet:
    """A detector box rebuilt from its `glyph_box` row: the cell-canonical box the row holds (`value` = [class, x, y, w, h]), exactly as the pass reads a real detection."""

    def __init__(self, name, canon, cat):
        self.smufl_name, self.category, self.confidence = name, cat, 0.9
        self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = (float(t) for t in canon)


def page_rows(slice_dir, page):
    from tools.omr.staged import claim_readout as CR
    return CR.read_rows(pathlib.Path(slice_dir), [page])


def replay(plate, slice_dir, page, env=None):
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import gather as G
    from tools.omr.staged import lane_report as LR
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q
    from tools.omr.staged.review import rerun as RR
    saved = {k: os.environ.get(k) for k in (env or {})}
    for k, v in (env or {}).items():
        os.environ[k] = v
    try:
        rows = page_rows(slice_dir, page)
        keep_q = ("direction_word", "dynamic_letter", "dynamic_letter_neighbours", "glyph_box", "staff_lines", "document_identity")
        obs = [o for o in rows["observations"] if o.get("quantity") in keep_q]
        log, _ = RR.rebuild_gather({"observations": obs, "abstentions": [], "verdicts": []})
        (pws, cells), = CM.load_prepared(LR.LIB / LR.PLATES[plate]["pdf"], [page], root=LR.CELL_MAP_ROOT)
        local = G._system_local(pws.staves)
        dets = {}
        for o in obs:
            if o["quantity"] != "glyph_box":
                continue
            v, d = o.get("value"), (o.get("detail") or {})
            if not (isinstance(v, list) and v and d.get("bbox_page_px")):
                continue
            sub = R.Subject.from_key(o["subject"]) if hasattr(R, "Subject") else None
            p = o["subject"].split("/")
            ck = R.cell(int(p[1]), int(p[2]), int(p[3]), int(p[4])).to_key()
            gi = int(p[5])
            lst = dets.setdefault(ck, {})
            lst[gi] = FakeDet(str(v[0]), v[1:5], d.get("category") or "")
        detections = {}
        for ck, m in dets.items():
            n = max(m) + 1
            detections[ck] = [m.get(i) or FakeDet("none", [-9e5, -9e5, 1, 1], "") for i in range(n)]
        G.gather_page_claims(log, pws, cells, local, detections)
        out = []
        for r in log.rows(Q.CLAIMED_AREA, R.page(page), scope=R.Scope.SELF_AND_DESCENDANTS):
            d = r.detail or {}
            if d.get("owner") == "word" and d.get("unit") == "area":
                out.append(dict(id=r.id, box=[float(t) for t in r.value], source=d.get("source"), text=d.get("text"), owner_row=d.get("owner_row"),
                                compound_of=d.get("compound_of"), detector_letter=d.get("detector_letter"), dynamic_token=d.get("dynamic_token"),
                                standing=d.get("standing"), category=d.get("category")))
        words = {r.id: dict(text=r.value, box=(r.detail or {}).get("bbox_page_px"), dynamics=(r.detail or {}).get("dynamics"),
                            includes=(r.detail or {}).get("includes_dynamic_glyphs"))
                 for r in log.rows(Q.DIRECTION_WORD, R.page(page), scope=R.Scope.SELF_AND_DESCENDANTS)}
        census = [dict(r.detail or {}) for r in log.rows(Q.CLAIMED_AREA, R.page(page), scope=R.Scope.SELF_AND_DESCENDANTS)
                  if (r.detail or {}).get("why") == "page_claim_census"]
        # the slice's rows with THIS tree's page-claim rows in place of the saved ones (a claim row filed by `cv_page_claims` is this pass's, owner word / bracket): what
        # `claim_readout.build_page` reads to cut the ledger canvas. The ids of the new rows are the rebuilt log's (the claims name only their own rows).
        mine = []
        for r in log.rows(Q.CLAIMED_AREA, R.page(page), scope=R.Scope.SELF_AND_DESCENDANTS):
            if r.reader == "cv_page_claims":
                mine.append(dict(id=r.id, subject=r.subject.to_key(), quantity=r.quantity, value=r.value, reader=r.reader, frame=r.frame, score=r.score,
                                 detail=dict(r.detail or {}), basis=[]))
        rows_out = {"observations": [o for o in rows["observations"] if not (o.get("quantity") == "claimed_area" and o.get("reader") == "cv_page_claims")] + mine,
                    "abstentions": [a for a in rows["abstentions"] if not (a.get("quantity") == "claimed_area" and a.get("reader") == "cv_page_claims")],
                    "verdicts": rows.get("verdicts", [])}
        return dict(claims=out, words=words, census=census, binary=pws.page.binary, rows=rows_out)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env", nargs="*", default=[])
    a = ap.parse_args()
    env = dict(e.split("=", 1) for e in a.env)
    got = replay(a.plate, a.slice, a.page, env)
    got.pop("binary")
    got.pop("rows")
    pathlib.Path(a.out).write_text(json.dumps(got, indent=1, default=str))
    print("claims", len(got["claims"]))


if __name__ == "__main__":
    main()
