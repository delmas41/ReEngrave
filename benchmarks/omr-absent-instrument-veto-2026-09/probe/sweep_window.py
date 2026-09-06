"""Sweep the absent-instrument veto's page window, offline, from ONE run.

A `report`-mode transcription changes no name and records the raw material the
veto reasons about (`contextual.absent_instrument_veto`): the per-page label
evidence, the staff->slot map, and each slot's name and provenance. The veto is
a pure function of those plus the window, and it only ever REMOVES a name — so
every window's outcome can be computed from a single expensive run, and a
confirmation run at the chosen window is the only re-transcription needed.

Both sides of the trade are reported, because a count of vetoes hides which
one you bought:

  BENEFIT  impossible-instrument staves removed. Beethoven 5's first three
           movements have no Piccolo, Contrabassoon or Trombone (the reference
           encodings' part lists say so), so any such name before the finale is
           categorically wrong whatever the page prints.
  COST     full systems only, scored against the printed lineups read off
           `p1-margin` / `p44-margin` (LINEUPS, from `score_full_systems.py` on
           branch claude/roster-wholework-2026-09). A system carrying every
           staff the movement has needs no page-by-page truth: nothing can be
           added to a full lineup. Reduced systems are NOT scored — which parts
           were dropped is a fact about the page this harness does not know.

Usage:  sweep_window.py REPORT.json [--work beet5] [--max-window 60]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.absent_instrument import find_vetoes           # noqa: E402
from score_full_systems import LINEUPS                        # noqa: E402

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}
FINALE_FIRST_PAGE = 44


def staff_rows(r):
    """(page, system, staff_index, emitted name) for every staff record."""
    for page in r.get("pages", []):
        pi = page.get("page_index")
        for sy in page.get("systems", []):
            si = sy.get("system_index")
            for st in sorted(sy.get("staves", []),
                             key=lambda s: s.get("staff_geometry", {})
                             .get("line_ys_page", [0])[0]):
                yield pi, si, st.get("staff_index"), st.get("instrument")


def full_systems(r, work):
    """(page, system, [staff_index...], [truth name...]) for scoreable systems."""
    for page in r.get("pages", []):
        pi = page.get("page_index")
        for sy in page.get("systems", []):
            sts = sorted(sy.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            for lo, hi, n, names in LINEUPS[work]:
                if lo <= pi <= hi and len(sts) == n:
                    yield (pi, sy.get("system_index"),
                           [s.get("staff_index") for s in sts],
                           [s.get("instrument") for s in sts], names)
                    break


def main(path, work="beet5", max_window=60):
    r = json.load(open(path))
    blob = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not blob:
        print("REFUSING: no absent_instrument_veto block — "
              "re-run with OMR_ABSENT_INSTRUMENT_VETO=report")
        return 1
    evidence = collections.defaultdict(dict)
    for e in blob["label_evidence"]:
        evidence[e["page_index"]][e["staff_index"]] = e["instrument"]
    evidence = dict(evidence)
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in blob["staff_slots"]}
    name_by_slot = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    source = {s["slot"]: s["source"] for s in blob["slot_instruments"]}

    rows = list(staff_rows(r))
    fulls = list(full_systems(r, work))
    n_full = sum(len(f[2]) for f in fulls)
    print(f"=== {Path(path).name}   work={work}")
    print(f"INPUT ASSERTION: pages={len(r.get('pages', []))} "
          f"staff-records={len(rows)} slot-map-entries={len(slot_by_staff)} "
          f"label-evidence-entries={len(blob['label_evidence'])} "
          f"full-systems={len(fulls)} full-system-staves={n_full}")
    if not rows or not slot_by_staff:
        print("REFUSING: nothing to sweep")
        return 1
    print(f"slots named by source: "
          f"{dict(collections.Counter(source.values()))}")
    pages_labelled = sorted(evidence)
    print(f"pages with at least one confident label: {len(pages_labelled)} "
          f"of {len({p for p, _, _, _ in rows})}")
    att = collections.defaultdict(set)
    for p, by in evidence.items():
        for nm in by.values():
            att[nm].add(p)
    print()
    print("attestation span per instrument (pages a confident label was read):")
    for nm in sorted(att):
        ps = sorted(att[nm])
        print(f"  {nm:16s} n={len(ps):3d}  first={ps[0]:3d} last={ps[-1]:3d}"
              f"  biggest gap={max([b - a for a, b in zip(ps, ps[1:])] or [0]):3d}")

    base_bad = [(p, s, i, nm) for p, s, i, nm in rows
                if p < FINALE_FIRST_PAGE and nm in FINALE_ONLY]
    print()
    print(f"BASELINE impossible-instrument staves (page < {FINALE_FIRST_PAGE}): "
          f"{len(base_bad)}  "
          f"{dict(collections.Counter(nm for *_, nm in base_bad))}")

    base_ok = base_un = base_wrong = 0
    for pi, si, idxs, got, want in fulls:
        for g, wnt in zip(got, want):
            if g is None:
                base_un += 1
            elif g == wnt:
                base_ok += 1
            else:
                base_wrong += 1
    print(f"BASELINE full systems: correct {base_ok} unnamed {base_un} "
          f"wrong {base_wrong}  of {n_full}")

    for rule in ("window", "span"):
        print()
        print(f"--- rule = {rule} "
              f"{'(nearest attestation)' if rule == 'window' else '(attested span, widened)'}")
        print(f"{'W':>4} {'vetoes':>7} {'impossible':>11} {'full:correct':>13} "
              f"{'full:unnamed':>13} {'full:wrong':>11}")
        prev = None
        for w in range(0, max_window + 1):
            vs = find_vetoes(staff_keys=list(slot_by_staff),
                             slot_by_staff=slot_by_staff,
                             instrument_name_by_slot=name_by_slot,
                             instrument_source=source, evidence=evidence,
                             window=w, rule=rule)
            killed = {(v["page_index"], v["system_index"], v["staff_index"])
                      for v in vs}
            imposs = sum(1 for p, s, i, nm in rows
                         if p < FINALE_FIRST_PAGE and nm in FINALE_ONLY
                         and (p, s, i) not in killed)
            ok = un = wrong = 0
            for pi, si, idxs, got, want in fulls:
                for staff_index, g, wnt in zip(idxs, got, want):
                    if (pi, si, staff_index) in killed:
                        g = None
                    if g is None:
                        un += 1
                    elif g == wnt:
                        ok += 1
                    else:
                        wrong += 1
            row = (len(vs), imposs, ok, un, wrong)
            mark = "" if row == prev else "  <-"
            print(f"{w:4d} {len(vs):7d} {imposs:11d} {ok:13d} {un:13d} "
                  f"{wrong:11d}{mark}")
            prev = row
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    work = "beet5"
    mw = 60
    for a in sys.argv[1:]:
        if a.startswith("--work="):
            work = a.split("=", 1)[1]
        if a.startswith("--max-window="):
            mw = int(a.split("=", 1)[1])
    raise SystemExit(main(args[0], work, mw))
