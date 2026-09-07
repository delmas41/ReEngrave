"""WHAT changes when `parts` is sorted? Compared musically, never by bytes.

⚠️ A BYTE COMPARISON IS USELESS HERE and was already caught being so today:
music21 mints a fresh random `<score-instrument id="I…">` on every write, so
two writes of one score differ on ~92 lines. This walks the parsed scores and
compares part identity and note content.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_parts_order_diff.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

import page_normalise                                    # noqa: E402
from music21 import chord, converter, note, stream       # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
ADDITIONS = (MAIN / "benchmarks/omr-scan-e2e-2026-09"
             / "works.staves-additions-completion.json")


def content(part) -> tuple:
    out = []
    for m in part.getElementsByClass(stream.Measure):
        body = []
        for el in m.recurse().notesAndRests:
            if isinstance(el, note.Rest):
                body.append(("R", float(el.duration.quarterLength)))
            elif isinstance(el, chord.Chord):
                body.append((tuple(sorted(p.nameWithOctave for p in el.pitches)),
                             float(el.duration.quarterLength)))
            elif isinstance(el, note.Note):
                body.append(((el.pitch.nameWithOctave,),
                             float(el.duration.quarterLength)))
            else:
                body.append(("U", float(el.duration.quarterLength)))
        out.append((m.number, tuple(body)))
    return tuple(out)


def main() -> int:
    add = json.loads(ADDITIONS.read_text())
    tmp = Path(tempfile.mkdtemp(prefix="parts-order-diff-"))
    for rid, r in add["rows"].items():
        if r.get("status") != "done":
            continue
        smap = r.get("staves_for_works_json") or []
        if not any(list(s["parts"]) != sorted(set(s["parts"])) for s in smap):
            continue
        truth = REC / f"{rid}.truth.musicxml"
        arms = {}
        for tag, m in (
                ("as_confirmed", [{"name": s["name"], "parts": list(s["parts"])}
                                  for s in smap]),
                ("sorted", [{"name": s["name"], "parts": sorted(set(s["parts"]))}
                            for s in smap])):
            out = tmp / f"{rid}.{tag}.musicxml"
            page_normalise.write(truth, m, out)
            arms[tag] = list(converter.parse(str(out)).parts)

        a, b = arms["as_confirmed"], arms["sorted"]
        print(f"\n=== {rid}  ({len(a)} vs {len(b)} output parts) ===")
        entry0 = smap[0]
        print(f"    entry 0 {entry0['name']!r}: as confirmed {entry0['parts']}")
        print(f"                     sorted {sorted(set(entry0['parts']))}")
        for i, (pa, pb) in enumerate(zip(a, b)):
            na = getattr(pa, "partName", None)
            nb = getattr(pb, "partName", None)
            ca, cb = content(pa), content(pb)
            if na != nb or ca != cb:
                bars = [m for (m, _x), (_m2, _y) in zip(ca, cb)
                        if dict(ca).get(m) != dict(cb).get(m)]
                print(f"  part {i}: NAME {na!r} -> {nb!r}"
                      f"   content differs in {len(bars)} bar(s)"
                      f"{' e.g. ' + str(bars[:6]) if bars else ''}")
        print(f"  identical parts: "
              f"{sum(1 for pa, pb in zip(a, b) if content(pa) == content(pb))}"
              f"/{len(a)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
