"""THE DENOMINATOR SEAN'S COMPLAINT NEEDS: bars the PAGE prints SILENT.

⚠️ Every count in the 2026-09-11 handoff (118 / 44 / 26) is defined by OUR
OUTPUT -- "a bar whose entire content is one pitched note". That set can only
ever be an upper bound on *a note where the page prints silence*, because a bar
we under-read looks exactly the same from the file. The population the fault is
actually about is defined by the PRINT: a bar whose only mark is one centred
whole rest.

This probe walks every bar of every staff of one printed system, asks the crop
what the print holds (`print_ink.census`), keeps the bars whose only mark is a
whole rest, and reports what OUR FILE wrote in each of them. That gives a rate
with an honest denominator, and it is the number a repair should be measured
against.

⚠️ It refuses unless the crop's own staff and barline grids agree with the
exporter's system map, for the reason `bar_crop` gives.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bar_crop import barlines, staves_of  # noqa: E402
from locate import SYSMAP, index  # noqa: E402
from population import ARTEFACT, bars  # noqa: E402
from print_ink import census, looks_like  # noqa: E402
from steps import step_of  # noqa: E402

#: A stem or a slur belonging to the NEIGHBOURING staff reaches into this
#: staff's band, so "the only mark" cannot mean "the only blob". A stem is
#: TALL AND THIN -- at least this many staff spaces high and under a third of
#: a space wide -- and is excluded from the count rather than from the crop,
#: so the exclusion is visible in the record.
INTRUDER_MIN_H_SPACES = 1.6
INTRUDER_MAX_W_SPACES = 0.45


def is_intruder(b):
    return (b["h_spaces"] >= INTRUDER_MIN_H_SPACES
            and b["w_spaces"] <= INTRUDER_MAX_W_SPACES)


def what_we_wrote(r):
    if r is None:
        return "NO MEASURE"
    ev = r["events"]
    if not ev:
        return "empty"
    if len(ev) == 1 and ev[0]["measure_rest"]:
        return "measure rest"
    pitched = [e for e in ev if e["pitch"]]
    rests = [e for e in ev if not e["pitch"]]
    if pitched and not rests:
        return ("PITCHED NOTE" if len(pitched) == 1
                else f"{len(pitched)} PITCHED NOTES")
    if rests and not pitched:
        return f"{len(rests)} rest(s)"
    return f"{len(pitched)} note(s) + {len(rests)} rest(s)"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crop", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, required=True)
    ap.add_argument("--xml", default=str(ARTEFACT))
    ap.add_argument("--sysmap", default=str(SYSMAP))
    ap.add_argument("--bl-frac", type=float, default=0.80)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    where, _ = index(json.loads(Path(a.sysmap).read_text()))
    by_key = {(r["part"], r["number"]): r for r in bars(a.xml)}

    # The system map, inverted: (staff, bar_in_system) -> the exported measure.
    here = {}
    for (pid, num), w in where.items():
        if w["page"] == a.page and w["system"] == a.system:
            here[(w["staff"], w["bar_in_system"])] = (pid, num)
    if not here:
        print("DEAD: the system map holds no such system", file=sys.stderr)
        return 2
    n_staves = 1 + max(s for s, _ in here)
    n_bars = 1 + max(b for _, b in here)

    im = Image.open(a.crop)
    sts = staves_of(im)
    bl = barlines(im, sts[0][0], sts[-1][4], frac=a.bl_frac)
    print(f"REACH  crop staves={len(sts)} vs map {n_staves}; "
          f"crop bars={len(bl)-1} vs map {n_bars}")
    if len(sts) != n_staves or len(bl) - 1 != n_bars:
        print("REFUSED: grids disagree", file=sys.stderr)
        return 3

    silent, rows = [], []
    for s in range(n_staves):
        for b in range(n_bars):
            blobs = [x for x in census(im, sts[s], bl[b], bl[b + 1])
                     if not is_intruder(x)]
            key = here.get((s, b))
            wrote = what_we_wrote(by_key.get(key) if key else None)
            only_rest = (len(blobs) == 1
                         and looks_like(blobs[0]) == "REST-SHAPED")
            rows.append(dict(staff=s, bar=b, part=key[0] if key else None,
                             measure=key[1] if key else None,
                             n_blobs=len(blobs), print_silent=only_rest,
                             wrote=wrote, blobs=blobs[:3],
                             pitches=[e["pitch"] for e in
                                      (by_key.get(key) or {}).get("events", [])
                                      if e["pitch"]],
                             clef=(where.get(key) or {}).get("clef") if key else None))
            if only_rest:
                silent.append(rows[-1])

    print(f"\nbars on this system                : {len(rows)}")
    print(f"bars the PRINT shows as ONE REST-SHAPED MARK and nothing else: {len(silent)}")
    if not silent:
        print("DEAD: no print-silent bar found -- the instrument cannot speak "
              "about this system", file=sys.stderr)
        return 2

    c = collections.Counter(r["wrote"] for r in silent)
    print("\nwhat OUR FILE writes in those bars:")
    for k, v in c.most_common():
        mark = "  <-- A NOTE WHERE THE PAGE PRINTS SILENCE" if "PITCHED" in k else ""
        print(f"   {k:<24} {v:>3}{mark}")

    print("\nthe offending bars:")
    for r in silent:
        if "PITCHED" in r["wrote"]:
            st = [step_of(p, r["clef"]) for p in r["pitches"]]
            inside = sum(1 for x in st if x is not None and 0 <= x <= 8)
            at_slot = sum(1 for x in st if x in (5, 6))
            print(f"   {r['part']} m{r['measure']}  staff {r['staff']} bar {r['bar']}"
                  f"  -> {r['wrote']:<16} pitches={r['pitches']} "
                  f"steps={st} inside_staff={inside}/{len(st)} at_rest_slot={at_slot}")

    # ⚠️ THE PARTITION IS THE RESULT, not the count. A note standing where the
    # page prints one rest came from SOMEWHERE, and the staff step says where:
    # at the whole rest's own slot it is that rest's ink read as a notehead;
    # outside the staff entirely it cannot be the rest and must have entered
    # through the measure cell's padding from a neighbour.
    slot = outside = elsewhere = 0
    for r in silent:
        if "PITCHED" not in r["wrote"]:
            continue
        for st in (step_of(x, r["clef"]) for x in r["pitches"]):
            if st is None:
                continue
            if st in (5, 6):
                slot += 1
            elif st < 0 or st > 8:
                outside += 1
            else:
                elsewhere += 1
    tot = slot + outside + elsewhere
    print(f"\nthe {tot} phantom NOTES, by where they stand on the staff:")
    print(f"   at the WHOLE REST's own slot (step 5-6) : {slot}")
    print(f"   OUTSIDE the staff (step <0 or >8)       : {outside}")
    print(f"   inside the staff, elsewhere             : {elsewhere}")

    if a.json_out:
        Path(a.json_out).write_text(json.dumps(rows, indent=1))
        print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
