"""Which works that CHANGE METER are also held as a printed EDITION?

⚠️ THE POOL FINDING LEFT THIS OPEN AND CALLED IT A DESKTOP JOB. It is not:
`data/score-library/catalog.json` is COMMITTED (1980 entries, 223 works, 234
editions) and records every held edition with its path, publisher, page count,
scan type and text-layer flag. Only the PDF BYTES are gitignored. So "do we hold
a printed edition of this work" is answerable anywhere; "is that plate legible"
is not, and this probe never pretends otherwise.

⚠️⚠️ THE JOIN IS ACROSS TWO ID SPACES AND THE REPO HAS BEEN BITTEN BY IT TWICE.
A dossier is keyed `beethoven-sym5-mvt4` (composer + genre + number + MOVEMENT);
the score library is keyed `beethoven--symphony-5` (composer + genre + number,
NO movement). CLAUDE.md states the trap in two places -- `OMR_WORK_ID` is *"the
score LIBRARY's id, never the dossier's"*, and `mxl_verdicts` records that the
wrong one is *"refused as 'no usable window rows', not silently matched to
nothing"*. So this maps explicitly and ABSTAINS where it cannot, rather than
forcing a nearest match: an unmapped dossier is REPORTED, never dropped.

⚠️ A movement is not a work. Several dossiers collapse onto one library work
(four movements of a symphony -> one edition), so an edition count is a count of
PRINTINGS of the piece, not of fixtures.

    python3 benchmarks/omr-meter-fixture-pool-2026-09/probe_edition_join.py
    python3 benchmarks/omr-meter-fixture-pool-2026-09/probe_edition_join.py --check --json

`--check` exits non-zero when the instrument is DEAD (catalog unreadable, or the
mapping resolved NOTHING -- which would mean the id rule is wrong rather than
the library empty). Never on a threshold.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data" / "score-library" / "catalog.json"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from probe_fixture_pool import classify, DOSSIERS  # noqa: E402

#: dossier genre token -> library genre slug. DECLARED, because the two
#: vocabularies were built by different tools years apart and a guess here
#: silently mis-joins a work rather than failing.
GENRE = {
    "sym": "symphony",
    "pc": "piano-concerto",
    "vc": "violin-concerto",
}


def library_id(dossier_stem: str):
    """`beethoven-sym5-mvt4` -> `beethoven--symphony-5`, or None to ABSTAIN."""
    # `-full` is the same shape as `-mvt<N>`: a whole-work encoding of the
    # SAME piece, so it maps identically. `holst-planets-*` and
    # `tchaikovsky-1812-overture` carry no genre+number at all and ABSTAIN.
    m = re.match(r"^([a-z]+)-([a-z]+)(\d+)(?:-mvt\d+|-full)?$", dossier_stem)
    if not m:
        return None
    composer, genre_token, number = m.groups()
    genre = GENRE.get(genre_token)
    if genre is None:
        return None
    return f"{composer}--{genre}-{number}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        cat = json.load(open(CATALOG))
    except Exception as exc:
        print(f"DEAD: cannot read the catalog: {exc}")
        return 3

    editions = {}
    for e in cat.get("entries", []):
        if e.get("kind") != "edition":
            continue
        editions.setdefault(e.get("work_id"), []).append(e)

    # every dossier that carries a real mid-movement change
    rows, abstained = [], []
    for f in sorted(DOSSIERS.glob("*.json")):
        j = json.load(open(f))
        length, engraving, _ = classify(j)
        if not (length or engraving):
            continue
        lid = library_id(f.stem)
        if lid is None:
            abstained.append(f.stem)
            continue
        rows.append((f.stem, lid, len(length), len(engraving), editions.get(lid, [])))

    held = [r for r in rows if r[4]]
    unheld = [r for r in rows if not r[4]]

    print(f"REACH  catalog entries {len(cat.get('entries', []))}  "
          f"editions indexed {sum(len(v) for v in editions.values())}  "
          f"works with an edition {len(editions)}")
    print(f"       dossiers carrying a real change {len(rows) + len(abstained)}  "
          f"mapped {len(rows)}  ABSTAINED {len(abstained)}")
    print()
    print(f"  movements whose work IS held as an edition ... {len(held)}")
    print(f"  movements whose work is NOT held ............. {len(unheld)}")
    print()
    print("HELD — a meter change AND a printed edition on disk:")
    for stem, lid, nlen, neng, eds in sorted(held, key=lambda r: (-r[3], -r[2])):
        shape = f"{nlen} length" + (f" + {neng} ENGRAVING" if neng else "")
        pubs = ", ".join(sorted({(e.get("variant") or "?") for e in eds}))
        scans = ", ".join(sorted({(e.get("image_type") or "?") for e in eds}))
        print(f"  {stem:28s} -> {lid:28s} {shape:22s} {len(eds)} ed. [{pubs}] ({scans})")
    if unheld:
        print()
        print("NOT HELD — the encoding changes meter, no edition on disk:")
        for stem, lid, nlen, neng, _ in sorted(unheld):
            print(f"  {stem:28s} -> {lid:28s} {nlen} length"
                  + (f" + {neng} ENGRAVING" if neng else ""))
    if abstained:
        print()
        print(f"ABSTAINED — id rule does not reach these {len(abstained)} "
              f"(reported, never forced):")
        for s in abstained:
            print(f"  {s}")

    if a.json:
        out = ROOT / "benchmarks/omr-meter-fixture-pool-2026-09/out/edition-join.json"
        out.write_text(json.dumps({
            "held": [{"dossier": s, "work_id": l, "length_changes": n,
                      "engraving_changes": g,
                      "editions": [{"path": e["path"],
                                    "variant": e.get("variant"),
                                    "pages": e.get("pages"),
                                    "image_type": e.get("image_type"),
                                    "has_text_layer": e.get("has_text_layer")}
                                   for e in eds]}
                     for s, l, n, g, eds in held],
            "not_held": [{"dossier": s, "work_id": l} for s, l, _, _, _ in unheld],
            "abstained": abstained,
        }, indent=2))
        print(f"\nwrote {out}")

    if a.check:
        if not rows:
            print("\nDEAD: the id mapping resolved NOTHING — the rule is wrong, "
                  "not the library empty.")
            return 3
        print("\nCHECK OK — the mapping resolved and the join can tell held from not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
