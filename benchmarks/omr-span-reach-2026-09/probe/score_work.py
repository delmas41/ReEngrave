"""Score a 2x2 `compose.py` pair for ANY work — the IMPOSSIBLE grade only.

`omr-spans-veto-composition-2026-09/probe/score_2x2.py` hardcodes Beethoven 5:
its finale page, its finale-only instruments, and hand-read LINEUPS for the
correct/wrong/unnamed columns. Two of those three generalise cheaply and the
third does not, so this scores the two that do and refuses to fake the third.

    IMPOSSIBLE   a staff on a page BEFORE the work's first entry of instrument
                 X, named X. Categorically wrong whatever the page prints,
                 because the instrument has not entered the piece yet.
    CHANGED      every staff record whose emitted name differs between two
                 cells, listed, so a reader can see what moved rather than only
                 how many.

⚠️ **IMPOSSIBLE IS A WEAK GRADE AND MUST BE REPORTED AS ONE.** It counts names
that cannot be right. It says nothing about whether the remaining names are
right, and a cell can improve it by naming FEWER staves. The correct/wrong
table needs a hand-read lineup per region, which this does not have and does
not pretend to.

⚠️ The `--config` file's `entry_page` per instrument is the only work-specific
input, and where it comes from decides what the number means. Prefer a page
read by eye off the print; a page inferred from the reference encodings is
ENCODING evidence and must be labelled as such in the config's `provenance`.
"""
from __future__ import annotations

import argparse
import collections
import json


def load(path):
    r = json.load(open(path))
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit(f"REFUSING: {path} has no veto report block")
    return {
        "path": path,
        "mvt": r.get("movement_reference"),
        "reference": (r.get("contextual") or {}).get("reference") or [],
        "slot_by_staff": {(s["page_index"], s["system_index"],
                           s["staff_index"]): s["slot"]
                          for s in b["staff_slots"]},
        "name_by_slot": {s["slot"]: s["instrument"]
                         for s in b["slot_instruments"]},
        "vetoed": {(v["page_index"], v["system_index"], v["staff_index"])
                   for v in b["vetoes"]},
        "mode": b.get("mode"), "rule": b.get("rule"), "window": b.get("window"),
    }


def names(arm, veto_on: bool):
    out = {}
    for key, slot in arm["slot_by_staff"].items():
        if veto_on and key in arm["vetoed"]:
            out[key] = None
        else:
            out[key] = arm["name_by_slot"].get(slot) if slot >= 0 else None
    return out


def impossible(emitted, entry: dict[str, int]):
    """Staff records naming an instrument before that instrument enters."""
    bad = []
    for key, name in emitted.items():
        if name is None:
            continue
        first = entry.get(name)
        if first is not None and key[0] < first:
            bad.append(key)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spans_off")
    ap.add_argument("spans_on")
    ap.add_argument("--config", required=True,
                    help="JSON: {entry_page: {Instrument: first page index}, "
                         "provenance: '...'}")
    ap.add_argument("--show-changed", type=int, default=25)
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    entry = cfg["entry_page"]
    off, on = load(args.spans_off), load(args.spans_on)

    if set(off["slot_by_staff"]) != set(on["slot_by_staff"]):
        raise SystemExit("REFUSING: the two arms saw different staff records — "
                         "they did not share a read pass")
    keys = list(off["slot_by_staff"])

    print("=== INPUT ASSERTIONS ===")
    print(f"  staff records           : {len(keys)}")
    print(f"  pages                   : {len({k[0] for k in keys})}")
    print(f"  reference slots         : off={len(off['reference'])} "
          f"on={len(on['reference'])}")
    print(f"  veto config             : mode={off['mode']} rule={off['rule']} "
          f"window={off['window']}")
    moved = sum(1 for k in keys
                if off["slot_by_staff"][k] != on["slot_by_staff"][k])
    print(f"  slot assignments moved by spans: {moved} of {len(keys)}")
    print(f"  entry pages (provenance: {cfg.get('provenance', '?')}):")
    for k, v in sorted(entry.items(), key=lambda kv: kv[1]):
        print(f"      {k:16s} first appears on page {v}")

    cells = {}
    for stag, arm in (("spans-off", off), ("spans-on", on)):
        for vtag, von in (("veto-off", False), ("veto-on", True)):
            em = names(arm, von)
            bad = impossible(em, entry)
            cells[(stag, vtag)] = {
                "emitted": em, "bad": bad,
                "by_name": collections.Counter(em[k] for k in bad),
                "pages": sorted({k[0] for k in bad}),
                "named": sum(1 for v in em.values() if v is not None),
            }

    print()
    print("=== THE 2x2 — IMPOSSIBLE (weak grade: a lower bound on error) ===")
    print(f"{'':24s} {'IMPOSSIBLE':>11s} {'named staves':>13s}")
    for stag in ("spans-off", "spans-on"):
        for vtag in ("veto-off", "veto-on"):
            c = cells[(stag, vtag)]
            print(f"  {stag:10s} {vtag:9s} {len(c['bad']):11d} "
                  f"{c['named']:13d}")

    for tag, c in cells.items():
        if not c["bad"]:
            continue
        print(f"\n  {tag[0]} / {tag[1]}  by name: "
              f"{dict(c['by_name'].most_common())}")
        print(f"      pages: {c['pages']}")

    base = cells[("spans-off", "veto-off")]["emitted"]
    for tag in (("spans-on", "veto-off"), ("spans-off", "veto-on"),
                ("spans-on", "veto-on")):
        em = cells[tag]["emitted"]
        diff = [k for k in keys if base[k] != em[k]]
        print(f"\n=== CHANGED vs spans-off/veto-off: {tag[0]}/{tag[1]} — "
              f"{len(diff)} staff records ===")
        counts = collections.Counter((base[k], em[k]) for k in diff)
        for (a, b), n in counts.most_common(args.show_changed):
            print(f"   {n:5d}  {str(a):18s} -> {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
