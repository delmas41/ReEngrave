"""Record -> MusicXML, coverage report, and the SYSTEM MAP the artefact needs.

    python3 benchmarks/omr-cleanup-count-2026-09/export_arm.py \
        --record out/record-p1-p4.json --tag p1-p4

⚠️ Run SEPARATELY from the gather, never with `--musicxml`. The import hazard
runs both ways (manager log, 2026-09-11): `staged/__main__.py` imports the
exporter AFTER the gather so a mid-run edit REACHES it, while a module
imported at process start keeps its code so a mid-run edit does NOT -- and
`_provenance()` reads git at the END, so the stamp names neither. Two
processes, two stamps, no ambiguity.

**The system map is the piece that does not exist anywhere else.** The
exported file numbers measures per PART, from 1, across every system the part
spans; the human is looking at ONE SYSTEM of ONE PAGE of the print. Nothing in
the MusicXML says which measures those are. This walks `export.build`'s own
`StaffRun`s -- the exporter's structures, called rather than re-derived, so
the map cannot drift from the file -- and writes, for each (page, system):
which part carries which measure numbers, and which printed staff it came
from.

⚠️ It asserts the map against the file rather than trusting the reconstruction:
every (part, measure) in the map must exist in the XML, and every measure in
the XML must appear in the map exactly once. A map that silently disagreed
with the file would send the human to the wrong bars, which is worse than no
map at all -- they would count real music as wrong.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as sx          # noqa: E402


def system_map(result):
    """{(page, system): [{part_index, part_name, staff, measures:[n..]}]}"""
    rec = sx.Record(result)
    parts = sx.build(rec)[0]
    out = collections.defaultdict(list)
    for pi, part in enumerate(parts):
        name = next((r.name for r in part if r.name), None) or sx._default_name(part)
        n = 0
        for run in part:
            first = n + 1
            n += run.n_measures
            if run.n_measures == 0:
                continue
            out[(run.page, run.system)].append({
                "part_index": pi,
                "part_id": f"P{pi + 1}",
                "part_name": name,
                "staff": run.staff,
                "clef": run.clef,
                "fifths": run.fifths,
                "n_measures": run.n_measures,
                "first_measure": first,
                "last_measure": n,
            })
    return out


def _measures_in_xml(xml):
    """{part_id: [measure numbers]} straight out of the emitted text."""
    out = {}
    for chunk in re.split(r'(?=<part id=")', xml):
        m = re.match(r'<part id="([^"]+)"', chunk)
        if not m:
            continue
        out[m.group(1)] = [int(x) for x in
                           re.findall(r'<measure number="(\d+)"', chunk)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "out"))
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = json.loads(Path(args.record).read_text())

    xml, report = sx.to_musicxml(result)
    xml_path = out_dir / f"beethoven5-mvt1-{args.tag}.musicxml"
    xml_path.write_text(xml)
    (out_dir / f"coverage-{args.tag}.json").write_text(json.dumps(report, indent=1))

    smap = system_map(result)
    in_xml = _measures_in_xml(xml)

    # --- the control. A map that disagrees with the file is worse than none.
    seen = collections.Counter()
    problems = []
    for (page, sysi), rows in smap.items():
        for r in rows:
            have = set(in_xml.get(r["part_id"], ()))
            for n in range(r["first_measure"], r["last_measure"] + 1):
                seen[(r["part_id"], n)] += 1
                if n not in have:
                    problems.append(
                        f"map names {r['part_id']} m{n} (p{page}/s{sysi}) "
                        f"and the file has no such measure")
    for pid, nums in in_xml.items():
        for n in nums:
            if seen[(pid, n)] != 1:
                problems.append(
                    f"file has {pid} m{n}; the map claims it {seen[(pid, n)]} times")
    if problems:
        print("MAP DOES NOT MATCH THE FILE -- refusing to write it", file=sys.stderr)
        for p in problems[:20]:
            print("  " + p, file=sys.stderr)
        print(f"  ... {len(problems)} problems", file=sys.stderr)
        return 2

    payload = {
        "_README": "Which exported measures belong to which PRINTED system. "
                   "Derived by calling export.build; asserted against the "
                   "emitted XML measure-for-measure.",
        "record": str(Path(args.record)),
        "provenance": result.get("provenance"),
        "part_join": report.get("part_join"),
        "systems": [
            {"page": p, "system": s, "staves": rows}
            for (p, s), rows in sorted(smap.items())
        ],
    }
    (out_dir / f"system-map-{args.tag}.json").write_text(json.dumps(payload, indent=1))

    print(f"{xml_path}  parts={report['written'].get('parts')} "
          f"measures={sum(len(v) for v in in_xml.values())}")
    print(f"systems={len(smap)}  map checks: {sum(seen.values())} "
          f"(part, measure) pairs, all present exactly once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
