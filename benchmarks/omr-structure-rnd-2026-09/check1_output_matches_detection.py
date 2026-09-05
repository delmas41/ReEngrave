"""CHECK 1 — does the OUTPUT match the DETECTION?

⚠️ THIS CHECK NEEDS NO GROUND TRUTH AT ALL. It compares two stages of our own
pipeline — what phase 1 detected on the page, and what the exporter emitted —
so it runs on any page anyone ever hands the pipeline, including one with no
reference encoding, no dossier and no hand-read truth. That is the property
that makes it survive having no MusicXML.

MEASUREMENT ONLY. Reads committed artifacts; writes only its own JSON.

## The rule, and why it is stated this way

A system may OMIT a part that is tacet through it; it can never invent one. So
the page's roster is at least as large as its largest system, and:

    n_score_parts  ==  max(staves per system)

is the conservation statement available without truth.

Three verdicts, and the asymmetry is deliberate:

* `FRAGMENTED`  — n_parts > max_system_staves. The exporter emitted one part
  per (system, staff) instead of one per part. This is a DEFECT and the check's
  reason for existing.
* `LOST`        — n_parts < max_system_staves. Parts went missing on the way out.
* `OK`          — equal.

⚠️ `OK` IS NOT A PROOF OF CORRECTNESS, and this must not be forgotten when the
number looks good. A page whose two systems print DIFFERENT eleven staves has a
roster of twelve and a max of eleven, so the correct answer is 12 and this rule
expects 11 — it scores the silent mis-join `OK`. Beethoven 5 p.4 is exactly that
page, in two editions. The rule catches FRAGMENTATION, which is the large, known,
22.4%-of-scan-error defect; it is blind to mis-JOINING, which is cheap today.
Both facts are reported.

## Measure conservation, the second half

Also free, also truth-less: every detected measure should reach the output.

    sum(measures over all detected staves)  ==  sum(measures over all emitted parts)

A mismatch means music was dropped or duplicated between stages, independently
of how the parts were grouped.
"""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures"
)
JSON_SUFFIX = ".reconciliation.omr.json"
XML_SUFFIX = ".reconciliation.omr.musicxml"
OUT = Path(__file__).with_name("check1-output-vs-detection.json")


def detected(doc: dict) -> dict:
    """Per-system staff counts and total detected measures, from phase 1."""
    systems = [s for pg in doc.get("pages", []) for s in pg.get("systems", [])
               if s.get("staves")]
    sizes = [len(s["staves"]) for s in systems]
    measures = sum(len(st.get("measures", []))
                   for s in systems for st in s["staves"])
    return {"n_systems": len(systems), "system_sizes": sizes,
            "max_system_staves": max(sizes) if sizes else 0,
            "sum_system_staves": sum(sizes),
            "detected_measures": measures}


def emitted(path: Path) -> dict:
    """Parts and measures from the exported MusicXML. Real parser, no regex."""
    root = ET.parse(path).getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    score_parts = root.findall(f".//{ns}part-list/{ns}score-part")
    parts = root.findall(f"./{ns}part")
    measures = sum(len(p.findall(f"./{ns}measure")) for p in parts)
    # `<print new-system="yes">` is how MusicXML carries a system break.
    new_systems = [e for e in root.iter(f"{ns}print")
                   if e.get("new-system") == "yes"]
    names = [(sp.findtext(f"{ns}part-name") or "").strip()
             for sp in score_parts]
    return {"n_score_parts": len(score_parts), "n_parts": len(parts),
            "emitted_measures": measures, "n_new_system_prints": len(new_systems),
            "part_names": names}


def main() -> int:
    js = sorted(FIXTURES.glob(f"*{JSON_SUFFIX}"))
    # An audit that can return "nothing found" must first prove it looked.
    assert js, f"EMPTY INPUT — no transcriptions under {FIXTURES}"
    assert len(js) == 20, f"expected the 20-row gate, found {len(js)}"

    rows = []
    for jp in js:
        row = os.path.basename(jp).split(".reconciliation")[0]
        xp = FIXTURES / f"{row}{XML_SUFFIX}"
        assert xp.exists(), f"MISSING export for {row}: {xp}"
        det = detected(json.loads(jp.read_text()))
        emi = emitted(xp)
        assert det["max_system_staves"] > 0, f"no staves detected on {row}"
        assert emi["n_score_parts"] > 0, f"no score-parts emitted on {row}"

        if emi["n_score_parts"] > det["max_system_staves"]:
            verdict = "FRAGMENTED"
        elif emi["n_score_parts"] < det["max_system_staves"]:
            verdict = "LOST"
        else:
            verdict = "OK"
        rows.append({"row": row, "verdict": verdict,
                     "measures_ok": det["detected_measures"] == emi["emitted_measures"],
                     **det, **emi})

    assert len(rows) == 20
    n_staves = sum(r["sum_system_staves"] for r in rows)
    assert n_staves == 396, f"expected 396 staves, counted {n_staves}"

    hdr = (f"{'row':46s} {'sys':>3} {'sizes':>16} {'max':>4} {'parts':>6} "
           f"{'verdict':>11} {'detM':>6} {'emitM':>6} {'M':>3} {'nsys<print>':>11}")
    print(f"CHECK 1 — output vs detection. NO GROUND TRUTH USED.")
    print(f"fixtures: {len(js)}  staves: {n_staves}  provenance: {FIXTURES}\n")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['row']:46s} {r['n_systems']:>3} {str(r['system_sizes']):>16} "
              f"{r['max_system_staves']:>4} {r['n_score_parts']:>6} "
              f"{r['verdict']:>11} {r['detected_measures']:>6} "
              f"{r['emitted_measures']:>6} {'ok' if r['measures_ok'] else 'BAD':>3} "
              f"{r['n_new_system_prints']:>11}")

    frag = [r for r in rows if r["verdict"] == "FRAGMENTED"]
    lost = [r for r in rows if r["verdict"] == "LOST"]
    okm = [r for r in rows if not r["measures_ok"]]
    print("\n=== summary ===")
    print(f"  OK          : {sum(1 for r in rows if r['verdict'] == 'OK')}/20")
    print(f"  FRAGMENTED  : {len(frag)}/20  -> {[r['row'] for r in frag]}")
    print(f"  LOST        : {len(lost)}/20  -> {[r['row'] for r in lost]}")
    print(f"  measure conservation failures: {len(okm)}/20 "
          f"-> {[r['row'] for r in okm]}")
    print("\n⚠️ OK is not a proof of correctness: a page whose systems print")
    print("   DIFFERENT staves of equal count has a roster larger than its max,")
    print("   and this rule scores it OK. See the blind-spot section in CHECK1.md.")
    OUT.write_text(json.dumps({"rows": rows}, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
