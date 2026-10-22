"""What does the PAGE print — ties, or slurs? The confound the tie work missed.

`pairing_pitches.py` measured that a quarter of the tie links bind two
different pitches and named the PAIRING as the suspect, on the reasoning that
an engraved page's pitch reading is near-perfect so nothing else is left.
There is a third suspect it did not list: the arc's CLASS. A tie and a slur
are the same glyph, so a page that prints many slurs and few ties gives the
detector many chances to call a slur a tie, and every such arc lands on two
notes of different pitch BECAUSE THAT IS WHAT A SLUR DOES.

This counts, per work, what the TRUTH encoding prints — `<tied>` against
`<slur>` — beside what we detect and what fraction of our pairings bind two
pitches. No geometry, no pairing: just the population.

⚠️ A `<tied>` element is written at BOTH ends of one tie and a `<slur>` at both
ends of one slur, so both counts are halved here and the ratio is unaffected
either way. Reported as elements AND as the derived ratio so neither reading
can be mistaken for the other.

    python3 .../arc_population.py <fixtures-dir>
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from geometry import walk  # noqa: E402


def truth_arcs(path: pathlib.Path) -> tuple[int, int]:
    text = path.read_text(errors="replace")
    return (len(re.findall(r"<tied[ />]", text)),
            len(re.findall(r"<slur[ />]", text)))


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("FATAL: give a fixtures dir\n")
        return 2
    root = pathlib.Path(sys.argv[1])
    rows = []
    for omr in sorted(root.glob("*.omr.json")):
        stem = omr.name[: -len(".omr.json")]
        truth = root / f"{stem}.musicxml"
        if not truth.is_file():
            continue
        t_tied, t_slur = truth_arcs(truth)
        det_tie = det_slur = 0
        result = json.loads(omr.read_text())
        for page in result.get("pages", []):
            for sys_ in page.get("systems", []):
                for staff in sys_.get("staves", []):
                    for m in staff.get("measures", []):
                        for d in m.get("detections", []):
                            cl = (d.get("class") or "").lower()
                            if cl == "tie":
                                det_tie += 1
                            elif cl == "slur":
                                det_slur += 1
        same = diff = 0
        for r in walk(result):
            left, right = r["pick_l"], r["pick_r"]
            if left is None or right is None or left[2] is right[2]:
                continue
            pl, pr = left[2].get("pitch"), right[2].get("pitch")
            if pl is not None and pl == pr:
                same += 1
            else:
                diff += 1
        rows.append((stem, t_tied, t_slur, det_tie, det_slur, same, diff))
    if not rows:
        sys.stderr.write("FATAL: no fixture pair found — a dead instrument.\n")
        return 2
    print(f"{'work':30s} {'truth<tied>':>11s} {'truth<slur>':>11s} "
          f"{'slur share':>10s} | {'det tie':>7s} {'det slur':>8s} | "
          f"{'same':>4s} {'DIFF':>4s} {'DIFF rate':>9s}")
    for stem, tt, ts, dt, ds, same, diff in rows:
        share = (ts / (tt + ts)) if (tt + ts) else float("nan")
        rate = (diff / (same + diff)) if (same + diff) else float("nan")
        print(f"{stem[:30]:30s} {tt:11d} {ts:11d} {share:10.3f} | "
              f"{dt:7d} {ds:8d} | {same:4d} {diff:4d} {rate:9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
