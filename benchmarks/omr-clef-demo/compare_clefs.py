"""Compare per-staff clef reads between two OMR JSON outputs (production vs fine-tuned).

Also derives, per staff, the median notehead pitch (as a MIDI-ish diatonic step
proxy) so a human can sanity-check whether the read clef is plausible for the
register the notes actually sit in.

Usage:
    python3 compare_clefs.py prod.omr.json ft.omr.json
    python3 compare_clefs.py prod.omr.json            # single file
"""
from __future__ import annotations

import json
import re
import sys
from statistics import median

_PITCH_RE = re.compile(r"^([A-Ga-g])([#b]*)(-?\d+)$")


def _diatonic(pitch) -> float | None:
    """Note-name string ('F3', 'C#4', 'Bb2') → diatonic step value (7 per octave).

    NOTE: pitch is derived under the *assumed* clef, so this is a soft signal:
    the same physical notehead yields different values under different clefs.
    """
    if isinstance(pitch, (int, float)):
        return float(pitch)
    if not isinstance(pitch, str):
        return None
    m = _PITCH_RE.match(pitch.strip())
    if not m:
        return None
    step = m.group(1).upper()
    octave = int(m.group(3))
    return "CDEFGAB".index(step) + 7 * octave


def staff_rows(path: str) -> list[dict]:
    d = json.load(open(path))
    rows = []
    gi = 0  # global staff index across systems
    for pg in d["pages"]:
        for sysr in pg["systems"]:
            for st in sysr["staves"]:
                # collect notehead pitches if present
                pitches = []
                for m in st.get("measures", []):
                    for det in m.get("detections", []):
                        if det.get("category") == "notehead":
                            v = _diatonic(det.get("pitch"))
                            if v is not None:
                                pitches.append(v)
                rows.append({
                    "gi": gi,
                    "sys": sysr["system_index"],
                    "staff": st["staff_index"],
                    "clef": st.get("clef"),
                    "n_meas": st.get("n_measures"),
                    "n_notes": len(pitches),
                    "pitch_med": round(median(pitches), 1) if pitches else None,
                    "pitch_lo": min(pitches) if pitches else None,
                    "pitch_hi": max(pitches) if pitches else None,
                })
                gi += 1
    return rows


def main(argv: list[str]) -> int:
    prod = staff_rows(argv[1])
    ft = staff_rows(argv[2]) if len(argv) > 2 else None

    if ft is None:
        print(f"{'idx':>3} {'sys':>3} {'st':>3} {'clef':>8} {'#m':>3} {'#n':>4} "
              f"{'pmed':>6} {'plo':>5} {'phi':>5}")
        for r in prod:
            print(f"{r['gi']:>3} {r['sys']:>3} {r['staff']:>3} {str(r['clef']):>8} "
                  f"{r['n_meas']:>3} {r['n_notes']:>4} {str(r['pitch_med']):>6} "
                  f"{str(r['pitch_lo']):>5} {str(r['pitch_hi']):>5}")
        dist = {}
        for r in prod:
            dist[r["clef"]] = dist.get(r["clef"], 0) + 1
        print("\nclef distribution:", dist)
        return 0

    # side-by-side
    print(f"{'idx':>3} {'PROD clef':>10} {'FT clef':>10}  {'changed':>7}  "
          f"{'#notes':>6} {'pmed':>6} {'plo':>5} {'phi':>5}")
    n_changed = 0
    for rp, rf in zip(prod, ft):
        changed = "*" if rp["clef"] != rf["clef"] else ""
        if changed:
            n_changed += 1
        print(f"{rp['gi']:>3} {str(rp['clef']):>10} {str(rf['clef']):>10}  "
              f"{changed:>7}  {str(rf['n_notes']):>6} {str(rf['pitch_med']):>6} "
              f"{str(rf['pitch_lo']):>5} {str(rf['pitch_hi']):>5}")
    dp, df = {}, {}
    for r in prod:
        dp[r["clef"]] = dp.get(r["clef"], 0) + 1
    for r in ft:
        df[r["clef"]] = df.get(r["clef"], 0) + 1
    print(f"\nPROD clef distribution: {dp}")
    print(f"FT   clef distribution: {df}")
    print(f"staves with changed clef: {n_changed}/{len(prod)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
