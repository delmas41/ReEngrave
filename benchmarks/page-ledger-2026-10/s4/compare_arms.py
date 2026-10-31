"""2.240 step 3: what the step-3 GATHER changes (ledger gap look honours the filter, flat traces are not arc ink, held pages' owners filed
after their far-head readings) do to the RECORDED page owners -- two gathered records of the same pages, rows as filed (no re-derivation).

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/compare_arms.py BEFORE.record.json AFTER.record.json [--focus glyph/4/1/1/3/5]
"""
import argparse
import collections
import json

from tools.omr.staged import claim_readout as CR
from tools.omr.staged import page_owner as PO


def rows(rec):
    src = CR.resolve_source(rec)
    pages = CR.slice_pages(src)
    r = CR.read_rows(src, pages)
    own, led, arcs = {}, collections.defaultdict(list), {}
    for kind in ("observations", "abstentions"):
        for o in r[kind]:
            q = o.get("quantity")
            if q == "page_mark_owner":
                d = o.get("detail") or {}
                for m in d.get("members") or [o["subject"]]:
                    own[m] = (("abstain" if kind == "abstentions" else d.get("status")), o.get("value"),
                              (o.get("reason") if kind == "abstentions" else d.get("reason")), d.get("family"))
            elif q == "far_head_owner_ledger":
                led[o["subject"]].append(dict(o.get("detail") or {}, fits=(kind == "observations"), pos=o.get("value")))
            elif q == "system_arc" and kind == "observations":
                d = o.get("detail") or {}
                arcs[o["subject"]] = (d.get("trace") or [], d.get("space_page_px"))
    return pages, own, led, arcs


def arc_drops(led):
    """{(glyph, candidate, y)} of every rung the owner's filter dropped as `arc_ink`."""
    return {(g, d.get("candidate"), round(float(y), 1)) for g, rs in led.items() for d in rs
            for y, w in (d.get("not_ledger_dropped") or []) if w == "arc_ink"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--focus", action="append", default=[])
    a = ap.parse_args()
    pb, ob, lb, _ab = rows(a.before)
    pa, oa, la, _aa = rows(a.after)
    print("pages before %s after %s" % (pb, pa))
    heads = [k for k, v in ob.items() if v[3] == "head"]
    ch = [(k, ob[k], oa.get(k)) for k in heads if oa.get(k) and ob[k][:2] != oa[k][:2]]
    print("head boxes with an owner: before %d after %d; owner/status changed %d" % (len(heads), sum(1 for k in oa if oa[k][3] == "head"), len(ch)))
    print("  changes by (before reason -> after reason):", dict(collections.Counter("%s:%s -> %s:%s" % (b[0], b[2], c[0], c[2]) for _k, b, c in ch)))
    for k, b, c in ch[:40]:
        print("   ", k, b[:3], "->", c[:3])
    db, da = arc_drops(lb), arc_drops(la)
    kept = sorted(db - da)
    print("rungs dropped as arc_ink: before %d, after %d; KEPT now (their only 'arc' is a flat trace) %d" % (len(db), len(da), len(kept)))
    for p in kept[:30]:
        print("    ", p)
    print("owner-ledger readings that changed fits/pos:", sum(1 for g in lb for x, y in zip(lb[g], la.get(g, []))
                                                           if (x["fits"], x["pos"]) != (y["fits"], y["pos"])))
    for f in a.focus:
        for arm, own, led in (("before", ob, lb), ("after", oa, la)):
            print(arm, f, own.get(f))
            for d in led.get(f, []):
                print("     ", {k: d.get(k) for k in ("candidate", "fits", "pos", "ledger_reason", "not_ledger_dropped", "rungs_between", "line_y",
                                                   "line_how")})


if __name__ == "__main__":
    main()
