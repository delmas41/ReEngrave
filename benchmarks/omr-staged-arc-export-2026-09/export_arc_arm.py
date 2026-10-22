"""Do the arcs reach the file, and what does the report say did not?

⚠️ ONE GATHER, EXPORTED TWICE -- `reexport_arm.py`'s discipline: the transcribe
half is held byte-identical, so the two arms differ only in the exporter. The
OFF arm is produced by removing the pairing pass, which reproduces the state
this session found -- `arc_kind` and `arc_owner` deciding, `grep '<slur'`
returning zero.

⚠️⚠️ WHAT THIS IS BLIND TO. It compares two EXPORTS over one fixed record, so
it cannot see a GATHER change -- and this session made one (`Q.CELL_BOX`). A
record gathered before that quantity existed carries no cell boxes, every bar
reports `arc_bar_has_no_geometry`, and the ON arm writes NOTHING while looking
like it ran. The `--check-gather` guard below refuses such a record outright,
because a zero that means "you fed me the wrong file" and a zero that means
"the exporter is broken" are indistinguishable in the output.

    python3 export_arc_arm.py <staged.json>
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402


def main() -> int:
    result = json.load(open(sys.argv[1]))
    rec = SX.Record(result)

    # ── the guard, before any number ────────────────────────────────────────
    n_cell_box = len(rec.obs_of(Q.CELL_BOX))
    n_arc = len(rec.obs_of(Q.ARC_BOX))
    print(f"record: {n_arc} arc_box rows, {n_cell_box} cell_box rows")
    if n_arc and not n_cell_box:
        print("!! this record predates Q.CELL_BOX — re-gather before reading "
              "any number below. STOP.")
        return 2

    xml, rep = SX.to_musicxml(result)
    w = rep["written"]
    print(f"\nON : <slur> {xml.count('<slur ')}  <tied> {xml.count('<tied ')}"
          f"  slurs {w.get('slurs', 0)}  ties {w.get('ties', 0)}")
    print(f"     notes {w.get('notes', 0)}  rests {w.get('rests', 0)}"
          f"  parts {w['parts']}")
    print(f"     arcs not written ({rep['arcs_not_written_total']}): "
          f"{rep['arcs_not_written']}")
    print(f"     balance: {rep['balance']['balanced']}")

    # ── the OFF arm: the exporter as this session found it ──────────────────
    keep = SX._pair_arcs
    SX._pair_arcs = lambda parts, counters: {}
    try:
        off_xml, off_rep = SX.to_musicxml(result)
    finally:
        SX._pair_arcs = keep
    print(f"\nOFF: <slur> {off_xml.count('<slur ')}  "
          f"<tied> {off_xml.count('<tied ')}")

    # ⚠️ THE CONTROL THAT MAKES THE ABOVE A RESULT. Strip the arc elements from
    # the ON arm and the two files must be IDENTICAL: anything else means the
    # pass moved a note, a rest or a bar, which it has no business doing.
    # ⚠️ THE EMPTY WRAPPER COUNTS AS AN ARC ELEMENT. `_mxl_note` opens a
    # `<notations>` block only when the note has something to put in it, so
    # removing the `<slur>` leaves `<notations></notations>` behind and the
    # naive strip reports the two files as DIFFERENT -- which it did, on the
    # first run, and the diff was 206 lines of exactly that and nothing else.
    # A control that flags its own artefact as a defect trains its reader to
    # ignore it.
    import re
    def strip(s):
        s = re.sub(r'\s*<(slur|tie|tied)\b[^>]*/>', '', s)
        return re.sub(r'\s*<notations>\s*</notations>', '', s)
    same = strip(xml) == strip(off_xml)
    print(f"\noutside the arc elements, the two files are "
          f"{'IDENTICAL' if same else 'DIFFERENT — INVESTIGATE'}")
    print(f"notes  ON {w.get('notes',0)} vs OFF {off_rep['written'].get('notes',0)}")
    print(f"rests  ON {w.get('rests',0)} vs OFF {off_rep['written'].get('rests',0)}")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
