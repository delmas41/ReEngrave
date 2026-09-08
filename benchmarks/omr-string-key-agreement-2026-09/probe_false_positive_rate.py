"""How often does `key_consensus` cry wolf on data that is already CORRECT?

The module's danger is not missing a contradiction; it is manufacturing one. A
reference encoding is a published, human-made score, so a contradiction raised
against one is a FALSE POSITIVE unless a human adjudicates it otherwise. This
runs the consensus over every orchestral reference encoding the library holds
and reports the rate.

⚠️ Read the abstention column as a RESULT, not a shortfall -- a score whose
witnesses split is one the module correctly declines to name a key for.
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
from tools.omr.key_consensus import StaffKey, analyse   # noqa: E402


def _root(path: pathlib.Path):
    try:
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path) as z:
                n = next((n for n in z.namelist()
                          if n.endswith((".xml", ".musicxml"))
                          and not n.startswith("META-INF")), None)
                return None if n is None else ET.fromstring(z.read(n))
        return ET.parse(path).getroot()
    except Exception:                                          # noqa: BLE001
        return None


def readings(path: pathlib.Path, at: str = "1"):
    root = _root(path)
    if root is None:
        return None
    names = {sp.get("id"): (sp.findtext("part-name") or "").strip()
             for sp in root.iter("score-part")}
    out, i = [], 0
    for part in root.iter("part"):
        nm, cur = names.get(part.get("id"), ""), None
        for meas in part.iter("measure"):
            f = meas.findtext("./attributes/key/fifths")
            if f is not None:
                try:
                    cur = int(f)
                except ValueError:
                    pass
            if (meas.get("number") or "") == at:
                break
        out.append(StaffKey(i, label=nm, read_fifths=cur))
        i += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="library/reference")
    ap.add_argument("--min-parts", type=int, default=8,
                    help="orchestral only; a duo has nothing to corroborate")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    files = sorted(p for p in pathlib.Path(a.root).rglob("*")
                   if p.suffix.lower() in (".mxl", ".musicxml", ".xml"))
    tally = collections.Counter()
    offenders, n_scored = [], 0
    for f in files:
        rs = readings(f)
        if rs is None or len(rs) < a.min_parts:
            tally["skipped_not_orchestral"] += 1
            continue
        c = analyse(rs)
        n_scored += 1
        if c.concert_fifths is None:
            tally[f"abstained:{c.reason.split()[0]}"] += 1
            continue
        tally[f"decided:{c.strength}"] += 1
        if c.contradictions:
            tally["WITH_CONTRADICTIONS"] += 1
            offenders.append({
                "path": str(f), "concert": c.concert_fifths,
                "strength": c.strength, "nosig": c.no_signature_score,
                "n": len(c.contradictions),
                "staves": [(x.staff_index, x.label, x.read, x.expected)
                           for x in c.contradictions[:6]]})
        else:
            tally["clean"] += 1

    print(f"=== scored {n_scored} orchestral scores (>= {a.min_parts} parts)")
    for k, v in tally.most_common():
        print(f"  {k:<34} {v}")
    n_dec = sum(v for k, v in tally.items() if k.startswith("decided:"))
    if n_dec:
        print(f"\n  of {n_dec} DECIDED: clean {tally['clean']}, "
              f"with contradictions {tally['WITH_CONTRADICTIONS']} "
              f"({tally['WITH_CONTRADICTIONS']/n_dec:.1%})")
    print(f"\n=== {len(offenders)} scores raising a contradiction ===")
    for o in sorted(offenders, key=lambda x: -x["n"])[:20]:
        print(f"\n  {pathlib.Path(o['path']).name}")
        print(f"    concert={o['concert']} strength={o['strength']} "
              f"nosig={o['nosig']} n={o['n']}")
        for s in o["staves"]:
            print(f"      {s[0]:>3} {str(s[1])[:30]:<30} read={s[2]} exp={s[3]}")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            {"tally": dict(tally), "offenders": offenders}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
