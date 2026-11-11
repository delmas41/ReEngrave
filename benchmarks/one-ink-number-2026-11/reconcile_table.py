"""ROADMAP 2.293 step 1: the three figures, side by side on the SAME page, from the JSON `run_reconcile.sh` wrote (old readout `readout.json`, new `ink_number.json`).

    python3 benchmarks/one-ink-number-2026-11/reconcile_table.py [RECON_DIR]

For every (plate page, slice) it prints the number each old tool reported, with its own denominator, then the new ink number's four lines:
  2.283 audit  = old readout "one owner" over the NON-STAFF ink (its table's denominator);
  2.288 lane   = old readout "one owner" over ALL ink (render_tally's percentage);
  2.286 --ink  = old readout's unclaimed / refused / residue / weak / debris / outside bucket over ALL ink (conservation.ink_line, before 2.293).
"""
import json
import pathlib
import sys

D = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/private/tmp/claude-501/scratch293/recon")
UNC = ("unclaimed", "refused", "residue", "weak_claim", "debris", "outside_cells")


def old_numbers(path):
    r = json.loads((path / "readout.json").read_text())
    t = r["total"]
    sp, tot = t["state_px"], t["ink_px"]
    staff = sp.get("staff_line", 0)
    one = sp.get("one", 0)
    unc = sum(v for k, v in sp.items() if k.startswith(UNC))
    con = sum(v for k, v in sp.items() if k.startswith("contested"))
    return {"ink": tot, "staff": staff / tot, "one_all": one / tot, "one_nonstaff": one / (tot - staff), "twin_nonstaff": sp.get("twin", 0) / (tot - staff),
            "contested_nonstaff": con / (tot - staff), "unc_nonstaff": unc / (tot - staff), "unc_all": unc / tot, "weak_all": sp.get("weak_claim", 0) / tot}


def new_numbers(path):
    r = json.loads((path / "ink_number.json").read_text())
    t = r["total"]
    tot = t["ink_px"]
    L = t["lines"]
    staff = t["one"]["by_kind"].get("staff_line", 0)
    return {"ink": tot, "one": L["one"] / tot, "one_nonstaff": (L["one"] - staff) / (tot - staff), "weak": L["weak"] / tot, "twice": L["twice"] / tot,
            "none": L["none"] / tot, "links": "%d/%d" % (t["links_filed"], t["strokes_filed"]), "ledger": t["one"]["ledger_px"] / tot, "cell": t["one"]["cell_px"] / tot}


def main():
    print("%-14s %-20s | %-34s | %s" % ("page/slice", "dark px (staff %)", "OLD readout (2.236 PageInk)", "NEW ink number (all dark px)"))
    for name in ("brahms-r2", "brahms-1029", "litolff-r2", "litolff-1029"):
        try:
            o = old_numbers(D / ("old_" + name))
            n = new_numbers(D / ("ink_" + name))
        except FileNotFoundError:
            continue
        print("%-14s %9d (%4.1f%%) | 2.283-style one owner of non-staff %5.1f%%   (twin %4.1f, contested %4.1f, unclaimed+weak %4.1f)" % (
            name, o["ink"], 100 * o["staff"], 100 * o["one_nonstaff"], 100 * o["twin_nonstaff"], 100 * o["contested_nonstaff"], 100 * o["unc_nonstaff"]))
        print("%-14s %-20s | 2.288-style one owner of ALL ink   %5.1f%%" % ("", "", 100 * o["one_all"]))
        print("%-14s %-20s | 2.286-style unclaimed/debris bucket of ALL ink %5.1f%%   (of non-staff %5.1f%%)" % ("", "", 100 * o["unc_all"], 100 * o["unc_nonstaff"]))
        print("%-14s %-20s | NEW  one %5.1f%% (non-staff %5.1f%%; page ledger %4.1f%% + cell box %4.1f%%)  weak %4.1f%%  twice %4.1f%%  none %4.1f%%   links %s" % (
            "", "", 100 * n["one"], 100 * n["one_nonstaff"], 100 * n["ledger"], 100 * n["cell"], 100 * n["weak"], 100 * n["twice"], 100 * n["none"], n["links"]))


main()
