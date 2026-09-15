"""What a SECOND document would have to be, and which ones this project
already holds.

⚠️⚠️ THIS IS THE DELIVERABLE OF A DEAD-END EXPLORATION. `probe_reach.py`
finds **three cautionaries, all on one piece of music**, so no rule may be
fitted here. The useful output is therefore not a rule but a SHORTLIST: which
held works print a mid-movement meter change at all, since a cautionary can
only be engraved where a meter change falls on a system boundary.

⚠️ A DOSSIER MEATER CHANGE IS A FACT ABOUT THE ENCODING, NOT ABOUT THE PRINT.
`meter_changes` names the BAR; whether a system break happens to fall just
before that bar — which is the only thing that makes an engraver print a
courtesy signature — is a property of the PLATE and is not derivable from any
committed file. So every row below is a CANDIDATE to be checked against the
page, never a cautionary. A work with many changes is likelier to put one at a
break, which is the whole of the ranking.

⚠️ CONTROL: the dossier-id -> library-id mapping is DERIVED, and it is checked
against the 41 catalog entries that carry an explicit `dossier_prefix`. If the
derivation cannot reproduce those, the probe exits non-zero rather than
publish a join nobody checked.

    python3 benchmarks/omr-meter-cautionary-2026-09/probe_second_document.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

DOSSIERS = ROOT / "data" / "dossiers"
CATALOG = ROOT / "data" / "score-library" / "catalog.json"

#: `beethoven-sym5-mvt1` -> (`beethoven`, `sym5`).  ⚠️ Only the shapes the
#: corpus actually uses are handled and anything else is reported UNJOINED
#: rather than forced to a nearest match — the rule `instruments.lookup` and
#: the roster parser both had to learn the hard way.
_ID = re.compile(r"^(?P<composer>[a-z]+)-(?P<work>[a-z]+\d+)-mvt(?P<mvt>\d+)$")

_GENRE = {"sym": "symphony", "conc": "concerto"}


def _library_id(dossier_id: str):
    m = _ID.match(dossier_id)
    if not m:
        return None, None
    work = m.group("work")
    gm = re.match(r"^([a-z]+)(\d+)$", work)
    if not gm:
        return None, None
    genre = _GENRE.get(gm.group(1))
    if genre is None:
        return None, None
    return (f"{m.group('composer')}--{genre}-{gm.group(2)}",
            f"{m.group('composer')}-{work}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out",
                    default=str(HERE / "out" / "second-document.json"))
    a = ap.parse_args()

    files = sorted(DOSSIERS.glob("*.json"))
    if not files:
        print(f"DEAD: no dossiers under {DOSSIERS}")
        return 2
    if not CATALOG.is_file():
        print(f"DEAD: no catalog at {CATALOG}")
        return 2
    catalog = json.loads(CATALOG.read_text())
    editions = [e for e in catalog["entries"] if e.get("kind") == "edition"]

    print("═══ REACH ═══")
    print(f"  dossiers ....................... {len(files)}")
    print(f"  committed catalog editions ..... {len(editions)}")

    # ── control: the derived id mapping must reproduce the explicit one ────
    explicit = {(e["work_id"], e["dossier_prefix"])
                for e in catalog["entries"] if e.get("dossier_prefix")}
    derived = set()
    for p in files:
        d = json.loads(p.read_text())
        lib, prefix = _library_id(d["work_id"])
        if lib:
            derived.add((lib, prefix))
    missed = {pair for pair in explicit if pair not in derived}
    print(f"\n═══ CONTROL: the derived work-id join ═══")
    n_rows = sum(1 for e in catalog["entries"] if e.get("dossier_prefix"))
    print(f"  catalog rows carrying an explicit dossier_prefix  {n_rows} rows,"
          f" {len(explicit)} distinct (work_id, prefix) pairs")
    print(f"  ...reproduced by the derived mapping ............. "
          f"{len(explicit) - len(missed)}")
    if missed:
        print(f"  ⚠️ NOT reproduced: {sorted(missed)}")
        print("  The join is unchecked — refusing to publish a shortlist "
              "built on it.")
        return 3
    print("  ✓ every explicit pair is reproduced.")

    # ── the candidates ────────────────────────────────────────────────────
    by_lib: dict = {}
    for e in editions:
        by_lib.setdefault(e["work_id"], []).append(e)

    rows, unjoined = [], []
    for p in sorted(files):
        d = json.loads(p.read_text())
        changes = [c for c in (d.get("meter_changes") or [])
                   if int(c.get("measure", 1)) > 1]
        lib, _prefix = _library_id(d["work_id"])
        if lib is None:
            unjoined.append(d["work_id"])
        held = by_lib.get(lib or "", [])
        rows.append({
            "dossier": d["work_id"], "library_work_id": lib,
            "total_measures": d.get("total_measures"),
            "constant_meter": d.get("constant_meter"),
            "n_mid_movement_changes": len(changes),
            "changes": [{"measure": c["measure"],
                         "raw": f"{c['beats']}/{c['beat_type']}"}
                        for c in changes],
            "held_editions": [{"path": e["path"],
                               "publisher": e.get("publisher"),
                               "image_type": e.get("image_type"),
                               "pages": e.get("pages")} for e in held],
        })

    with_change = [r for r in rows if r["n_mid_movement_changes"]]
    with_ed = [r for r in with_change if r["held_editions"]]
    print(f"\n═══ CANDIDATES ═══")
    print(f"  dossier works .................. {len(rows)}")
    print(f"  ...with a MID-MOVEMENT change .. {len(with_change)}")
    print(f"  ...and a held edition PDF ...... {len(with_ed)}")
    print(f"  dossier ids the mapping refuses  {len(unjoined)}  {unjoined}")

    print("\n  ranked by how many changes the encoding holds "
          "(more changes = more chances one falls on a system break):\n")
    for r in sorted(with_ed, key=lambda x: -x["n_mid_movement_changes"])[:20]:
        pubs = sorted({(e["publisher"] or "?")[:34]
                       for e in r["held_editions"]})
        print(f"  {r['dossier']:<28} {r['n_mid_movement_changes']:>3} changes"
              f"  {r['total_measures']:>4} bars   {len(r['held_editions'])} ed."
              f"  {pubs[:2]}")
        print(f"        at bars "
              f"{[c['measure'] for c in r['changes']][:12]}"
              + (" ..." if len(r["changes"]) > 12 else ""))

    # ⚠️ Named apart because the corpus this thread already runs on is the
    # cheapest second document there is: a fixture that exists, whose weights
    # and windows are already hand-verified.
    print("\n  ⚠️ ALREADY IN THE METER CORPUS (cheapest to run):")
    fixtures = {"beethoven-sym5-mvt4", "beethoven-sym5-mvt1",
                "brahms-sym1-mvt1", "brahms-sym1-mvt4"}
    for r in rows:
        if r["dossier"] in fixtures:
            print(f"      {r['dossier']:<22} "
                  f"{r['n_mid_movement_changes']:>3} mid-movement changes at "
                  f"{[c['measure'] for c in r['changes']][:10]}")

    Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json_out).write_text(json.dumps(
        {"n_dossiers": len(rows), "n_with_change": len(with_change),
         "n_with_change_and_edition": len(with_ed),
         "unjoined": unjoined, "works": rows}, indent=1) + "\n")
    print(f"\nwrote {a.json_out}")
    if not with_ed:
        print("DEAD: no held edition prints a mid-movement meter change.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
