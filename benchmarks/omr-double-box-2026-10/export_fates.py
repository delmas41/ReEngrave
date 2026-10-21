"""2.185: run the REAL exporter on a record (in-process, read-only) and keep its own per-subject fate (`_place_notes`' `fates`:
written / written_relocated / the refusal reason) for every notehead and rest box. usage: export_fates.py RECORD.json OUTDIR
Changes no code: it wraps `export.marks_census` to copy the `fates` dict it is handed, and writes the MusicXML beside it."""
import json, sys, os, pathlib
sys.path.insert(0, ".")
from tools.omr.staged import export as X
from tools.omr.staged.record_io import load_record
rec, outdir = sys.argv[1:3]
os.makedirs(outdir, exist_ok=True)
cap = {}
orig = X.marks_census
def wrap(r, fates):
    cap["fates"] = dict(fates)
    return orig(r, fates)
X.marks_census = wrap
result = load_record(rec)
xml, report = X.to_musicxml(result)
pathlib.Path(outdir, "out.musicxml").write_text(xml)
json.dump(cap.get("fates", {}), open(os.path.join(outdir, "fates.json"), "w"))
json.dump(report.get("marks_census"), open(os.path.join(outdir, "marks_census.json"), "w"))
print("fates", len(cap.get("fates", {})), "xml bytes", len(xml))
