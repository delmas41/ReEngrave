"""Are the labels the OCR rungs read RIGHT? -- against HAND-READ truth.

Part A measured what a margin-label read COSTS and how far it REACHES (50 of
75 staves). Neither is accuracy, and this repo has the scar: `Tr. Teq.` ->
Trumpet resolves at MEDIUM confidence on a trombone staff, and in the staged
path nothing outranks a matched label, so a confident wrong label IS the
graft. Reach was measured first on purpose; this is the other half.

⚠️⚠️ THE TRUTH HAD TO BE ASSEMBLED FROM TWO HAND-READ SOURCES, BECAUSE THE
OBVIOUS ONE IS CIRCULAR. `printed-lineups.json` looks like the answer and is
not: its own `_provenance` says the `full` lineup's NAMES come from the OCR's
read of page 1 ("The opening system reads 12 of 12 -- Flauti, Oboi, ... --
which is where `full` below comes from"). Scoring the OCR against names the
OCR supplied would be the reader agreeing with itself, which is the
correlated-witness hazard in its purest form.

What IS independent, and is used here:

  STRUCTURE -- which slot each staff of a SHORT system carries -- from
  `printed-lineups.json`'s per-system suppression lists, which come from the
  hand-verified `works.json` prose ("system 2 suppresses Oboi, Trombe and
  Timpani"). A human read that off the print.

  NAMES -- from `works.json`'s own `staves[i].name`, hand-confirmed per
  entry. These are RICHER than anything the OCR produced a name for:
  `Clarinetti in B`, `Corni in Es`, `Timpani in C.G.`. A truth carrying a
  transposition the reader never read is not a copy of the reader.

So a row where the two agree is not circular.

⚠️ IT SCORES THE RESOLVED INSTRUMENT, NOT THE STRING, and that is the right
unit: the raw text reaches no consumer -- `adjudicate_instrument` puts it
through `instruments.lookup` and a label that resolves to the right
instrument has done its whole job. `Obol.` for `Oboi` is a MISREAD STRING and
a CORRECT label, and counting it as an error would measure the OCR against a
standard nothing downstream applies.

    python3 benchmarks/omr-surya-staged-cost-2026-09/probe_label_accuracy.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                        # noqa: E402

PHASE2 = REPO / "benchmarks" / "omr-part-join-phase2-2026-09"
REACH = PHASE2 / "out" / "margin-label-reach.log"
LINEUPS = PHASE2 / "printed-lineups.json"
WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"

_PAGE = re.compile(r"^page (\d+): (\d+) staves, (\d+) labels")
_STAFF = re.compile(r"^\s+staff\s+(\d+)\s+('.*?')\s+conf=(\S+)")


def read_labels() -> dict[int, dict[int, tuple[str, str]]]:
    """{page: {staff_index: (text, confidence)}} from the committed log."""
    out: dict[int, dict[int, tuple[str, str]]] = {}
    page = None
    for line in REACH.read_text().splitlines():
        m = _PAGE.match(line)
        if m:
            page = int(m.group(1))
            out[page] = {}
            continue
        m = _STAFF.match(line)
        if m and page is not None:
            out[page][int(m.group(1))] = (m.group(2).strip("'"), m.group(3))
    return out


def works_names() -> dict[str, str]:
    """Hand-confirmed instrument name per lineup slot, from works.json.

    Keyed by the lineup's own short name so the structure file can join to
    it: the two were written by different sessions and spell the slot
    differently ('Clarinetti' vs 'Clarinetti in B').
    """
    d = json.loads(WORKS.read_text())
    rows = d if isinstance(d, list) else list(
        d.get("rows", d).values() if isinstance(d.get("rows", d), dict)
        else d.get("rows", d))
    by_id = {str(r.get("row_id")): r for r in rows if isinstance(r, dict)}
    p1 = by_id["beethoven-sym5-mvt1-984073-p1"]["staves"]
    p2 = by_id["beethoven-sym5-mvt1-984073-p2"]["staves"]
    full = json.loads(LINEUPS.read_text())["full"]
    names = {short: p1[i]["name"] for i, short in enumerate(full)}
    names["Violoncello e Basso"] = p2[10]["name"]
    return names


def main() -> int:
    labels = read_labels()
    names = works_names()
    systems = json.loads(LINEUPS.read_text())["systems"]

    # A staff index in the reach log is numbered across the PAGE, not per
    # system -- so a page's systems are laid end to end in printed order.
    offset: dict[tuple[int, int], int] = {}
    seen: dict[int, int] = {}
    for s in systems:
        offset[(s["page"], s["system"])] = seen.get(s["page"], 0)
        seen[s["page"]] = seen.get(s["page"], 0) + s["staves"]

    correct = wrong = unread = 0
    rows = []
    for s in systems:
        base = offset[(s["page"], s["system"])]
        for i, slot in enumerate(s["lineup"]):
            truth_name = names.get(slot)
            t = lookup(truth_name) if truth_name else None
            truth_inst = t.instrument.name if t else None
            got = labels.get(s["page"], {}).get(base + i)
            if got is None:
                unread += 1
                continue
            text, conf = got
            m = lookup(text)
            read_inst = m.instrument.name if m else None
            ok = (read_inst is not None and read_inst == truth_inst)
            correct += ok
            wrong += (not ok)
            rows.append((s["page"], s["system"], base + i, text, conf,
                         read_inst, truth_name, truth_inst, ok))

    print("%-4s %-3s %-4s %-22s %-7s %-14s %-20s %-14s %s"
          % ("page", "sys", "st", "read text", "conf", "-> instrument",
             "hand-read truth", "-> instrument", ""))
    for r in rows:
        print("%-4s %-3s %-4s %-22s %-7s %-14s %-20s %-14s %s"
              % (r[0], r[1], r[2], repr(r[3])[:22], r[4], r[5], r[6], r[7],
                 "ok" if r[8] else "WRONG <--"))
    n = correct + wrong
    print()
    print("ACCURACY  %d labels scored: correct %d, WRONG %d  (%.1f%%)"
          % (n, correct, wrong, 100.0 * correct / n if n else 0.0))
    print("REACH     %d staves carry no read label (not scored here)" % unread)
    print()
    print("⚠️ names from works.json (hand-confirmed, carries transpositions "
          "the reader never read); structure from printed-lineups.json's "
          "hand-read suppression lists. Neither is an OCR output.")
    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
