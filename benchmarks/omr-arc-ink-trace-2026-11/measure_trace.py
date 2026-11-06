"""ROADMAP 2.272 step 1: how far each arc's trace stops short of its ink, and what stopped the walk.

    python3 benchmarks/omr-arc-ink-trace-2026-11/measure_trace.py ON.record.json [OFF.record.json]

ON is a gather with OMR_ARC_INK_TRACE=1 (its `Q.SYSTEM_ARC` rows carry `ink_trace`: per piece the box trace's x extent, and per end the columns added,
where and why the walk stopped, and what it crossed). OFF (optional) is the same pages with the flag off: curves are counted by piece group, so the
fold (more than one piece -> one curve) is read as OFF curves vs ON curves.
"""
import collections
import json
import sys

from tools.omr.staged.record_io import load_record


def rows(path):
    rec = load_record(path)
    r = rec.get("record", rec)
    return [o for o in r["observations"] if o["quantity"] == "system_arc"]


def main():
    on = rows(sys.argv[1])
    off = rows(sys.argv[2]) if len(sys.argv) > 2 else None
    n_curves = len(on)
    short = 0
    stops = collections.Counter()
    stops_short = collections.Counter()
    crossed = collections.Counter()
    added_sp = []
    folds = 0
    for o in on:
        d = o["detail"]
        sp = float(d.get("space_page_px") or 15.0)
        it = d.get("ink_trace") or []
        if len(d.get("pieces") or []) > 1:
            folds += 1
        curve_short = False
        for m in it:
            for side in ("left", "right"):
                e = m.get(side)
                if not e:
                    continue
                stops[e["stop"]] += 1
                a = e["added_px"] / sp
                if a >= 0.5:
                    curve_short = True
                    stops_short[e["stop"]] += 1
                    added_sp.append(round(a, 1))
                for k, v in (e.get("crossed") or {}).items():
                    crossed[k] += 1
        short += curve_short
    print("curves:", n_curves, "curves with an end walked >= 0.5 sp further:", short, "curves of >1 piece:", folds)
    print("stop reason, every end:", dict(stops))
    print("stop reason, ends walked >= 0.5 sp:", dict(stops_short))
    print("ends walked >= 0.5 sp: n", len(added_sp), "median", sorted(added_sp)[len(added_sp) // 2] if added_sp else None, "max", max(added_sp) if added_sp else None)
    print("bridged columns' obstacle (curves-ends touching):", dict(crossed))
    if off is not None:
        print("OFF curves:", len(off), "ON curves:", n_curves)
        op = sum(len(o["detail"].get("pieces") or []) for o in off)
        print("OFF pieces in curves:", op)


if __name__ == "__main__":
    main()
