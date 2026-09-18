"""P1-P4 of PREREGISTRATION.md, from a committed record. No re-gather.

THE ONE STATISTIC. `Q.NOTEHEAD_STAFF_POSITION`'s VALUE is `pos_float`, kept
unrounded. The stored `residual` is `abs(...)` and CANNOT carry a sign, so it
is never read here -- the whole question is a direction.

    r_signed  = pos_float - round(pos_float)
    r_outward = +r_signed  below the staff   (pos grows downward)
                -r_signed  above the staff
                 undefined inside

so POSITIVE r_outward means "the grid placed this head FURTHER from the staff
than the nearest real position", which is what extrapolating at too WIDE a
pitch does.

⚠️ POSITIVE CONTROL. Every table prints its n, and the probe exits non-zero if
any population it was asked about is empty. Three clean believable zeros were
paid for on this thread already; a probe that can only print "no bias" is not
a probe.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recordstream import stream_array  # noqa: E402

TOP_LINE = 0.0
BOTTOM_LINE = 8.0
MIDDLE_LINE = 4.0


def outward(pos: float) -> float | None:
    """Signed residual, positive = away from the staff. None inside."""
    r = pos - round(pos)
    if pos < TOP_LINE:
        return -r
    if pos > BOTTOM_LINE:
        return r
    return None


def ledger_index(pos: float) -> float:
    """How many staff SPACES beyond the nearest staff edge line."""
    if pos < TOP_LINE:
        return (TOP_LINE - pos) / 2.0
    if pos > BOTTOM_LINE:
        return (pos - BOTTOM_LINE) / 2.0
    return 0.0


def band_of(pos: float) -> str:
    m = ledger_index(pos)
    if m == 0.0:
        return "inside the staff"
    if m <= 0.75:
        return "edge -> 1st ledger"
    if m <= 1.75:
        return "1st -> 2nd ledger"
    if m <= 2.75:
        return "2nd -> 3rd ledger"
    return "3rd ledger and beyond"

OUTSIDE = ("edge -> 1st ledger", "1st -> 2nd ledger",
           "2nd -> 3rd ledger", "3rd ledger and beyond")


def inside_control(pos: float) -> tuple[str, float]:
    """The control: the SAME statistic inside the staff, signed the same way
    (away from the staff's own middle line), banded by the same distance."""
    r = pos - round(pos)
    away = r if pos > MIDDLE_LINE else -r
    d = abs(pos - MIDDLE_LINE)
    band = ("0-1 from middle" if d <= 1 else
            "1-2 from middle" if d <= 2 else
            "2-3 from middle" if d <= 3 else "3-4 from middle")
    return band, away


def summarise(vals: list[float]) -> dict:
    return {"n": len(vals),
            "mean": round(statistics.fmean(vals), 4),
            "median": round(statistics.median(vals), 4),
            "stdev": round(statistics.stdev(vals), 4) if len(vals) > 1 else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True,
                    help="publisher/document, for the report only")
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    pos_of: dict[str, float] = {}
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "notehead_staff_position":
            continue
        try:
            pos_of[o["subject"]] = float(o["value"])
        except (TypeError, ValueError):
            continue

    proj: dict[str, str] = {}
    owner: dict[str, dict] = {}
    for v in stream_array(a.record, "verdicts"):
        q = v.get("quantity")
        if q == "stem_direction" and v.get("reason") == "stem_projection":
            proj[v["subject"]] = v.get("value")
        elif q == "glyph_owner":
            owner[v["subject"]] = v

    if not pos_of:
        print("DEAD: no notehead_staff_position observations", file=sys.stderr)
        return 2
    print(f"{a.label}: {len(pos_of)} heads with a position, "
          f"{len(proj)} with a projected stem direction")

    out: dict = {"label": a.label, "record": a.record,
                 "heads_with_position": len(pos_of)}

    # ── P1: outward drift beyond the staff, by ledger band ────────────────
    by_band: dict[str, list[float]] = collections.defaultdict(list)
    for s, p in pos_of.items():
        r = outward(p)
        if r is not None:
            by_band[band_of(p)].append(r)
    if not any(by_band.get(b) for b in OUTSIDE):
        print("DEAD: no head stands outside the staff", file=sys.stderr)
        return 2
    print("\n== P1  OUTWARD signed residual beyond the staff "
          "(+ = further out than the grid's nearest position)")
    print(f"{'band':<24} {'n':>6} {'mean':>8} {'median':>8} {'sd':>7}")
    out["p1_outside"] = {}
    for b in OUTSIDE:
        v = by_band.get(b)
        if not v:
            print(f"{b:<24} {0:>6}   (none)")
            out["p1_outside"][b] = {"n": 0}
            continue
        s = summarise(v)
        out["p1_outside"][b] = s
        print(f"{b:<24} {s['n']:>6} {s['mean']:>8.4f} {s['median']:>8.4f} "
              f"{(s['stdev'] if s['stdev'] is not None else float('nan')):>7.3f}")

    # ── P2: the inside-the-staff control ──────────────────────────────────
    ctrl: dict[str, list[float]] = collections.defaultdict(list)
    for s, p in pos_of.items():
        if outward(p) is None:
            b, away = inside_control(p)
            ctrl[b].append(away)
    print("\n== P2  CONTROL: the same statistic INSIDE the staff, signed away "
          "from the middle line")
    print(f"{'band':<24} {'n':>6} {'mean':>8} {'median':>8} {'sd':>7}")
    out["p2_inside"] = {}
    for b in ("0-1 from middle", "1-2 from middle",
              "2-3 from middle", "3-4 from middle"):
        v = ctrl.get(b)
        if not v:
            continue
        s = summarise(v)
        out["p2_inside"][b] = s
        print(f"{b:<24} {s['n']:>6} {s['mean']:>8.4f} {s['median']:>8.4f} "
              f"{(s['stdev'] if s['stdev'] is not None else float('nan')):>7.3f}")

    # ── the CONFOUND split: a head owned by ANOTHER staff has its position
    #    measured against the wrong lines, which is a different fault.
    split: dict[str, list[float]] = collections.defaultdict(list)
    for s, p in pos_of.items():
        r = outward(p)
        if r is None:
            continue
        v = owner.get(s)
        if v is None:
            k = "no ownership verdict"
        elif v.get("outcome") != "decided":
            k = "ownership abstained"
        else:
            from_key = s.rsplit("/", 2)[0] if s.count("/") >= 2 else s
            k = ("owned by ANOTHER staff"
                 if str(v.get("value")) not in ("", "None", from_key)
                 else "owned by this staff")
        split[k].append(r)
    print("\n== CONFOUND SPLIT: outward drift by what `glyph_owner` says")
    out["by_owner"] = {}
    for k in sorted(split):
        s = summarise(split[k])
        out["by_owner"][k] = s
        print(f"{k:<26} {s['n']:>6} {s['mean']:>8.4f}")

    # ── P4: does the drift separate the stem convention's own failures? ───
    conv: dict[str, list[float]] = collections.defaultdict(list)
    for s, p in pos_of.items():
        r = outward(p)
        d = proj.get(s)
        if r is None or d is None:
            continue
        if ledger_index(p) < 1.0:      # the `6+` band of the handoff's table
            continue
        want = "down" if p <= MIDDLE_LINE else "up"
        conv["convention RIGHT" if want == d else "convention WRONG"].append(r)
    print("\n== P4  beyond the 1st ledger: outward drift where the stem "
          "convention agrees vs disagrees")
    out["p4_convention"] = {}
    if not conv:
        print("  (no head beyond the 1st ledger carries a projected stem)")
        out["p4_convention"] = {"n": 0}
    for k in sorted(conv):
        s = summarise(conv[k])
        out["p4_convention"][k] = s
        print(f"{k:<26} {s['n']:>6} {s['mean']:>8.4f} {s['median']:>8.4f}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
