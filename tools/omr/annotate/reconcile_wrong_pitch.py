"""Reconcile wrong_pitch verdict entries with the current matcher output.

When the user marks a notehead as TP-but-wrong-pitch, the verdict stores
`wrong_pitch: <correct_pitch>`. If the matcher's resolved pitch later
catches up to that value (e.g., because the user changed the cell's clef
or pitch_resolver got smarter), the `wrong_pitch` correction is no longer
needed — the matcher now agrees with the user. This script clears those
stale entries so the scorer credits the matcher for the right pitch.

A `wrong_pitch` entry is kept if the matcher's current pitch still differs
from the user's correction.

CLI:
    python3 -m tools.omr.annotate.reconcile_wrong_pitch \
        [--verdicts-dir benchmarks/omr-phase2.5/verdicts] \
        [--detections-dir benchmarks/omr-phase2.5/detections] \
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _normalize_pitch(p: str | None) -> str:
    if not p:
        return ""
    return p.strip().replace("♭", "b").replace("♯", "#").upper()


def _parse_pitch(p: str | None) -> tuple[str, int, int] | None:
    """Parse a pitch like "C4", "F#5", "Bb3", "C##4", "Dbb2" into
    (step, alter, octave). Returns None if unparseable.

    alter: -2 = double-flat, -1 = flat, 0 = natural, 1 = sharp, 2 = double-sharp.
    """
    if not p:
        return None
    s = p.strip().replace("♭", "b").replace("♯", "#")
    if not s:
        return None
    step = s[0].upper()
    if step not in {"C", "D", "E", "F", "G", "A", "B"}:
        return None
    rest = s[1:]
    alter = 0
    i = 0
    while i < len(rest) and rest[i] in {"#", "b"}:
        alter += 1 if rest[i] == "#" else -1
        i += 1
    octave_str = rest[i:].strip()
    # Handle negative octaves like "C-1" if they ever show up.
    if not octave_str:
        return None
    try:
        octave = int(octave_str)
    except ValueError:
        return None
    return (step, alter, octave)


def _accidental_only_difference(matcher_pitch: str | None, user_pitch: str | None) -> bool:
    """True iff the two pitches have the same step + octave but different
    alter. E.g. (C4, C#4) → True; (C4, D4) → False; (C4, Db4) → False
    (different step). The notehead's "step" is what the matcher assigns
    from staff position; the alter comes from a separate accidental
    detection, so an alter-only difference is not a notehead error.
    """
    a = _parse_pitch(matcher_pitch)
    b = _parse_pitch(user_pitch)
    if a is None or b is None:
        return False
    step_a, alter_a, oct_a = a
    step_b, alter_b, oct_b = b
    return (step_a == step_b) and (oct_a == oct_b) and (alter_a != alter_b)


def reconcile_one(verdict_path: Path, detections_dir: Path, dry_run: bool = False) -> dict:
    state = json.loads(verdict_path.read_text())
    cid = state["cell_id"]
    det_path = detections_dir / f"{cid}.json"
    if not det_path.exists():
        return {"cell_id": cid, "skipped": "no detections JSON"}
    dets = json.loads(det_path.read_text())
    det_by_id = {d["id"]: d for d in dets.get("detections", [])}

    cleared = []
    cleared_accidental = []
    kept = []
    for v in state["verdicts"]:
        wp = v.get("wrong_pitch")
        if not wp:
            continue
        det = det_by_id.get(v["detection_id"])
        if det is None:
            kept.append((v["detection_id"], wp, "no matching detection"))
            continue
        cur = det.get("pitch")
        if _normalize_pitch(cur) == _normalize_pitch(wp):
            cleared.append((v["detection_id"], wp))
            if not dry_run:
                v.pop("wrong_pitch", None)
        elif _accidental_only_difference(cur, wp):
            # Same staff position (step+octave), different alter. The notehead
            # matcher's job is staff-position-to-step; accidentals are a
            # separate detection. So this is NOT a notehead error.
            cleared_accidental.append((v["detection_id"], cur, wp))
            if not dry_run:
                v.pop("wrong_pitch", None)
        else:
            kept.append((v["detection_id"], wp, f"matcher still says {cur}"))

    if cleared and not dry_run:
        verdict_path.write_text(json.dumps(state, indent=2))

    return {
        "cell_id": cid,
        "cleared": cleared,
        "cleared_accidental": cleared_accidental,
        "kept": kept,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts-dir", default="benchmarks/omr-phase2.5/verdicts")
    ap.add_argument("--detections-dir", default="benchmarks/omr-phase2.5/detections")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vdir = Path(args.verdicts_dir)
    ddir = Path(args.detections_dir)
    total_cleared = 0
    total_cleared_accidental = 0
    total_kept = 0

    for vp in sorted(vdir.glob("*.verdict.json")):
        result = reconcile_one(vp, ddir, dry_run=args.dry_run)
        if result.get("skipped"):
            continue
        cleared = result["cleared"]
        cleared_accidental = result.get("cleared_accidental", [])
        kept = result["kept"]
        if not cleared and not cleared_accidental and not kept:
            continue
        print(f"{result['cell_id']}:")
        for did, wp in cleared:
            verb = "would clear" if args.dry_run else "cleared"
            print(f"  {verb} {did} (wrong_pitch={wp} matches matcher exactly)")
        for did, cur, wp in cleared_accidental:
            verb = "would clear" if args.dry_run else "cleared"
            print(f"  {verb} {did} (matcher={cur}, user={wp} — accidental-only diff, not a notehead error)")
        for did, wp, reason in kept:
            print(f"  kept {did} (wrong_pitch={wp}: {reason})")
        total_cleared += len(cleared)
        total_cleared_accidental += len(cleared_accidental)
        total_kept += len(kept)

    suffix = " (dry-run, no files written)" if args.dry_run else ""
    print(f"\nsummary: cleared {total_cleared} exact + "
          f"{total_cleared_accidental} accidental-only, "
          f"kept {total_kept}{suffix}")


if __name__ == "__main__":
    main()
