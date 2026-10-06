"""lane-slur-not-ledger (Sean 2026-10-06): out-of-sample replay on the 10-06 night-combined records. READ ONLY, no gather.
For every far head with a recorded far-head row/abstention, replay the note-first reader on the gather-frame raster
with `READER_KEYWORDS['slur_not_ledger']` OFF (= what the record holds -- the control that can fail: OFF must give the
recorded position) and ON; and the ownership-by-ledgers witness (`far_head_owner.owner_by_ledgers`) both ways.

  python3 slur_not_ledger_oos.py <scratch dir with x/*.json> <doc> <out.json>
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_measured as OM
import overnight_1004_report as R
from tools.omr.annotate import far_head_reader as FH, far_head_owner as FO

NEWTAG = "20261006-night-combined"


def staves_of(data, page):
    sb = {s: b for s, c, b in data["boxes"] if c == "staff" and R.page_of(s) == page}
    out = []
    for key, lines in data["staff_lines"].items():
        if key.startswith("staff/%d/" % page):
            parts = key.split("/")
            b = [bb for s, bb in sb.items() if s.split("/")[1:4] == parts[1:4]]
            if b:
                out.append(dict(key=key, lines=lines, x0=b[0][0], x1=b[0][2]))
    return out


def box_backed(row):
    return (row["on"]["pos"] != row["off"]["pos"]) or any("arc_box" in x["why"] for x in (row["on"]["refused"] or []))


def run(src, doc, out, prior=None):
    """`prior`: an earlier run of this driver under a SHAPE-ONLY rule (a superset of the refusals the box-backed rule can
    make): only the heads it refused a box-backed rung on are replayed again; every other head's ON arm is its OFF arm."""
    data = json.load(open(src))
    old = {r["subject"]: r for r in json.load(open(prior))["rows"]} if prior else None
    G = data["glyphs"]
    rep = OM.CachedReplay(doc, data)
    far = {s: g for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g and "fh" in g}
    by_page = collections.defaultdict(list)
    for s in far:
        by_page[R.page_of(s)].append(s)
    rows, st = [], collections.Counter()
    for page in sorted(by_page):
        staves = staves_of(data, page)
        for s in by_page[page]:
            g = far[s]
            ctx = rep.adopt_for(page, g["fh"]["shape_source"])
            key = "staff/" + "/".join(s.split("/")[1:4])
            gl = data["staff_lines"][key]
            cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
            rec = int(round(float(g["fh"]["value"])))
            if old is not None and s in old and not box_backed(old[s]):
                o = old[s]
                st["repro" if o["off"]["pos"] == rec else "mismatch"] += 1
                st["carried"] += 1
                rows.append(dict(o, on=dict(o["off"]), repro=(o["off"]["pos"] == rec)))
                continue
            res = {}
            for arm in ("off", "on"):
                FH.READER_KEYWORDS["slur_not_ledger"] = (arm == "on")
                r = ctx.read(s, tuple(g["box"]), cls, gl)
                nf = (r.get("detail") or {}).get("note_first") or {}
                res[arm] = dict(pos=r["pos"], reason=r["reason"], refused=nf.get("refused_rungs"),
                                between=nf.get("between"), k=nf.get("k"), line_y=nf.get("line_y"),
                                edge_y=(r.get("detail") or {}).get("edge_y"), owner=None)
            # the ownership witness (4 more reads) only where the rule touched the head's own-staff read: a rung it
            # refused or a changed position. A refusal that only the NEIGHBOUR's read would make is NOT measured here.
            touched = (res["off"]["pos"] != res["on"]["pos"]) or any(
                "not_straight" in x["why"] or "arc_box" in x["why"] for x in (res["on"]["refused"] or []))
            if touched and any(x["key"] == key for x in staves):
                for arm in ("off", "on"):
                    FH.READER_KEYWORDS["slur_not_ledger"] = (arm == "on")
                    o = FO.owner_by_ledgers(ctx, s, tuple(g["box"]), cls, key, staves)
                    res[arm]["owner"] = dict(owner=o["owner"], word=o["word"], own=key,
                                             cands={k: dict(fits=v["fits"], pos=v["pos"], reason=v["reason"]) for k, v in o["candidates"].items()})
            st["touched"] += bool(touched)
            FH.READER_KEYWORDS["slur_not_ledger"] = True
            ok = res["off"]["pos"] == rec
            st["repro" if ok else "mismatch"] += 1
            rows.append(dict(subject=s, page=page, doc=doc, recorded=rec, repro=ok,
                             geo=g["geo_rounded"] if g.get("geo_rounded") is not None else g["geo"],
                             box=g["box"], cls=cls, off=res["off"], on=res["on"]))
        print(doc, "page", page, dict(st), flush=True)
        rep.gray.pop(page, None)
    Path(out).write_text(json.dumps(dict(doc=doc, stats=dict(st), rows=rows), default=float))
    print("wrote", out, dict(st))


if __name__ == "__main__":
    S = Path(sys.argv[1]); doc = sys.argv[2]
    run(S / "x" / f"{doc}-{NEWTAG}.json", doc, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
