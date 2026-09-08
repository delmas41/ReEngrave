"""Do the bowed strings of a score ALWAYS print the same key signature?

Sean's claim, 2026-09-08: "there will never be a case where one of the string
instruments would have a different key than the others". If it holds, it
repairs a refusal recorded at `tools/omr/staged/groups.py:97` -- a key
signature across the staves of ONE SYSTEM is refused as a redundant group
BECAUSE transposing instruments genuinely differ. Restricted to the strings,
that reason evaporates and the group becomes legitimate.

This measures the claim instead of asserting it, over every reference encoding
the score library holds. It reads `<key><fifths>` per part, per measure, and
asks whether the string-family parts agree AT EVERY MEASURE (not just at the
head -- a mid-movement key change that reached one string part and not another
would be the counter-example that matters).

⚠️ THE OCTAVE TRAP. Contrabass is `chromatic: -12` in `instruments.py`. That is
an OCTAVE transposition and does NOT change the key signature, so the test for
"shares the strings' key" is `chromatic % 12 == 0`, never `chromatic == 0`.
Getting this wrong drops the bass -- the staff a witness rule most wants,
being bottom-of-page and often unlabelled.

⚠️ WHAT A DISAGREEMENT MEANS. Not necessarily a falsification: it can be
SCORDATURA (a retuned string part is written transposed -- Mahler 4 mvt 2's
solo violin is the canonical orchestral case), or an encoding artefact. Every
disagreement is printed with its work and its values so a human adjudicates.
The script never decides that for itself.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr import instruments as INST  # noqa: E402


def _root(path: pathlib.Path):
    """Parse .mxl (zip) or .musicxml. Returns the score root, or None."""
    try:
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path) as z:
                name = next((n for n in z.namelist()
                             if n.endswith((".xml", ".musicxml"))
                             and not n.startswith("META-INF")), None)
                if name is None:
                    return None
                return ET.fromstring(z.read(name))
        return ET.parse(path).getroot()
    except Exception:                                          # noqa: BLE001
        return None


def _is_string_part(name: str) -> bool:
    """True only for the BOWED string section.

    Uses the repo's own lexicon and its own family taxonomy, so this cannot
    drift from what the pipeline believes. Harp is `keyboard` there, not
    `string`, which is what keeps a harp's pedal-driven enharmonic spelling out
    of the witness set.
    """
    try:
        m = INST.lookup(name or "")
    except Exception:                                          # noqa: BLE001
        return False
    inst = getattr(m, "instrument", None)
    if inst is None or getattr(inst, "family", None) != "string":
        return False
    return getattr(inst, "chromatic", 0) % 12 == 0


def scan(path: pathlib.Path) -> dict | None:
    root = _root(path)
    if root is None:
        return None
    names = {}
    for sp in root.iter("score-part"):
        pid = sp.get("id")
        nm = sp.findtext("part-name") or ""
        if pid:
            names[pid] = nm.strip()

    # measure number -> {part name -> fifths in effect}
    running: dict[str, int | None] = {}
    per_measure: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for part in root.iter("part"):
        pid = part.get("id")
        nm = names.get(pid, pid or "")
        if not _is_string_part(nm):
            continue
        cur = None
        for meas in part.iter("measure"):
            n = meas.get("number") or "?"
            f = meas.findtext("./attributes/key/fifths")
            if f is not None:
                try:
                    cur = int(f)
                except ValueError:
                    pass
            if cur is not None:
                per_measure[n][f"{nm}#{pid}"] = cur
        running[nm] = cur

    if len(set(k.split("#")[1] for m in per_measure.values() for k in m)) < 2:
        return {"path": str(path), "n_string_parts": len(running),
                "status": "too_few_string_parts"}

    bad = []
    for n, d in per_measure.items():
        vals = set(d.values())
        if len(vals) > 1:
            bad.append({"measure": n, "values": d})
    return {"path": str(path), "n_string_parts": len(running),
            "n_measures_checked": len(per_measure),
            "status": "DISAGREES" if bad else "agrees",
            "disagreements": bad[:5], "n_disagreeing_measures": len(bad)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="library/reference")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    files = sorted(p for p in pathlib.Path(a.root).rglob("*")
                   if p.suffix.lower() in (".mxl", ".musicxml", ".xml"))
    if a.limit:
        files = files[:a.limit]

    tally = collections.Counter()
    rows = []
    for i, f in enumerate(files, 1):
        r = scan(f)
        if r is None:
            tally["unreadable"] += 1
            continue
        tally[r["status"]] += 1
        if r["status"] == "DISAGREES":
            rows.append(r)
        if i % 200 == 0:
            print(f"  ... {i}/{len(files)}", file=sys.stderr)

    print(json.dumps({"n_files": len(files), "tally": dict(tally),
                      "disagreeing": rows}, indent=1)[:400])
    print("\n=== TALLY ===")
    for k, v in tally.most_common():
        print(f"  {k:<24} {v}")
    print(f"\n=== {len(rows)} SCORES WHERE THE STRINGS DISAGREE ===")
    for r in rows:
        print(f"\n  {r['path']}")
        print(f"    {r['n_disagreeing_measures']} of {r['n_measures_checked']} measures")
        for d in r["disagreements"][:3]:
            print(f"    m{d['measure']}: {d['values']}")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            {"n_files": len(files), "tally": dict(tally),
             "disagreeing": rows}, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
