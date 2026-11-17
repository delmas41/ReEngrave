"""2.305 r9 -- replay ONE gathered record (gathered with both arc flags ON) through ADJUDICATE..EXPORT on THIS tree (cwd), in the flag
state of the environment, and write (1) the funnel facts file judge.py reads and (2) every arc span EXPORT marked, with the path that made it.

    cd TREE && OMR_PAGE_ARC_WRITE=1 OMR_ARC_MEETING_AT_HEAD=1 python3 .../r9/replay.py GATHERED.record.json OUTPREFIX [--no-readjudicate]

Paths (read from the exporter's own calls, never re-derived):
  old_box      `_legacy._paired_spans` over the detector arc boxes left in the cells (the OLD box path)
  anchored     `_anchored_slur_spans` (2.2xx slur anchoring over the same boxes)
  page_arc     a page-ink run the page pass bound and wrote (`page_arc/<row>` in `_page_bound_slur_spans`; a tie pair `pa_ties`)
  curve        a 2.223 detector-curve binding (`_page_bound_slur_spans`, any other curve key)
  across       `_across_system_spans`
  record_tie   `_record_tie_spans` over a `Q.TIE_PAIR` pair that no page-arc run wrote (the old tie pairing of boxes)
Reads only; decides nothing.
"""
from __future__ import annotations

import gc
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "benchmarks/note-loss-funnel-2026-11"))

from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

SPANS = []
CTX = {}


def _g(det):
    return str(det.get("glyph")) if isinstance(det, dict) else None


OLD_OFF = "--old-off" in sys.argv      # MEASUREMENT ONLY: the old box slurs and the old record tie pairs write nothing (the page pass alone)


def _wrap_paired(orig):
    def f(*a, **k):
        out = orig(*a, **k)
        if OLD_OFF:
            return []
        for s in out:
            SPANS.append(dict(src=CTX.get("old_kind_src", "old_box"), kind=CTX.get("kind"), a=_g(s[2]), b=_g(s[3])))
        return out
    return f


def _wrap_anchored(orig):
    def f(*a, **k):
        out = orig(*a, **k)
        if OLD_OFF:
            return []
        for s in out:
            SPANS.append(dict(src="anchored", kind="slur", a=_g(s[2]), b=_g(s[3])))
        return out
    return f


def _wrap_bound(orig):
    def f(measures, bound, *a, **k):
        out = orig(measures, bound, *a, **k)
        for s in out:
            ga, gb = _g(s[2]), _g(s[3])
            src = "curve"
            for key, c in bound.items():
                if {c["start"], c["stop"]} == {ga, gb}:
                    src = "page_arc" if str(key).startswith("page_arc/") else "curve"
                    SPANS.append(dict(src=src, kind="slur", a=ga, b=gb, key=str(key)))
                    break
            else:
                SPANS.append(dict(src="page_bound?", kind="slur", a=ga, b=gb))
        return out
    return f


def _wrap_across(orig):
    def f(*a, **k):
        xs, xt = orig(*a, **k)
        for s in xs:
            SPANS.append(dict(src="across", kind="slur", a=_g(s[2]), b=_g(s[3])))
        for s in xt:
            SPANS.append(dict(src="across", kind="tie", a=_g(s[2]), b=_g(s[3])))
        return xs, xt
    return f


def _wrap_ties(orig):
    def f(measures, record_ties, *a, **k):
        out = orig(measures, record_ties, *a, **k)
        pa = CTX.get("pa_tie_keys") or set()
        if OLD_OFF:
            ct = {frozenset((b["curve"]["start"], b["curve"]["stop"])) for b in (CTX.get("arc_boxes") or ())
                  if b.get("curve") and b["curve"].get("kind") == "tie" and b["curve"].get("start") and b["curve"].get("stop")}
            out = [s for s in out if (_g(s[2]), _g(s[3])) in pa or (_g(s[3]), _g(s[2])) in pa or frozenset((_g(s[2]), _g(s[3]))) in ct]
        for s in out:
            ga, gb = _g(s[2]), _g(s[3])
            SPANS.append(dict(src="page_arc" if (ga, gb) in pa or (gb, ga) in pa else "record_tie", kind="tie", a=ga, b=gb))
        return out
    return f


def _wrap_plan(orig):
    def f(rec):
        p = orig(rec)
        if p is not None:
            CTX["pa_tie_keys"] = {(str(r["start"]), str(r["stop"])) for r in p["written"] if r["kind"] == "tie"}
            CTX["plan_counts"] = dict(p["counts"])
        return p
    return f


def _wrap_bykind(orig):
    def f(*a, **k):
        by_kind, merged = orig(*a, **k)
        CTX["kinds_present"] = sorted(by_kind)
        return by_kind, merged
    return f


CONT = []


def _wrap_rule(orig):
    from tools.omr.staged import arc_claim as AC

    def f(ex, ey, sgn, heads, sp, side, ok, by_height, others, unread, meet_back):
        out = orig(ex, ey, sgn, heads, sp, side, ok, by_height, others, unread, meet_back)
        if out.get("unbound") == "continues_in_another_curve":
            cands = sorted((dict(key=h["key"], cx=h["cx"], cy=h["cy"], w=h["w"], h=h["h"], d_edge=AC._to_head(h, ex, ey),
                                 d_centre=abs(h["cx"] - ex) + abs(h["cy"] - ey)) for h in heads if ok(h["key"])), key=lambda h: h["d_edge"])
            CONT.append(dict(ex=ex, ey=ey, sgn=sgn, sp=sp, side=side, others=list(others or ()), closest=cands[:2]))
        return out
    return f


def install():
    from tools.omr.staged import arc_claim as AC
    AC._bind_end_by_rule = _wrap_rule(AC._bind_end_by_rule)
    E._legacy._paired_spans = _wrap_paired(E._legacy._paired_spans)
    E._anchored_slur_spans = _wrap_anchored(E._anchored_slur_spans)
    E._page_bound_slur_spans = _wrap_bound(E._page_bound_slur_spans)
    E._across_system_spans = _wrap_across(E._across_system_spans)
    E._record_tie_spans = _wrap_ties(E._record_tie_spans)
    E._page_arc_plan = _wrap_plan(E._page_arc_plan)
    orig_place = E._place_arcs

    def place(rec, runs):
        out = orig_place(rec, runs)
        from tools.omr.staged.record import Q
        plan = E._page_arc_plan(rec)
        boxes = []
        for o in rec.obs_of(Q.ARC_BOX):
            sub = o["subject"]
            kv = rec.verdict(Q.ARC_KIND, sub) or {}
            anv = rec.verdict(Q.ARC_IS_NOT_AN_ARC, sub) or {}
            pb = ((kv.get("detail") or {}).get("page_binding") or ((kv.get("detail") or {}).get("grammar") or {}).get("page_binding") or {})
            boxes.append(dict(sub=sub, box=E._page_box_of(o), kind=kv.get("value") if kv.get("outcome") == "decided" else None,
                              kind_reason=kv.get("reason"), not_arc=anv.get("value") if anv.get("outcome") == "decided" else None,
                              owner=rec.value(Q.ARC_OWNER, sub), replaced=bool(plan and sub in plan["replaced"]),
                              curve=dict(kind=pb.get("kind"), start=pb.get("start"), stop=pb.get("stop"), why=pb.get("why"), curve=pb.get("curve"),
                                         left={k: v for k, v in (pb.get("left") or {}).items() if k in ("head", "unbound", "edge")},
                                         right={k: v for k, v in (pb.get("right") or {}).items() if k in ("head", "unbound", "edge")}) if pb else None))
        CTX["arc_boxes"] = boxes
        if plan is not None:
            CTX["runs"] = [{k: v for k, v in r.items() if k in ("row", "ordinal", "status", "why", "kind", "start", "stop", "witnesses", "witness_by_ink",
                                                               "home", "left", "right", "unbound", "edge", "kind_unread", "piece", "x_range")}
                           for r in plan["runs"]]
        return out
    E._place_arcs = place


def main():
    path, outp = sys.argv[1], sys.argv[2]
    install()
    res = load_record(path)
    rec = res["record"] if "record" in res else res
    if "--no-readjudicate" not in sys.argv:
        log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec["abstentions"], "verdicts": [],
                                    "format": rec.get("format")})
        RR.run_stages(log)
        res = {"record": log.to_json(), "summary": log.summary()}
        del log
        gc.collect()
    # the funnel's own facts (extract.py), from this replayed record
    import extract as X
    tmp = outp + ".record.json"
    with open(tmp, "w") as fh:
        json.dump(res, fh, default=str)
    SPANS.clear()
    X.main(tmp, outp + ".facts.json")
    # a record tie pair whose two notes a 2.223 curve binding named as a tie is that curve's (ink-traced), not the old box pairing's
    ctie = {frozenset((b["curve"]["start"], b["curve"]["stop"])) for b in (CTX.get("arc_boxes") or ())
            if b.get("curve") and b["curve"].get("kind") == "tie" and b["curve"].get("start") and b["curve"].get("stop")}
    for s in SPANS:
        if s["src"] == "record_tie" and frozenset((s["a"], s["b"])) in ctie:
            s["src"] = "curve_tie"
    with open(outp + ".spans.json", "w") as fh:
        json.dump(dict(spans=SPANS, plan_counts=CTX.get("plan_counts"), arc_boxes=CTX.get("arc_boxes"), runs=CTX.get("runs"), continues=CONT, flags={k: v for k, v in os.environ.items() if k.startswith("OMR_")}),
                  fh, default=str)
    if "--keep-record" not in sys.argv:
        os.remove(tmp)
    print("spans", len(SPANS), {s: sum(1 for x in SPANS if x["src"] == s) for s in sorted({x["src"] for x in SPANS})})


if __name__ == "__main__":
    main()
