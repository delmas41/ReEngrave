"""ROADMAP 2.39b -- per-consumer changed-row diff between a base (2.39's
first half, `claude/acceptance-measure-notehead-box-e75821`) and a new
(2.39b) GATHER-through-ADJUDICATE record on the SAME page, SAME weights,
SAME settings -- the same shape as `diff_2.39_ab.py`, extended with:

  - the `Q.NOTEHEAD_RECENTRE` population itself (observed / declined by
    reason / a shift histogram), which the base record cannot carry at
    all (item 2's own proof obligation);
  - a STAFF-POSITION measurement (item 3's own scope boundary): how many
    regular noteheads' ROUNDED `Q.NOTEHEAD_STAFF_POSITION` WOULD change if
    a future round moved the position reader onto the re-centred centre
    -- computed, never wired, exactly as the brief asks.

Usage: python3 diff_2.39b_ab.py base.json new.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

VERDICT_QUANTITIES = [
    "notehead_is_not_a_notehead", "glyph_owner", "duration",
    "notehead_is_a_whole_rest", "stem", "beam_stroke",
]
OBSERVATION_QUANTITIES = ["ledger_rung_ink", "notehead_ink",
                         "ledger_owner_density", "stem", "beam_stroke"]


def _load(path):
    with open(path) as f:
        return json.load(f)["record"]


def _verdict_index(record, quantity):
    out = {}
    for v in record["verdicts"]:
        if v["quantity"] == quantity:
            out[v["subject"]] = v
    return out


def _obs_index(record, quantity):
    out = defaultdict(list)
    for o in record["observations"]:
        if o["quantity"] == quantity:
            out[o["subject"]].append(o)
    return out


def diff_verdicts(base, new, quantity):
    b = _verdict_index(base, quantity)
    n = _verdict_index(new, quantity)
    subjects = sorted(set(b) | set(n))
    changed = []
    for s in subjects:
        bv, nv = b.get(s), n.get(s)
        b_key = None if bv is None else (bv["outcome"], bv["value"], bv["reason"])
        n_key = None if nv is None else (nv["outcome"], nv["value"], nv["reason"])
        if b_key != n_key:
            changed.append((s, b_key, n_key))
    return changed


def diff_observation_counts(base, new, quantity):
    b = _obs_index(base, quantity)
    n = _obs_index(new, quantity)
    subjects = sorted(set(b) | set(n))
    changed = []
    for s in subjects:
        bl, nl = len(b.get(s, [])), len(n.get(s, []))
        bv = [round(o["value"], 4) if isinstance(o["value"], float) else o["value"]
              for o in b.get(s, [])]
        nv = [round(o["value"], 4) if isinstance(o["value"], float) else o["value"]
              for o in n.get(s, [])]
        if bl != nl or sorted(map(str, bv)) != sorted(map(str, nv)):
            changed.append((s, bv, nv))
    return changed


def recentre_population(new):
    obs = [o for o in new["observations"] if o["quantity"] == "notehead_recentre"]
    abst = [a for a in new["abstentions"] if a["quantity"] == "notehead_recentre"]
    reasons = Counter(a["reason"] for a in abst)
    dy_hist = Counter(round(o["value"][1], 1) for o in obs)
    dx_hist = Counter(round(o["value"][0], 1) for o in obs)
    fills = [o["detail"]["fill"] for o in obs if o.get("detail")]
    return {
        "observed": len(obs), "declined": len(abst),
        "declined_by_reason": dict(reasons),
        "dy_histogram": dict(sorted(dy_hist.items())),
        "dx_histogram": dict(sorted(dx_hist.items())),
        "fill_min": round(min(fills), 4) if fills else None,
        "fill_median": (round(sorted(fills)[len(fills) // 2], 4)
                        if fills else None),
    }


def staff_position_swing(new):
    """Item 3's own scope boundary, MEASURED not wired: for every regular
    notehead carrying both `Q.NOTEHEAD_RECENTRE` (accepted) and
    `Q.NOTEHEAD_STAFF_POSITION`, would a re-centred dy change the ROUNDED
    staff position? `Q.NOTEHEAD_STAFF_POSITION.value` is already in
    half-step units (`detail.rounded` is `round(value)`); a staff SPACE is
    two half-steps, so a `dy_sp` shift (staff spaces) moves the raw value
    by `2 * dy_sp` half-steps before rounding -- no grid re-derivation, the
    position reader's own unit is used as filed.
    """
    recentre = {o["subject"]: o for o in new["observations"]
               if o["quantity"] == "notehead_recentre"}
    positions = {o["subject"]: o for o in new["observations"]
                if o["quantity"] == "notehead_staff_position"}
    changed = []
    checked = 0
    for subject, pos in positions.items():
        r = recentre.get(subject)
        if r is None:
            continue
        checked += 1
        dy_sp = r["value"][1]
        old_rounded = round(pos["value"])
        new_rounded = round(pos["value"] + 2 * dy_sp)
        if old_rounded != new_rounded:
            changed.append((subject, old_rounded, new_rounded))
    return {"checked": checked, "would_change": len(changed),
            "examples": changed[:10]}


def main():
    base_path, new_path = sys.argv[1], sys.argv[2]
    base, new = _load(base_path), _load(new_path)
    print(f"base={base_path} new={new_path}")
    print("-- notehead_recentre population (new arm only) --")
    print(json.dumps(recentre_population(new), indent=2))
    print("-- staff-position swing (new arm only, MEASURED not wired) --")
    print(json.dumps(staff_position_swing(new), indent=2))
    print("-- per-consumer verdict/observation deltas --")
    for q in VERDICT_QUANTITIES:
        changed = diff_verdicts(base, new, q)
        print(f"  verdict {q}: {len(changed)} changed rows")
        for s, bk, nk in changed[:20]:
            print(f"    {s}: base={bk} new={nk}")
    for q in OBSERVATION_QUANTITIES:
        changed = diff_observation_counts(base, new, q)
        print(f"  observation {q}: {len(changed)} changed subjects")
        for s, bv, nv in changed[:10]:
            print(f"    {s}: base={bv} new={nv}")


if __name__ == "__main__":
    main()
