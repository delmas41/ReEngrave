"""What would slot 9 be, under each candidate repair? Offline, on the blob.

Three arms, all run through the SHIPPED `align_to_layout` / `fit_layouts` with
nothing patched, so the arithmetic is the production arithmetic:

`baseline`
    what ships: every layout offered whole.

`veto`
    the proposal stands but a name the work's roster does not contain is
    REFUSED — the shape of `absent_instrument.py`. Slot 9 becomes UNNAMED.

`constrain`
    the roster filters the layout's PARTS before the DP runs, so `Tuba` is not
    a part any layout can offer this work. The existing continuation move
    (`EXTEND_PENALTY`, the two-horns-on-two-staves case) is then the cheapest
    reading of slot 9 — if the arithmetic agrees, which is what this measures.

Also prints the DP totals, so the margin by which `Tuba` beat a continuation is
a number rather than a story.

Usage:  counterfactuals.py BLOB.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.score_layouts import (  # noqa: E402
    LAYOUTS, ScoreLayout, align_to_layout, fit_layouts)

# The work's IMSLP roster, `source_kind: catalog` (see FINDINGS).
BRAHMS1_ROSTER = {"Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                  "Horn", "Trumpet", "Trombone", "Timpani",
                  # `strings` is a SECTION word; the catalog parse drops it,
                  # so the string names are supplied here explicitly rather
                  # than trusted to the parse. See the sibling session's
                  # fault (a): 13 of 219 rosters name no string at all.
                  "Violin", "Viola", "Cello", "Contrabass"}


def restrict(layout: ScoreLayout, allowed: set[str]) -> ScoreLayout:
    """The same layout with parts the work does not have removed."""
    return ScoreLayout(layout.name + "|roster",
                       tuple(p for p in layout.parts if p in allowed),
                       layout.note)


def main(path: str) -> None:
    b = (json.loads(Path(path).read_text())
         .get("contextual", {})["absent_instrument_veto"])
    si = {s["slot"]: s for s in b["slot_instruments"]}
    n = b["reference_size"]
    labels = {k: v["instrument"] for k, v in si.items()
              if v["source"] in ("label", "roster")}
    unlabelled = [i for i in range(n) if i not in labels]
    print(f"{path}\n  n={n}  unlabelled slots={unlabelled}")

    # ── the margin: Tuba vs a trombone continuation, on the winning layout ──
    base = fit_layouts(n, labels=labels)
    win = base.layout
    tot, assign = align_to_layout(win, n, labels, None)
    print(f"\n  winning layout `{win.name}` total={tot:.2f} "
          f"({tot / n:.3f}/staff)  slot9={assign[9]}")
    forced = dict(labels)
    forced[9] = "Trombone"
    tot2, assign2 = align_to_layout(win, n, forced, None)
    print(f"  same layout, slot 9 LABELLED Trombone: total={tot2:.2f} "
          f"slot9={assign2[9]}")
    no_tuba = ScoreLayout(win.name + "|noTuba",
                          tuple(p for p in win.parts if p != "Tuba"))
    tot3, assign3 = align_to_layout(no_tuba, n, labels, None)
    print(f"  same layout with `Tuba` REMOVED:      total={tot3:.2f} "
          f"slot9={assign3[9]}  <- what the continuation move costs")
    print(f"  margin Tuba-over-continuation = {tot - tot3:.2f} points "
          f"({(tot - tot3) / n:.3f}/staff)")

    # ── the three arms ──────────────────────────────────────────────────────
    print("\n  arm        slot9            layout                score/staff")
    for arm in ("baseline", "veto", "constrain"):
        if arm == "constrain":
            lays = tuple(restrict(l, BRAHMS1_ROSTER) for l in LAYOUTS)
        else:
            lays = LAYOUTS
        fit = fit_layouts(n, labels=labels, layouts=lays)
        if fit is None:
            print(f"  {arm:<10s} (no fit)")
            continue
        got = fit.assignment[9]
        if arm == "veto" and got not in BRAHMS1_ROSTER:
            got = f"REFUSED ({got})"
        print(f"  {arm:<10s} {str(got):<16s} {fit.layout.name:<21s} "
              f"{fit.score_per_staff:.3f}")

    # ── does `constrain` disturb any slot the reading already got right? ────
    lays = tuple(restrict(l, BRAHMS1_ROSTER) for l in LAYOUTS)
    a = fit_layouts(n, labels=labels)
    c = fit_layouts(n, labels=labels, layouts=lays)
    print("\n  slot-by-slot, baseline vs constrain:")
    for i in range(n):
        flag = "  CHANGED" if a.assignment[i] != c.assignment[i] else ""
        print(f"   {i:2d} {str(a.assignment[i]):<15s} -> "
              f"{str(c.assignment[i]):<15s}{flag}")


if __name__ == "__main__":
    main(sys.argv[1])
