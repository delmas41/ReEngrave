#!/usr/bin/env python3
"""lud_bars: which bars went kept -> narrowed between 20261009-all and 20261010-night.

Reads ONLY the saved first-two-stages diff (`readout diff`'s JSON) and the
exporter's coverage JSON (for the bar numbering). No record is loaded here.
Optionally merges the per-bar tonight totals that lud_extract.py wrote.

A BAR IS KEYED ON (page, system, cell) (CLAUDE.md §10: a cell index restarts
per system). The staves with an undecided note in it are listed beside the count.

Numbering. `export_bar` is the exporter's own measure number
(coverage.json `measure_numbering`, scheme `document`): offset(page/system) +
cell + 1. That formula is checked here against every held-out bar the
exporter itself listed (`bars_held_out_sum.held[].measure`) and the script
EXITS 3 on the first mismatch -- a control that can fail. `printed_bar` is
filled ONLY where the system's margin number was read AND equals the file
number (`printed_bar_check` state `agree`); otherwise it is left empty and
the margin reading is shown beside it. Nothing is guessed.
"""
import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
COMPARE = LIB / "overnight-20261010-night" / "compare"
KEY = re.compile(r"^glyph/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$")

# The printed bar number at the START of a system, read BY EYE from the print by this lane
# (out/print/overnight-20261010-undecided/printed_bar_numbers.png), where the margin reader
# abstained or disagreed. NOT a machine reading. Printed number of bar k of the system is taken
# as start + cell, which holds only if the exporter's cell count for the system is the printed
# bar count (not checked).
BY_EYE = {("brahms1-breitkopf", 13, 1): 251, ("brahms1-breitkopf", 22, 0): 409,
          ("brahms1-breitkopf", 16, 0): 303, ("brahms1-breitkopf", 18, 1): 343,
          ("brahms1-breitkopf", 3, 0): 38, ("brahms1-breitkopf", 25, 0): 472,
          ("brahms1-breitkopf", 16, 1): 315, ("brahms1-breitkopf", 23, 1): 444,
          ("brahms1-breitkopf", 14, 1): 273, ("brahms1-breitkopf", 18, 0): 336,
          ("beethoven5-litolff", 15, 1): 452, ("beethoven5-litolff", 10, 1): 288,
          ("beethoven5-litolff", 7, 0): 171, ("beethoven5-litolff", 16, 0): 472,
          ("beethoven5-litolff", 3, 0): 49, ("beethoven5-litolff", 10, 0): 274,
          ("beethoven5-litolff", 16, 1): 489, ("beethoven5-litolff", 12, 0): 338,
          ("beethoven5-litolff", 13, 0): 366}


def parse(k):
    m = KEY.match(k)
    return tuple(int(x) for x in m.groups())  # page, system, staff, cell, glyph


def numbering(doc):
    cov = json.load(open(COMPARE / f"{doc}.coverage.json"))
    mn = cov["measure_numbering"]
    off = {(s["page"], s["system_index"]): s["offset"] for s in mn["systems"]}
    nbars = {(s["page"], s["system_index"]): s["bars"] for s in mn["systems"]}
    chk = {}
    for s in mn["printed_bar_check"]["systems"]:
        p, si = (int(x) for x in s["system"].split("/"))
        chk[(p, si)] = s
    bad = 0
    held = cov["bars_held_out_sum"]["held"]
    for h in held:
        o = off.get((h["page"], h["system"]))
        if o is None or o + h["cell"] + 1 != h["measure"]:
            bad += 1
    if bad:
        print(f"CONTROL FAILED: offset+cell+1 != exporter measure on {bad} of {len(held)} held bars", file=sys.stderr)
        sys.exit(3)
    return off, nbars, chk, len(held)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--extract", help="lud_extract.py JSON for this doc (adds tonight totals)")
    a = ap.parse_args()
    doc = a.doc
    d = json.load(open(COMPARE / f"{doc}-first-two-stages.json"))
    off, nbars, chk, nheld = numbering(doc)
    print(f"{doc}: numbering control passed on {nheld} held bars (0 mismatches)")

    tot = None
    if a.extract:
        ex = json.load(open(a.extract))
        tot = {tuple(int(x) for x in k.split("/")): v for k, v in ex["bar_totals"].items()}

    bars = {}
    transitions = collections.Counter()
    for p in d["changed_pairs"]:
        if p["family"] != "note":
            continue
        st = tuple(p["status"])
        transitions[st] += 1
        if st not in (("kept", "narrowed"), ("narrowed", "kept")):
            continue
        page, sysi, staff, cell, _g = parse(p["b"])
        b = bars.setdefault((page, sysi, cell), {"k2n": 0, "n2k": 0, "staves": set(), "staves_n2k": set(),
                                                "reasons": collections.Counter()})
        if st == ("kept", "narrowed"):
            b["k2n"] += 1
            b["staves"].add(staff)
            m = re.search(r"-- (.+)$", p["why"][1][0] if p["why"][1] else "")
            b["reasons"][m.group(1) if m else "?"] += 1
        else:
            b["n2k"] += 1
            b["staves_n2k"].add(staff)

    rows = []
    for (page, sysi, cell), b in bars.items():
        if b["k2n"] == 0:
            continue
        o = off.get((page, sysi))
        export_bar = None if o is None else o + cell + 1
        c = chk.get((page, sysi), {})
        state = c.get("state", "no_row")
        printed_conf = export_bar if state == "agree" else ""
        rdg = c.get("printed", "")
        delta = c.get("delta", "")
        row = {
            "doc": doc, "page": page, "system": sysi, "cell": cell,
            "bar_in_system": cell + 1, "bars_in_system": nbars.get((page, sysi), ""),
            "export_bar": export_bar,
            "printed_bar_confirmed": printed_conf,
            "printed_bar_by_eye": (BY_EYE[(doc, page, sysi)] + cell) if (doc, page, sysi) in BY_EYE else "",
            "system_start_margin_reading": rdg,
            "system_start_state": state,
            "system_start_export_minus_printed": (-delta if delta != "" else ""),
            "kept_to_narrowed": b["k2n"],
            "narrowed_to_kept": b["n2k"],
            "net_undecided": b["k2n"] - b["n2k"],
            "staves_with_new_undecided": len(b["staves"]),
            "staves": " ".join(str(s) for s in sorted(b["staves"])),
            "reasons": "; ".join(f"{r} x{n}" for r, n in b["reasons"].most_common()),
        }
        if tot is not None:
            t = tot.get((page, sysi, cell), {})
            row["notes_in_bar_tonight_kept"] = t.get("kept", 0)
            row["notes_in_bar_tonight_narrowed"] = t.get("narrowed", 0)
            row["notes_in_bar_tonight_other"] = sum(v for k, v in t.items() if k not in ("kept", "narrowed"))
        rows.append(row)
    rows.sort(key=lambda r: (-r["kept_to_narrowed"], r["page"], r["system"], r["cell"]))

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csvp = out / f"undecided-bars-{doc}.csv"
    with open(csvp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # per-system totals
    sysrows = collections.defaultdict(lambda: [0, 0, set()])
    for r in rows:
        s = sysrows[(r["page"], r["system"])]
        s[0] += r["kept_to_narrowed"]
        s[1] += 1
        s[2].update(r["staves"].split())
    k2n_total = sum(r["kept_to_narrowed"] for r in rows)
    lines = []
    lines.append(f"== {doc}: note transitions in the diff (family note)")
    for st, n in sorted(transitions.items(), key=lambda kv: -kv[1]):
        lines.append(f"   {st[0]:>10} -> {st[1]:<10} {n}")
    lines.append(f"   kept->narrowed notes {k2n_total} in {len(rows)} distinct bars "
                 f"(of {sum(nbars.values())} bars x staves not counted; {len(nbars)} systems)")
    dist = collections.Counter(r["kept_to_narrowed"] for r in rows)
    lines.append("   bars by number of newly undecided notes: " +
                 ", ".join(f"{k}:{dist[k]}" for k in sorted(dist)))
    lines.append("")
    lines.append(f"== {doc}: top 10 bars (page/system/bar-in-system -> export bar)")
    for r in rows[:10]:
        pc = ""
        if r["printed_bar_confirmed"] != "":
            pc = f", printed {r['printed_bar_confirmed']} (margin reader agrees)"
        elif r["printed_bar_by_eye"] != "":
            pc = f", printed {r['printed_bar_by_eye']} (by eye)"
        lines.append(f"   p{r['page']} s{r['system']} bar {r['bar_in_system']}/{r['bars_in_system']} "
                     f"(export bar {r['export_bar']}{pc}): {r['kept_to_narrowed']} notes on "
                     f"{r['staves_with_new_undecided']} staves [{r['staves']}]")
    lines.append("")
    lines.append(f"== {doc}: top systems by newly undecided notes")
    for (page, sysi), (n, nb, sv) in sorted(sysrows.items(), key=lambda kv: -kv[1][0])[:12]:
        lines.append(f"   p{page} s{sysi}: {n} notes in {nb} bars, {len(sv)} staves")
    txt = "\n".join(lines)
    (out / f"undecided-bars-{doc}.txt").write_text(txt + "\n")
    print(txt)
    print(f"wrote {csvp}")


if __name__ == "__main__":
    main()
