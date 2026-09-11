"""REACH FIRST: how many written `<tied>` land on a note carrying no tie.

⚠️ *A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.* So this runs
BEFORE the repair, over the exact `.omr.json` fixtures the A/B will re-export,
and prints a POSITIVE figure proving it reached the code (`chord_events`,
`tie_flag_events_*`) beside every zero.

It calls `voicing.group_chords_in_measure` — the function under repair — so a
reach figure here cannot drift from what the exporters do.

    python3 benchmarks/omr-chord-tie-2026-09/probe/reach.py <fixtures-dir>...
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.voicing import group_chords_in_measure  # noqa: E402

KEYS = ("tied_to_next", "tied_from_prev")


def _measures(result: dict):
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    yield measure


def tally(result: dict) -> dict:
    t = {k: 0 for k in (
        "events", "chord_events", "notes", "chord_notes",
        "tie_flag_events_to_next", "tie_flag_events_from_prev",
        "tie_to_next_on_an_unflagged_note", "tie_from_prev_on_an_unflagged_note",
        "tie_to_next_event_with_no_flagged_note",
        "tie_from_prev_event_with_no_flagged_note",
        "under_emitted_to_next", "under_emitted_from_prev",
    )}
    for measure in _measures(result):
        for ev in group_chords_in_measure(measure.get("detections", [])):
            t["events"] += 1
            heads = ev.get("noteheads") or []
            if ev.get("kind") == "rest" or not heads:
                continue
            t["notes"] += len(heads)
            if len(heads) > 1:
                t["chord_events"] += 1
                t["chord_notes"] += len(heads)
            for key in KEYS:
                if not ev.get(key):
                    continue
                short = key.replace("tied_", "")
                t[f"tie_flag_events_{short}"] += 1
                flagged = [i for i, h in enumerate(heads) if h.get(key)]
                if not flagged:
                    # The event flag is set and NO head carries it. Only
                    # reachable from a hand-built event — measured, not assumed.
                    t[f"tie_{short}_event_with_no_flagged_note"] += 1
                    continue
                if 0 not in flagged:
                    # Today's renderers write it at head 0 — the WRONG note.
                    t[f"tie_{short}_on_an_unflagged_note"] += 1
                # A second flagged head gets no element at all today.
                t[f"under_emitted_{short}"] += len(flagged) - 1
    return t


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    files: list[pathlib.Path] = []
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json` found. A missing fixture "
                         "reads as a zero.\n")
        return 2
    pooled: dict[str, int] = {}
    for f in files:
        t = tally(json.loads(f.read_text()))
        for k, v in t.items():
            pooled[k] = pooled.get(k, 0) + v
        print(f"{f.name[:52]:54s} "
              f"chords={t['chord_events']:5d} "
              f"to_next={t['tie_flag_events_to_next']:4d} "
              f"wrong={t['tie_to_next_on_an_unflagged_note']:4d} "
              f"from_prev={t['tie_flag_events_from_prev']:4d} "
              f"wrong={t['tie_from_prev_on_an_unflagged_note']:4d}")
    print(f"\n{len(files)} files")
    for k in sorted(pooled):
        print(f"  {k:44s} {pooled[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
