"""ROADMAP 2.141 -- why W2 (`ledger_owner_aware`) failed on Litolff tiles 6 and 10: per-bar cause features
and the cause tests, on a saved record, in process. DIAGNOSIS ONLY: no product code, no flag.

PATH: STAGED INFER (inferences.solve_bare_stem_bar, rule collapse_narrowed_by_bar) reading the
ADJUDICATE verdicts the record holds.

    python3 causes_2_141.py RECORD CELLS.json OUT.json [--label lit|brah]

CELLS.json is a list of {"cell": [page, system, staff, cell], "tag": "..."}. The record is loaded once
via record_io.load_record (never read raw), its GATHER rows rebuilt and its OWN verdicts inserted as
written, frozen (step 2's way, `step2_2_136.py`). For each cell:
  - the rule's own function runs with OMR_INFER_CARRIED_METER_FIX=1 (what W2 settles) and again with
    `consequences._left_the_bar` patched to ALSO take a box whose DECIDED `notehead_is_a_whole_rest` is
    true out of the bar (the what-if for cause W; nothing is written anywhere);
  - the cause tests below are evaluated from the verdicts.

CAUSE TESTS (all read the record; none reads the print):
  W  a note of the bar sum (DECIDED or NARROWED duration, not left the bar) whose glyph carries a DECIDED
     Q.NOTEHEAD_IS_A_WHOLE_REST == True. EXPORT refuses that box (`ink_is_a_whole_rest`); the INFER sum counts it.
  U  a standing duration of the bar that is ABSTAINED (not left the bar): an element nobody sized, which the
     bar sum skips as if it held no time (a whole rest abstained `rest_stands_where_no_rest_hangs`, a note abstained).
  S  a DECIDED note of the bar with beam_levels >= 1 whose only beam evidence is the detector's box
     (cv_beams == 0, yolo_kept >= 1) -- no CV stroke, so no ink witness read it (a slur drawn as a beam box).
  T  a member or decided neighbour whose head carries a stem each way (HEAD_STEM_REACH 'both', head_stem
     `unison_two_voices`, or `beam_voices` set): two voices share a head and the beam levels were counted per voice.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("cells")
    ap.add_argument("out")
    a = ap.parse_args()

    from tools.omr.staged import consequences as C
    from tools.omr.staged import infer as INF
    from tools.omr.staged import inferences as INFS
    from tools.omr.staged.record import (Candidate, Kind, Outcome, Q, Subject, Verdict)
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    for v in rec.get("verdicts") or ():
        cands = tuple(Candidate(value=c["value"], support=c.get("support", 0.0))
                      for c in v.get("candidates") or ())
        vv = Verdict(
            id=v["id"], subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
            outcome=Outcome(v["outcome"]), value=v.get("value"), decider=v["decider"], reason=v["reason"],
            considered=tuple(v.get("considered") or ()), used=tuple(v.get("used") or ()),
            missing=tuple(v.get("missing") or ()), declined=tuple(v.get("declined") or ()),
            excluded=tuple(tuple(e) for e in v.get("excluded") or ()),
            correlated=tuple(frozenset(g) for g in v.get("correlated") or ()),
            basis=tuple(v.get("basis") or ()), candidates=cands, margin=v.get("margin"),
            supersedes=v.get("supersedes"), detail=dict(v.get("detail") or {}))
        log._vrd[vv.id] = vv
        log._index(vv.quantity, vv.subject, vv.id)
    del doc, rec
    log.freeze()
    say("log built")

    real_left = C._left_the_bar

    def left_plus_whole_rest_ink(lg, glyph):
        why = real_left(lg, glyph)
        if why is not None:
            return why
        wr = lg.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, glyph)
        if wr is not None and wr.outcome is Outcome.DECIDED and wr.value is True:
            return wr
        return None

    def solve(cell, patched):
        os.environ[INF.CARRIED_METER_FIX_ENV] = "1"
        C._left_the_bar = left_plus_whole_rest_ink if patched else real_left
        try:
            o = INFS.solve_bare_stem_bar(log, cell, any_reason=True)
        finally:
            C._left_the_bar = real_left
        props = {p.subject.glyph: [(p.value or {}).get("beats"), (p.value or {}).get("beam_levels")]
                 for p in (o.proposals or [])}
        return {"decline": o.decline, "landings": o.landings, "settled": props,
                "ambiguous": o.ambiguous, "members": o.members}

    jobs = json.load(open(a.cells))
    rows = []
    for job in jobs:
        p, s, st, c = job["cell"]
        cell = Subject(Kind.CELL, page=p, system=s, staff=st, cell=c)
        elems = []
        for v in C._standing(log, cell, Q.DURATION):
            g = v.subject
            left = real_left(log, g)
            wr = log.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, g)
            reach = log.rows(Q.HEAD_STEM_REACH, g)
            hs = log.verdict(Q.HEAD_STEM, g)
            d = v.detail or {}
            box = C._page_box(log, g)
            e = {
                "glyph": g.glyph, "outcome": v.outcome.value, "reason": v.reason,
                "is_rest": bool(C._is_rest(v)),
                "beats": (v.value or {}).get("beats") if isinstance(v.value, dict) else None,
                "beam_levels": (v.value or {}).get("beam_levels") if isinstance(v.value, dict) else None,
                "cand": [[(c.value or {}).get("beats"), (c.value or {}).get("beam_levels")]
                         for c in v.candidates if isinstance(c.value, dict)],
                "left_the_bar": left.quantity if left is not None else None,
                "whole_rest_ink": (wr.value if (wr is not None and wr.outcome is Outcome.DECIDED) else None),
                "reach": reach[-1].value if reach else None,
                "head_stem_reason": hs.reason if hs is not None else None,
                "cv_beams": d.get("cv_beams"), "yolo_kept": d.get("yolo_kept"),
                "beam_voices": d.get("beam_voices"), "beam_side": d.get("beam_side"),
                "levels_certain": d.get("levels_certain"), "levels_possible": d.get("levels_possible"),
                "certain_conflicts": d.get("certain_conflicts"),
                "box": box,
            }
            elems.append(e)
        voices = log.verdict(Q.VOICES, cell)
        live = [e for e in elems if e["left_the_bar"] is None]
        notes = [e for e in live if e["outcome"] in ("decided", "narrowed")]
        W = [e["glyph"] for e in notes if e["whole_rest_ink"] is True]
        U = [e["glyph"] for e in live if e["outcome"] == "abstained"]
        S = [e["glyph"] for e in notes if e["outcome"] == "decided" and not e["is_rest"]
             and (e["beam_levels"] or 0) >= 1 and (e["cv_beams"] or 0) == 0 and (e["yolo_kept"] or 0) >= 1]
        T = [e["glyph"] for e in notes if not e["is_rest"] and
             (e["reach"] == "both" or e["head_stem_reason"] == "unison_two_voices" or e["beam_voices"])]
        row = {"cell": job["cell"], "tag": job.get("tag"),
               "voices": ({"n": (voices.value or {}).get("n_voices"), "why": voices.reason}
                          if voices is not None and isinstance(voices.value, dict) else None),
               "W": W, "U": U, "S": S, "T": T,
               "w2_as_written": solve(cell, False), "whatif_whole_rest_ink_out": solve(cell, True),
               "elems": elems}
        rows.append(row)
        say(f"{job['cell']} W={W} U={U} S={S} T={T} "
            f"as_written={row['w2_as_written']['settled']} whatif={row['whatif_whole_rest_ink_out']['decline'] or row['whatif_whole_rest_ink_out']['settled']}")
    Path(a.out).write_text(json.dumps(rows, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
