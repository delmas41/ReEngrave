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
from tools.omr.staged.__main__ import (               # noqa: E402
    _provenance, _settings)


def _export_stamp() -> dict:
    """The tree and settings of the EXPORTING process, not the gathering one.

    ⚠️ Two processes, two stamps. A record is gathered once and exported many
    times, sometimes hours later off a different tree, and the export is where
    every element count in the artefact comes from.
    """
    stamp = _provenance()
    # ⚠️ NO `args`: this arm's own `--record`/`--tag`/`--out-dir` say nothing
    # about how the music was read, and `--out`-shaped arguments are exactly
    # what `_settings` excludes for making two arms of one A/B look different.
    stamp["settings"] = _settings()
    return stamp


def system_map(result):
    """{(page, system): [{part_index, part_name, staff, measures:[n..]}]}

    ⚠️ THE NUMBERS COME FROM THE EXPORTER'S OWN RULE, CALLED, NOT RESTATED.
    Since 2026-09-14 a measure is numbered by its place in the DOCUMENT's bar
    sequence rather than by its part's own running count, and a map that kept
    the old count would name the wrong bars — which is the one failure this
    map exists to prevent, since it sends a human to the wrong music. The
    per-part fallback below is reached only where `_document_bar_offsets`
    refused, and then it is again exactly what the exporter did.
    """
    rec = sx.Record(result)
    parts = sx.build(rec)[0]
    # ⚠️ CALLED, NOT RE-DERIVED -- the one thing this map used to compute for
    # itself. It kept its own running per-part count, which was a second copy
    # of the exporter's numbering rule; the day the exporter started numbering
    # by the DOCUMENT's bar sequence instead, the copy disagreed and the
    # map-vs-file control below went red on 108 (part, measure) pairs. That is
    # the control working, and the repair is to stop holding the rule twice.
    offsets, numbering = sx._document_bar_offsets(parts)
    # ⚠️⚠️ AND THE TACET SPANS, because since 2026-09-15 the exporter WRITES
    # BARS FOR A SYSTEM A PART IS NOT PRINTED ON. This map walked the part's
    # `StaffRun`s only, so padded bars belonged to no row and the control
    # below fired on 2,924 (part, measure) pairs -- exactly the run's own
    # `tacet_bars_padded` count. The control was RIGHT and the map was
    # incomplete; the repair is to walk what the exporter walks.
    spans = None if offsets is None else sx._spans_from_numbering(numbering)
    out = collections.defaultdict(list)
    for pi, part in enumerate(parts):
        name = next((r.name for r in part if r.name), None) or sx._default_name(part)
        # ⚠️⚠️ THIS LOOP WAS BROKEN ON MAIN AND RAISED `NameError: starts` ON
        # EVERY RUN (found 2026-09-17, the first re-run since the numbering
        # change). The 2026-09-14 repair computed `first`/`last` from
        # `offsets` and left the two pre-repair lines BELOW it, which
        # overwrote both from a `starts` dict that no longer exists -- so the
        # arm could not build a map at all, and the per-part fallback also
        # read `n` before assignment. Repaired here rather than worked
        # around: this map's whole job is to send a human to the RIGHT bars.
        # ⚠️ `running` is the part's OWN count and is used only where
        # `_document_bar_offsets` refused; it is kept separate from `first`
        # so a single missing offset key cannot poison the fallback for the
        # rest of the part.
        running = 0
        for sys_key, run, sys_bars in sx._tacet_walk(part, offsets, spans):
            # ⚠️ A TACET SPAN'S LENGTH IS THE SYSTEM'S, a present run's is its
            # OWN -- which is what the exporter writes, and they can differ
            # wherever a staff read fewer bars than its system voted for.
            n_meas = sys_bars if run is None else run.n_measures
            if n_meas == 0:
                continue
            base = None if offsets is None else offsets.get(sys_key)
            first = (running + 1) if base is None else (base + 1)
            last = first + n_meas - 1
            running += n_meas
            out[sys_key].append({
                "part_index": pi,
                "part_id": f"P{pi + 1}",
                "part_name": name,
                # ⚠️ `tacet` IS THE FIELD THE HUMAN NEEDS: these bars are in
                # the FILE and are NOT on the PRINT, so they are padding and
                # never a fix-action. A map that did not say so would invite
                # counting silence as missing music.
                "tacet": run is None,
                "staff": None if run is None else run.staff,
                "clef": None if run is None else run.clef,
                "fifths": None if run is None else run.fifths,
                "n_measures": n_meas,
                "first_measure": first,
                "last_measure": last,
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
        # ⚠️ THE TREE THAT GATHERED IT ...
        "provenance": result.get("provenance"),
        # ⚠️⚠️ ... AND THE TREE THAT EXPORTED IT, which nothing recorded until
        # 2026-09-17. FINDINGS.md's own note on the first count: *"the base arm
        # is not the artefact Sean looked at and the difference CANNOT BE
        # ATTRIBUTED -- export_arm.py writes no provenance stamp. The record
        # names the tree that GATHERED it and nothing names the tree that
        # EXPORTED it, hours later in a separate process. A cleanup artefact
        # whose own numbers cannot be reproduced is a gap worth closing before
        # the next count."* This is that gap, closed before this count.
        # ⚠️ IMPORTED, never restated: `_provenance` carries the atomicity rule
        # (commit and dirty are set together or neither is) and `_settings` the
        # OMR_-only rule, and a second copy here would drift from both.
        "export_provenance": _export_stamp(),
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
