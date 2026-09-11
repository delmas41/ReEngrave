"""Is the RECORD's tie pairing pitch-consistent? A no-truth-file check.

⚠️ THE REPAIR EXPOSED THIS AND DID NOT CAUSE IT. `transcribe._pair_ties_in_staff`
sets `tied_to_next` on a LEFT notehead and `tied_from_prev` on a RIGHT one by
GEOMETRY, and records no link between them. MusicXML `<tied>` carries no
`number=` and resolves BY PITCH, so a pairing that binds two different pitches
cannot be written correctly by any renderer. The old chord hoist wrote both
ends at the chord's LOWEST note, which MASKED such a pairing whenever the two
chords shared their bottom pitch.

This walks the exported-event stream of a stored `.omr.json` and asks, for each
event carrying a `tied_to_next` head, whether the NEXT event of that voice
carries a `tied_from_prev` head of the SAME PITCH.

    python3 .../pairing_pitches.py <fixtures-dir-or-file>... [--list]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.voicing import group_chords_in_measure  # noqa: E402


def _staff_streams(result: dict):
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                events = []
                for measure in staff.get("measures", []):
                    events += group_chords_in_measure(
                        measure.get("detections", []))
                yield events


def tally(result: dict, listing: list) -> collections.Counter:
    c: collections.Counter = collections.Counter()
    for events in _staff_streams(result):
        for i, ev in enumerate(events):
            heads = ev.get("noteheads") or []
            left = [h for h in heads if h.get("tied_to_next")]
            if not left:
                continue
            c["links_from"] += len(left)
            nxt = events[i + 1] if i + 1 < len(events) else None
            right = [h for h in (nxt.get("noteheads") or [])
                     if h.get("tied_from_prev")] if nxt else []
            if not right:
                c["no_next_event_end"] += len(left)
                continue
            rp = {h.get("pitch") for h in right}
            for h in left:
                if h.get("pitch") in rp:
                    c["same_pitch"] += 1
                else:
                    c["DIFFERENT_pitch"] += 1
                    listing.append((h.get("pitch"), sorted(p for p in rp)))
    return c


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--list"]
    listing_on = "--list" in sys.argv
    files: list[pathlib.Path] = []
    for a in args:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json` found.\n")
        return 2
    pooled: collections.Counter = collections.Counter()
    for f in files:
        listing: list = []
        c = tally(json.loads(f.read_text()), listing)
        pooled += c
        print(f"{f.name[:52]:54s} from={c['links_from']:4d} "
              f"same={c['same_pitch']:4d} DIFF={c['DIFFERENT_pitch']:4d} "
              f"no_end={c['no_next_event_end']:4d}")
        if listing_on:
            for a, b in listing[:6]:
                print(f"      {a} -> {b}")
    print("\n  pooled: " + "  ".join(f"{k}={v}" for k, v in sorted(pooled.items())))
    if not pooled["links_from"]:
        sys.stderr.write("⚠️ ZERO tie links — a dead instrument.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
