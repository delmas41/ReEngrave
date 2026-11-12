"""ROADMAP 2.303 PART 1 probe: `gather_patient.py`, plus a log of what the OCR returned for EVERY text candidate and what the lexicon did with it.

    python3 benchmarks/dynamics-not-words-2026-11/gather_probe.py PDF --pages ... [every `tools.omr.staged` argument]   (env PROBE_OUT=FILE.json)

The record keeps only a page-level `rejected` list (`gather_direction_words`: "the split is page-level"), so the per-candidate text a lexicon refused is lost.
This wraps `direction_text.read_directions` (to read the candidate list it returns) and `direction_text.lexicon_lookup` (to log `(candidate index, text, accepted)` --
the candidate index is the loop variable `i` of the reader's own `run`). Nothing it wraps changes a value. Writes PROBE_OUT (candidates with page boxes + every
reading) when the run ends.
"""
import json
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
import tools.omr.direction_text as DT  # noqa: E402

DT.DIRECTION_CROP_TIMEOUT_S = 120.0
LOG = []          # one list per read_directions call
_cur = {"readings": []}
_orig_lookup = DT.lexicon_lookup


def _lookup(text, *a, **k):
    hit = _orig_lookup(text, *a, **k)
    f = sys._getframe(1)
    i = f.f_locals.get("i", f.f_locals.get("index"))
    _cur["readings"].append(dict(candidate=i if isinstance(i, int) else None, text=text, accepted=None if hit is None else hit.text,
                                 where=f.f_code.co_name))
    return hit


_orig_read = DT.read_directions


def _read(*a, **k):
    _cur["readings"] = []
    found, info = _orig_read(*a, **k)
    cands = [dict(i=i, staff=int(c.staff_index), measure=int(c.measure_index), box=[float(v) for v in c.bbox_page]) for i, c in enumerate(info.get("candidates") or ())]
    LOG.append(dict(candidates=cands, readings=list(_cur["readings"]), found=[dict(text=d.text, staff=int(d.staff_index), measure=int(d.measure_index), reader=d.reader) for d in found],
                    rejected=list(info.get("rejected") or ())))
    return found, info


DT.lexicon_lookup = _lookup
DT.read_directions = _read
try:
    sys.argv = ["tools.omr.staged"] + sys.argv[1:]
    runpy.run_module("tools.omr.staged", run_name="__main__")
finally:
    out = os.environ.get("PROBE_OUT")
    if out:
        with open(out, "w") as fh:
            json.dump(LOG, fh)
