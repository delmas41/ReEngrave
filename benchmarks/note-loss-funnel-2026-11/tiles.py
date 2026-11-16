"""ROADMAP 2.311 -- THE FUNNEL AGAINST SEAN'S NOTE-LEVEL TILE ANSWERS, on the pages a record holds.

    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/tiles.py --doc brahms FACTS.json [--json OUT]

Truth: every tile in `benchmarks/acceptance/judged-tiles.json` (the committed index `tools.omr.staged.judged build`
writes from every answers file) of this plate whose answer is a note value, a rest value, or "not a note" -- Sean's
words kept verbatim -- on a page the record holds. Matched BY PLACE, never by glyph key:
  * `mark`   -- the tile carries a mark-sized page box (its `position.page_box`, or a `page_box` no wider than 120 px:
               `judged.with_derived_positions`); a record box is the mark when the two overlap (`judged.boxes_overlap`);
  * `window` -- older galleries kept only the tile WINDOW; the mark is taken to be the head/rest box that contains the
               window's centre (OUR assumption that the tile was centred on its mark -- reported apart).
For a NOTE answer the bucket is the funnel's (A..G, W; see funnel.py), and a written note's value (type + dots, in
quarters) is compared with Sean's. For "not a note" the question is whether a note is written on that mark, and what
else the record already says about that ink (another detector class on it; ADJUDICATE's refusal reason).
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from tools.omr.staged import judged as J

import funnel as F  # noqa: E402  (same directory)

BEATS = {"whole": 4.0, "half": 2.0, "quarter": 1.0, "eighth": 0.5, "16th": 0.25, "32nd": 0.125, "64th": 0.0625, "breve": 8.0}
KINDS = ("not_a_note", "duration", "rest")


def written_beats(h: dict) -> float | None:
    b = BEATS.get(h.get("type"))
    if b is None:
        return None
    nd = len((h.get("sub") or {}).get("dot") or [])
    return b * (2 - 0.5 ** nd)


def centre_in(c, b, slack=4.0):
    return b[0] - slack <= c[0] <= b[2] + slack and b[1] - slack <= c[1] <= b[3] + slack


def tiles_for(doc: str, pages: set) -> list:
    d = J.with_derived_positions(json.load(open("benchmarks/acceptance/judged-tiles.json")))
    out = []
    for r in d["tiles"]:
        if r.get("doc") != doc or r["answer_kind"] not in KINDS or r.get("followup"):
            continue
        pl, bx = J.row_place(r), J.row_box(r)
        sub = r.get("subject") or ""
        pg = int(sub.split("/")[1]) if sub.startswith("glyph/") else (pl[0] if pl else None)
        if pg not in pages:
            continue
        if pl and bx:
            out.append(dict(r, _page=pg, _how="mark", _box=bx))
        elif isinstance(r.get("page_box"), list) and len(r["page_box"]) == 4:
            out.append(dict(r, _page=pg, _how="window", _box=[float(x) for x in r["page_box"]]))
        else:
            out.append(dict(r, _page=pg, _how="none", _box=None))
    return out


def run(facts: dict, doc: str) -> dict:
    pages = {g["page"] for g in facts["glyphs"].values()}
    glyphs_by_page = collections.defaultdict(list)
    for k, g in facts["glyphs"].items():
        glyphs_by_page[g["page"]].append((k, g))
    written_by_page = collections.defaultdict(list)
    for h in facts["written"]:
        written_by_page[h["page"]].append(h)
    rows = []
    for t in tiles_for(doc, pages):
        row = dict(item=t["item"], tile=t["tile"], page=t["_page"], how=t["_how"], answer=t["answer"],
                   kind=t["answer_kind"], value=t["value"], box=t["_box"])
        if t["_how"] == "none":
            row.update(bucket="unplaced")
            rows.append(row)
            continue
        gl = glyphs_by_page[t["_page"]]
        if t["_how"] == "mark":
            copies = [(k, g) for k, g in gl if J.boxes_overlap(g["box"], t["_box"])[0]]
            mark = t["_box"]
        else:
            c = ((t["_box"][0] + t["_box"][2]) / 2, (t["_box"][1] + t["_box"][3]) / 2)
            hr = [(k, g) for k, g in gl if (g["head"] or g["rest"]) and centre_in(c, g["box"])]
            if not hr:
                row.update(bucket="unplaced", why="no head/rest box at the window centre")
                rows.append(row)
                continue
            mark = min(hr, key=lambda kg: (kg[1]["box"][2] - kg[1]["box"][0]) * (kg[1]["box"][3] - kg[1]["box"][1]))[1]["box"]
            copies = [(k, g) for k, g in gl if J.boxes_overlap(g["box"], mark)[0]]
        wr = [h for h in written_by_page[t["_page"]] if J.boxes_overlap(h["box"], mark)[0]]
        wn = [h for h in wr if h["kind"] == "note"]
        wrest = [h for h in wr if h["kind"] == "rest"]
        row["copies"] = [(k, g["cls"], g["fate"]) for k, g in copies]
        if t["answer_kind"] == "not_a_note":
            row["bucket"] = "fake_written" if wn else ("written_as_rest" if wrest else "not_written")
            if wn:
                row["written"] = [(h["type"], h["pitch"], h["blue"]) for h in wn]
            row["record_says"] = sorted({str(g["cls"]) for k, g in copies if not g["head"]})
            row["refusals"] = sorted({str(g["fate"]) for k, g in copies if g["fate"] and g["fate"] != "written"})
        elif t["answer_kind"] == "rest":
            if wrest:
                wb = written_beats(wrest[0])
                ok = t["value"] is not None and wb is not None and abs(wb - float(t["value"])) < 1e-6
                row.update(bucket="rest_written_right" if ok else "rest_written_wrong_value", written=wb)
            elif wn:
                row.update(bucket="rest_written_as_note")
            else:
                row.update(bucket="rest_not_written", refusals=sorted({str(g["fate"]) for k, g in copies}))
        else:
            if wn:
                h = min(wn, key=lambda h: abs(h["cx"] - (mark[0] + mark[2]) / 2) + abs(h["cy"] - (mark[1] + mark[3]) / 2))
                wb = written_beats(h)
                ok = t["value"] is not None and wb is not None and abs(wb - float(t["value"])) < 1e-6
                row.update(bucket="W", value_ok=ok, written=wb, blue=h["blue"], type=h["type"])
            elif wrest:
                row.update(bucket="note_written_as_rest")
            elif not copies:
                row.update(bucket="A", reason="no box")
            else:
                hc = [(k, g) for k, g in copies if g["head"]]
                if not hc:
                    row.update(bucket="B", reason="boxed as " + ",".join(sorted({str(g["cls"]) for k, g in copies})))
                else:
                    fated = [(k, g, g["fate"] or "no_fate") for k, g in hc]
                    use = [x for x in fated if x[2] not in F.TWIN] or fated
                    k, g, fate = max(use, key=lambda x: F.RANK[F.bucket_of_fate(x[2])])
                    dv = (g.get("v") or {}).get("duration") or {}
                    row.update(bucket=F.bucket_of_fate(fate), reason=fate, dur=(dv.get("outcome"), dv.get("reason")))
        rows.append(row)
    return dict(doc=doc, pages=sorted(pages), rows=rows)


def render(res: dict) -> str:
    rows = res["rows"]
    out = ["%s, pages %s: %d of Sean's note-level tile answers" % (res["doc"], res["pages"], len(rows))]
    for kind in KINDS:
        rk = [r for r in rows if r["kind"] == kind]
        if not rk:
            continue
        out.append(" %s (%d)" % (kind, len(rk)))
        for how in ("mark", "window", "none"):
            rh = [r for r in rk if r["how"] == how]
            if not rh:
                continue
            c = collections.Counter(r["bucket"] for r in rh)
            out.append("   placed by %-6s %3d: %s" % (how, len(rh), dict(c.most_common())))
            if kind == "duration":
                w = [r for r in rh if r["bucket"] == "W"]
                out.append("      written: value right %d, wrong %d (blue among wrong %d)" % (
                    sum(r["value_ok"] for r in w), sum(not r["value_ok"] for r in w), sum(r["blue"] for r in w if not r["value_ok"])))
                rc = collections.Counter(r.get("reason") for r in rh if r["bucket"] not in ("W", "unplaced"))
                if rc:
                    out.append("      lost by: %s" % dict(rc.most_common()))
            if kind == "not_a_note":
                fk = [r for r in rh if r["bucket"] == "fake_written"]
                out.append("      written as a note: %s" % [(r["item"], r["tile"], r["answer"][:30], r["record_says"]) for r in fk])
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(json.load(open(a.facts)), a.doc)
    print(render(res))
    if a.json:
        Path(a.json).write_text(json.dumps(res, default=str, indent=0))


if __name__ == "__main__":
    main()
