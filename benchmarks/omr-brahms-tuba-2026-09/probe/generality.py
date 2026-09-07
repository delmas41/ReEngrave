"""How general is the fault? Two questions, both answered from committed data.

**Q1 — the exposure.** For every work the catalog holds a roster for, which
parts of the layout library does the work NOT have? A `score_order` proposal can
only ever name a part of the winning layout, so a part absent from the roster is
a name that CANNOT be right if it is proposed. The Brahms shape (`Trombone`
present, `Tuba` absent, and `Tuba` printed directly under `Trombone` in three of
the ten layouts) is counted by name.

**Q2 — the incumbent corpus.** Over the committed whole-work runs, how many
staff records carry a `score_order` name their work's roster excludes? This is
the live cost, not a hypothetical one.

Usage:  generality.py [BLOB.json ...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.score_layouts import LAYOUTS  # noqa: E402

CATALOG = ROOT / "data" / "score-library" / "catalog.json"
# Section words the catalog parse is known to drop (sibling session's fault
# (a): 13 of 219 rosters name no string at all). Treated as PRESENT rather
# than absent, so this survey cannot manufacture exposure out of a parse gap.
STRINGS = {"Violin", "Viola", "Cello", "Contrabass"}


def rosters() -> dict[str, set[str]]:
    works = json.loads(CATALOG.read_text()).get("works", {})
    out = {}
    for wid, w in works.items():
        instr = (w or {}).get("instrumentation") or {}
        if instr.get("describes") != "work":
            continue
        names = {e.get("instrument") for e in (instr.get("roster") or [])
                 if e.get("instrument")}
        if not names:
            continue
        out[wid] = names | STRINGS      # see STRINGS
    return out


def main(blobs: list[str]) -> None:
    r = rosters()
    print(f"Q1 — exposure.  {len(r)} works carry a parsed catalog roster.\n")

    # Which layout parts are absent from how many rosters?
    absent = collections.Counter()
    parts = {p for lay in LAYOUTS for p in lay.parts}
    for wid, names in r.items():
        for p in parts:
            if p not in names:
                absent[p] += 1
    print("  layout part            works whose roster LACKS it")
    for p, c in absent.most_common():
        print(f"   {p:<22s} {c:4d} / {len(r)}")

    # The exact Brahms shape, and the two other "next part is absent" pairs a
    # layout can produce directly under a part the work DOES have.
    print("\n  the exact Brahms shape (roster has Trombone, lacks Tuba):")
    shape = [w for w, n in r.items() if "Trombone" in n and "Tuba" not in n]
    print(f"   {len(shape)} works  e.g. {sorted(shape)[:8]}")

    print("\n  every adjacent (have, lack) pair the layouts can produce:")
    pair = collections.Counter()
    for lay in LAYOUTS:
        for a, b in zip(lay.parts, lay.parts[1:]):
            if a == b:
                continue
            for wid, n in r.items():
                if a in n and b not in n:
                    pair[(a, b)] += 1
    for (a, b), c in pair.most_common(15):
        print(f"   {a:<16s} -> {b:<16s} {c:4d} works")

    # ── Q2 ──────────────────────────────────────────────────────────────────
    print("\nQ2 — the live cost on the committed whole-work runs.\n")
    for path in blobs:
        doc = json.loads(Path(path).read_text())
        b = (doc.get("contextual") or {}).get("absent_instrument_veto")
        if not b:
            print(f"  {path}: no blob"); continue
        pdf = str(doc.get("source_pdf") or "")
        wid = None
        for w in r:
            key = w.split("--")
            if len(key) == 2 and key[0] in pdf and key[1] in pdf:
                wid = w; break
        si = {s["slot"]: s for s in b["slot_instruments"]}
        slot_of = {(s["page_index"], s["system_index"], s["staff_index"]):
                   s["slot"] for s in b["staff_slots"]}
        names = r.get(wid, set())
        bad_slots = {k for k, v in si.items()
                     if v["source"].startswith("score_order")
                     and v["instrument"] not in names}
        recs = [k for k, sl in slot_of.items() if sl in bad_slots]
        by_src = collections.Counter(si[s]["source"] for s in si)
        print(f"  {Path(path).name}")
        print(f"    work_id={wid}  reference_size={b['reference_size']}")
        print(f"    slot sources: {dict(by_src)}")
        print(f"    score_order slots naming an OFF-ROSTER instrument: "
              f"{ {s: si[s]['instrument'] for s in sorted(bad_slots)} }")
        print(f"    staff records affected: {len(recs)} of {len(slot_of)}")


if __name__ == "__main__":
    main(sys.argv[1:])
