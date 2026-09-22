"""Would carrying a part's key across systems be RIGHT? — scored against the PRINT.

The reach was measured first (15 of 26 Litolff abstentions, 21 of 21 Breitkopf
sit on a part another system read). ⚠️ **Reach is not accuracy, and this repo
has been bitten by treating them as the same thing**, so this asks the second
question and nothing else.

THE RULE UNDER TEST, stated before it is scored: group staves into PARTS by the
pipeline's own `slot_index`; where some systems of a part DECIDED a key and
others abstained, carry the decided value to the abstaining staves. ⚠️ Where
the decided readings DISAGREE the carry REFUSES — there is no single answer to
carry, and picking one is the guess the whole reconciler exists not to make.

⚠️⚠️ **TWO SCORES, BECAUSE AN ABSTENTION IS NOT NEUTRAL IN THE FILE.** A staff
whose key abstains exports no `<key>` at all, which any reader takes as *no
accidentals*. So on a horn, trumpet or timpani — which print no signature —
abstaining is ACCIDENTALLY RIGHT, and this file already records that 17 of 33
"right" rows are exactly that. A carry that writes −3 onto such a staff makes
the file WORSE. Therefore:

  * READING  — did we name the right signature? (abstention = not named)
  * FILE     — what a reader of the exported MusicXML would see, where an
               abstention counts as 0 accidentals.

The FILE column is the one that decides whether to build this.

⚠️ A TRUTH-FREE CONTROL runs first: among parts whose systems decided a key
MORE THAN ONCE, do those readings agree? That needs no print and tests the
carry's own premise — a part keeps one signature down the page.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
TRUTH = Path("benchmarks/omr-keysig-truth-2026-09/truth.json")


def litolff_truth():
    """(page, system, staff_index) -> (instrument, fifths), from the PRINT."""
    t = json.loads(TRUTH.read_text())
    inst = t["instruments"]
    out = {}
    for s in t["systems"]:
        for i, name in enumerate(s["lineup"]):
            if name not in inst:
                raise SystemExit(f"REFUSED: lineup names {name!r}, truth does not")
            out[(s["page"], s["system"], i)] = (name, inst[name]["fifths"])
    return out


def load(record_path):
    d = json.loads(Path(record_path).read_text())["record"]
    keys, slots = {}, {}
    for v in d["verdicts"]:
        if v["quantity"] == "key_signature":
            keys[v["subject"]] = v
        elif v["quantity"] == "slot_index":
            slots[v["subject"]] = v
    return keys, slots


def main() -> int:
    truth = litolff_truth()
    keys, slots = load(REC / "beethoven5-p1-p4-ink-identity.record.json")

    rows = []
    for subj, kv in keys.items():
        _, p, s, i = subj.split("/")
        key = (int(p), int(s), int(i))
        if key not in truth:
            raise SystemExit(f"REFUSED: no truth for {subj}")
        name, tf = truth[key]
        sv = slots.get(subj)
        rows.append({
            "subject": subj, "instrument": name, "truth": tf,
            "decided": kv["outcome"] == "decided",
            "value": kv.get("value") if kv["outcome"] == "decided" else None,
            "slot": sv["value"] if sv and sv["outcome"] == "decided" else None,
        })

    print(f"REACH    {len(rows)} staves; "
          f"{sum(r['decided'] for r in rows)} decided, "
          f"{sum(not r['decided'] for r in rows)} abstained; "
          f"{sum(r['slot'] is None for r in rows)} have no named part")

    # ── how good is the reading TODAY, before any carry ──────────────────
    base_read = sum(r["decided"] and r["value"] == r["truth"] for r in rows)
    base_file = sum((r["value"] if r["decided"] else 0) == r["truth"] for r in rows)
    print(f"TODAY    reading right {base_read}/{len(rows)}; "
          f"FILE right {base_file}/{len(rows)}")

    # ── CONTROL, needs no truth: does a part agree with itself? ──────────
    parts = collections.defaultdict(list)
    for r in rows:
        if r["slot"] is not None:
            parts[r["slot"]].append(r)
    multi = {k: v for k, v in parts.items()
             if sum(x["decided"] for x in v) >= 2}
    agree = {k: v for k, v in multi.items()
             if len({x["value"] for x in v if x["decided"]}) == 1}
    print(f"CONTROL  parts decided on 2+ systems: {len(multi)}; "
          f"those whose readings AGREE: {len(agree)}")
    for k, v in sorted(multi.items()):
        vals = [x["value"] for x in v if x["decided"]]
        if len(set(vals)) > 1:
            print(f"   ⚠️ part {k} ({v[0]['instrument']}) disagrees: {vals}")

    # ── the carry ────────────────────────────────────────────────────────
    fixed = broken = already = still = refused = 0
    detail = []
    for slot, members in sorted(parts.items()):
        dec = [m for m in members if m["decided"]]
        ab = [m for m in members if not m["decided"]]
        if not dec or not ab:
            continue
        vals = {m["value"] for m in dec}
        if len(vals) > 1:
            refused += len(ab)
            detail.append((slot, members[0]["instrument"], "REFUSED (sources disagree)",
                           sorted(vals), None, len(ab)))
            continue
        carried = vals.pop()
        for m in ab:
            before_ok = (0 == m["truth"])          # abstention reads as no accidentals
            after_ok = (carried == m["truth"])
            if after_ok and not before_ok:
                fixed += 1
            elif before_ok and not after_ok:
                broken += 1
            elif before_ok and after_ok:
                already += 1
            else:
                still += 1
        detail.append((slot, members[0]["instrument"], "carry",
                       carried, ab[0]["truth"], len(ab)))

    print()
    print("CARRY, scored on the FILE a reader would open:")
    print(f"   staves it speaks for            : {fixed + broken + already + still}")
    print(f"   WRONG -> RIGHT  (the gain)      : {fixed}")
    print(f"   RIGHT -> WRONG  (the cost)      : {broken}")
    print(f"   right either way (no change)    : {already}")
    print(f"   wrong either way                : {still}")
    print(f"   refused, sources disagreed      : {refused}")
    print()
    print("per part:")
    for slot, inst, kind, carried, tf, n in detail:
        print(f"   slot {slot:>2} {inst:<20} {kind:<28} carry={carried} truth={tf} n={n}")

    (HERE / "out" / "litolff.json").write_text(json.dumps(
        {"staves": len(rows), "today_reading": base_read, "today_file": base_file,
         "fixed": fixed, "broken": broken, "already": already, "still": still,
         "refused": refused}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
