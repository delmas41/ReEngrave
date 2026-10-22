#!/usr/bin/env python3
"""The mechanism, isolated: which slot each staff gets, per page window.

`slots.build_reference` + `slots.align` see nothing a transcription adds — they
read staff geometry, bracket groups and labels — so the collapse this
workstream is about can be reproduced for the price of a staff detection and a
Surya read per page (~5 s) instead of a transcription (~280 s/page).

⚠️ THIS IS NOT THE END-TO-END NUMBER, and must not be quoted as one.
`contextual` names a staff from the reference slot, the document roster and the
score-order prior together; this probe reads ONLY the reference slot, which is
the half the rule changes. The end-to-end figure comes from real `transcribe`
runs scored by the wholework harness.

    python3 .../probe_window_slots.py PDF --windows 1 0-2 --truth beet5-12
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr.slots import assign_slots, labels_by_staff  # noqa: E402
from tools.omr import staff_labels_surya as S            # noqa: E402

# Lineups read off the print, in printed order — the canonical
# `instruments.Instrument.name` values, so a lexicon fault shows as an error
# rather than scoring as correct against itself. Same source as
# `omr-roster-wholework-2026-09/probe/score_full_systems.py`.
#
# ⚠️ BOTH SIZES ARE SCORED, and the 11-staff one is the arm that can LOSE.
# Pages 2+ print eleven staves because `Violoncello e Basso` share the last one;
# under the old rule those pages align 1:1 against an eleven-slot reference and
# are named by construction, while a twelve-slot reference makes `align` drop
# one slot somewhere and can slide the strings. Scoring only the full system
# would report the win and hide the cost.
TRUTHS = {
    "beet5": {
        12: ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
             "Timpani", "Violin", "Violin", "Viola", "Cello", "Contrabass"],
        # the condensed lineup: the last staff carries cellos AND basses, so
        # either name is scored correct on it.
        11: ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
             "Timpani", "Violin", "Violin", "Viola",
             ("Cello", "Contrabass")],
    },
}


def window_pages(spec):
    lo, _, hi = spec.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


def run(pdf, pages, dpi, mode):
    staved, labels = [], []
    for pi in pages:
        pws = detect_staves(render_page(pdf, pi, dpi=dpi))
        staved.append(pws)
        labels.append(labels_by_staff(S.read_staff_labels_surya(pws)))
    ref = assign_slots(staved, labels, most_labelled=mode)
    names = {s.index: s.instrument for s in ref}
    out = []
    for pi, pws in zip(pages, staved):
        by_system = defaultdict(list)
        for st in sorted(pws.staves, key=lambda s: s.top_y):
            by_system[st.system_index].append(st)
        for sysi, staves in sorted(by_system.items()):
            out.append({"page": pi, "system": sysi, "size": len(staves),
                        "slots": [st.slot_index for st in staves],
                        "named": [names.get(st.slot_index) for st in staves]})
    return len(ref), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--windows", nargs="+", default=["1", "0-2"])
    ap.add_argument("--modes", nargs="+", default=["off", "on", "pure"])
    ap.add_argument("--truth", default="")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    truth = TRUTHS.get(args.truth)
    if args.truth and truth is None:
        raise SystemExit(f"unknown truth {args.truth!r}")

    recs = []
    for spec in args.windows:
        pages = window_pages(spec)
        cache = {}
        for mode in args.modes:
            n_ref, systems = run(Path(args.pdf), pages, args.dpi, mode)
            scored = ""
            if truth:
                per_size = {}
                for s in systems:
                    want = truth.get(s["size"])
                    if want is None:
                        continue      # reduced system: which parts rest is a
                        # fact about the page and this harness does not know it
                    h, t = per_size.get(s["size"], (0, 0))
                    for got, w in zip(s["named"], want):
                        t += 1
                        h += 1 if (got == w or (isinstance(w, tuple)
                                                and got in w)) else 0
                    per_size[s["size"]] = (h, t)
                scored = "   " + "  ".join(
                    f"size {k}: {v[0]}/{v[1]}" for k, v in sorted(per_size.items())
                ) if per_size else "   (no scoreable system in this window)"
            print(f"pages {spec:6s} mode {mode:5s}  reference={n_ref} slots"
                  f"{scored}")
            for s in systems:
                print(f"    p{s['page']} sys{s['system']} size {s['size']:3d} "
                      f"slots={s['slots']}  names={s['named']}")
            recs.append({"window": spec, "mode": mode, "reference": n_ref,
                         "systems": systems,
                         "score": scored.strip() or None})
            cache[mode] = systems
        print()

    if args.json:
        Path(args.json).write_text(json.dumps(recs, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
