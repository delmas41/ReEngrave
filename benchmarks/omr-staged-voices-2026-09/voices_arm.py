#!/usr/bin/env python3
"""The stem-direction / voices arm: REACH, then the three rules it un-inerts.

    python3 benchmarks/omr-staged-voices-2026-09/voices_arm.py <staged.json>

⚠️ REACH FIRST, AND FOR THIS FAMILY REACH IS THE WHOLE STORY. The rules were
all present before this landed; what was absent was their INPUT. So the
question a reader needs answered before any other is *how many stems did the
CV rung actually read on this page* — a page whose stems are missed behaves
exactly as it did, and a clean zero from that page says nothing about the
rules.

⚠️ THREE RULES WERE INERT AND THEY ARE COUNTED APART, because their repairs
differ: the divisi guard in `adjudicate_event` (it reported
`not_implemented`), `_directions_conflict` in `export._events`, and
`_paired_spans`'s one-voice test (handed an EMPTY `voice_of` map).
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402


def main(path: str) -> int:
    result = json.load(open(path))
    rec = result["record"]
    prov = result.get("provenance") or {}
    print(f"record    : {path}")
    print(f"provenance: commit={prov.get('commit')} dirty={prov.get('dirty')}")

    # ── 1. REACH ──────────────────────────────────────────────────────────
    stems = [o for o in rec["observations"] if o["quantity"] == Q.STEM]
    heads = [o for o in rec["observations"] if o["quantity"] == Q.NOTEHEAD_CLASS]
    print("\n── REACH ──")
    print(f"  CV stem rows        : {len(stems)}")
    print(f"  noteheads read      : {len(heads)}")
    if not stems:
        print("  ⚠️ ZERO STEMS. Every rule below stays inert on this page and"
              " nothing here is a result about them.")
        return 0

    # ── 2. STEM DIRECTION ─────────────────────────────────────────────────
    d = collections.Counter()
    for v in rec["verdicts"]:
        if v["quantity"] == Q.STEM_DIRECTION:
            d[(v["outcome"], v["reason"], v.get("value"))] += 1
    print("\n── STEM DIRECTION ──")
    for (outcome, reason, value), n in sorted(d.items(), key=lambda kv: -kv[1]):
        print(f"  {outcome:10s} {reason:18s} {str(value):6s} {n}")
    decided = sum(n for (o, _r, _v), n in d.items() if o == "decided")
    total = sum(d.values())
    if total:
        print(f"  decided {decided} of {total} noteheads "
              f"({decided / total:.1%})")
    print("  ⚠️ `no_stem` is ORDINARY (a whole note has none, and on a scan a"
          " stem is often missed); `stems_disagree` is ink we cannot read.")

    # ── 3. VOICES, AND THE GUARD ──────────────────────────────────────────
    v_reasons = collections.Counter()
    two = 0
    for v in rec["verdicts"]:
        if v["quantity"] == Q.VOICES:
            v_reasons[(v["outcome"], v["reason"])] += 1
            if v["outcome"] == "decided" and (v["value"] or {}).get("n_voices", 1) > 1:
                two += 1
    guard = collections.Counter()
    separated = 0
    for v in rec["verdicts"]:
        if v["quantity"] == Q.EVENT and v["outcome"] == "decided":
            det = v.get("detail") or {}
            guard[det.get("divisi_guard")] += 1
            separated += int(det.get("divisi_separated") or 0)
    print("\n── VOICES ──")
    for k, n in sorted(v_reasons.items()):
        print(f"  {k[0]:10s} {k[1]:20s} {n}")
    print(f"  bars the record says hold TWO streams: {two}")
    print("\n── THE DIVISI GUARD (was `not_implemented`) ──")
    print(f"  per bar: {dict(guard)}")
    print(f"  chords SEPARATED that x alone would have merged: {separated}")

    # ── 4. THE FILE, AND THE CONTROL ──────────────────────────────────────
    xml, rep = SX.to_musicxml(result)
    print("\n── EXPORT ──")
    print(f"  two-voice bars      : {rep['written'].get('two_voice_bars', 0)}")
    print(f"  <backup> elements   : {xml.count('<backup>')}")
    print(f"  rests duplicated    : "
          f"{rep['written'].get('rests_duplicated_across_voices', 0)}")
    print(f"  balance             : {json.dumps(rep['balance'])}")
    print(f"  arcs not written    : {json.dumps(rep['arcs_not_written'])}")

    # ⚠️ ONE RECORD, EXPORTED TWICE. With the VOICES verdicts removed the
    # exporter falls back to one stream and `_paired_spans` to an empty map,
    # which is exactly the behaviour this change replaced.
    off = {**result, "record": {
        **rec, "verdicts": [v for v in rec["verdicts"]
                            if v["quantity"] != Q.VOICES]}}
    xml_off, rep_off = SX.to_musicxml(off)
    print("\n── THE ARM (voices verdicts removed) ──")
    print(f"  file identical      : "
          f"{hashlib.md5(xml.encode()).hexdigest() == hashlib.md5(xml_off.encode()).hexdigest()}")
    moved = {k: (rep["written"].get(k), rep_off["written"].get(k))
             for k in set(rep["written"]) | set(rep_off["written"])
             if rep["written"].get(k) != rep_off["written"].get(k)}
    print(f"  counters that moved : {moved or 'nothing'}")
    print("  ⚠️ NOTHING MOVING HERE IS A REAL ANSWER, NOT A NULL RESULT: it"
          " means the page holds no bar the record reads as two streams.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
