"""Does every bar of an EXPORTED MusicXML file sum to the `<time>` in force?

⚠️ THIS IS THE INDEPENDENT CONTROL FOR ROADMAP 2.8, AND IT DELIBERATELY DOES
NOT IMPORT THE EXPORTER. 2.8 makes `tools/omr/staged/export.py` hold out a bar
whose events do not sum to the meter; a control that reused the exporter's own
arithmetic would be a computation of the same number rather than a measurement
of the file (CLAUDE.md §2 rule 7). So this reads the FILE with
`xml.etree.ElementTree` and nothing else, the way any MusicXML reader would.

The rules it applies, and why each one:

  * **per VOICE, and every voice must fill.** `<backup>` puts voice 2 back at
    the head of the bar, so a reader sees each voice's own timeline. A bar
    whose second voice runs out early is a bar we did not read to its meter.
  * **a `<chord>` member does not advance the cursor** — CLAUDE.md §10's
    double-counting trap, and the defect that made the staged bar sums
    double-count every chord once before.
  * **a `<grace>` note has no duration** and is skipped.
  * **`<rest measure="yes"/>` IS the bar**, whatever `<duration>` it carries —
    a whole rest means the BAR whatever the meter (CLAUDE.md §10). This is the
    one place the control departs from a naive `<duration>` sum, and
    `--strict-measure-rest` turns it off so the difference can be SEEN rather
    than assumed to be zero.
  * **the meter in force is the last `<time>` this part declared**, per bar.
    A bar in a part that has declared no `<time>` yet is UNASSESSABLE and is
    counted apart — never folded into "does not add up" (the `bar_fill.py`
    lesson: a constant bar length silently carries one document's meter onto
    another, 96.3% "overfull" against the wrong constant).

Exit 1 when NOTHING was assessable — the state in which a clean "0 wrong" is a
lie. It does NOT gate on a count of bad bars.
"""
from __future__ import annotations

import argparse
import collections
import json
import xml.etree.ElementTree as ET


def _int_text(el, default=None):
    if el is None or not (el.text or "").strip():
        return default
    return float(el.text)


def bar_sums(meas, div, strict_measure_rest=False):
    """`{voice: units}` for one `<measure>`, plus whether it holds a measure rest."""
    per_voice = collections.defaultdict(float)
    has_measure_rest = False
    holds = collections.Counter()
    for el in meas:
        if el.tag != "note":
            continue
        if el.find("chord") is not None:
            continue                     # a chord member does not advance time
        if el.find("grace") is not None:
            continue
        d = _int_text(el.find("duration"))
        if d is None:
            continue
        v = el.find("voice")
        v = (v.text or "1") if v is not None else "1"
        rest = el.find("rest")
        if rest is not None and rest.get("measure") == "yes":
            has_measure_rest = True
            holds["rest:measure"] += 1
            if not strict_measure_rest:
                per_voice[v] = None      # sentinel: this voice IS the bar
                continue
        elif rest is not None:
            t = el.find("type")
            holds["rest:%s" % (t.text if t is not None else "untyped")] += 1
        else:
            holds["note"] += 1
        if per_voice.get(v) is None and v in per_voice:
            continue                     # already full by a measure rest
        per_voice[v] += d / div
    return per_voice, has_measure_rest, holds


def check(path, strict_measure_rest=False, show=12):
    root = ET.parse(path).getroot()
    names = {}
    for sp in root.findall(".//score-part"):
        pn = sp.find("part-name")
        names[sp.get("id")] = (pn.text if pn is not None else sp.get("id"))
    rows = []
    n_exact = n_short = n_over = n_unassessable = 0
    by_part = collections.Counter()
    for part in root.findall("part"):
        pid = part.get("id")
        div = None
        beats = beat_type = None
        for meas in part.findall("measure"):
            attrs = meas.find("attributes")
            if attrs is not None:
                d = _int_text(attrs.find("divisions"))
                if d is not None:
                    div = d
                t = attrs.find("time")
                if t is not None:
                    b, bt = _int_text(t.find("beats")), _int_text(t.find("beat-type"))
                    if b is not None and bt is not None:
                        beats, beat_type = b, bt
            if div is None or beats is None or beat_type is None:
                n_unassessable += 1
                continue
            want = beats * 4.0 / beat_type
            per_voice, _mr, holds = bar_sums(meas, div, strict_measure_rest)
            bad = None
            for v, got in sorted(per_voice.items()):
                if got is None:          # a measure rest fills its voice
                    continue
                if abs(got - want) < 1e-6:
                    continue
                bad = (v, got)
                break
            if bad is None:
                n_exact += 1
                continue
            v, got = bad
            if got < want:
                n_short += 1
            else:
                n_over += 1
            by_part[names.get(pid, pid)] += 1
            rows.append({"part": names.get(pid, pid), "part_id": pid,
                         "measure": meas.get("number"), "voice": v,
                         "quarters": round(got, 4), "want": round(want, 4),
                         "kind": "short" if got < want else "overfull",
                         "holds": dict(holds)})
    assessed = n_exact + n_short + n_over
    return {
        "file": str(path),
        "strict_measure_rest": strict_measure_rest,
        "assessed": assessed, "exact": n_exact,
        "short": n_short, "overfull": n_over,
        "wrong": n_short + n_over,
        "unassessable": n_unassessable,
        "fraction_exact": (n_exact / assessed) if assessed else None,
        "by_part": dict(by_part.most_common()),
        "bars": rows[: show if show >= 0 else len(rows)],
        "bars_total": len(rows),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("musicxml", nargs="+")
    ap.add_argument("--strict-measure-rest", action="store_true",
                    help="count a `measure=\"yes\"` rest by its <duration> "
                         "instead of treating it as the whole bar")
    ap.add_argument("--show", type=int, default=12,
                    help="how many offending bars to list (-1 = all)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    out = []
    dead = True
    for p in args.musicxml:
        r = check(p, args.strict_measure_rest, args.show)
        out.append(r)
        if r["assessed"]:
            dead = False
        print("%s\n  assessed %d  exact %d  SHORT %d  OVERFULL %d  "
              "unassessable %d" % (p, r["assessed"], r["exact"], r["short"],
                                   r["overfull"], r["unassessable"]))
        if r["by_part"]:
            print("  by part: %s" % r["by_part"])
        for b in r["bars"]:
            print("    m%-5s %-28s voice %s  %s of %s  %s"
                  % (b["measure"], b["part"][:28], b["voice"], b["quarters"],
                     b["want"], b["holds"]))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out if len(out) > 1 else out[0], fh, indent=2)
        print("wrote %s" % args.json)
    if dead:
        print("INSTRUMENT DEAD: no bar could be assessed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
