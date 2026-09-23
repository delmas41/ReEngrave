"""ROADMAP 2.3, second instrument: score each INFER duration against the
REFERENCE ENCODING, on the pages whose cell->measure map is clean.

⚠️ ONLY PAGES 3 AND 4. The verified `984073-p2` row records that this raster
DROPS ONE BARLINE (pipeline 16 bars against the print's 17, at m19|m20), so
page 2's cell->measure map is off by one after that point and a silently
shifted join scores a right answer wrong. Pages 3 and 4 are admitted because
the record's own cell counts are UNANIMOUS across every staff and match the
verified window exactly:

    p3 s0 16 cells x 11 staves + s1 18 x 8   = 34 = mm 49-82   ✓
    p4 s0 15 cells x 11 staves + s1 15 x 11  = 30 = mm 83-112  ✓

That unanimity is the join's control and it is checked again at run time; a
page whose staves disagree is REFUSED rather than scored.

⚠️ A PAGE TRUTH IS NOT AN ENCODING TRUTH (CLAUDE.md 10). What is taken from
the encoding here is a bar's note DURATIONS, which is the quantity under
test; nothing about layout, spelling or placement is taken from it.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.training.musicxml_truth import load_truth      # noqa: E402

DURATION_RULES = ("collapse_duration_by_column", "collapse_duration_to_barline")
# cell -> reference measure, only for the pages whose join is clean
FIRST_MEASURE = {(3, 0): 49, (3, 1): 65, (4, 0): 83, (4, 1): 98}
EXPECT_CELLS = {(3, 0): 16, (3, 1): 18, (4, 0): 15, (4, 1): 15}


def staff_parts(rows, page, system, staff):
    row = next(r for r in rows
               if r["row_id"] == f"beethoven-sym5-mvt1-984073-p{page}")
    sap = row.get("systems_as_printed")
    if sap:
        key = f"system_{system + 1}"
        if key in sap:
            return sap[key][staff]["name"], sap[key][staff]["parts"]
    return row["staves"][staff]["name"], row["staves"][staff]["parts"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--works", default="benchmarks/omr-scan-e2e-2026-09/works.json")
    ap.add_argument("--out")
    a = ap.parse_args()

    d = load_record(a.arm)
    rec, inf = d["record"], d["inference"]
    vby = {v["id"]: v for v in rec["verdicts"]}
    truth = load_truth(a.truth)
    rows = json.loads(Path(a.works).read_text())["rows"]

    gbox, ncls = {}, {}
    cells = collections.defaultdict(set)
    for o in rec["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            gbox[s] = o["value"]
        elif q == "notehead_class":
            ncls[s] = o["value"]
        if s.startswith("cell/"):
            _, p, sy, st, c = s.split("/")
            cells[(int(p), int(sy), int(st))].add(int(c))

    # JOIN CONTROL: every staff of an admitted system must agree on cell count
    for (p, sy), want in EXPECT_CELLS.items():
        got = {n for (pp, ss, _st), v in
               ((k, v) for k, v in cells.items()) if (pp, ss) == (p, sy)
               for n in [len(v)]}
        if got != {want}:
            print(f"⚠️ REFUSING page {p} system {sy}: cell counts {got}, "
                  f"expected all staves at {want}")
            FIRST_MEASURE.pop((p, sy), None)

    out = []
    for rule, subj, vid in inf["inferred"]:
        if rule not in DURATION_RULES:
            continue
        _, p, sy, st, ce, gi = subj.split("/")
        p, sy, st, ce = int(p), int(sy), int(st), int(ce)
        if (p, sy) not in FIRST_MEASURE:
            out.append({"subject": subj, "rule": rule,
                        "scored": False,
                        "why": "page/system has no clean cell->measure join"})
            continue
        meas = FIRST_MEASURE[(p, sy)] + ce
        name, parts = staff_parts(rows, p, sy, st)

        # ⚠️ THE REFERENCE BAR IS TAKEN PER PART, NOT CONCATENATED.
        # A staff carrying two parts (Flauti = [0, 1]) gives a PART-MAJOR note
        # list, while our noteheads are read LEFT TO RIGHT. Concatenating the
        # two and comparing by index aligns part 1's first note against our
        # second EVENT, which is nonsense wherever the parts differ. Each
        # part's own sequence is kept separate and the comparison runs against
        # whichever part's length matches our event count.
        ref_by_part = []
        for pi in parts:
            seq = [round(n.duration_ql, 4)
                   for n in truth.parts[pi].measures[meas - 1].notes
                   if not (n.rest or n.grace or n.chord)]
            ref_by_part.append(seq)
        ref = [x for seq in ref_by_part for x in seq]
        v = vby[vid]
        prior = vby.get(v.get("supersedes"))
        inferred = (v.get("value") or {}).get("beats")
        top = None
        if prior and prior.get("candidates"):
            best = max(prior["candidates"], key=lambda c: c.get("support", 0))
            top = (best.get("value") or {}).get("beats")

        # our bar: noteheads left to right, GROUPED INTO EVENTS by x.
        # ⚠️ Heads stacked at one x are ONE event (a chord, or two parts on
        # one staff playing together) -- measured: `cell/4/0/0/12` holds 4
        # heads at 2 distinct x, which is 2 events, not 4. Counting heads
        # where the reference counts notes is what made the first draft of
        # this probe compare 4 against 4 by accident.
        ours = sorted(
            (gbox[s][1], s) for s in gbox
            if s.startswith(f"glyph/{p}/{sy}/{st}/{ce}/") and s in ncls)
        events = []
        for x, s in ours:
            if events and x - events[-1][-1][0] < 80:
                events[-1].append((x, s))
            else:
                events.append([(x, s)])
        idx = next((i for i, ev in enumerate(events)
                    if any(s == subj for _x, s in ev)), None)

        rec_row = {
            "subject": subj, "rule": rule, "scored": True,
            "ref_measure": meas, "staff_name": name, "ref_parts": parts,
            "inferred_beats": inferred, "reader_top_beats": top,
            "ref_bar_durations": ref,
            "ref_bar_sum": round(sum(ref), 4),
            "our_noteheads_in_bar": len(ours),
            "our_events_in_bar": len(events),
            "our_event_index": idx,
            "ref_notes_per_part": [len(seq) for seq in ref_by_part],
            # ⚠️ A bar whose reference durations are ALL THE SAME cannot
            # discriminate a right alignment from a wrong one: every index
            # gives the same answer. Such a row is reported and EXCLUDED from
            # the tally, because a check that cannot fail is not a check.
            "ref_bar_is_rhythmically_uniform": len(set(ref)) <= 1,
            "inferred_present_in_ref_bar": inferred in ref,
            "reader_top_present_in_ref_bar": (top in ref) if top is not None else None,
        }
        # POSITIONAL: honest only when our EVENT count matches some part's
        # own note count, so index i means the same instant on both sides.
        match = next((seq for seq in ref_by_part
                      if len(seq) == len(events)), None)
        if idx is not None and match is not None:
            rec_row["positional_ref_duration"] = match[idx]
            if rec_row["ref_bar_is_rhythmically_uniform"]:
                rec_row["positional_verdict"] = (
                    "UNINFORMATIVE: the reference bar is rhythmically uniform "
                    f"({match}), so every alignment agrees and this row "
                    "discriminates nothing")
            else:
                rec_row["positional_verdict"] = (
                    "INFERRED CORRECT" if abs(match[idx] - (inferred or -1)) < 1e-6
                    else ("READER'S TOP WAS CORRECT"
                          if top is not None and abs(match[idx] - top) < 1e-6
                          else "BOTH WRONG"))
        else:
            rec_row["positional_ref_duration"] = None
            rec_row["positional_verdict"] = (
                f"NOT COMPARABLE: our bar has {len(events)} events "
                f"({len(ours)} heads), reference parts have "
                f"{[len(s) for s in ref_by_part]} notes")
        out.append(rec_row)

    scored = [r for r in out if r.get("scored")]
    pos = [r for r in scored if r.get("positional_ref_duration") is not None]
    informative = [r for r in pos
                   if not r.get("ref_bar_is_rhythmically_uniform")]
    print(f"{len(out)} inferences | {len(scored)} on a clean join | "
          f"{len(pos)} positionally comparable | "
          f"{len(informative)} INFORMATIVE (a uniform reference bar "
          f"discriminates nothing)\n")
    for r in out:
        if not r.get("scored"):
            print(f"  {r['subject']:<22} SKIPPED — {r['why']}")
            continue
        print(f"  {r['subject']:<22} m{r['ref_measure']:<4}{r['staff_name']:<22}"
              f"inferred={r['inferred_beats']}  reader_top={r['reader_top_beats']}")
        print(f"{'':24}ref per part {r['ref_notes_per_part']} -> "
              f"{r['ref_bar_durations']}; ours {r['our_events_in_bar']} events "
              f"({r['our_noteheads_in_bar']} heads) at idx {r['our_event_index']}")
        print(f"{'':24}-> {r['positional_verdict']}")
    if informative:
        tally = collections.Counter(r["positional_verdict"] for r in informative)
        print("\nPOSITIONAL TALLY (informative rows only):", dict(tally))
    else:
        print("\n⚠️ NO INFORMATIVE ROW. Every positionally comparable bar has "
              "a rhythmically uniform reference, so the encoding cannot "
              "discriminate a right inference from a wrong one here. This "
              "instrument returns NO evidence about these rules on this "
              "document -- which is a result about the instrument, not "
              "about the rules.")
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
