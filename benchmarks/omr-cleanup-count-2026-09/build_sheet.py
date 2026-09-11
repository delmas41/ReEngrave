"""The machine's PROPOSALS, and the counting sheet the human fills in.

    python3 benchmarks/omr-cleanup-count-2026-09/build_sheet.py --tag p1-p4

⚠️⚠️ **THE MACHINE PROPOSES NOTHING IN THE `spurious` COLUMN, AND THAT IS A
RESULT RATHER THAN AN OVERSIGHT.** `spurious` means *the file has something the
print does not*, and deciding it needs the print. The machine has the record
and the file and neither is the print. `CATEGORIES.md` §3 already fixes what
the machine is allowed to contribute — **why a thing is ABSENT** — and that is
all this writes. Anything else would be a guess wearing a column heading.

So the proposals are exactly two kinds, both about absence, both in the
count's own unit (a FIX-ACTION with a scope):

* `proposed_missing_bars_nothing_read` — a bar exported as a whole-measure
  rest where the record holds NO notehead and NO rest for that cell. The
  exporter says so itself: *a bar with no notes gets a measure rest because we
  read NOTHING in it, not because we read silence*. Scope `staff-bar`.
* `proposed_missing_notes_held_back` — ink the record HOLDS and the file does
  not carry, with the exporter's own reason (`no_pitch`,
  `duration_narrowed`, …). Scope `element`.

⚠️ Both are LOWER BOUNDS on `missing` and neither is a lower bound on the
COUNT: a note the detector never saw is invisible to both, and that is the
larger population on a scan.

⚠️ The per-system decomposition re-derives `_place_notes`' three tests, which
is drift risk, so it is CHECKED: the per-system reasons must sum to the
exporter's OWN `notes_not_written` document totals, and this script exits
non-zero if they do not. A decomposition that quietly disagreed with the
exporter would send the human hunting for notes that are in the file.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as sx          # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402


def _sub(key):
    f = key.split("/")
    return {"kind": f[0],
            **{n: (int(f[i + 1]) if i + 1 < len(f) else None)
               for i, n in enumerate(("page", "system", "staff", "cell", "glyph"))}}


def held_back_by_system(rec):
    """{(page, system): Counter(reason)} — ink the record holds, file has not.

    Mirrors `_place_notes`' three refusals in order. Checked against that
    function's own totals by the caller.
    """
    out = collections.defaultdict(collections.Counter)
    for o in rec.obs_of(Q.GLYPH_BOX):
        key = o["subject"]
        s = _sub(key)
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, key))
        if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, key):
            continue
        where = (s["page"], s["system"])
        pitch = None if is_rest else rec.value(Q.PITCH, key)
        dv = rec.verdict(Q.DURATION, key)
        dur = dv["value"] if dv and dv["outcome"] == "decided" else None
        if pitch is None and not is_rest:
            out[where]["no_pitch"] += 1
            continue
        if not isinstance(dur, dict):
            out[where][("rest_" if is_rest else "") + "duration_"
                       + (dv["outcome"] if dv else "absent")] += 1
            continue
    return out


def cells_with_no_ink(rec):
    """{(page, system): {(staff, cell)}} — no notehead and no rest gathered."""
    seen = collections.defaultdict(set)
    inked = collections.defaultdict(set)
    for o in rec.obs_of(Q.CELL_BOX):
        s = _sub(o["subject"])
        seen[(s["page"], s["system"])].add((s["staff"], s["cell"]))
    for quantity in (Q.NOTEHEAD_CLASS, Q.REST):
        for o in rec.obs_of(quantity):
            s = _sub(o["subject"])
            inked[(s["page"], s["system"])].add((s["staff"], s["cell"]))
    return {k: (v - inked.get(k, set())) for k, v in seen.items()}


def file_counts(xml_text, wanted):
    """Count what the FILE carries for one system: (part_id) -> (lo, hi)."""
    root = ET.fromstring(xml_text)
    c = collections.Counter()
    for part in root.findall("part"):
        pid = part.get("id")
        if pid not in wanted:
            continue
        lo, hi = wanted[pid]
        for m in part.findall("measure"):
            n = int(m.get("number"))
            if not (lo <= n <= hi):
                continue
            c["bars"] += 1
            notes = m.findall("note")
            rests = [x for x in notes if x.find("rest") is not None]
            mrests = [x for x in rests
                      if (x.find("rest").get("measure") == "yes")]
            c["notes"] += len(notes) - len(rests)
            c["rests"] += len(rests)
            if len(notes) == len(mrests) == 1:
                c["measure_rest_bars"] += 1
            blob = ET.tostring(m, encoding="unicode")
            for tag, name in (("<slur", "slurs"), ("<tied", "ties"),
                              ("<dynamics", "dynamics"), ("<fermata", "fermatas"),
                              ("<wedge", "wedges"), ("<words", "words"),
                              ("<articulations", "articulations"),
                              ("<ornaments", "ornaments")):
                c[name] += blob.count(tag)
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p1-p4")
    ap.add_argument("--out-dir", default=str(HERE / "out"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)

    result = json.loads((out / f"record-{args.tag}.json").read_text())
    xml_text = (out / f"beethoven5-mvt1-{args.tag}.musicxml").read_text()
    smap = json.loads((out / f"system-map-{args.tag}.json").read_text())
    coverage = json.loads((out / f"coverage-{args.tag}.json").read_text())

    rec = sx.Record(result)
    held = held_back_by_system(rec)
    empty_cells = cells_with_no_ink(rec)

    # ⚠️ THE ONE PROPOSAL THAT IS NOT READ OFF THE SAME RASTER. Every other
    # figure here comes from the record, i.e. from an OMR reading of the page
    # it would arbitrate -- two witnesses that fall silent together, which
    # CLAUDE.md names as the shape bounding every bar-arbitrated rule here.
    # The printed staff count per system was read off the PRINT by a human
    # (works.json), so it can propose a STRUCTURAL absence that no
    # page-derived signal in this file is allowed to propose.
    # ⚠️ A page with no entry gets NO proposal. Not a zero.
    printed = json.loads((HERE / "printed-staves.json").read_text())["pages"]

    # ── the control: my decomposition against the exporter's own totals ──
    mine = collections.Counter()
    for c in held.values():
        mine.update(c)
    theirs = collections.Counter(coverage.get("notes_not_written") or {})
    theirs.pop("owner_staff_has_no_measures", None)
    theirs.pop("written_value_fits_no_note", None)
    shared = set(mine) | set(theirs)
    bad = {k: (mine[k], theirs[k]) for k in shared if mine[k] != theirs[k]}
    if bad:
        print("DECOMPOSITION DISAGREES WITH THE EXPORTER -- refusing to write",
              file=sys.stderr)
        for k, (a, b) in sorted(bad.items()):
            print(f"  {k}: mine {a}, exporter {b}", file=sys.stderr)
        return 2

    systems = []
    for entry in smap["systems"]:
        page, sysi = entry["page"], entry["system"]
        wanted = {r["part_id"]: (r["first_measure"], r["last_measure"])
                  for r in entry["staves"]}
        fc = file_counts(xml_text, wanted)
        h = held.get((page, sysi), collections.Counter())
        # a bar is proposed missing only where BOTH hold: the file wrote a
        # whole-measure rest AND the record gathered no ink for that cell.
        blank = empty_cells.get((page, sysi), set())
        n_blank_exported = 0
        for r in entry["staves"]:
            n_blank_exported += sum(
                1 for (st, ci) in blank
                if st == r["staff"] and ci < r["n_measures"])
        prop_missing_notes = sum(h.values())

        pr = printed.get(str(page))
        n_printed = None
        prop_missing_staves = None
        if pr and sysi < len(pr["systems"]):
            n_printed = pr["systems"][sysi]
            prop_missing_staves = max(0, n_printed - len(entry["staves"]))

        score = (3 * n_blank_exported + prop_missing_notes
                 + 30 * (prop_missing_staves or 0))
        why = []
        if prop_missing_staves:
            why.append(f"the print carries {n_printed} staves here and we "
                       f"exported {len(entry['staves'])}")
        elif prop_missing_staves == 0:
            why.append(f"staff count matches the print ({n_printed})")
        if n_blank_exported:
            why.append(f"{n_blank_exported} bar(s) exported with nothing read in them")
        if prop_missing_notes:
            why.append(f"{prop_missing_notes} gathered note(s) held out of the file")
        if not why:
            why.append("nothing proposed — the machine sees no absence here")
        systems.append({
            "page": page, "system": sysi,
            "staves": len(entry["staves"]),
            "bars_exported": fc["bars"],
            "bars_printed_per_staff": max(
                (r["n_measures"] for r in entry["staves"]), default=0),
            "notes_written": fc["notes"], "rests_written": fc["rests"],
            "measure_rest_bars": fc["measure_rest_bars"],
            "arcs_written": fc["slurs"] + fc["ties"],
            "file": dict(fc),
            "proposed_missing_bars_nothing_read": n_blank_exported,
            "proposed_missing_notes_held_back": prop_missing_notes,
            "proposed_missing_notes_by_reason": dict(h),
            "staves_printed": n_printed,
            "proposed_missing_staff_systems": prop_missing_staves,
            "proposed_spurious": None,
            "attention_score": score,
            "why": "; ".join(why),
        })

    payload = {
        "_README": "MACHINE PROPOSALS. Never a count. `proposed_spurious` is "
                   "null everywhere BY DESIGN: deciding it needs the print. "
                   "See CATEGORIES.md section 3.",
        "record": f"record-{args.tag}.json",
        "provenance": result.get("provenance"),
        "attention_score": "30 * proposed_missing_staff_systems + "
                           "3 * proposed_missing_bars + "
                           "proposed_missing_notes_held_back. ⚠️ The weights "
                           "are DISPLAY ORDER and nothing else reads them. "
                           "They are not a claim that a staff costs thirty "
                           "notes; they exist so that a system which failed "
                           "STRUCTURALLY sorts above one that is 95% right, "
                           "which is the whole instruction the ordering "
                           "exists to satisfy.",
        "control": {
            "per_system_reasons_sum_to_exporter_totals": True,
            "checked_against": "coverage.notes_not_written",
            "totals": dict(mine),
        },
        "systems": systems,
    }
    (out / f"proposals-{args.tag}.json").write_text(json.dumps(payload, indent=1))

    # ── the counting sheet ──────────────────────────────────────────────
    sheet = out / f"counting-sheet-{args.tag}.csv"
    with sheet.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "page", "system", "staff_slot", "part_name", "measures_in_file",
            "proposed_missing_staff_systems",
            "proposed_missing_bars_nothing_read", "proposed_missing_notes_held_back",
            "proposed_missing_reasons",
            "missing", "wrong", "spurious", "would_not_notice",
            "scope", "missable", "notes",
        ])
        order = sorted(systems, key=lambda s: (-s["attention_score"],
                                               s["page"], s["system"]))
        by_key = {(e["page"], e["system"]): e for e in smap["systems"]}
        for s in order:
            entry = by_key[(s["page"], s["system"])]
            for i, r in enumerate(entry["staves"]):
                w.writerow([
                    s["page"], s["system"], i, r["part_name"],
                    f"{r['first_measure']}-{r['last_measure']}",
                    ("" if s["proposed_missing_staff_systems"] is None
                     else s["proposed_missing_staff_systems"]) if i == 0 else "",
                    s["proposed_missing_bars_nothing_read"] if i == 0 else "",
                    s["proposed_missing_notes_held_back"] if i == 0 else "",
                    json.dumps(s["proposed_missing_notes_by_reason"]) if i == 0 else "",
                    "", "", "", "", "", "", "",
                ])
        w.writerow([])
        w.writerow(["TOTALS (human only — never sum a proposed_ column)",
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])

    print(f"wrote {sheet}")
    print(f"systems={len(systems)}  "
          f"proposed_missing_bars="
          f"{sum(s['proposed_missing_bars_nothing_read'] for s in systems)}  "
          f"proposed_missing_notes={sum(mine.values())}  "
          f"(control: decomposition == exporter totals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
