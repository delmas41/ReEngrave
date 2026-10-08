"""lane-staccato-unread (ROADMAP 2.59 follow-up): GATHER+ADJUDICATE replay of a saved record, through `dot_role` only,
and a per-dot table of what the reader said plus the geometry of every head in reach of the dot.

    python3 staccato_unread_replay.py REC.json OUT.json [--pages 12,13]   (no --pages = the whole document)

READ ONLY on the record.  Observations/abstentions are never pooled (`record_io`), so they are streamed with ijson
exactly as `mark_identity_rebuild.load_pages_streaming` does.
Per dot: its role verdict (outcome/value/reason), canonical box, page box, space, and for every head of its own cell
and of the staves just above/below: key, class, canonical box, not-a-notehead verdict, owner verdict.
"""
import argparse, json, sys, time, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import mark_identity_rebuild as M                                       # noqa: E402
from tools.omr.staged import adjudicate                                 # noqa: E402
from tools.omr.staged import adjudicators                               # noqa: E402,F401
from tools.omr.staged.record import Kind, Q, Scope, Subject            # noqa: E402


def _v(v):
    if v is None:
        return None
    return {"o": getattr(v.outcome, "value", str(v.outcome)),
            "v": v.value if isinstance(v.value, (str, int, float, bool, type(None))) else str(v.value)[:60],
            "r": v.reason,
            "d": {k: (x if isinstance(x, (str, int, float, bool, type(None))) else str(x)[:60])
                  for k, x in (v.detail or {}).items()
                  if k in ("head", "owner", "articulation", "head_owned_elsewhere", "head_refused")}}


def _box(log, sub):
    r = log.rows(Q.GLYPH_BOX, sub)
    if not r:
        return None, None, None
    val = r[-1].value
    pb = (r[-1].detail or {}).get("bbox_page_px")
    cls = val[0] if isinstance(val, (list, tuple)) and val else None
    xywh = [float(x) for x in val[1:5]] if isinstance(val, (list, tuple)) and len(val) >= 5 else None
    return cls, xywh, pb


def extract(log):
    dots = {}
    for sub in log.subjects(Kind.GLYPH):
        if not log.rows(Q.AUG_DOT, sub):
            continue
        key = sub.to_key()
        cls, xywh, pb = _box(log, sub)
        cell = sub.at(Kind.CELL)
        sp = None
        for r in log.rows(Q.CELL_STAFF_SPACE, cell, scope=Scope.SELF_AND_ANCESTORS):
            sp = float(r.value)
        dr = (log.rows(Q.AUG_DOT, sub)[-1].detail or {})
        heads = []
        for ds in (0, -1, 1):
            if cell.staff + ds < 0:
                continue
            c = Subject(Kind.CELL, page=cell.page, system=cell.system, staff=cell.staff + ds, cell=cell.cell)
            boxes = {r.subject.to_key(): r for r in log.rows(Q.GLYPH_BOX, c, scope=Scope.SELF_AND_DESCENDANTS)}
            for r in log.rows(Q.NOTEHEAD_CLASS, c, scope=Scope.SELF_AND_DESCENDANTS):
                br = boxes.get(r.subject.to_key())
                if br is None:
                    continue
                hv = br.value
                hxy = [float(x) for x in hv[1:5]] if isinstance(hv, (list, tuple)) and len(hv) >= 5 else None
                heads.append({"k": r.subject.to_key(), "ds": ds, "cls": hv[0], "box": hxy,
                              "pb": (br.detail or {}).get("bbox_page_px"),
                              "np": _v(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, r.subject)),
                              "own": _v(log.verdict(Q.GLYPH_OWNER, r.subject))})
        dots[key] = {"cls": cls, "box": xywh, "pb": pb, "space": sp, "det_role": dr.get("detector_role"),
                     "role": _v(log.verdict(Q.DOT_ROLE, sub)), "own": _v(log.verdict(Q.GLYPH_OWNER, sub)),
                     "heads": heads}
    inst, lines = {}, {}
    for sub in log.subjects(Kind.STAFF):
        v = log.verdict(Q.INSTRUMENT, sub)
        if v is not None and v.outcome.value == "decided" and isinstance(v.value, dict):
            inst[sub.to_key()] = v.value.get("name")
        rr = log.rows(Q.STAFF_LINES, sub)
        if rr:
            lines[sub.to_key()] = list(rr[-1].value)
    return dots, inst, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record"); ap.add_argument("out")
    ap.add_argument("--pages", default=None)
    a = ap.parse_args()
    pages = set(int(x) for x in a.pages.split(",")) if a.pages else None
    t0 = time.time()
    if pages is None:
        import ijson
        obs, ab = [], []
        with open(a.record, "rb") as f:
            for kind, bucket in (("observations", obs), ("abstentions", ab)):
                f.seek(0)
                for row in ijson.items(f, f"record.{kind}.item", use_float=True):
                    bucket.append(row)
        rec = {"observations": obs, "abstentions": ab, "verdicts": []}
    else:
        rec = M.load_pages_streaming(a.record, pages)["record"]
    log = M.rebuild(rec, pages)
    print(f"rebuilt {len(rec['observations'])} obs in {time.time() - t0:.0f}s", flush=True)
    t1 = time.time()
    order = adjudicate.ORDER[:adjudicate.ORDER.index(Q.DOT_ROLE) + 1]
    adjudicate.run(log, order=order)
    print(f"adjudicate through dot_role {time.time() - t1:.0f}s", flush=True)
    dots, inst, lines = extract(log)
    Path(a.out).write_text(json.dumps({"flag_dot_follows_note": os.environ.get("OMR_DOT_FOLLOWS_NOTE"),
                                       "dots": dots, "inst": inst, "staff_lines": lines}))
    print("wrote", a.out, len(dots), "dots", flush=True)


if __name__ == "__main__":
    main()
