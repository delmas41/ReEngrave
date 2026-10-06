"""lane-local-staff-lines (Sean 2026-10-06): how often is the LOCAL five-line fit implausible, and what changes when the
five lines are fitted as a comb and searched window by window. READ ONLY on the extracted records, no gather.

For every far head of a 10-06 night-combined record and both candidate staves (its own and `neighbour_staff`): the
local five lines OLD (`local_staff_lines`, per-line +-0.5 sp darkest row; the global lines where it declines) and NEW
(`local_staff_lines_in_windows`); an implausible fit = not five lines, or any adjacent gap < 0.6 or > 1.4 of THAT staff's
own global spacing. Where either arm is flagged or the two differ, the reader and the owner witness are run both ways
(`READER_KEYWORDS['local_lines_in_window']` off = the record's own reader: the control, replay must equal the record).

  python3 local_lines_audit.py <scratch dir with x/*.json> <doc> <out.json>
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_measured as OM
import overnight_1004_report as R
import slur_not_ledger_oos as O
from tools.omr.annotate import far_head_reader as FH, far_head_owner as FO

TAG = "20261006-night-combined"
KW = "local_lines_in_window"


def fit_old(gray, gl, box):
    x0, _y0, x1, _y1 = box
    w = x1 - x0
    loc = FH.local_staff_lines(gray, list(gl), x0, x1, w if w > 0 else 20.0)
    return (list(loc), False) if loc is not None else (list(gl), True)      # (lines, declined -> global)


def fit_new(gray, gl, box):
    x0, _y0, x1, _y1 = box
    w = x1 - x0
    return FH.local_staff_lines_in_windows(gray, list(gl), x0, x1, w if w > 0 else 20.0)


def flag(lines, gl, declined=False):
    """None = plausible; else the word."""
    if lines is None:
        return "abstained"
    sp = (max(gl) - min(gl)) / 4.0
    if len(lines) != 5:
        return "not_five"
    if declined:
        return "declined"
    if not FH.gaps_plausible(lines, sp):
        return "implausible_gap"
    return None


def run(src, doc, out):
    data = json.load(open(src))
    G = data["glyphs"]
    rep = OM.CachedReplay(doc, data)
    far = {s: g for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g}
    by_page = collections.defaultdict(list)
    for s in far:
        by_page[R.page_of(s)].append(s)
    rows, st = [], collections.Counter()
    for page in sorted(by_page):
        staves = O.staves_of(data, page)
        gray = rep.gray_of(page)
        for s in by_page[page]:
            g = far[s]
            key = "staff/" + "/".join(s.split("/")[1:4])
            if key not in data["staff_lines"] or not any(x["key"] == key for x in staves):
                st["no_own_staff"] += 1
                continue
            box = tuple(g["box"])
            nb = FO.neighbour_staff(box, key, staves)
            cands = {key: data["staff_lines"][key]}
            if nb is not None:
                cands[nb["key"]] = nb["lines"]
            row = dict(subject=s, page=page, doc=doc, own=key, nb=None if nb is None else nb["key"], box=list(box),
                       recorded=R.decided_pos(g), rec_owner=(g.get("own") or {}).get("value"), cand={})
            touched = False
            for ck, gl in cands.items():
                ol, odecl = fit_old(gray, gl, box)
                nw = fit_new(gray, gl, box)
                of, nf = flag(ol, gl, odecl), flag(nw["lines"], gl)
                diff = (nw["lines"] is None) or any(abs(a - b) > 0.01 for a, b in zip(ol, nw["lines"]))
                touched |= bool(of) or diff
                st["fit_old_flagged"] += bool(of); st["fit_new_flagged"] += bool(nf); st["fits"] += 1
                st["old_" + str(of)] += 1; st["new_" + str(nf)] += 1
                st["fallback_lines"] += len(nw["fallback"])
                row["cand"][ck] = dict(old=ol, old_flag=of, new=nw["lines"], new_flag=nf, fallback=nw["fallback"],
                                       why=nw.get("why"), gl=list(gl))
            st["far_heads"] += 1
            row["touched"] = bool(touched)
            if touched and g.get("fh"):
                ctx = rep.adopt_for(page, g["fh"]["shape_source"])
                cls = next((c for (ss, c, b) in rep.boxes_by_page[page] if ss == s), g.get("cls"))
                res = {}
                for arm in ("old", "new"):
                    FH.READER_KEYWORDS[KW] = (arm == "new")
                    r = ctx.read(s, box, cls, data["staff_lines"][key])
                    o = FO.owner_by_ledgers(ctx, s, box, cls, key, staves)
                    res[arm] = dict(pos=r["pos"], reason=r["reason"], owner=o["owner"], word=o["word"],
                                    fits={k: (v["fits"], v["pos"], v["reason"]) for k, v in o["candidates"].items()})
                FH.READER_KEYWORDS[KW] = True
                row.update(old=res["old"], new=res["new"])
                rec = int(round(float(g["fh"]["value"]))) if g["fh"].get("value") is not None else None
                row["repro"] = (res["old"]["pos"] == rec)
                st["replayed"] += 1; st["repro" if row["repro"] else "mismatch"] += 1
                st["pos_changed"] += (res["old"]["pos"] != res["new"]["pos"])
                st["owner_changed"] += ((res["old"]["owner"], res["old"]["word"]) != (res["new"]["owner"], res["new"]["word"]))
            rows.append(row)
        print(doc, "page", page, dict(st), flush=True)
        rep.gray.pop(page, None)
    Path(out).write_text(json.dumps(dict(doc=doc, stats=dict(st), rows=rows), default=float))
    print("wrote", out, dict(st))


if __name__ == "__main__":
    S = Path(sys.argv[1]); doc = sys.argv[2]
    run(S / "x" / f"{doc}-{TAG}.json", doc, sys.argv[3])
