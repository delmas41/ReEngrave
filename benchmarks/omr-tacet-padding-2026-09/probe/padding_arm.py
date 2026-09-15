"""The A/B: a tacet span left as a hole, and the same span PADDED.

    python3 benchmarks/omr-tacet-padding-2026-09/probe/padding_arm.py
    python3 benchmarks/omr-tacet-padding-2026-09/probe/padding_arm.py --check --write

⚠️⚠️ **WHY THIS IS NOT A RE-EXPORT.** A cloud container has no `omr-weights/`
and no `library/`, so no staged record can be gathered here and none is
committed — `benchmarks/omr-cleanup-count-2026-09/out/` holds the EXPORTED file
and the SYSTEM MAP, not `record-p1-p4.json`. So `to_musicxml` cannot be called
on the real document. This arm takes `numbering_arm.py`'s move one step on: it
reconstructs the exporter's own `StaffRun` objects from the map — which was
asserted measure-for-measure against that XML when it was written — and calls
the **SHIPPED** `export._document_bar_offsets`, `export._tacet_walk` and
`export._pad_tacet_span` on them. The rules under test are the ones in the
tree; only their INPUT is reconstructed.

⚠️ **THE BASE FILE IS REPAIR 2's OUTPUT, NOT THE COMMITTED ARTEFACT.** Padding
is the third of three ranked repairs and it builds on the second: a padded bar
has to be written at a definite place in the document's bar sequence, and that
sequence is what `benchmarks/omr-measure-numbering-2026-09/` produced. Splicing
into the per-part-numbered artefact would be padding onto numbers the previous
repair has already shown mean two different things.

⚠️ **THE BLIND SPOT, STATED RATHER THAN BURIED.** An arm that splices measures
into an already-exported file is blind by construction to everything upstream
of `_part_xml`: a GATHER change, a JOIN change, a note that did or did not
reach the file. ⚠️⚠️ And one of those is not hypothetical here — the committed
record was gathered BEFORE `adjudicate_slot_index`'s short-system rule landed,
so its 12-part join still carries the 12-of-75 graft that repair measured. This
arm therefore pads the join it is given; it does NOT claim that join is right.
Driving `to_musicxml` end to end is `tools/omr/tests/test_staged_tacet_padding.py`'s
job, on synthetic records, for exactly that reason. The two instruments have
opposite blind spots on purpose.

⚠️ **ARM B IS A COUNTERFACTUAL AND IS LABELLED ONE.** On this document the
meter is decided on ONE system of seven, so the shipped rule refuses every one
of the 149 tacet bars and arm A is a clean, correct, completely inert zero. A
zero that means *"the rule declined"* and a zero that means *"the instrument is
dead"* must not read alike, so arm B supplies the meter and measures what the
padding is worth the day the meter is settled. The meter it supplies is the
2/4 this file's own system p1/s0 READS, and CLAUDE.md records `OMR_METER_CARRY=1`
deciding `carried` 2/4 on all six abstaining systems of this exact document at
support +6/+13/+9/+18/+9/+7. It is still a counterfactual: nothing here reads a
meter off page 2.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as SX          # noqa: E402

SYSTEM_MAP = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"
BASE_XML = ROOT / ("benchmarks/omr-measure-numbering-2026-09/out/"
                   "beethoven5-mvt1-p1-p4.document-numbered.musicxml")
COMMITTED_XML = ROOT / ("benchmarks/omr-cleanup-count-2026-09/out/"
                        "beethoven5-mvt1-p1-p4.musicxml")
OUT = HERE / "out"

_PART_SPLIT = re.compile(r'(?=  <part id=")')
_MEASURE = re.compile(r'(    <measure number="(\d+)">.*?    </measure>\n)', re.S)


# ─────────────────────────────────────────────────────────────────────────────
# Reconstruction — the exporter's own structures, from the exporter's own map
# ─────────────────────────────────────────────────────────────────────────────


def rebuild_parts(smap):
    """`[[StaffRun, ...], ...]` in the exporter's own part and system order."""
    by_part = collections.defaultdict(list)
    order = []
    for sd in smap["systems"]:
        key = (sd["page"], sd["system"])
        order.append(key)
        for st in sd["staves"]:
            run = SX.StaffRun(
                key=SX._staff_key(key[0], key[1], st["staff"]),
                page=key[0], system=key[1], staff=st["staff"],
                clef=st.get("clef"), fifths=st.get("fifths"),
                n_measures=int(st["n_measures"]),
                n_measures_decided=True)
            by_part[st["part_index"]].append((order.index(key), run))
    parts = []
    for pi in sorted(by_part):
        parts.append([r for _o, r in sorted(by_part[pi], key=lambda e: e[0])])
    return parts, order


def fidelity_problems(smap):
    """Does the map account for every staff the export says each system had?"""
    problems = []
    widths = set(smap["part_join"]["staves_per_system"])
    for sd in smap["systems"]:
        n = len(sd["staves"])
        if n not in widths:
            problems.append(
                "p%d/s%d: the map holds %d staves, the export's own "
                "staves_per_system is %s" % (sd["page"], sd["system"], n,
                                             sorted(widths)))
    return problems


def part_measures(xml):
    """`{part id: [(number, whole <measure> block including newline)]}`."""
    out = {}
    for chunk in _PART_SPLIT.split(xml):
        m = re.match(r'  <part id="(P\d+)"', chunk)
        if not m:
            continue
        out[m.group(1)] = [(int(mo.group(2)), mo.group(1))
                           for mo in _MEASURE.finditer(chunk)]
    return out


def meters_from_the_file(xml, smap):
    """`{(page, system): meter dict or None}`, read off the file's OWN stream.

    ⚠️ DERIVED, NEVER ASSUMED. `_part_xml` writes an `<attributes>` block at a
    bar whose clef, key or meter CHANGED, and a `<time>` element appears in it
    iff the meter is not None — so walking each part's measures and updating a
    running meter at every attributes block recovers exactly what
    `Q.METER` held per system. Every part is walked and the readings must
    AGREE per system (`Q.METER` is scoped to the system, so two parts
    disagreeing would mean the reconstruction is wrong, not the record).
    """
    parts = part_measures(xml)
    runs = collections.defaultdict(list)
    for sd in smap["systems"]:
        for st in sd["staves"]:
            runs[st["part_id"]].append(((sd["page"], sd["system"]),
                                        int(st["n_measures"])))
    seen = collections.defaultdict(set)
    for pid, rl in runs.items():
        idx, cur = 0, "UNSET"
        for key, n in rl:
            for _i in range(n):
                _num, body = parts[pid][idx]
                idx += 1
                am = re.search(r"<attributes>(.*?)</attributes>", body, re.S)
                if am:
                    t = re.search(r"<time([^>]*)>\s*<beats>(\d+)</beats>"
                                  r"\s*<beat-type>(\d+)</beat-type>",
                                  am.group(1), re.S)
                    if t is None:
                        cur = None
                    else:
                        sym = re.search(r'symbol="(\w+)"', t.group(1))
                        cur = {"numerator": int(t.group(2)),
                               "denominator": int(t.group(3))}
                        if sym:
                            cur["raw"] = sym.group(1)
                seen[key].add(json.dumps(cur, sort_keys=True))
    out, disagree = {}, []
    for key, vals in seen.items():
        if len(vals) != 1:
            disagree.append("p%d/s%d: %s" % (key[0], key[1], sorted(vals)))
        v = json.loads(sorted(vals)[0])
        out[key] = None if v in (None, "UNSET") else v
    return out, disagree


# ─────────────────────────────────────────────────────────────────────────────
# The arm: call the SHIPPED padder and splice what it writes into the file
# ─────────────────────────────────────────────────────────────────────────────


def pad(parts, offsets, spans, meters):
    """`({part index: {number: block}}, counters)` from `_pad_tacet_span`."""
    counters = collections.Counter()
    blocks = {}
    for pi, part in enumerate(parts):
        here = {}
        first = False        # every part of this document opens with a run
        for sys_key, maybe_run, sys_bars in SX._tacet_walk(part, offsets, spans):
            if maybe_run is not None:
                continue
            lines = []
            first = SX._pad_tacet_span(
                lines, sys_key, sys_bars, offsets, meters, 96, counters,
                SX.meter_segments_enabled(), first)
            for mo in _MEASURE.finditer("\n".join(lines) + "\n"):
                here[int(mo.group(2))] = mo.group(1)
        blocks[pi] = here
    return blocks, counters


def splice(xml, blocks, part_ids):
    """Insert each part's padded measures, in number order, into its `<part>`."""
    chunks = _PART_SPLIT.split(xml)
    out, pi = [], 0
    for chunk in chunks:
        m = re.match(r'  <part id="(P\d+)"', chunk)
        if not m:
            out.append(chunk)
            continue
        add = blocks.get(pi, {})
        if not add:
            out.append(chunk)
            pi += 1
            continue
        pieces = _MEASURE.split(chunk)
        # `re.split` with two groups yields [pre, block, number, pre, ...]
        rebuilt, buf = [], []
        existing = []
        i = 0
        while i < len(pieces):
            if i % 3 == 0:
                buf.append(pieces[i])
                i += 1
            else:
                existing.append((int(pieces[i + 1]), pieces[i]))
                buf.append(None)
                i += 2
        merged = sorted(existing + list(add.items()), key=lambda e: e[0])
        head = buf[0]
        tail = buf[-1] if len(buf) > 1 else ""
        rebuilt.append(head)
        rebuilt.extend(b for _n, b in merged)
        rebuilt.append(tail)
        out.append("".join(rebuilt))
        pi += 1
    if pi != len(part_ids):
        raise SystemExit("the file holds %d parts, the map %d"
                         % (pi, len(part_ids)))
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    smap = json.loads(SYSTEM_MAP.read_text())
    base = BASE_XML.read_text()
    parts, order = rebuild_parts(smap)

    # ── 0. REACH, before anything else ──────────────────────────────────────
    print("=" * 78)
    print("0. REACH — what this instrument can speak about")
    print("=" * 78)
    n_meas = sum(run.n_measures for part in parts for run in part)
    print("   document        : %s" % smap["record"])
    print("   record commit   : %s (dirty=%s)"
          % (smap["provenance"]["commit"][:8], smap["provenance"]["dirty"]))
    print("   base file       : %s" % BASE_XML.name)
    print("   parts           : %d" % len(parts))
    print("   systems         : %d  (%s)"
          % (len(order), ", ".join("p%d/s%d" % k for k in order)))
    print("   measures in file: %d" % n_meas)

    offsets, numbering = SX._document_bar_offsets(parts)
    if offsets is None:
        print()
        print("INSTRUMENT DEAD: the document's bar sequence was REFUSED (%s),"
              % numbering.get("refused"))
        print("so there is no number line to pad into and nothing to measure.")
        return 2
    spans = [((r["page"], r["system_index"]), int(r["bars"]))
             for r in numbering["systems"] if r["bars"] is not None]

    tacet = []
    for pi, part in enumerate(parts):
        have = {(r.page, r.system) for r in part}
        miss = [(k, n) for k, n in spans if k not in have]
        if miss:
            tacet.append((pi, miss))
    n_tacet_bars = sum(n for _pi, miss in tacet for _k, n in miss)
    print("   parts TACET on at least one system: %d of %d"
          % (len(tacet), len(parts)))
    print("   TACET BARS the document holds     : %d   <-- the population"
          % n_tacet_bars)
    for pi, miss in tacet:
        print("       P%-3d %3d bars  (%s)"
              % (pi + 1, sum(n for _k, n in miss),
                 ", ".join("p%d/s%d" % k for k, _n in miss)))
    if not tacet or n_tacet_bars == 0:
        print()
        print("INSTRUMENT DEAD: every part appears on every system, so there")
        print("is no tacet span to pad. That is not a clean result.")
        return 2

    meters, disagree = meters_from_the_file(base, smap)
    if disagree:
        print()
        print("RECONSTRUCTION INCOMPLETE — parts disagree about a system's meter:")
        for d in disagree:
            print("  -", d)
        return 2
    problems = fidelity_problems(smap)
    if problems:
        print()
        print("RECONSTRUCTION INCOMPLETE:")
        for p in problems:
            print("  -", p)
        return 2

    print()
    print("   the METER each system holds, read off the file's own attribute")
    print("   stream (all 12 parts agree on every system):")
    known = 0
    for key, _n in spans:
        m = meters.get(key)
        print("       p%d/s%d  %s" % (key[0], key[1],
                                      "—  (no meter was read)" if m is None
                                      else "%d/%d" % (m["numerator"],
                                                      m["denominator"])))
        known += 1 if m is not None else 0
    print("   systems with a meter: %d of %d" % (known, len(spans)))
    reachable = sum(n for _pi, miss in tacet for k, n in miss
                    if meters.get(k) is not None)
    print("   TACET BARS WHOSE LENGTH IS KNOWN  : %d of %d   <-- ARM A's reach"
          % (reachable, n_tacet_bars))

    # ── 1. ARM A — the document as it stands ────────────────────────────────
    print()
    print("=" * 78)
    print("1. ARM A — the shipped rule, on the meters this document ACTUALLY")
    print("   READ.  `export._pad_tacet_span`, called, not restated.")
    print("=" * 78)
    a_blocks, a_counters = pad(parts, offsets, spans, meters)
    a_padded = int(a_counters.get("tacet_bars_padded", 0))
    a_refused = int(a_counters.get("tacet_bars_not_padded_without_meter", 0))
    print("   bars padded                        : %d" % a_padded)
    print("   bars REFUSED (no meter was read)   : %d" % a_refused)
    print("   the partition balances             : %s"
          % (a_padded + a_refused == n_tacet_bars))
    if a_padded == 0:
        print()
        print("   ⚠️ A CLEAN ZERO THAT IS THE RULE WORKING, NOT THE INSTRUMENT")
        print("   FAILING. Every tacet bar on this document sits on a system")
        print("   whose meter was never read, and a MusicXML rest must carry a")
        print("   <duration>: writing one would assert 4.0 quarters in a 2/4")
        print("   movement. The lever is the METER, not this rule.")

    # ── 2. ARM B — the counterfactual: the meter settled ────────────────────
    print()
    print("=" * 78)
    print("2. ARM B — COUNTERFACTUAL: the same rule once the meter is settled")
    print("=" * 78)
    read_meters = [m for m in meters.values() if m is not None]
    if not read_meters:
        print("   this document reads NO meter anywhere; no counterfactual.")
        return 2
    supplied = dict(read_meters[0])
    print("   supplying %d/%d — the meter this file's own p1/s0 READS — to"
          % (supplied["numerator"], supplied["denominator"]))
    print("   every system. NOT a reading: see this module's header.")
    b_meters = {k: (meters.get(k) or supplied) for k, _n in spans}
    b_blocks, b_counters = pad(parts, offsets, spans, b_meters)
    b_padded = int(b_counters.get("tacet_bars_padded", 0))
    b_refused = int(b_counters.get("tacet_bars_not_padded_without_meter", 0))
    print("   bars padded                        : %d" % b_padded)
    print("   bars REFUSED                       : %d" % b_refused)
    print("   the partition balances             : %s"
          % (b_padded + b_refused == n_tacet_bars))

    part_ids = ["P%d" % (i + 1) for i in range(len(parts))]
    b_xml = splice(base, b_blocks, part_ids)
    base_m = part_measures(base)
    new_m = part_measures(b_xml)
    print()
    print("   %-5s %8s %8s   %s" % ("part", "before", "after", "numbers"))
    for pi, pid in enumerate(part_ids):
        nums = [n for n, _b in new_m[pid]]
        print("   %-5s %8d %8d   %s"
              % (pid, len(base_m[pid]), len(new_m[pid]),
                 "1..%d contiguous" % max(nums)
                 if nums == list(range(1, max(nums) + 1))
                 else "GAPS: %d numbers over a span of %d"
                      % (len(nums), max(nums))))

    # ── 3. THE CONTROLS ─────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("3. THE CONTROLS — every one of them can fail")
    print("=" * 78)
    # (a) EVERY EXISTING MEASURE IS UNTOUCHED — byte for byte, in order.
    untouched = True
    for pid in part_ids:
        added = set(b_blocks[int(pid[1:]) - 1])
        kept = [(n, b) for n, b in new_m[pid] if n not in added]
        if kept != base_m[pid]:
            untouched = False
            print("   P%s: an EXISTING measure changed" % pid)
    print("   every existing measure byte-identical and in order : %s"
          % untouched)
    # (b) the positive control for (a): the files DO differ
    print("   the padded file DIFFERS from the base (positive)   : %s"
          % (b_xml != base))
    # (c) removing exactly the inserted blocks restores the base byte for byte
    stripped = b_xml
    for pi, pid in enumerate(part_ids):
        for _n, block in sorted(b_blocks[pi].items()):
            stripped = stripped.replace(block, "", 1)
    print("   deleting exactly the inserted blocks restores the")
    print("   base file byte for byte                            : %s"
          % (stripped == base))
    # (d) a padded measure holds SILENCE and nothing else
    notes = sum(len(re.findall(r"<pitch>", b))
                for pi in range(len(parts)) for b in b_blocks[pi].values())
    rests = sum(len(re.findall(r"<rest", b))
                for pi in range(len(parts)) for b in b_blocks[pi].values())
    sized = sum(len(re.findall(r'<rest measure="yes"/>', b))
                for pi in range(len(parts)) for b in b_blocks[pi].values())
    print("   padded bars: %d <pitch>, %d <rest>, %d of them measure=\"yes\""
          % (notes, rests, sized))
    silence = notes == 0 and rests == b_padded and sized == b_padded
    print("   a padded bar is a sized full-measure rest, nothing")
    print("   else                                               : %s" % silence)
    # (e) the file's parts now agree about how many bars there are
    lens = {len(new_m[pid]) for pid in part_ids}
    numsets = {tuple(n for n, _b in new_m[pid]) for pid in part_ids}
    print("   after padding every part holds the SAME measure")
    print("   numbers                                            : %s   (%s)"
          % (len(numsets) == 1, sorted(lens)))
    base_sets = {tuple(n for n, _b in base_m[pid]) for pid in part_ids}
    print("   and before padding they did NOT (positive control)  : %s   (%s)"
          % (len(base_sets) > 1,
             sorted({len(base_m[p]) for p in part_ids})))

    # (f) music21 reads it back, with the NOTE SEQUENCE unchanged
    m21 = None
    try:
        from music21 import converter                       # noqa: PLC0415
        m21 = True
    except Exception:                                       # noqa: BLE001
        print("   music21 absent — read-back control SKIPPED")
    seq_ok = None
    if m21:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "a.musicxml"
            pb = Path(td) / "b.musicxml"
            pa.write_text(base)
            pb.write_text(b_xml)
            sa = converter.parse(str(pa), format="musicxml")
            sb = converter.parse(str(pb), format="musicxml")

            def seqs(sc):
                # ⚠️ `pitches`, not `pitch` — a Chord is a `note` to music21's
                # `.notes` filter and has no `.pitch`. Comparing the whole
                # tuple is also the stronger control: a chord losing a member
                # would otherwise pass.
                return [[(tuple(q.nameWithOctave for q in n.pitches),
                          float(n.quarterLength))
                         for n in p.recurse().notes] for p in sc.parts]
            qa, qb = seqs(sa), seqs(sb)
            seq_ok = qa == qb
            print("   music21: parts %d -> %d, measures %d -> %d"
                  % (len(sa.parts), len(sb.parts),
                     sum(len(p.getElementsByClass("Measure")) for p in sa.parts),
                     sum(len(p.getElementsByClass("Measure")) for p in sb.parts)))
            print("   the NOTE SEQUENCE of every part is unchanged        : %s"
                  % seq_ok)
            print("   (positive control: it holds %d notes, not zero)      : %s"
                  % (sum(len(q) for q in qa), sum(len(q) for q in qa) > 0))

            # ⚠️ AND WHAT IT BUYS, WHICH IS NOT THE MEASURE COUNT. The point
            # of a padded span is that asking the SCORE for a stretch of bars
            # returns every part's account of it. `measures()` slices each
            # part by its own measure NUMBERS, so a part with a hole there
            # comes back empty and a reader cannot tell "silent" from
            # "absent" — the ABSENT/DECLINED collapse, in the music.
            print()
            print("   asking the SCORE for a stretch of bars — parts that")
            print("   come back with a measure at all:")
            for lo, hi in ((5, 7), (70, 72), (100, 102)):
                na = sum(1 for p in sa.measures(lo, hi).parts
                         if len(p.getElementsByClass("Measure")))
                nb = sum(1 for p in sb.measures(lo, hi).parts
                         if len(p.getElementsByClass("Measure")))
                print("       bars %3d-%-3d : %2d of %d  ->  %2d of %d"
                      % (lo, hi, na, len(sa.parts), nb, len(sb.parts)))

    if args.write:
        OUT.mkdir(exist_ok=True)
        (OUT / "beethoven5-mvt1-p1-p4.tacet-padded-COUNTERFACTUAL.musicxml"
         ).write_text(b_xml)
        (OUT / "padding.json").write_text(json.dumps({
            "base": BASE_XML.name,
            "tacet_bar_total": n_tacet_bars,
            "systems_with_a_meter": known,
            "systems": len(spans),
            "arm_a": {"padded": a_padded, "refused_no_meter": a_refused},
            "arm_b_counterfactual": {"meter": supplied, "padded": b_padded,
                                     "refused_no_meter": b_refused},
            "measures": {"before": sum(len(v) for v in base_m.values()),
                         "after": sum(len(v) for v in new_m.values())},
        }, indent=2))
        print()
        print("   written to %s" % OUT)

    ok = (untouched and b_xml != base and stripped == base and silence
          and len(numsets) == 1 and len(base_sets) > 1
          and a_padded + a_refused == n_tacet_bars
          and b_padded + b_refused == n_tacet_bars
          and (seq_ok is not False))
    print()
    print("ALL CONTROLS PASS" if ok else "A CONTROL FAILED")
    if args.check and not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
