"""ROADMAP 2.293: one compact table from `claim_readout ink --out DIR` results (ink_number.json).

    python3 benchmarks/one-ink-number-2026-11/summary_table.py DIR [DIR ...]

Per directory: the four lines for the pages together and per page, the sub-lines of ONE OWNER (page ledger vs cell box, linked), of CLAIMED TWICE and the
unowned families, as percentages of the page's dark pixels. Every figure is a pixel count over that denominator.
"""
import json
import pathlib
import sys


def row(name, t):
    tot = t["ink_px"]
    L, o, w = t["lines"], t["one"], t["twice"]
    staff = o["by_kind"].get("staff_line", 0)
    pc = lambda x: 100.0 * x / tot
    print("%-24s %9d px | one %5.1f (non-staff %5.1f; page ledger %5.1f, cell box %5.1f; linked %4.1f) weak %4.1f twice %4.1f none %4.1f | twice: one kind %4.1f (box+register %4.1f) "
          "two kinds %4.1f views-disagree %4.1f twin-views %4.1f" % (
              name, tot, pc(L["one"]), 100.0 * (L["one"] - staff) / (tot - staff), pc(o["ledger_px"]), pc(o["cell_px"]), pc(o["linked_px"]), pc(L["weak"]), pc(L["twice"]),
              pc(L["none"]), pc(w["twin_px"]), pc(w["twin_mixed_px"]), pc(w["two_kinds_px"]), pc(w["views_disagree_px"]), pc(w["twin_views_px"])))


def main():
    for d in sys.argv[1:]:
        r = json.loads((pathlib.Path(d) / "ink_number.json").read_text())
        name = pathlib.Path(d).name
        row(name + " ALL", r["total"])
        for p, t in r["per_page"].items():
            row("  page " + p, t)
        tot = r["total"]["ink_px"]
        rk = lambda dd, n=99: {k: round(100.0 * v / tot, 2) for k, v in sorted(dd.items(), key=lambda kv: -kv[1])[:n]}
        print("   one owner, cell box (to do):", rk(r["total"]["one"]["by_kind_cell"]))
        print("   one owner, page ledger:     ", rk(r["total"]["one"]["by_kind_ledger"]))
        print("   claimed twice by kind:      ", rk(r["total"]["twice"]["twin_by_kind"], 8), "pairs", rk(r["total"]["twice"]["pairs"], 5))
        print("   no owner (shape guess):     ", rk(r["total"]["none"]["by_class"]))
        print("   weak:                       ", rk(r["total"]["weak"]["by_kind"]))


main()
