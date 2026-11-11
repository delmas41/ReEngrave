"""2.291: one block per non-plain bar from PLATE.bars.json: events, voices, and every glyph box of the cell with its fate.
usage: show.py BARS.json [red|partial|all]"""
import json
import sys

bars = json.load(open(sys.argv[1]))
which = sys.argv[2] if len(sys.argv) > 2 else "red"
for b in bars:
    if which != "all" and b["status"] != which:
        continue
    r = b["red"] or {}
    m = b.get("meter") or {}
    mv = m.get("value") or {}
    print("== %s %s m%s %s why=%s want=%s counted=%s meter=%s/%s %s/%s 2v=%s unread=%s" % (
        b["plate"], tuple(b["key"]), b["measure"], b["status"], b["why"], r.get("want_quarters"), r.get("counted_quarters"),
        mv.get("numerator"), mv.get("denominator"), m.get("outcome"), m.get("reason"), r.get("two_voice"), b["unread_glyphs"]))
    for g in b["glyphs"]:
        dur = g["duration"] or {}
        print("    %-22s %-12s %-34s %s %s dur=%s/%s own=%s" % (
            g["sub"].split("glyph/")[1], g["cls"][:12] if g["cls"] else "", (g["fate"] or "-")[:34],
            "H" if g["head"] else ("R" if g["rest"] else "."), [round(x) for x in g["box"]] if g["box"] else None,
            dur.get("outcome"), dur.get("reason"), g["owner"]))
