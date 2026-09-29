import json
import sys

from tools.omr.staged import export as E, record_io
from tools.omr.staged.record import Q

label = sys.argv[1]
path = sys.argv[2]

doc = record_io.load_record(path)
rec = E.Record(doc)
n_stem = len(rec.obs_of(Q.STEM))
n_beam = len(rec.obs_of(Q.BEAM_STROKE))
beamambig = sum(1 for v in rec.verdicts_of(Q.DURATION)
                if v.get("outcome") == "narrowed"
                and v.get("reason") == "beams_ambiguous")
stems_attached_zero_beamambig = sum(
    1 for v in rec.verdicts_of(Q.DURATION)
    if v.get("outcome") == "narrowed" and v.get("reason") == "beams_ambiguous"
    and (v.get("detail") or {}).get("stems_attached") == 0)
xml, report = E.to_musicxml(doc)
written = report.get("written")
nnw = report.get("notes_not_written")
print(json.dumps({
    "label": label,
    "n_stem_rows": n_stem,
    "n_beam_rows": n_beam,
    "beamambig_narrowed": beamambig,
    "of_beamambig_stems_attached_zero": stems_attached_zero_beamambig,
    "written": written,
    "notes_not_written": nnw,
}, indent=1))
