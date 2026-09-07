"""STEP 1 — does the shared-delta property hold in the reference encodings?

Sean's claim: `fifths_offset` is defined as *written key = concert key +
offset* (`tools/omr/instruments.py:13`), so at a genuine key change

    written'[staff] - written[staff] = concert' - concert = Δ   for EVERY staff

The offsets cancel. If it holds, a mid-staff key change can be corroborated by
its VALUE and not only by its BAR — and, decisively, WITHOUT knowing which
staff is the clarinet.

This measures it on `library/reference/`, which is ground truth independent of
OMR and free to read. It reports the rate AND the exception taxonomy, because
a rule that holds 95% of the time with a KNOWN detectable 5% is usable and one
that holds 95% for unknown reasons is not.

Outputs `out/shared-delta.json` and a table on stdout. Exits 2 on an empty
fixture set.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _refs import encodings, root          # noqa: E402  fail-loud
from keys import load_keys                 # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def analyse(sk) -> dict:
    """Every bar at which any staff states a key change, with its taxonomy."""
    n = sk.n_measures
    eff = {id(st): st.effective(n) for st in sk.staves}

    # A staff's FIRST stated key is its opening signature, not a change.
    changes: dict[int, list[dict]] = defaultdict(list)
    restated_same: dict[int, list[dict]] = defaultdict(list)
    for sidx, st in enumerate(sk.staves):
        prev: int | None = None
        seen_any = False
        for ordinal in sorted(set(st.stated) | st.nontraditional):
            if ordinal in st.nontraditional and ordinal not in st.stated:
                prev = None
                seen_any = True
                continue
            val = st.stated[ordinal]
            if seen_any and prev is not None and val != prev:
                changes[ordinal].append({
                    "i": sidx,
                    "part": st.part_name or st.part_id,
                    "staff": st.staff,
                    "before": prev,
                    "after": val,
                    "delta": val - prev,
                })
            elif seen_any and prev is not None:
                restated_same[ordinal].append({
                    "i": sidx, "part": st.part_name or st.part_id,
                    "staff": st.staff, "value": val,
                })
            prev = val
            seen_any = True

    events = []
    for ordinal in sorted(changes):
        changers = changes[ordinal]
        deltas = {c["delta"] for c in changers}
        # Classify every staff that did NOT change at this bar.
        silent = []
        changed_idx = {c["i"] for c in changers}
        for sidx, st in enumerate(sk.staves):
            key = (st.part_name or st.part_id, st.staff)
            if sidx in changed_idx:
                continue
            reasons = []
            if not st.stated and not st.nontraditional:
                reasons.append("no_key_ever")            # unpitched / percussion
            if st.nontraditional:
                reasons.append("nontraditional_key")
            first_stated = min(st.stated) if st.stated else None
            if first_stated is not None and first_stated > ordinal:
                reasons.append("enters_later")
            if not st.any_note:
                reasons.append("never_plays")
            elif ordinal not in st.any_note:
                reasons.append("no_note_in_bar")
            elif ordinal not in st.sounding:
                reasons.append("resting_in_bar")
            if any(r["i"] == sidx for r in restated_same.get(ordinal, [])):
                reasons.append("restated_same_key")
            if st.transpose_at(ordinal) != st.transpose_at(max(ordinal - 1, 0)):
                reasons.append("transposition_changes")
            if not reasons:
                reasons.append("PRESENT_AND_SILENT")
            silent.append({"part": key[0], "staff": key[1],
                           "reasons": reasons,
                           "key_here": eff[id(st)][ordinal]})
        # A crook change breaks the identity by construction — name it.
        crook = [c for c in changers
                 if ordinal in sk.staves[c["i"]].transpose]
        events.append({
            "ordinal": ordinal,
            "measure_number": (sk.measure_numbers[ordinal]
                               if ordinal < len(sk.measure_numbers) else ""),
            "n_staves": len(sk.staves),
            "n_changing": len(changers),
            "deltas": sorted(deltas),
            "agree": len(deltas) == 1,
            "changers": changers,
            "silent": silent,
            "crook_changes": [f"{c['part']}/{c['staff']}" for c in crook],
        })
    return {"path": sk.path, "n_measures": n, "n_staves": len(sk.staves),
            "ragged_parts": sk.ragged_parts, "events": events}


def main() -> int:
    files = encodings()
    sys.stderr.write(f"reading {len(files)} encodings under {root()}\n")
    works = []
    failed = []
    for i, f in enumerate(files):
        if i % 200 == 0:
            sys.stderr.write(f"  {i}/{len(files)}\n")
        try:
            works.append(analyse(load_keys(f)))
        except Exception as exc:            # noqa: BLE001 — recorded, not hidden
            failed.append({"path": f, "error": f"{type(exc).__name__}: {exc}"})

    if not works:
        sys.stderr.write("FATAL: parsed zero encodings.\n")
        return 2

    with_events = [w for w in works if w["events"]]
    all_events = [e for w in with_events for e in w["events"]]
    multi = [e for e in all_events if e["n_changing"] >= 2]

    agree = [e for e in multi if e["agree"]]
    disagree = [e for e in multi if not e["agree"]]
    solo = [e for e in all_events if e["n_changing"] == 1]

    # Taxonomy of the staves that stay silent at a multi-staff change.
    silent_reasons: Counter[str] = Counter()
    present_and_silent = []
    for e in multi:
        for s in e["silent"]:
            for r in s["reasons"]:
                silent_reasons[r] += 1
            if "PRESENT_AND_SILENT" in s["reasons"]:
                present_and_silent.append({"event": e["ordinal"], **s})

    print("=" * 72)
    print(f"corpus: {len(files)} encodings, parsed {len(works)}, "
          f"failed {len(failed)}")
    print(f"  works with >=1 mid-score key change : {len(with_events)}")
    print(f"  key-change BARS total               : {len(all_events)}")
    print(f"    bars where >=2 staves change      : {len(multi)}")
    print(f"    bars where exactly 1 staff changes: {len(solo)}")
    print()
    print("--- Q1: among the staves that DO change at a bar, is the delta shared?")
    if multi:
        print(f"  all-agree : {len(agree)} / {len(multi)} = "
              f"{len(agree)/len(multi):.4f}")
        print(f"  disagree  : {len(disagree)}")
    print()
    print("--- Q2: coverage — do ALL staves change at that bar?")
    full = [e for e in multi if e["n_changing"] == e["n_staves"]]
    print(f"  bars where EVERY staff changes: {len(full)} / {len(multi)} = "
          f"{len(full)/len(multi):.4f}" if multi else "  n/a")
    if multi:
        frac = [e["n_changing"] / e["n_staves"] for e in multi]
        frac.sort()
        print(f"  fraction of staves changing: min={frac[0]:.3f} "
              f"median={frac[len(frac)//2]:.3f} max={frac[-1]:.3f}")
    print()
    print("--- why a staff stays silent at a multi-staff key change")
    for reason, count in silent_reasons.most_common():
        print(f"  {reason:26s} {count}")
    print(f"  (PRESENT_AND_SILENT rows: {len(present_and_silent)})")
    print()
    print("--- the disagreeing bars, enumerated")
    for e in disagree[:60]:
        name = os.path.basename(next(
            w["path"] for w in with_events if e in w["events"]))
        print(f"  {name}  bar#{e['measure_number']} (ord {e['ordinal']}) "
              f"deltas={e['deltas']} n_changing={e['n_changing']}/{e['n_staves']}"
              f"{' CROOK:' + ','.join(e['crook_changes']) if e['crook_changes'] else ''}")
        by_delta = defaultdict(list)
        for c in e["changers"]:
            by_delta[c["delta"]].append(f"{c['part']}/{c['staff']}"
                                        f" {c['before']}->{c['after']}")
        for d, members in sorted(by_delta.items()):
            print(f"      Δ={d:+d}  n={len(members):3d}  {'; '.join(members[:4])}"
                  f"{' …' if len(members) > 4 else ''}")
    if len(disagree) > 60:
        print(f"  … {len(disagree) - 60} more")

    if failed:
        print()
        print(f"--- {len(failed)} encodings failed to parse")
        for f in failed[:10]:
            print(f"  {os.path.basename(f['path'])}: {f['error']}")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "shared-delta.json"), "w") as fh:
        json.dump({
            "root": root(),
            "n_encodings": len(files),
            "n_parsed": len(works),
            "failed": failed,
            "n_works_with_changes": len(with_events),
            "n_change_bars": len(all_events),
            "n_multi_staff_bars": len(multi),
            "n_solo_bars": len(solo),
            "n_agree": len(agree),
            "n_disagree": len(disagree),
            "silent_reasons": dict(silent_reasons),
            "present_and_silent": present_and_silent[:400],
            "disagreeing": [
                {**e, "path": next(w["path"] for w in with_events
                                   if e in w["events"])}
                for e in disagree
            ],
            "works": [{"path": w["path"], "n_events": len(w["events"]),
                       "n_staves": w["n_staves"],
                       "ragged_parts": w["ragged_parts"]}
                      for w in with_events],
        }, fh, indent=1)
    print(f"\nwrote {OUT}/shared-delta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
