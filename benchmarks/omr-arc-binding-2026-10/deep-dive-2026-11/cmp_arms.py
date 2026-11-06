"""ARC CURVE-ONLY TEST (throwaway; branch arc-curve-only-test). Fate ledger of two arms side by side, identity = the OFF arm's curve/piece rows.

    python3 cmp_arms.py PLATE OFF.arcs.json OFF.musicxml ON.arcs.json ON.musicxml [--out cmp.json]

Both arms go through `ledger_cmp.py` (the deep dive's `ledger.py` + (a) the over-joined set of the OFF arm applied to both, so rows match one to one,
(b) an END CHECK applied to both: a row that is 'written' but whose bound head stands more than 3 sp from the traced end of the curve is re-labelled
'written_far_end' (indicative: against our own trace, not truth)). Prints per-page fates, the dropped-by-rule table and the NEW writes.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger_cmp as LC      # noqa: E402

END_SP = 3.0


def adj(r):
    f = r["fate"]
    if f == "written" and r.get("ext_gap") is not None and r["ext_gap"] > END_SP:
        return "written_far_end"
    return f


def run(dump, xml):
    return LC.build(dump, xml)


def table(res, pages, label):
    rows = [r for r in res["rows"] if r["fate"] != "not_an_arc"]
    n = max(1, len(pages))
    c = collections.Counter(adj(r) for r in rows)
    raw = collections.Counter(r["fate"] for r in rows)
    out = ["%s: real arcs %d (%.1f/page)" % (label, len(rows), len(rows) / n)]
    for f in ("written", "written_far_end", "written_as_slur", "written_as_tie", "wrong_note", "two_arcs", "dropped"):
        out.append("   %-16s %4d  %.1f/page   (raw ledger label: %d)" % (f, c[f], c[f] / n, raw[f] if f != "written_far_end" else raw["written"] - c["written"] - 0))
    lost = collections.Counter((r.get("lost_at"), r.get("lost_rule")) for r in rows if r["fate"] == "dropped")
    out.append("   dropped by first rule:")
    for (a, rule), k in lost.most_common(14):
        out.append("      %s %-80s %4d" % (a, str(rule)[:80], k))
    return "\n".join(out), c


def main():
    plate, offa, offx, ona, onx = sys.argv[1:6]
    off_d, on_d = json.load(open(offa)), json.load(open(ona))
    off_x, on_x = pathlib.Path(offx).read_text(), pathlib.Path(onx).read_text()
    LC.FORCED.clear()
    r0 = run(off_d, off_x)
    why_of = {}
    for v in off_d["verdicts"]:
        if v["quantity"] == "arc_kind":
            why_of[v["subject"]] = (((v.get("detail") or {}).get("page_binding")) or {}).get("why")
    for o in off_d["system_arc"]:
        pcs = o["detail"].get("pieces") or []
        if len(pcs) > 1 and any(why_of.get(q) == "joined_not_at_a_barline" for q in pcs):
            LC.FORCED.update(pcs)      # the ledger's own `overjoined` set is empty (its test is on the curve id); this is the OFF arm's rule, applied to both
    r1 = run(on_d, on_x)
    r0 = run(off_d, off_x)           # again, with the same forced set (OFF is unchanged by it; kept for symmetry)
    pages = off_d["pages"]
    t0, c0 = table(r0, pages, "OFF (INK_TRACE on, bypass off)")
    t1, c1 = table(r1, pages, "ON  (INK_TRACE on, bypass on)")
    print("PLATE", plate, "pages", pages)
    print(t0)
    print(t1)
    k0 = {tuple(r["pieces"]): r for r in r0["rows"]}
    k1 = {tuple(r["pieces"]): r for r in r1["rows"]}
    print("rows OFF %d ON %d common %d" % (len(k0), len(k1), len(set(k0) & set(k1))))
    trans = collections.Counter((adj(k0[k]), adj(k1[k])) for k in set(k0) & set(k1) if k0[k]["fate"] != "not_an_arc")
    print("OFF fate -> ON fate (common rows):")
    for (a, b), n in sorted(trans.items(), key=lambda t: -t[1]):
        print("   %-16s -> %-16s %d" % (a, b, n))
    new = [k1[k] for k in k1 if k in k0 and adj(k1[k]) in ("written", "written_far_end") and adj(k0[k]) not in ("written", "written_far_end")]
    lost_now = [k1[k] for k in k1 if k in k0 and adj(k0[k]) in ("written",) and adj(k1[k]) not in ("written", "written_far_end", "written_as_slur", "written_as_tie")]
    print("NEW writes (ON written, OFF not): %d ; written OFF (clean) but not ON: %d" % (len(new), len(lost_now)))
    bind_gap = [r["ext_gap"] for r in new if r.get("ext_gap") is not None]
    if bind_gap:
        bind_gap.sort()
        print("   new writes' end gap (sp) median %.2f, p90 %.2f, >3sp: %d" % (bind_gap[len(bind_gap) // 2], bind_gap[int(len(bind_gap) * 0.9)], sum(1 for g in bind_gap if g > END_SP)))
    # reasons for ON drops (the bypass's own refusals)
    why = collections.Counter()
    for v in on_d["verdicts"]:
        if v["quantity"] == "arc_kind" and v["outcome"] != "decided":
            d = v.get("detail") or {}
            pb = d.get("page_binding") or {}
            why[("no_curve" if d.get("no_curve") else (pb.get("why") or "?"))] += 1
    print("ON arc_kind abstentions by why (per BOX):", dict(why))
    if "--out" in sys.argv:
        o_ = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        o_.write_text(json.dumps(dict(off=r0, on=r1, new=new, plate=plate), default=str))
        (o_.parent / (o_.stem + ".off.ledger.json")).write_text(json.dumps(r0, default=str))
        (o_.parent / (o_.stem + ".on.ledger.json")).write_text(json.dumps(r1, default=str))


main()
