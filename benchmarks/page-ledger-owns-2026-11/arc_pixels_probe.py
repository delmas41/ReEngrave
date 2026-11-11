"""2.284b (read only): the arc / hairpin ink claims of a gather -- strokes claimed per arm, and (ON, `OMR_PAGE_LEDGER_OWNS`) the pixel census each
claim row carries (`pixels`: own_px on the line outside every mark box, claimed_px, claimed_px_in_marks, crossing_own_px; `crossings`), with the
crossings by mark class. Pixels are the stroke map's reduced frame.

    usage: arc_pixels_probe.py RECORD [RECORD ...]
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import claim_readout as CR  # noqa: E402

for rec in sys.argv[1:]:
    src = CR.cut_record(pathlib.Path(rec))
    cls = {}
    per = collections.defaultdict(collections.Counter)
    cross_by = collections.defaultdict(collections.Counter)
    with open(src / "observations.jsonl") as fh:
        for line in fh:
            if '"glyph_box"' in line[:120]:
                o = json.loads(line)
                if isinstance(o.get("value"), list):
                    cls[o["subject"]] = o["value"][0]
    with open(src / "observations.jsonl") as fh:
        for line in fh:
            if '"claimed_area"' not in line[:200] or '"unit": "ink"' not in line:
                continue
            o = json.loads(line)
            d = o.get("detail") or {}
            own = d.get("owner")
            if own not in ("arc", "hairpin"):
                continue
            c = per[own]
            c["rows"] += 1
            c["strokes"] += len(o.get("value") or ())
            for k, v in (d.get("pixels") or {}).items():
                c[k] += int(v)
            for cr in d.get("crossings") or ():
                c["crossings"] += 1
                cross_by[own][str(cls.get(cr[3], "?"))] += 1
    print(pathlib.Path(rec).name, {k: dict(v) for k, v in per.items()}, "crossings by class:", {k: dict(v.most_common()) for k, v in cross_by.items()})
