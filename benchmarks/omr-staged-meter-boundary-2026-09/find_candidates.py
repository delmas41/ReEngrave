"""Which works can supply a SECOND document and publisher for the boundary test?

⚠️ TWO DIFFERENT ARMS NEED TWO DIFFERENT THINGS, and conflating them is how
"a second document and publisher" turns into one weaker measurement:

  * the ENGRAVED arm needs a movement in `orchestral_eval.SCORE_DIR` that
    encodes a mid-piece `<time>` change — it removes the LEGIBILITY confound
    and is what made the first measurement discriminating. Its "publisher" is
    always LilyPond, so it is a second DOCUMENT and not a second publisher;
  * the SCAN arm needs a held PDF edition of that same work from a publisher
    that is NOT Litolff — that is the second PUBLISHER, and it is the one that
    says whether the mechanism has reach on real print.

A work that can supply both is worth far more than two works supplying one
each, because the two arms then differ ONLY in the printing.

    python3 .../find_candidates.py            # the ranked table
    python3 .../find_candidates.py --json out/candidates.json
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.training.orchestral_eval import SCORE_DIR  # noqa: E402

CATALOG = ROOT / "data" / "score-library" / "catalog.json"


def _score_xml(path: Path) -> ET.Element:
    if path.suffix == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.endswith(".xml") and "META-INF" not in n
                     and not n.endswith("container.xml")]
            return ET.fromstring(z.read(names[0]))
    return ET.parse(path).getroot()


def time_changes(path: Path) -> list:
    """(measure number, beats, beat-type) for every `<time>` in part 1.

    ⚠️ PART ONE ONLY, DELIBERATELY. A meter is a fact of the SYSTEM and every
    part restates it; walking all of them multiplies each change by the part
    count and says nothing more.
    """
    root = _score_xml(path)
    parts = root.findall("part")
    if not parts:
        return []
    out = []
    for m in parts[0].findall("measure"):
        t = m.find("attributes/time")
        if t is None:
            continue
        out.append((m.get("number"), t.findtext("beats"), t.findtext("beat-type")))
    return out


def main(as_json=None):
    cat = json.loads(CATALOG.read_text())["entries"]
    editions = {}
    for e in cat:
        if e.get("kind") != "edition":
            continue
        editions.setdefault(e["work_id"], []).append(e)

    # reference encodings carry the work_id; SCORE_DIR files carry the dossier
    # id, and the two are joined through the catalog's own reference rows.
    ref_workid = {}
    for e in cat:
        if e.get("kind") == "reference":
            ref_workid.setdefault(Path(e["path"]).stem, e["work_id"])

    rows = []
    for src in sorted(SCORE_DIR.glob("*.mxl")):
        try:
            changes = time_changes(src)
        except Exception as exc:                                # noqa: BLE001
            rows.append({"work": src.stem, "error": str(exc)[:60]})
            continue
        if len(changes) < 2:
            continue
        rows.append({"work": src.stem, "n_changes": len(changes) - 1,
                     "changes": changes})

    # join to editions by the composer+genre+number key the library uses
    def work_id_for(stem):
        # `beethoven-sym5-mvt4` -> `beethoven--symphony-5`
        parts = stem.split("-")
        comp = parts[0]
        for i, p in enumerate(parts):
            if p.startswith("sym") and p[3:].isdigit():
                return f"{comp}--symphony-{p[3:]}"
        return None

    for r in rows:
        wid = work_id_for(r["work"])
        r["work_id"] = wid
        eds = editions.get(wid, []) if wid else []
        r["editions"] = [{"publisher": (e.get("publisher") or "?")[:48],
                          "variant": e.get("variant"), "pages": e.get("pages"),
                          "path": e["path"]} for e in eds]

    rows.sort(key=lambda r: (-len(r.get("editions") or []), -r.get("n_changes", 0)))
    for r in rows:
        if "error" in r:
            continue
        print(f"\n{r['work']}  ({r['n_changes']} change(s))  work_id={r['work_id']}")
        print(f"   meters: {r['changes']}")
        for e in r["editions"]:
            print(f"   edition: {e['variant']:28s} {e['pages']:>4} pp  {e['publisher']}")
    if as_json:
        Path(as_json).write_text(json.dumps(rows, indent=2))
        print(f"\nwrote {as_json}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    main(ap.parse_args().json)
