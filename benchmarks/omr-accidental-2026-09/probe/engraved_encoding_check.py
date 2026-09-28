"""ROADMAP 2.7 — every `<accidental>` our ENGRAVED file writes, looked up in
the source encoding: same part (ordinal), same measure number, a note of the
same step and octave — does the encoding sound the same alteration there?

⚠️ WHAT THIS CAN AND CANNOT SAY. It checks the SOUND we wrote on a note we
marked as printed against the encoding's sound for that letter+octave in that
bar, which is independent of our pairing geometry (the encoding knows nothing
of boxes). It cannot say the glyph was drawn on that note — Verovio draws one
accidental per `<alter>` (100 drawn vs 20 encoded as printed,
`pagetruth.json` `render_fidelity`), so the encoding's own `<accidental>` is
not the page. A `mismatch` is a wrong sound; a `no_such_note` means the
measure/part join or our pitch is off and is reported, not scored.

    python3 benchmarks/omr-accidental-2026-09/probe/engraved_encoding_check.py \\
        --ours <engraved-arm.musicxml> --truth <fixture .musicxml> --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _notes(path):
    root = ET.parse(path).getroot()
    out = collections.defaultdict(list)     # (part_idx, measure) -> notes
    for pi, part in enumerate(root.findall("part")):
        for m in part.findall("measure"):
            num = m.get("number")
            for n in m.findall("note"):
                p = n.find("pitch")
                if p is None:
                    continue
                alter = p.findtext("alter")
                out[(pi, num)].append({
                    "step": p.findtext("step"), "octave": p.findtext("octave"),
                    "alter": int(float(alter)) if alter else 0,
                    "accidental": n.findtext("accidental")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shift-part", type=int, default=0,
                    help="CONTROL: look each note up in part i+N of the "
                         "truth; the agreement must collapse")
    a = ap.parse_args()
    ours, truth = _notes(a.ours), _notes(a.truth)
    rows = []
    for (pi, num), notes in sorted(ours.items()):
        for n in notes:
            if not n["accidental"]:
                continue
            cands = [t for t in truth.get((pi + a.shift_part, num), [])
                     if t["step"] == n["step"] and t["octave"] == n["octave"]]
            alters = sorted({t["alter"] for t in cands})
            if not cands:
                verdict = "no_such_note"
            elif alters == [n["alter"]]:
                verdict = "agree"
            elif n["alter"] in alters:
                verdict = "agree_one_of"
            else:
                verdict = "MISMATCH"
            rows.append({"part": pi, "measure": num,
                         "note": f'{n["step"]}{n["octave"]}',
                         "ours": [n["alter"], n["accidental"]],
                         "truth_alters": alters, "check": verdict})
    tally = dict(collections.Counter(r["check"] for r in rows))
    Path(a.out).write_text(json.dumps({"tally": tally, "rows": rows},
                                      indent=1))
    print(json.dumps(tally))
    for r in rows:
        if r["check"] != "agree":
            print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
